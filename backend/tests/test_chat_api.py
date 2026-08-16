from fastapi.testclient import TestClient

from tests.conftest import FakeAnthropicClient


def _register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={"emailAddress": email, "fullName": "Taylor Client", "password": "super-secret-1"},
    )
    assert response.status_code == 201
    return response.json()


def test_visitor_can_send_a_message_without_auth(
    client: TestClient, fake_anthropic_client: FakeAnthropicClient
) -> None:
    response = client.post(
        "/api/chat/messages",
        json={"messages": [{"role": "user", "content": "What services do you offer?"}]},
    )

    assert response.status_code == 200
    assert response.json()["message"] == fake_anthropic_client.messages.reply


def test_authenticated_user_reply_uses_their_token(
    client: TestClient, fake_anthropic_client: FakeAnthropicClient
) -> None:
    registered = _register(client, "taylor@example.com")
    token = registered["accessToken"]

    response = client.post(
        "/api/chat/messages",
        json={"messages": [{"role": "user", "content": "When is my meeting?"}]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    system_prompt = fake_anthropic_client.messages.last_kwargs["system"]
    assert "Taylor Client" in system_prompt


def test_message_requires_at_least_one_turn(client: TestClient) -> None:
    response = client.post("/api/chat/messages", json={"messages": []})

    assert response.status_code == 422


def test_page_context_is_forwarded(
    client: TestClient, fake_anthropic_client: FakeAnthropicClient
) -> None:
    response = client.post(
        "/api/chat/messages",
        json={
            "messages": [{"role": "user", "content": "Tell me about this page"}],
            "pageContext": "Blog post: Why Website Maintenance Matters",
        },
    )

    assert response.status_code == 200
    system_prompt = fake_anthropic_client.messages.last_kwargs["system"]
    assert "Blog post: Why Website Maintenance Matters" in system_prompt


def test_returns_503_when_assistant_not_configured(client: TestClient) -> None:
    from site_api.api.dependencies import get_chat_service
    from site_api.services.chat import ChatService

    unconfigured_service = ChatService(None, None, None, None, "claude-opus-5")  # type: ignore[arg-type]
    client.app.dependency_overrides[get_chat_service] = lambda: unconfigured_service

    response = client.post(
        "/api/chat/messages",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )

    assert response.status_code == 503
    del client.app.dependency_overrides[get_chat_service]
