"""a2a.server.types模块的单元测试"""

import asyncio
import pytest
from typing import List, Dict, Any, AsyncIterable

from a2a.server.types import Agent, GenericAgent


async def async_gen_wrapper(items):
    """辅助函数，将列表转换为异步迭代器"""
    for item in items:
        yield item


class TestAgent:
    """测试Agent基类和工厂方法"""
    
    def test_agent_factory_creation(self):
        """测试使用工厂方法创建Agent实例"""
        # 准备测试数据
        mock_invoke_result = "Hello, World!"
        mock_stream_results = ["Hello, ", "World", "!"]
        
        # 创建模拟函数
        def mock_invoke(input, session_id, history=None, **kwargs):
            return mock_invoke_result
            
        async def mock_stream(input, session_id, history=None, **kwargs):
            return async_gen_wrapper(mock_stream_results)
        
        # 使用工厂方法创建Agent
        agent = Agent.create(
            invoke_fn=mock_invoke,
            stream_fn=mock_stream,
            content_types=["text/plain", "application/json"]
        )
        
        # 验证Agent类型和属性
        assert isinstance(agent, GenericAgent)
        assert agent.supported_content_types == ["text/plain", "application/json"]
        
        # 验证调用结果
        result = agent.invoke("Test input", "session123")
        assert result == mock_invoke_result
        
        # 验证流式调用结果
        stream_result = asyncio.run(self._collect_stream_results(agent, "Test input", "session123"))
        assert stream_result == mock_stream_results
    
    async def _collect_stream_results(self, agent, input_text, session_id):
        """辅助方法：收集异步迭代器的所有结果"""
        results = []
        async for item in await agent.stream(input_text, session_id):
            results.append(item)
        return results


class TestGenericAgent:
    """测试GenericAgent实现"""
    
    def test_invoke_without_agent_instance(self):
        """测试不使用agent_instance的invoke调用"""
        # 准备测试数据
        test_input = "Test input"
        test_session = "session456"
        test_history = [{"role": "user", "content": "Previous message"}]
        expected_result = "Expected response"
        
        # 创建跟踪调用参数的模拟函数
        call_args = {}
        def mock_invoke(**kwargs):
            nonlocal call_args
            call_args = kwargs
            return expected_result
        
        # 创建Agent实例
        agent = GenericAgent(invoke_fn=mock_invoke)
        
        # 调用并验证结果
        result = agent.invoke(test_input, test_session, test_history)
        assert result == expected_result
        
        # 验证传递给invoke_fn的参数
        assert call_args["input"] == test_input
        assert call_args["session_id"] == test_session
        assert call_args["history"] == test_history
    
    def test_invoke_with_agent_instance(self):
        """测试使用agent_instance的invoke调用"""
        # 准备测试数据和mock对象
        class MockAgentInstance:
            def invoke_method(self, input, session_id, history=None, **kwargs):
                return f"Response to: {input}"
        
        mock_instance = MockAgentInstance()
        
        # 创建Agent实例
        agent = GenericAgent(
            invoke_fn=MockAgentInstance.invoke_method,
            agent_instance=mock_instance
        )
        
        # 调用并验证结果
        result = agent.invoke("Hello", "session789")
        assert result == "Response to: Hello"
    
    def test_invoke_with_custom_mapper(self):
        """测试使用自定义参数映射器的invoke调用"""
        # 准备测试数据
        def custom_mapper(input, session_id, history, kwargs):
            return {
                "prompt": input,
                "conversation_id": session_id,
                "messages": history,
                "extra": kwargs.get("temperature", 0.7)
            }
        
        def mock_invoke(prompt, conversation_id, messages=None, extra=None):
            return f"Prompt: {prompt}, ID: {conversation_id}, Extra: {extra}"
        
        # 创建Agent实例
        agent = GenericAgent(
            invoke_fn=mock_invoke,
            invoke_params_mapper=custom_mapper
        )
        
        # 调用并验证结果
        result = agent.invoke("Custom input", "custom_session", temperature=0.9)
        assert "Prompt: Custom input" in result
        assert "ID: custom_session" in result
        assert "Extra: 0.9" in result
    
    @pytest.mark.asyncio
    async def test_stream_functionality(self):
        """测试stream方法的基本功能"""
        # 准备测试数据
        expected_items = ["Part 1", "Part 2", "Part 3"]
        
        async def mock_stream_fn(input, session_id, history=None, **kwargs):
            return async_gen_wrapper(expected_items)
        
        # 创建Agent实例
        agent = GenericAgent(stream_fn=mock_stream_fn)
        
        # 调用stream方法
        stream_gen = await agent.stream("Stream input", "stream_session")
        
        # 收集并验证结果
        results = []
        async for item in stream_gen:
            results.append(item)
        
        assert results == expected_items
    
    def test_supported_content_types(self):
        """测试supported_content_types属性"""
        # 准备测试数据
        content_types = ["text/markdown", "image/png"]
        
        # 创建Agent实例
        agent = GenericAgent(content_types=content_types)
        
        # 验证属性值
        assert agent.supported_content_types == content_types
    
    def test_missing_functions_raise_error(self):
        """测试缺少必要函数时抛出适当的错误"""
        # 创建没有invoke_fn的Agent
        agent_without_invoke = GenericAgent(stream_fn=lambda: None)
        
        # 验证调用invoke时抛出ValueError
        with pytest.raises(ValueError, match="Invoke function is not set"):
            agent_without_invoke.invoke("Test", "session")
        
        # 创建没有stream_fn的Agent
        agent_without_stream = GenericAgent(invoke_fn=lambda: None)
        
        # 验证调用stream时抛出ValueError
        with pytest.raises(ValueError, match="Stream function is not set"):
            asyncio.run(agent_without_stream.stream("Test", "session")) 