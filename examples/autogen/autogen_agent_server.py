#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AutoGen Agent 服务器示例

此示例演示如何使用AutoGen创建一个智能代理，
并通过A2A SDK将其转换为A2A协议兼容的服务器。

使用方法:
1. 安装必要的依赖：pip install -r requirements-examples.txt
2. 设置OPENAI_API_KEY环境变量
3. 运行: python autogen_agent_server.py
"""

import os
import logging
import asyncio
import json
import dotenv
from pathlib import Path
from typing import AsyncIterable, List, Dict, Any, Union, Optional, Tuple

import autogen
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json

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
env_path = Path(__file__).parent.parent / '.env'
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

# 为AutoGen创建一个结果收集器
class AutoGenCollector:
    def __init__(self):
        self.messages = []
        self.system_messages = []
        self.last_message = None
    
    def collect(self, message):
        """收集消息"""
        # 过滤系统消息
        if message.get("role") == "system":
            self.system_messages.append(message.get("content", ""))
            return
        
        # 存储普通消息
        self.messages.append(message.get("content", ""))
        self.last_message = message.get("content", "")

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
            # 流式处理单个字符或块
            self._accumulated_text += stream_item
            self._chunk_counter += 1
            
            logger.info(f"处理流式项目: '{stream_item[:20]}...' (长度{len(stream_item)}), 累积: '{self._accumulated_text[:20]}...'")
            
            # 创建消息和工件
            parts = [TextPart(type="text", text=self._accumulated_text)]
            message = Message(role="agent", parts=parts)
            
            # 每个片段都是一个工件，不需要记录先前的值
            artifact = Artifact(
                name="streaming_response",
                parts=[TextPart(type="text", text=stream_item)],
                index=self._chunk_counter,
                append=True
            )
            
            # 检查是否是消息结束，以决定是否是最终状态
            is_final = stream_item.strip().endswith(('.', '!', '?', '。', '！', '？')) and len(self._accumulated_text) > 50
            
            return TaskState.WORKING, message, [artifact], is_final
            
        except Exception as e:
            logger.error(f"处理流式项目时出错: {e}")
            parts = [TextPart(type="text", text=f"处理流式项目出错: {str(e)}")]
            message = Message(role="agent", parts=parts)
            return TaskState.WORKING, message, None, False

# 直接实现Agent接口的AutoGen Agent
class AutoGenAgentImpl:
    """直接实现Agent接口的AutoGen Agent"""
    
    def __init__(self, default_params: Dict[str, Any] = None):
        """初始化AutoGen Agent"""
        self._content_types = ["text/plain"]
        self._default_params = default_params or {
            "temperature": 0,
            "timeout": 120,
            "model": OPENAI_MODEL
        }
    
    def get_config_list(self):
        """获取AutoGen配置列表"""
        config_list = [
            {
                "model": self._default_params.get("model", OPENAI_MODEL),
                "api_key": OPENAI_API_KEY,
            }
        ]
        return config_list
    
    def invoke(self, input: str, session_id: str, history: Optional[List[Dict[str, Any]]] = None, **kwargs) -> str:
        """同步调用AutoGen代理"""
        try:
            # 合并默认参数和传入参数
            params = {**self._default_params, **kwargs}
            
            # 获取配置
            config_list = self.get_config_list()
            
            # 设置代理配置
            llm_config = {
                "config_list": config_list,
                "temperature": params.get("temperature", 0),
                "timeout": params.get("timeout", 120),
            }
            
            # 创建助手代理
            assistant = AssistantAgent(
                name="智能助手",
                system_message="""你是一个智能助手，擅长回答各种问题。
                如果你需要执行代码，可以使用Python代码块，UserProxy会执行它们。
                如果你需要搜索信息，可以编写查找相关信息的Python代码。
                """,
                llm_config=llm_config,
            )
            
            # 创建用户代理（用于执行代码）
            user_proxy = UserProxyAgent(
                name="用户代理",
                human_input_mode="NEVER",
                code_execution_config={"work_dir": "agent_workspace"},
                llm_config=llm_config,  # 用于代码生成
                max_consecutive_auto_reply=5,
                is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
            )
            
            # 设置消息收集器
            collector = AutoGenCollector()
            
            # 修改AutoGen代理的回调函数，以捕获消息
            original_receive = assistant.receive
            
            def patched_receive(message, sender, config=None):
                """修补后的receive函数，用于收集消息"""
                collector.collect(message)
                return original_receive(message, sender, config)
            
            # 应用修补
            assistant.receive = patched_receive
            
            # 启动代理对话
            user_proxy.initiate_chat(
                assistant,
                message=input
            )
            
            # 恢复原始函数
            assistant.receive = original_receive
            
            # 从收集器中获取响应
            response = collector.last_message or "没有生成回复"
            
            return response
            
        except Exception as e:
            logger.error(f"调用AutoGen代理时出错: {e}")
            raise
    
    async def stream(self, input: str, session_id: str, history: Optional[List[Dict[str, Any]]] = None, **kwargs) -> AsyncIterable[str]:
        """异步流式调用AutoGen代理"""
        try:
            # 合并默认参数和传入参数
            params = {**self._default_params, **kwargs}
            
            # 创建一个消息队列
            message_queue = asyncio.Queue()
            
            # 获取配置
            config_list = self.get_config_list()
            
            # 设置代理配置
            llm_config = {
                "config_list": config_list,
                "temperature": params.get("temperature", 0),
                "timeout": params.get("timeout", 120),
            }
            
            # 创建助手代理
            assistant = AssistantAgent(
                name="智能助手",
                system_message="""你是一个智能助手，擅长回答各种问题。
                如果你需要执行代码，可以使用Python代码块，UserProxy会执行它们。
                如果你需要搜索信息，可以编写查找相关信息的Python代码。
                """,
                llm_config=llm_config,
            )
            
            # 创建用户代理（用于执行代码）
            user_proxy = UserProxyAgent(
                name="用户代理",
                human_input_mode="NEVER",
                code_execution_config={"work_dir": "agent_workspace"},
                llm_config=llm_config,  # 用于代码生成
                max_consecutive_auto_reply=5,
                is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
            )
            
            # 修改AutoGen代理的回调函数，以捕获并流式传输消息
            original_receive = assistant.receive
            
            def patched_receive(message, sender, config=None):
                """修补后的receive函数，用于收集并流式传输消息"""
                content = message.get("content", "")
                role = message.get("role", "")
                
                # 只处理非系统消息
                if role != "system" and content:
                    # 将消息放入队列
                    asyncio.run_coroutine_threadsafe(
                        message_queue.put(content),
                        asyncio.get_event_loop()
                    )
                
                return original_receive(message, sender, config)
            
            # 应用修补
            assistant.receive = patched_receive
            
            # 在后台线程中启动代理对话
            chat_task = asyncio.create_task(
                asyncio.to_thread(
                    user_proxy.initiate_chat,
                    assistant,
                    message=input
                )
            )
            
            # 处理流式消息
            timeout = params.get("timeout", 120)  # 秒
            end_time = asyncio.get_event_loop().time() + timeout
            accumulated_text = []
            last_message = None
            
            while (not chat_task.done() or not message_queue.empty()):
                # 检查是否超时
                now = asyncio.get_event_loop().time()
                if now > end_time:
                    break
                
                try:
                    # 尝试从队列获取消息，有超时时间
                    content = await asyncio.wait_for(message_queue.get(), 1.0)
                    
                    # 如果是新消息
                    if content != last_message:
                        # 如果之前有消息，流式输出的应该是差异部分
                        if last_message and content.startswith(last_message):
                            delta = content[len(last_message):]
                            if delta:  # 只有当有差异时才yield
                                last_message = content
                                accumulated_text.append(delta)
                                yield delta
                        else:
                            # 第一条消息或内容完全不同的消息
                            last_message = content
                            accumulated_text.append(content)
                            yield content
                    
                except asyncio.TimeoutError:
                    # 队列获取超时，继续循环
                    pass
            
            # 等待聊天任务完成
            if not chat_task.done():
                # 取消任务
                chat_task.cancel()
                try:
                    await chat_task
                except asyncio.CancelledError:
                    pass
            
            # 恢复原始函数
            assistant.receive = original_receive
            
            # 如果没有生成任何响应，至少返回一个默认消息
            if not accumulated_text:
                yield "没有生成回复"
                
        except Exception as e:
            logger.error(f"流式调用AutoGen代理时出错: {e}")
            yield f"错误: {str(e)}"
            raise
    
    @property
    def supported_content_types(self) -> List[str]:
        """返回支持的内容类型"""
        return self._content_types

def main():
    # 创建Agent Card描述
    agent_card = AgentCard(
        name="AutoGen Agent",
        description="基于AutoGen框架的可执行代码的智能代理",
        url="http://localhost:5002",
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
                id="code_execution",
                name="代码执行",
                description="可以执行Python代码来解决问题",
                examples=["计算斐波那契数列的前10个数", "使用matplotlib绘制正弦波图形"]
            ),
            AgentSkill(
                id="information_retrieval",
                name="信息检索",
                description="可以通过编写代码检索和处理信息",
                examples=["创建一个检索当前日期的函数", "生成随机密码"]
            )
        ]
    )
    
    # 创建AutoGen Agent实例
    agent = AutoGenAgentImpl()
    
    # 创建自定义响应处理器
    response_processor = CustomResponseProcessor()
    
    # 创建InMemoryTaskManager，并配置Agent和响应处理器
    task_manager = InMemoryTaskManager()
    # 为InMemoryTaskManager的委托DefaultTaskManager配置Agent和响应处理器
    task_manager._delegate.agent = agent
    task_manager._delegate.response_processor = response_processor
    
    # 确保工作目录存在
    os.makedirs("agent_workspace", exist_ok=True)
    
    # 创建A2A服务器
    server = A2AServer(
        host="0.0.0.0",
        port=5002,  # 使用不同端口，以便与其他示例并行运行
        agent_card=agent_card,
        task_manager=task_manager
    )
    
    logger.info("启动AutoGen Agent服务器，监听端口5002...")
    server.start()

if __name__ == "__main__":
    main() 