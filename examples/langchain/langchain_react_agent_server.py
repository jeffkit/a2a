#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LangChain ReAct Agent 服务器示例

此示例演示如何使用LangChain创建一个ReAct agent，
并通过A2A SDK将其转换为A2A协议兼容的服务器。

使用方法:
1. 安装必要的依赖：pip install -r requirements-examples.txt
2. 设置OPENAI_API_KEY环境变量
3. 运行: python langchain_react_agent_server.py
"""

import os
import logging
import asyncio
import dotenv
from pathlib import Path
from typing import AsyncIterable, List, Dict, Any, Optional, Tuple

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.tools import Tool

from a2a.server import A2AServer, InMemoryTaskManager
from a2a.server.types import Agent
from a2a.server.response_processor import ResponseProcessor, DefaultResponseProcessor
from a2a.types import (
    AgentCard, AgentProvider, AgentCapabilities, AgentSkill,
    Message, TextPart, Artifact, TaskState
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 尝试加载.env文件中的环境变量
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    logger.info(f"检测到.env文件，正在加载环境变量...")
    dotenv.load_dotenv(env_path)

# 确保有API密钥
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")

if not OPENAI_API_KEY:
    raise ValueError("请设置OPENAI_API_KEY环境变量")

logger.info(f"检测到OpenAI API配置，将使用OpenAI API。")
logger.info(f"模型: {OPENAI_MODEL}")

# 定义工具函数
def get_weather(location: str) -> str:
    """获取指定位置的天气信息"""
    # 在实际应用中，此处应调用真实的天气API
    weather_data = {
        "北京": "晴天，温度20°C",
        "上海": "多云，温度25°C",
        "广州": "雨，温度30°C",
        "深圳": "多云，温度28°C",
        "杭州": "阴天，温度22°C"
    }
    return weather_data.get(location, f"没有找到{location}的天气信息")

def calculate(expression: str) -> str:
    """计算数学表达式"""
    try:
        # 使用eval需要小心，实际生产环境应当使用更安全的方法
        result = eval(expression)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"

# 创建LangChain工具
weather_tool = Tool(
    name="天气查询",
    func=get_weather,
    description="获取指定城市的天气信息。输入应该是城市名称，如'北京'、'上海'等。"
)

calculator_tool = Tool(
    name="计算器",
    func=calculate,
    description="进行数学计算。输入应该是一个数学表达式，如'2 + 2'或'3 * 4'等。"
)

# 创建系统提示
SYSTEM_PROMPT = """你是一个智能助手，你可以使用以下工具来回答用户的问题：

工具:
- 天气查询: 获取特定城市的天气信息
- 计算器: 执行数学计算

