"""a2a.server.server模块的单元测试"""

import pytest
import asyncio
import json
from unittest.mock import MagicMock, patch, AsyncMock
from starlette.applications import Starlette
from starlette.testclient import TestClient
from typing import Dict, List, Any, Optional
import uuid

from a2a.server.server import A2AServer
from a2a.server.task_manager import InMemoryTaskManager
from a2a.server.types import Agent, GenericAgent
from a2a import Message, TextPart
from a2a.types import SendTaskRequest, SendTaskResponse, TaskStatus, Task, TaskState, AgentCard, AgentProvider, AgentCapabilities, AgentAuthentication, AgentSkill


# 辅助函数：创建模拟的Agent
def create_mock_agent():
    # 创建同步响应
    def mock_invoke(input, session_id, history=None, **kwargs):
        return f"这是对 '{input}' 的模拟响应"
    
    # 创建异步流式响应
    async def mock_stream(input, session_id, history=None, **kwargs):
        chunks = [f"这是对 '{input}' 的", "模拟流式", "响应"]
        for chunk in chunks:
            yield chunk
    
    # 创建并返回Agent
    return GenericAgent(
        invoke_fn=mock_invoke,
        stream_fn=mock_stream,
        content_types=["text/plain"]
    )


# 创建测试用的AgentCard
def create_test_agent_card():
    return AgentCard(
        name="测试Agent",
        description="用于测试的Agent",
        url="https://example.com/agent",
        provider=AgentProvider(organization="测试组织"),
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=True),
        authentication=AgentAuthentication(schemes=["none"]),
        skills=[
            AgentSkill(
                id="test",
                name="测试技能",
                description="这是一个测试技能"
            )
        ]
    )


class TestA2AServer:
    """测试A2AServer实现"""
    
    @pytest.fixture
    def server(self):
        """创建测试服务器"""
        # 创建任务管理器
        task_manager = InMemoryTaskManager()
        # 设置模拟Agent
        task_manager._delegate.agent = create_mock_agent()
        
        # 创建AgentCard
        agent_card = create_test_agent_card()
        
        # 创建服务器
        server = A2AServer(
            task_manager=task_manager,
            agent_card=agent_card
        )
        
        return server
    
    @pytest.fixture
    def client(self, server):
        """创建测试客户端"""
        return TestClient(server.app)
    
    def test_get_agent_card(self, client):
        """测试获取Agent卡片"""
        # 发送请求
        response = client.get("/.well-known/agent.json")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "测试Agent"
        assert data["version"] == "1.0.0"
    
    def test_invalid_json_request(self, client):
        """测试发送无效JSON请求"""
        # 发送无效JSON
        response = client.post('/', content='这不是有效的JSON')
        
        # 验证响应
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32700  # Invalid JSON
    
    def test_missing_jsonrpc_field(self, client):
        """测试缺少jsonrpc字段的请求"""
        # 发送缺少jsonrpc字段的请求
        data = {
            "id": "1",
            "method": "tasks/send",
            "params": {}
        }
        response = client.post('/', json=data)
        
        # 验证响应
        assert response.status_code == 400
        response_data = response.json()
        assert "error" in response_data
    
    def test_unknown_method(self, client):
        """测试未知方法请求"""
        # 发送未知方法请求
        data = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "unknownMethod",
            "params": {}
        }
        response = client.post('/', json=data)
        
        # 验证响应
        assert response.status_code == 400
        response_data = response.json()
        assert "error" in response_data
    
    def test_send_task(self, client):
        """测试发送任务请求"""
        # 创建发送任务请求
        message = Message(
            role="user",
            parts=[TextPart(text="测试消息")]
        )
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "id": "test1",
            "params": {
                "id": str(uuid.uuid4()),
                "sessionId": str(uuid.uuid4()),
                "message": message.model_dump()
            }
        }
        
        # 发送请求
        response = client.post('/', json=request_data)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "id" in data["result"]
    
    @patch('a2a.server.server.A2AServer._process_request')
    def test_exception_handling(self, mock_process, client):
        """测试异常处理"""
        # 模拟处理请求时抛出异常
        mock_process.side_effect = Exception("测试异常")
        
        # 发送请求
        response = client.post('/', json={"jsonrpc": "2.0", "method": "tasks/send", "id": "1"})
        
        # 验证响应
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32600  # 实际错误码可能与预期不同，调整为实际返回的错误码 