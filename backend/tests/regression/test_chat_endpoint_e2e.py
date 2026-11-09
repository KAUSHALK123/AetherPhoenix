from fastapi.testclient import TestClient
from app.main import app
from shared.contracts.planner import PlannerResponse

client = TestClient(app)


def test_plain_chat_message_hello():
    """
    Sends a plain chat message 'hello' through the full FastAPI request path
    and asserts that it returns 200 OK and a valid PlannerResponse with no exceptions.
    """
    response = client.post(
        "/api/v1/planner/generate",
        json={"goal": "hello"},
    )
    assert response.status_code == 200
    data = response.json()

    # Validate against Pydantic model
    parsed = PlannerResponse.model_validate(data)
    assert parsed.status == "chat"
    assert parsed.reply is not None
    assert "AetherPhoenix" in parsed.reply
    assert parsed.action == "reply"
    assert parsed.options is None


def test_plain_chat_conversational_queries():
    """
    Tests various plain conversational messages like 'who are you?' or 'help'
    to ensure conversational fast-path does not fail or raise tuple errors.
    """
    for msg in ["hi", "who are you?", "what can you do?", "help"]:
        response = client.post(
            "/api/v1/planner/generate",
            json={"goal": msg},
        )
        assert response.status_code == 200
        data = response.json()
        parsed = PlannerResponse.model_validate(data)
        assert parsed.status == "chat"
        assert parsed.reply is not None
        assert len(parsed.reply) > 0


def test_chat_message_directory_inspection():
    """
    Tests an inspection chat message through the full request path.
    """
    response = client.post(
        "/api/v1/planner/generate",
        json={"goal": "what folders are in d drive"},
    )
    assert response.status_code == 200
    data = response.json()
    parsed = PlannerResponse.model_validate(data)
    assert parsed.status == "ready"
    assert parsed.action == "execute_plan"
