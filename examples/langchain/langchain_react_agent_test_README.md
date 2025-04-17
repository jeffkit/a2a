# LangChain ReAct Agent 测试说明

本文档介绍如何测试 LangChain ReAct Agent，包括服务器和客户端测试。

## 环境准备

测试前需要确保以下条件：

1. 安装了Python 3.8+
2. 安装了所需依赖：`pip install -r examples/requirements-examples.txt`
3. 安装了本地A2A SDK：`pip install -e .`
4. 设置了必要的环境变量（如OpenAI API密钥）

## 环境变量

在运行测试前，确保设置了以下环境变量：

```bash
# 设置OpenAI API密钥
export OPENAI_API_KEY=your_api_key

# 可选：指定使用的模型，默认为 gpt-3.5-turbo
export OPENAI_MODEL=gpt-3.5-turbo
```

也可以在项目目录下创建`.env`文件来配置这些变量。

## 测试方法

### 方法一：使用自动测试脚本

使用提供的自动测试脚本来运行完整的测试流程：

```bash
bash examples/run_langchain_react_agent_test.sh
```

这个脚本会：
1. 检查依赖是否已安装
2. 启动LangChain ReAct Agent服务器
3. 等待服务器启动完成
4. 运行客户端测试
5. 关闭服务器

### 方法二：手动测试

如果您想逐步测试，可以按以下步骤进行：

1. 启动服务器：

```bash
python examples/langchain_react_agent_server.py
```

2. 在另一个终端中，运行客户端测试：

```bash
python examples/langchain_react_agent_client_test.py
```

## 测试内容

客户端测试会对LangChain ReAct Agent进行以下测试：

1. **同步对话测试**：测试多轮同步对话功能
2. **流式对话测试**：测试多轮流式响应功能
3. **多会话测试**：测试同时维护多个独立会话的能力

## 常见问题

### 端口占用问题

如果服务器启动时提示端口5001已被占用，可以修改服务器代码中的端口号：

```python
# 在langchain_react_agent_server.py中找到这一行
server = A2AServer(
    host="0.0.0.0",
    port=5001,  # 修改为其他可用端口
    ...
)
```

然后相应地更新客户端测试脚本中的URL：

```python
# 在langchain_react_agent_client_test.py中更新
SERVER_URL = "http://localhost:5001"  # 改为与服务器相同的端口
```

### API配额限制

如果使用OpenAI API时遇到配额限制问题，可以考虑：
1. 减少测试轮数
2. 延长测试间隔时间
3. 使用较低频率限制的API密钥

## 输出解读

测试输出包含详细的日志信息，包括：
- 服务器启动和配置信息
- 客户端发送的请求
- 服务器的响应内容
- 会话ID管理
- 任何错误或警告

如果所有测试都成功完成，将看到"所有测试完成!"的消息。 