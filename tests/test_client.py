import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from a2a.client import A2AClient
from a2a.types import (
    AgentCard,
    SendTaskResponse,
    Task,
    TaskStatus,
    TaskState,
    Message,
    TextPart,
)


@pytest.fixture
def mock_client():
    agent_card = AgentCard(
        name="Test Agent",
        url="http://example.com/agent",
        version="1.0.0",
        capabilities=MagicMock(),
        skills=[MagicMock()],
    )
    return A2AClient(agent_card=agent_card)


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_send_task(mock_post, mock_client):
    # 准备模拟响应
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "id": "test-id",
        "result": {
            "id": "task-123",
            "status": {
                "state": "completed",
                "timestamp": "2023-07-01T12:00:00Z",
            },
        },
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    # 调用测试方法
    payload = {
        "id": "task-123",
        "message": Message(
            role="user", parts=[TextPart(text="Hello, world!")]
        ).model_dump(),
    }
    response = await mock_client.send_task(payload)

    # 验证结果
    assert isinstance(response, SendTaskResponse)
    assert response.result.id == "task-123"
    assert response.result.status.state == TaskState.COMPLETED

    # 验证 post 被正确调用
    mock_post.assert_called_once_with(
        "http://example.com/agent", json=pytest.approx(dict), timeout=30
    ) 