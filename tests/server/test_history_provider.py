"""a2a.server.history_provider模块的单元测试"""

import pytest
import uuid
from typing import List, Dict, Any

from a2a.server.history_provider import (
    ConversationHistoryProvider, 
    InMemoryHistoryProvider,
    extract_text_from_message
)
from a2a import Message, TextPart


class TestExtractTextFromMessage:
    """测试extract_text_from_message工具函数"""
    
    def test_extract_text_from_message_with_text_parts_only(self):
        """测试从仅包含文本部分的消息提取文本"""
        # 创建测试消息
        message = Message(
            role="user",
            parts=[
                TextPart(text="第一部分"),
                TextPart(text="第二部分")
            ]
        )
        
        # 提取文本
        text = extract_text_from_message(message)
        
        # 验证结果
        assert text == "第一部分 第二部分"
    
    def test_extract_text_from_message_with_empty_content(self):
        """测试从空内容的消息提取文本"""
        # 创建没有内容的消息
        message = Message(
            role="user",
            parts=[]
        )
        
        # 提取文本
        text = extract_text_from_message(message)
        
        # 验证结果
        assert text == ""
    
    def test_extract_text_from_message_with_dict_content(self):
        """测试从字典格式内容的消息提取文本"""
        # 创建带有字典格式内容的消息
        message_dict = {
            "role": "user",
            "parts": [{"type": "text", "text": "直接文本内容"}]
        }
        message = Message.model_validate(message_dict)
        
        # 提取文本
        text = extract_text_from_message(message)
        
        # 验证结果
        assert text == "直接文本内容"


class TestInMemoryHistoryProvider:
    """测试InMemoryHistoryProvider实现"""
    
    @pytest.fixture
    def provider(self):
        """创建历史提供器测试实例"""
        return InMemoryHistoryProvider()
    
    @pytest.mark.asyncio
    async def test_add_get_message(self, provider):
        """测试添加和获取消息"""
        # 准备测试数据
        session_id = str(uuid.uuid4())
        user_message = Message(
            role="user",
            parts=[TextPart(text="用户消息")]
        )
        
        # 添加消息
        await provider.add_message(session_id, user_message)
        
        # 获取会话历史记录
        history = await provider.get_history(session_id)
        
        # 验证结果
        assert len(history) == 1
        assert history[0].role == "user"
        assert isinstance(history[0].parts[0], TextPart)
        assert history[0].parts[0].text == "用户消息"
    
    @pytest.mark.asyncio
    async def test_get_history_with_nonexistent_session(self, provider):
        """测试获取不存在会话的历史记录"""
        # 获取不存在会话的历史记录
        history = await provider.get_history("nonexistent_session")
        
        # 验证结果
        assert isinstance(history, list)
        assert len(history) == 0
    
    @pytest.mark.asyncio
    async def test_get_history_with_limit(self, provider):
        """测试获取有限数量的历史记录"""
        # 准备测试数据
        session_id = str(uuid.uuid4())
        
        # 添加多条消息
        for i in range(5):
            await provider.add_message(session_id, Message(
                role="user" if i % 2 == 0 else "agent",
                parts=[TextPart(text=f"消息 {i}")]
            ))
        
        # 获取有限数量的历史记录
        history = await provider.get_history(session_id, 3)
        
        # 验证结果
        assert len(history) == 3
        assert history[0].parts[0].text == "消息 2"
        assert history[1].parts[0].text == "消息 3"
        assert history[2].parts[0].text == "消息 4"
    
    @pytest.mark.asyncio
    async def test_clear_history(self, provider):
        """测试清除历史记录"""
        # 准备测试数据
        session_id = str(uuid.uuid4())
        
        # 添加消息
        await provider.add_message(session_id, Message(
            role="user",
            parts=[TextPart(text="测试消息")]
        ))
        
        # 验证消息已添加
        history = await provider.get_history(session_id)
        assert len(history) == 1
        
        # 清除历史记录
        await provider.clear_history(session_id)
        
        # 验证历史记录已清除
        history = await provider.get_history(session_id)
        assert len(history) == 0
    
    @pytest.mark.asyncio
    async def test_multiple_sessions(self, provider):
        """测试多个会话的独立性"""
        # 准备测试数据
        session1 = str(uuid.uuid4())
        session2 = str(uuid.uuid4())
        
        # 向不同会话添加消息
        await provider.add_message(session1, Message(
            role="user",
            parts=[TextPart(text="会话1的消息")]
        ))
        
        await provider.add_message(session2, Message(
            role="agent",
            parts=[TextPart(text="会话2的消息")]
        ))
        
        # 获取会话1的历史记录
        history1 = await provider.get_history(session1)
        assert len(history1) == 1
        assert history1[0].parts[0].text == "会话1的消息"
        
        # 获取会话2的历史记录
        history2 = await provider.get_history(session2)
        assert len(history2) == 1
        assert history2[0].parts[0].text == "会话2的消息"
        
        # 清除一个会话的历史记录
        await provider.clear_history(session1)
        
        # 验证只有目标会话被清除
        assert len(await provider.get_history(session1)) == 0
        assert len(await provider.get_history(session2)) == 1 