"""Intent parsing using deterministic rules with optional low-confidence LLM fallback."""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib import error, request

import yaml

from cloudpilot.intent.schema import IntentObject

ALLOWED_USE_CASES = {"static_website", "containerized_app", "database"}
ALLOWED_TIERS = {"low", "medium", "high"}
ALLOWED_CLOUDS = {"aws", "gcp", "digitalocean"}

FALLBACK_PROMPT = """
Extract deployment intent from this message. Return ONLY valid JSON.
Message: "{user_input}"

Return:
{{
  "use_case": "static_website|containerized_app|database|unknown",
  "traffic_tier": "low|medium|high|unknown",
  "cloud": "aws|gcp|digitalocean|unknown",
  "confidence": 0.0-1.0
}}
""".strip()


def _rules_path() -> Path:
    return Path(__file__).with_name("rules.yaml")


@lru_cache(maxsize=1)
def _load_rules() -> dict[str, dict[str, list[str]]]:
    with _rules_path().open("r", encoding="utf-8") as handle:
        rules = yaml.safe_load(handle) or {}
    if not isinstance(rules, dict):
        raise ValueError("rules.yaml must contain a dictionary at the root.")
    return rules


def _looks_like_regex(pattern: str) -> bool:
    return any(char in pattern for char in ("\\", "[", "]", "(", ")", "?", "+", "*", "^", "$", "|"))


def _matches_pattern(text: str, pattern: str) -> bool:
    if _looks_like_regex(pattern):
        return re.search(pattern, text, flags=re.IGNORECASE) is not None

    escaped = re.escape(pattern.strip())
    if " " in pattern.strip():
        return pattern.lower() in text.lower()
    return re.search(rf"\b{escaped}\b", text, flags=re.IGNORECASE) is not None


def _best_rule_match(text: str, field_rules: dict[str, list[str]]) -> str:
    best_label = ""
    best_score = 0

    for label, patterns in field_rules.items():
        score = sum(1 for pattern in patterns if _matches_pattern(text, pattern))
        if score > best_score:
            best_score = score
            best_label = label

    return best_label


def _extract_by_rules(text: str) -> dict[str, str]:
    rules = _load_rules()
    return {
        "use_case": _best_rule_match(text, rules.get("use_case", {})),
        "traffic_tier": _best_rule_match(text, rules.get("traffic_tier", {})),
        "cloud": _best_rule_match(text, rules.get("cloud", {})),
    }


def _normalize_choice(value: Any, allowed: set[str]) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip().lower()
    if normalized == "unknown":
        return ""
    return normalized if normalized in allowed else ""


def _extract_json_block(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}

    candidate = text[start : end + 1]
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _http_json_post(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(body).encode("utf-8")
    req = request.Request(url=url, data=payload, headers=headers, method="POST")
    with request.urlopen(req, timeout=8) as response:
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, dict) else {}


def _fallback_with_openai(prompt: str) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return {}

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    body = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "You extract structured intent from user deployment text."},
            {"role": "user", "content": prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = _http_json_post("https://api.openai.com/v1/chat/completions", headers, body)
    choices = response.get("choices", [])
    if not choices:
        return {}
    message = choices[0].get("message", {})
    content = message.get("content", "")
    return _extract_json_block(content)


def _fallback_with_gemini(prompt: str) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return {}

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0},
    }
    headers = {"Content-Type": "application/json"}

    response = _http_json_post(url, headers, body)
    candidates = response.get("candidates", [])
    if not candidates:
        return {}

    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        return {}
    content = parts[0].get("text", "")
    return _extract_json_block(content)


def _mock_llm_response() -> dict[str, Any]:
    raw = os.getenv("LLM_MOCK_RESPONSE", "").strip()
    if not raw:
        return {}
    return _extract_json_block(raw)


def _llm_fallback(text: str) -> dict[str, Any]:
    mode = os.getenv("LLM_FALLBACK_MODE", "mock").strip().lower()
    if mode in {"mock", "disabled", "off"}:
        return _mock_llm_response()

    prompt = FALLBACK_PROMPT.format(user_input=text)
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()

    try:
        if provider == "gemini":
            return _fallback_with_gemini(prompt)
        return _fallback_with_openai(prompt)
    except (error.URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError, IndexError):
        return {}


def parse(text: str) -> IntentObject:
    """Parse user text into a partial IntentObject with confidence score."""
    raw_input = text or ""
    clean_text = raw_input.strip()

    if not clean_text:
        return IntentObject(raw_input=raw_input, confidence=0.0)

    extracted = _extract_by_rules(clean_text)
    matched_fields = sum(1 for value in extracted.values() if value)
    confidence = matched_fields / 3.0

    result = {
        "use_case": extracted.get("use_case", ""),
        "traffic_tier": extracted.get("traffic_tier", ""),
        "cloud": extracted.get("cloud", ""),
        "confidence": confidence,
    }

    if confidence < 0.7:
        llm_result = _llm_fallback(clean_text)
        llm_use_case = _normalize_choice(llm_result.get("use_case"), ALLOWED_USE_CASES)
        llm_tier = _normalize_choice(llm_result.get("traffic_tier"), ALLOWED_TIERS)
        llm_cloud = _normalize_choice(llm_result.get("cloud"), ALLOWED_CLOUDS)

        if not result["use_case"] and llm_use_case:
            result["use_case"] = llm_use_case
        if not result["traffic_tier"] and llm_tier:
            result["traffic_tier"] = llm_tier
        if not result["cloud"] and llm_cloud:
            result["cloud"] = llm_cloud

        llm_confidence = llm_result.get("confidence")
        if isinstance(llm_confidence, (int, float)):
            bounded = max(0.0, min(float(llm_confidence), 1.0))
            result["confidence"] = max(result["confidence"], bounded)

    return IntentObject(
        use_case=result["use_case"],
        traffic_tier=result["traffic_tier"],
        cloud=result["cloud"],
        raw_input=raw_input,
        confidence=result["confidence"],
    )
