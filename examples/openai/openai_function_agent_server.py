#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
OpenAI Function Calling Agent 服务器示例

此示例演示如何使用OpenAI的function calling功能创建一个agent，
并通过A2A SDK将其转换为A2A协议兼容的服务器。

使用方法:
1. 安装必要的依赖：pip install -r requirements-examples.txt
2. 设置OPENAI_API_KEY环境变量或在.env文件中配置
3. 运行: python openai_function_agent_server.py
"""

import os
import json
import logging
import asyncio
import dotenv
from pathlib import Path
from typing import AsyncIterable, List, Dict, Any, Optional, Union, Tuple, Callable, AsyncGenerator

import openai
from openai import OpenAI
from a2a.server import A2AServer, InMemoryTaskManager
from a2a.server.types import Agent
from a2a.server.response_processor import ResponseProcessor, DefaultResponseProcessor
from a2a.types import (
    AgentCard, AgentProvider, AgentCapabilities, AgentAuthentication, AgentSkill,
    Task, TaskStatus, TaskState, Message, TextPart, Artifact,
    SendTaskRequest, SendTaskResponse, 
    SendTaskStreamingRequest, SendTaskStreamingResponse,
    TaskStatusUpdateEvent, TaskArtifactUpdateEvent,
    JSONRPCResponse, InternalError
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 尝试加载.env文件中的环境变量
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    logger.info(f"检测到.env文件，正在加载环境变量...")
    dotenv.load_dotenv(env_path)

# 获取OpenAI配置
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")

# 检查是否有有效的API密钥
USE_REAL_OPENAI = bool(OPENAI_API_KEY)
if USE_REAL_OPENAI:
    logger.info(f"检测到OpenAI API配置，将使用真实OpenAI API。")
    logger.info(f"模型: {OPENAI_MODEL}")
    if OPENAI_API_BASE:
        logger.info(f"API Base: {OPENAI_API_BASE}")
else:
    logger.info("未检测到有效的OpenAI API配置，将使用模拟代理。")

# 定义可用函数
AVAILABLE_FUNCTIONS = {
    "get_weather": {
        "description": "获取指定城市的天气信息",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，如'北京'、'上海'等"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "温度单位"
                }
            },
            "required": ["city"]
        }
    },
    "get_current_time": {
        "description": "获取当前时间",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "时区，如'Asia/Shanghai'、'America/New_York'等"
                }
            },
            "required": []
        }
    }
}

# 实现函数执行逻辑
def get_weather(city: str, unit: str = "celsius") -> str:
    """模拟获取天气信息"""
    # 实际应用中，这里应该调用真实的天气API
    weather_data = {
        "北京": {"temp": 20, "condition": "晴天"},
        "上海": {"temp": 25, "condition": "多云"},
        "广州": {"temp": 30, "condition": "雨"}
    }
    
    if city not in weather_data:
        return f"抱歉，没有找到{city}的天气信息。"
    
    temp = weather_data[city]["temp"]
    if unit == "fahrenheit":
        temp = temp * 9/5 + 32
    
    return f"{city}现在{weather_data[city]['condition']}，温度{temp}{'°C' if unit == 'celsius' else '°F'}"

def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """获取当前时间"""
    # 实际应用中，应该根据时区返回对应的时间
    from datetime import datetime
    return f"当前时间是：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ({timezone})"

# OpenAI函数调用的同步实现
def openai_function_invoke(input: str, session_id: str = None, history: Optional[List[Dict[str, Any]]] = None, temperature: float = 0.7, **kwargs) -> str:
    """同步调用OpenAI API进行函数调用"""
    try:
        client_args = {"api_key": OPENAI_API_KEY}
        if OPENAI_API_BASE:
            client_args["base_url"] = OPENAI_API_BASE
            
        client = OpenAI(**client_args)
        
        # 准备消息列表
        messages = []
        
        # 如果有历史记录，加入历史消息
        if history and isinstance(history, list):
            for msg in history:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    messages.append({"role": msg["role"], "content": msg["content"]})
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": input})
        
        model = kwargs.get("model", OPENAI_MODEL)
        logger.info(f"使用模型 {model} 处理请求")
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[
                {"type": "function", "function": {"name": name, **func}}
                for name, func in AVAILABLE_FUNCTIONS.items()
            ],
            tool_choice="auto",
            temperature=temperature
        )
        
        message = response.choices[0].message
        
        # 检查是否有函数调用
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            logger.info(f"模型调用函数: {function_name}({function_args})")
            
            # 执行函数调用
            if function_name == "get_weather":
                result = get_weather(**function_args)
            elif function_name == "get_current_time":
                result = get_current_time(**function_args)
            else:
                result = f"未知函数: {function_name}"
            
            # 添加助手消息和工具响应
            messages.append(message.model_dump())
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })
            
            # 将函数结果提供给模型生成最终回复
            final_response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            )
            
            return final_response.choices[0].message.content
        
        # 如果没有函数调用，返回原始响应
        return message.content
        
    except Exception as e:
        logger.error(f"调用OpenAI API时出错: {e}")
        raise

# OpenAI函数调用的异步流式实现
async def openai_function_stream(input: str, session_id: str = None, history: Optional[List[Dict[str, Any]]] = None, temperature: float = 0.7, **kwargs) -> AsyncIterable[str]:
    """异步流式调用OpenAI API进行函数调用 (简化版)"""
    # 注意：此实现是简化的，实际上OpenAI的流式函数调用更复杂
    # 这里我们把非流式版本的结果切分为几个部分来模拟流式响应
    try:
        full_response = openai_function_invoke(
            input=input, 
            session_id=session_id, 
            history=history if isinstance(history, list) else None,
            temperature=temperature, 
            model=kwargs.get("model", OPENAI_MODEL)
        )
        # 简单地将响应分成几个块
        chunk_size = max(len(full_response) // 5, 1)
        chunks = [full_response[i:i+chunk_size] for i in range(0, len(full_response), chunk_size)]
        
        # 模拟流式传输延迟
        for chunk in chunks:
            await asyncio.sleep(0.1)  # 模拟网络延迟
            yield chunk
        
    except Exception as e:
        logger.error(f"流式调用OpenAI API时出错: {e}")
        raise

# 添加自定义响应处理器
class CustomResponseProcessor(ResponseProcessor):
    """自定义响应处理器，专门处理代理的流式输出"""
    
    def __init__(self):
        """初始化自定义响应处理器"""
        self._accumulated_text = ""
        self._chunk_counter = 0
    
    def process_response(self, response: Any) -> Tuple[TaskState, Optional[Message], Optional[List[Artifact]]]:
        """处理同步响应"""
        from a2a.types import Message, Artifact, TaskState, TextPart
        
        if isinstance(response, str):
            text = response
            parts = [TextPart(type="text", text=text)]
            message = Message(role="agent", parts=parts)
            artifact = Artifact(parts=parts)
            return TaskState.COMPLETED, message, [artifact]
        else:
            # 尝试字符串化处理
            try:
                text = str(response)
                parts = [TextPart(type="text", text=text)]
                message = Message(role="agent", parts=parts)
                artifact = Artifact(parts=parts)
                return TaskState.COMPLETED, message, [artifact]
            except:
                # 无法处理的响应类型
                parts = [TextPart(type="text", text="无法处理的响应类型")]
                message = Message(role="agent", parts=parts)
                return TaskState.COMPLETED, message, None
    
    async def process_stream_item(self, stream_item: Any) -> Tuple[TaskState, Optional[Message], Optional[List[Artifact]], bool]:
        """处理流式项目"""
        from a2a.types import Message, Artifact, TaskState, TextPart
        
        try:
            # 流式处理单个字符
            self._accumulated_text += stream_item
            self._chunk_counter += 1
            
            logger.info(f"处理流式项目: '{stream_item}', 累积: '{self._accumulated_text}'")
            
            # 创建消息和工件
            parts = [TextPart(type="text", text=self._accumulated_text)]
            message = Message(role="agent", parts=parts)
            
            # 每个字符都是一个工件，所以不需要记录先前的值
            artifact = Artifact(
                name="streaming_response",
                parts=[TextPart(type="text", text=stream_item)],
                index=self._chunk_counter,
                append=True
            )
            
            # 检查是否是句子结束，以决定是否是最终状态
            is_final = stream_item in ['.', '!', '?', '。', '！', '？'] and len(self._accumulated_text) > 10
            
            return TaskState.WORKING, message, [artifact], is_final
            
        except Exception as e:
            logger.error(f"处理流式项目时出错: {e}")
            parts = [TextPart(type="text", text=f"处理流式项目出错: {str(e)}")]
            message = Message(role="agent", parts=parts)
            return TaskState.WORKING, message, None, False

# 添加一个直接实现Agent接口的类，绕过GenericAgent的类型问题
class DirectMockAgent:
    """直接实现Agent接口，而不使用GenericAgent工厂方法"""
    
    def __init__(self):
        """初始化模拟代理"""
        self._content_types = ["text/plain"]
    
    def invoke(self, input: str, session_id: str, history: Optional[List[Dict[str, Any]]] = None, **kwargs) -> str:
        """同步调用模拟代理"""
        from datetime import datetime
        
        responses = {
            "北京今天天气怎么样？": "北京今天天气晴朗，温度约为20°C，适合户外活动。",
            "现在几点了？": "当前时间是：" + datetime.now().strftime("%H:%M:%S"),
            "你好": "你好！我是模拟OpenAI代理。有什么可以帮助你的吗？",
        }
        
        # 对于未预设的问题，返回默认回复
        response = responses.get(input, f"您问的是：{input}。我是模拟代理，无法提供真实回答。")
        logger.info(f"模拟代理响应: {response}")
        return response
    
    async def stream(self, input: str, session_id: str, history: Optional[List[Dict[str, Any]]] = None, **kwargs) -> AsyncIterable[str]:
        """异步流式调用模拟代理
        
        直接返回一个异步生成器，符合A2A框架的要求
        为简化起见，直接逐字符返回，让response_processor处理格式转换
        """
        response = self.invoke(input, session_id, history, **kwargs)
        logger.info(f"模拟流式代理开始处理: {response}")
        
        # 最简单的流式返回：每个字符都作为一个单独的流式项
        for char in response:
            await asyncio.sleep(0.1)  # 增加延迟，便于观察
            logger.info(f"流式输出字符: {char}")
            yield char
    
    @property
    def supported_content_types(self) -> List[str]:
        """返回支持的内容类型"""
        return self._content_types

# 实现真实OpenAI代理接口类
class RealOpenAIAgent:
    """使用真实OpenAI API的代理实现"""
    
    def __init__(self):
        """初始化OpenAI代理"""
        self._content_types = ["text/plain"]
    
    def invoke(self, input: str, session_id: str, history: Optional[List[Dict[str, Any]]] = None, **kwargs) -> str:
        """同步调用OpenAI API"""
        return openai_function_invoke(input, session_id, history, **kwargs)
    
    async def stream(self, input: str, session_id: str, history: Optional[List[Dict[str, Any]]] = None, **kwargs) -> AsyncIterable[str]:
        """异步流式调用OpenAI API"""
        # 使用已有的流式函数实现
        async for chunk in openai_function_stream(input, session_id, history, **kwargs):
            yield chunk
    
    @property
    def supported_content_types(self) -> List[str]:
        """返回支持的内容类型"""
        return self._content_types

def main():
    # 创建Agent Card描述
    agent_card = AgentCard(
        name="OpenAI Function Agent",
        description="一个使用OpenAI function calling功能的智能助手",
        url="http://localhost:5003",
        provider=AgentProvider(
            organization="Example Org",
            url="https://example.org"
        ),
        version="1.0.0",
        capabilities=AgentCapabilities(
            streaming=True,
            pushNotifications=False,
            stateTransitionHistory=False
        ),
        authentication=None,
        skills=[
            AgentSkill(
                id="weather",
                name="天气查询",
                description="提供特定城市的天气信息",
                examples=["北京今天天气怎么样？", "上海的温度是多少？"]
            ),
            AgentSkill(
                id="time",
                name="时间查询",
                description="提供当前时间信息",
                examples=["现在几点了？", "告诉我当前的时间"]
            )
        ]
    )
    
    # 根据配置选择使用真实API还是模拟代理
    if USE_REAL_OPENAI:
        agent = RealOpenAIAgent()
        logger.info("使用实际的OpenAI API...")
    else:
        agent = DirectMockAgent()
        logger.info("使用模拟代理...")
    
    # 创建自定义响应处理器
    response_processor = CustomResponseProcessor()
    
    # 创建InMemoryTaskManager，并配置Agent和响应处理器
    task_manager = InMemoryTaskManager()
    # 为InMemoryTaskManager的委托DefaultTaskManager配置Agent和响应处理器
    task_manager._delegate.agent = agent
    task_manager._delegate.response_processor = response_processor
    
    # 创建A2A服务器
    server = A2AServer(
        host="0.0.0.0",
        port=5003,  # 修改为不同端口，避免冲突
        agent_card=agent_card,
        task_manager=task_manager
    )
    
    logger.info("启动OpenAI Function Agent服务器，监听端口5003...")
    server.start()

if __name__ == "__main__":
    main() 