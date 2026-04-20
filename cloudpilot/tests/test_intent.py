import pytest

from cloudpilot.intent import parser


def test_parse_preserves_raw_input() -> None:
    text = "deploy website"
    intent = parser.parse(text)
    assert intent.raw_input == text


def test_detects_static_website_use_case() -> None:
    intent = parser.parse("Deploy a website for my team")
    assert intent.use_case == "static_website"


def test_detects_containerized_app_use_case() -> None:
    intent = parser.parse("I need a docker backend service")
    assert intent.use_case == "containerized_app"


def test_detects_database_use_case() -> None:
    intent = parser.parse("Provision a mysql database")
    assert intent.use_case == "database"


def test_detects_aws_cloud() -> None:
    intent = parser.parse("Use ec2 for this deployment")
    assert intent.cloud == "aws"


def test_detects_gcp_cloud() -> None:
    intent = parser.parse("Host this on cloud run")
    assert intent.cloud == "gcp"


def test_detects_digitalocean_cloud() -> None:
    intent = parser.parse("Deploy on digitalocean")
    assert intent.cloud == "digitalocean"


def test_does_not_false_match_do_word_fragment() -> None:
    intent = parser.parse("I am doing a website experiment")
    assert intent.cloud == ""


def test_detects_low_tier_with_user_count_regex() -> None:
    intent = parser.parse("website for 200 users on aws")
    assert intent.traffic_tier == "low"


def test_detects_medium_tier_with_user_count_regex() -> None:
    intent = parser.parse("container app for 5000 users")
    assert intent.traffic_tier == "medium"


def test_detects_high_tier_with_large_scale_keyword() -> None:
    intent = parser.parse("enterprise database platform")
    assert intent.traffic_tier == "high"


def test_detects_high_tier_with_numeric_regex() -> None:
    intent = parser.parse("api for 250000 users")
    assert intent.traffic_tier == "high"


def test_confidence_is_full_when_three_fields_match() -> None:
    intent = parser.parse("deploy website on aws for 500 users")
    assert intent.use_case == "static_website"
    assert intent.cloud == "aws"
    assert intent.traffic_tier == "low"
    assert intent.confidence == 1.0


def test_confidence_is_partial_for_two_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parser, "_llm_fallback", lambda _text: {})
    intent = parser.parse("deploy website on aws")
    assert intent.use_case == "static_website"
    assert intent.cloud == "aws"
    assert intent.traffic_tier == ""
    assert intent.confidence == pytest.approx(2 / 3)


def test_fallback_invoked_for_low_confidence(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    def fake_fallback(_text: str) -> dict:
        called["value"] = True
        return {
            "use_case": "unknown",
            "traffic_tier": "medium",
            "cloud": "gcp",
            "confidence": 0.9,
        }

    monkeypatch.setattr(parser, "_llm_fallback", fake_fallback)
    intent = parser.parse("please help")

    assert called["value"] is True
    assert intent.traffic_tier == "medium"
    assert intent.cloud == "gcp"
    assert intent.confidence == 0.9


def test_fallback_not_invoked_when_confidence_high(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called(_text: str) -> dict:
        raise AssertionError("fallback should not be called")

    monkeypatch.setattr(parser, "_llm_fallback", fail_if_called)
    parser.parse("deploy website on aws for 500 users")


def test_fallback_only_fills_missing_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        parser,
        "_llm_fallback",
        lambda _text: {
            "use_case": "database",
            "traffic_tier": "medium",
            "cloud": "gcp",
            "confidence": 0.95,
        },
    )
    intent = parser.parse("website")

    assert intent.use_case == "static_website"
    assert intent.traffic_tier == "medium"
    assert intent.cloud == "gcp"


def test_empty_input_short_circuit(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    def fake_fallback(_text: str) -> dict:
        called["value"] = True
        return {}

    monkeypatch.setattr(parser, "_llm_fallback", fake_fallback)
    intent = parser.parse("   ")

    assert intent.use_case == ""
    assert intent.cloud == ""
    assert intent.traffic_tier == ""
    assert intent.confidence == 0.0
    assert called["value"] is False


def test_mock_mode_uses_mock_response_without_live_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_FALLBACK_MODE", "mock")
    monkeypatch.setenv(
        "LLM_MOCK_RESPONSE",
        '{"use_case":"unknown","traffic_tier":"medium","cloud":"gcp","confidence":0.88}',
    )

    def fail_if_called(_prompt: str) -> dict:
        raise AssertionError("live provider should not be called in mock mode")

    monkeypatch.setattr(parser, "_fallback_with_openai", fail_if_called)
    monkeypatch.setattr(parser, "_fallback_with_gemini", fail_if_called)

    intent = parser.parse("help me deploy something")

    assert intent.traffic_tier == "medium"
    assert intent.cloud == "gcp"
    assert intent.confidence == 0.88
