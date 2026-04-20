"""Conversation state machine implementation with deterministic skip logic."""

from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from cloudpilot.intent.parser import parse
from cloudpilot.intent.schema import IntentObject

QUESTION_STATES = ("ASK_USECASE", "ASK_SCALE", "ASK_CLOUD", "ASK_REGION")
TERMINAL_STATES = {"DEPLOYING", "DONE"}
FIELD_BY_STATE = {
    "ASK_USECASE": "use_case",
    "ASK_SCALE": "traffic_tier",
    "ASK_CLOUD": "cloud",
    "ASK_REGION": "region",
}


def _questions_path() -> Path:
    return Path(__file__).with_name("questions.yaml")


def _load_questions() -> dict[str, Any]:
    with _questions_path().open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("questions.yaml must contain a dictionary at the root.")
    return data


def _default_project_name(session_id: str) -> str:
    token = "".join(char for char in session_id if char.isalnum()).lower()
    suffix = token[:8] if token else "session"
    return f"deployment-{suffix}"


class ConversationSession:
    """State machine session for gathering missing deployment intent fields."""

    def __init__(
        self,
        session_id: str,
        intent: IntentObject | None = None,
    ) -> None:
        self.session_id = session_id
        self.intent = intent or IntentObject()
        if not self.intent.project_name:
            self.intent.project_name = _default_project_name(session_id)

        self._questions = _load_questions()
        self.current_state = "INIT"
        self._advance_to_next_state()

    @classmethod
    def from_user_input(cls, session_id: str, user_input: str) -> "ConversationSession":
        """Create a session prefilled from parser output to enable skip logic."""
        parsed_intent = parse(user_input)
        parsed_intent.raw_input = user_input
        return cls(session_id=session_id, intent=parsed_intent)

    def next_question(self) -> dict[str, Any] | None:
        """Return the current question definition or None if no question is pending."""
        if self.current_state in TERMINAL_STATES:
            return None

        question = self._questions.get(self.current_state)
        if not isinstance(question, dict):
            return None

        return {
            "state": self.current_state,
            "prompt": question.get("prompt", ""),
            "options": question.get("options", []),
        }

    def answer(self, value: str) -> None:
        """Apply an answer to the current state and move to the next state."""
        if self.current_state in TERMINAL_STATES:
            raise ValueError(f"Cannot answer while session is in terminal state {self.current_state}.")

        clean_value = value.strip()
        if not clean_value:
            raise ValueError("Answer value cannot be empty.")

        if self.current_state in FIELD_BY_STATE:
            setattr(self.intent, FIELD_BY_STATE[self.current_state], clean_value)
            self._advance_to_next_state()
            return

        if self.current_state == "CONFIRM":
            normalized = clean_value.lower()
            if normalized == "confirm":
                self.current_state = "DEPLOYING"
                return
            if normalized == "edit":
                self._reset_editable_fields()
                self._advance_to_next_state()
                return
            raise ValueError("Confirm state accepts only 'confirm' or 'edit'.")

        raise ValueError(f"Unsupported state transition from {self.current_state}.")

    def is_ready(self) -> bool:
        """Return True when required deployment fields are available."""
        return all(
            [
                bool(self.intent.use_case),
                bool(self.intent.traffic_tier),
                bool(self.intent.cloud),
                bool(self.intent.region),
                bool(self.intent.project_name),
            ]
        )

    def mark_done(self) -> None:
        """Mark session as completed after deployment workflow finishes."""
        self.current_state = "DONE"

    def snapshot(self) -> dict[str, Any]:
        """Return a serializable view of session state and intent fields."""
        return {
            "session_id": self.session_id,
            "current_state": self.current_state,
            "ready": self.is_ready(),
            "intent": asdict(self.intent),
        }

    def _advance_to_next_state(self) -> None:
        for state in QUESTION_STATES:
            field_name = FIELD_BY_STATE[state]
            if not getattr(self.intent, field_name):
                self.current_state = state
                return
        self.current_state = "CONFIRM"

    def _reset_editable_fields(self) -> None:
        self.intent.use_case = ""
        self.intent.traffic_tier = ""
        self.intent.cloud = ""
        self.intent.region = ""