在回答问题时，请先考虑是否需要使用工具，然后按照以下步骤思考：
1. 首先确定是否需要使用工具
2. 如果需要，选择合适的工具并正确使用
3. 根据工具结果提供完整的回答
"""

# 添加自定义响应处理器
class CustomResponseProcessor(ResponseProcessor):
    """自定义响应处理器，专门处理代理的流式输出"""
    
    def __init__(self):
        """初始化自定义响应处理器"""
        self._accumulated_text = ""
        self._chunk_counter = 0
    
    def process_response(self, response: Any) -> Tuple[TaskState, Optional[Message], Optional[List[Artifact]]]:
        """处理同步响应"""
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

# 直接实现Agent接口的LangChain ReAct Agent
class LangChainReActAgent:
    """直接实现Agent接口的LangChain ReAct Agent"""
    
    def __init__(self, default_params: Dict[str, Any] = None):
        """初始化LangChain ReAct Agent"""
        self._content_types = ["text/plain"]
        self._default_params = default_params or {
            "temperature": 0.0,
            "model": OPENAI_MODEL,
            "verbose": True
        }
    
    def invoke(self, input: str, session_id: str, history: Optional[List[Dict[str, Any]]] = None, **kwargs) -> str:
        """同步调用LangChain ReAct Agent"""
        try:
            # 合并默认参数和传入参数
            params = {**self._default_params, **kwargs}
            
            # 创建LLM
            llm = ChatOpenAI(
                model=params.get("model", OPENAI_MODEL),
                temperature=params.get("temperature", 0.0),
                api_key=OPENAI_API_KEY
            )
            
            # 创建工具列表
            tools = [weather_tool, calculator_tool]
            
            # 创建提示模板
            prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])
            
            # 创建ReAct代理
            agent = create_react_agent(llm, tools, prompt)
            
            # 创建Agent执行器
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=params.get("verbose", True),
                handle_parsing_errors=True
            )
            
            # 准备对话历史
            chat_history = []
            if history:
                for msg in history:
                    if msg["role"] == "user":
                        chat_history.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        chat_history.append(AIMessage(content=msg["content"]))
            
            # 执行代理
            response = agent_executor.invoke({
                "input": input,
                "chat_history": chat_history
            })
            
            return response["output"]
            
        except Exception as e:
            logger.error(f"调用LangChain Agent时出错: {e}")
            raise
    
    async def stream(self, input: str, session_id: str, history: Optional[List[Dict[str, Any]]] = None, **kwargs) -> AsyncIterable[str]:
        """异步流式调用LangChain ReAct Agent"""
        try:
            # 合并默认参数和传入参数
            params = {**self._default_params, **kwargs}
            
            # 创建流式LLM
            llm = ChatOpenAI(
                model=params.get("model", OPENAI_MODEL),
                temperature=params.get("temperature", 0.0),
                api_key=OPENAI_API_KEY,
                streaming=True
            )
            
            # 创建工具列表
            tools = [weather_tool, calculator_tool]
            
            # 创建提示模板
            prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])
            
            # 创建ReAct代理
            agent = create_react_agent(llm, tools, prompt)
            
            # 创建代理执行器
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=params.get("verbose", True),
                handle_parsing_errors=True
            )
            
            # 准备对话历史
            chat_history = []
            if history:
                for msg in history:
                    if msg["role"] == "user":
                        chat_history.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        chat_history.append(AIMessage(content=msg["content"]))
            
            # 创建一个队列用于消息传递
            message_queue = asyncio.Queue()
            collected_text = []
            
            # 自定义callback处理器
            class StreamingCallbackHandler:
                def __init__(self):
                    self.buffer = ""
                
                async def on_llm_new_token(self, token: str, **kwargs):
                    self.buffer += token
                    asyncio.run_coroutine_threadsafe(
                        message_queue.put(token),
                        asyncio.get_event_loop()
                    )
            
            # 启动代理（在线程中运行）
            agent_task = asyncio.create_task(
                asyncio.to_thread(
                    agent_executor.invoke,
                    {
                        "input": input, 
                        "chat_history": chat_history
                    },
                    {"callbacks": [StreamingCallbackHandler()]}
                )
            )
            
            # 处理流式消息
            timeout = 120  # 秒
            end_time = asyncio.get_event_loop().time() + timeout
            
            while not agent_task.done() or not message_queue.empty():
                # 检查是否超时
                now = asyncio.get_event_loop().time()
                if now > end_time:
                    break
                    
                try:
                    # 从队列获取消息，有超时时间
                    token = await asyncio.wait_for(message_queue.get(), 1.0)
                    collected_text.append(token)
                    yield token
                    
                except asyncio.TimeoutError:
                    # 队列获取超时，继续循环
                    pass
                    
            # 等待Agent任务完成
            if not agent_task.done():
                agent_task.cancel()
                try:
                    await agent_task
                except asyncio.CancelledError:
                    pass
                    
            # 如果没有收集到任何文本，至少返回一个默认消息
            if not collected_text:
                yield "没有生成回复"
                
        except Exception as e:
            logger.error(f"流式调用LangChain Agent时出错: {e}")
            raise
    
    @property
    def supported_content_types(self) -> List[str]:
        """返回支持的内容类型"""
        return self._content_types

def main():
    # 创建Agent Card描述
    agent_card = AgentCard(
        name="LangChain ReAct Agent",
        description="使用LangChain框架实现的ReAct思维模式代理",
        url="http://localhost:5001",
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
                examples=["北京今天天气怎么样？", "告诉我上海的天气"]
            ),
            AgentSkill(
                id="calculator",
                name="数学计算",
                description="执行数学计算",
                examples=["计算123乘以456", "5的平方根是多少？"]
            )
        ]
    )
    
    # 创建LangChain ReAct Agent
    agent = LangChainReActAgent()
    
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
        port=5001,  # 使用不同端口，以便与其他示例并行运行
        agent_card=agent_card,
        task_manager=task_manager
    )
    
    logger.info("启动LangChain ReAct Agent服务器，监听端口5001...")
    server.start()

if __name__ == "__main__":
    main() 