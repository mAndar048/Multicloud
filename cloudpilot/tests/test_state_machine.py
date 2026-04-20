import pytest

from cloudpilot.conversation.state_machine import ConversationSession
from cloudpilot.intent.schema import IntentObject


def test_session_starts_at_first_missing_state() -> None:
    session = ConversationSession(session_id="abc123")

    question = session.next_question()

    assert question is not None
    assert question["state"] == "ASK_USECASE"
    assert session.intent.project_name.startswith("deployment-")


def test_skip_logic_for_prefilled_fields() -> None:
    intent = IntentObject(
        use_case="static_website",
        traffic_tier="low",
        cloud="aws",
        project_name="demo",
    )
    session = ConversationSession(session_id="s-1", intent=intent)

    question = session.next_question()

    assert question is not None
    assert question["state"] == "ASK_REGION"


def test_confirm_flow_transitions_to_deploying() -> None:
    session = ConversationSession(session_id="session-1")
    session.answer("static_website")
    session.answer("low")
    session.answer("aws")
    session.answer("us-east-1")

    assert session.is_ready() is True
    assert session.current_state == "CONFIRM"

    confirm_question = session.next_question()
    assert confirm_question is not None
    assert confirm_question["state"] == "CONFIRM"

    session.answer("confirm")

    assert session.current_state == "DEPLOYING"
    assert session.next_question() is None


def test_confirm_rejects_invalid_value() -> None:
    intent = IntentObject(
        use_case="static_website",
        traffic_tier="low",
        cloud="aws",
        region="us-east-1",
        project_name="demo",
    )
    session = ConversationSession(session_id="s-2", intent=intent)

    with pytest.raises(ValueError, match="confirm"):
        session.answer("yes")


def test_from_user_input_prefills_from_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    from cloudpilot.conversation import state_machine

    def fake_parse(text: str) -> IntentObject:
        return IntentObject(
            use_case="static_website",
            traffic_tier="low",
            cloud="aws",
            raw_input=text,
            confidence=0.9,
        )

    monkeypatch.setattr(state_machine, "parse", fake_parse)

    session = state_machine.ConversationSession.from_user_input(
        session_id="prefill-1",
        user_input="deploy a website on aws for 500 users",
    )

    question = session.next_question()

    assert question is not None
    assert question["state"] == "ASK_REGION"
