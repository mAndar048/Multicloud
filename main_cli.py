"""CLI runner for exercising the CloudPilot conversation state machine."""

from uuid import uuid4

from cloudpilot.conversation.state_machine import ConversationSession


def _resolve_answer(options: list[dict], user_input: str) -> str:
    raw = user_input.strip()
    if not options:
        return raw

    if raw.isdigit():
        index = int(raw) - 1
        if 0 <= index < len(options):
            return str(options[index]["value"])

    valid_values = {str(option["value"]) for option in options}
    if raw in valid_values:
        return raw

    raise ValueError("Invalid option. Enter a number or one of the listed values.")


def main() -> None:
    print("CloudPilot CLI")
    user_input = input("Describe what you want to deploy: ").strip()

    session = ConversationSession.from_user_input(
        session_id=str(uuid4()),
        user_input=user_input,
    )

    while True:
        question = session.next_question()
        if question is None:
            break

        print(f"\n[{question['state']}] {question['prompt']}")
        options = question.get("options", [])
        for idx, option in enumerate(options, start=1):
            print(f"  {idx}. {option['label']} ({option['value']})")

        while True:
            user_answer = input("> ")
            try:
                answer_value = _resolve_answer(options, user_answer)
                session.answer(answer_value)
                break
            except ValueError as exc:
                print(str(exc))

    print("\nSession snapshot:")
    print(session.snapshot())


if __name__ == "__main__":
    main()
