"""a2a.server.response_processor模块的单元测试"""

import pytest
import json
from unittest.mock import MagicMock, patch

from a2a.server.response_processor import ResponseProcessor, DefaultResponseProcessor
from a2a import Message, TextPart
from a2a.types import Artifact, TaskState


class TestDefaultResponseProcessor:
    """测试DefaultResponseProcessor实现"""
    
    @pytest.fixture
    def processor(self):
        """创建ResponseProcessor测试实例"""
        return DefaultResponseProcessor()
    
    def test_process_text_response(self, processor):
        """测试处理文本响应"""
        # 准备测试数据
        text_response = "这是一个文本响应"
        
        # 处理响应
        result = processor.process_response(text_response)
        
        # 检查结果类型，返回格式为(TaskState, Message, List[Artifact])
        assert len(result) == 3
        state, message, artifacts = result
        
        # 验证状态
        assert isinstance(state, TaskState)
        assert state == TaskState.COMPLETED
        
        # 验证消息
        assert isinstance(message, Message)
        assert message.role == "agent"
        assert message.parts[0].text == "这是一个文本响应"
        
        # 验证制品
        assert isinstance(artifacts, list)
        assert len(artifacts) == 1
        assert isinstance(artifacts[0], Artifact)
        assert artifacts[0].parts[0].text == "这是一个文本响应"

    def test_process_json_response(self, processor):
        """测试处理JSON响应"""
        # 准备JSON测试数据
        json_data = {"result": "success", "items": [1, 2, 3]}
        json_response = json.dumps(json_data)
        
        # 处理响应
        result = processor.process_response(json_response)
        
        # 解构结果
        state, message, artifacts = result
        
        # 验证状态
        assert state == TaskState.COMPLETED
        
        # 验证消息
        assert message.role == "agent"
        assert json.loads(message.parts[0].text) == json_data
        
        # 验证制品
        assert len(artifacts) == 1
        assert json.loads(artifacts[0].parts[0].text) == json_data

    @pytest.mark.asyncio
    async def test_process_stream_item(self, processor):
        """测试处理流式响应项"""
        # 准备测试数据
        stream_item = {
            "content": "流式响应片段",
            "is_task_complete": False,
            "require_user_input": False
        }
        
        # 处理流式响应
        result = await processor.process_stream_item(stream_item)
        
        # 解构结果
        state, message, artifacts, is_complete = result
        
        # 验证状态
        assert state == TaskState.WORKING
        
        # 验证消息
        assert message.role == "agent"
        assert message.parts[0].text == "流式响应片段"
        
        # 验证未完成标志
        assert is_complete is False
        
        # 验证没有制品
        assert artifacts is None 