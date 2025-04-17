# OpenAI Function Agent 测试指南

本文档提供了如何测试 OpenAI Function Agent 的说明，包括同步请求、流式请求以及多轮对话和多会话的测试。

## 准备工作

确保你已经安装了所有必要的依赖：

```bash
pip install -r examples/requirements-examples.txt
pip install -e .
```

## 配置 OpenAI API

如果你想使用真实的 OpenAI API（而不是内置的模拟实现），你需要在 `.env` 文件中配置你的 API 密钥：

```
OPENAI_API_KEY=你的API密钥
OPENAI_MODEL=gpt-3.5-turbo  # 或其他支持函数调用的模型
# 可选：如果你使用非官方API或代理
# OPENAI_API_BASE=https://你的API地址
```

将此 `.env` 文件放在 `examples/` 目录下。

## 运行测试

有两种方式可以运行测试：

### 方式一：使用批处理脚本（推荐）

执行以下命令：

```bash
./examples/run_openai_function_agent_test.sh
```

这个脚本会自动：
1. 安装必要的依赖
2. 启动 OpenAI Function Agent 服务器
3. 等待服务器启动完成
4. 运行客户端测试
5. 测试完成后关闭服务器

### 方式二：手动运行

如果你想分步骤运行测试，请按以下步骤操作：

1. 在一个终端窗口中启动服务器：

```bash
python examples/openai_function_agent_server.py
```

2. 在另一个终端窗口中运行客户端测试：

```bash
python examples/openai_function_agent_client_test.py
```

## 测试内容

客户端测试包括以下几个部分：

1. **同步多轮对话测试**：测试常规的请求-响应模式下的多轮对话，确保会话上下文的正确保存和使用。

2. **流式多轮对话测试**：测试流式响应模式下的多轮对话，验证流式响应的正确处理。

3. **多会话测试**：测试同时处理多个独立会话的能力，确保不同会话之间的隔离性。

## 测试中包含的示例功能

测试脚本会通过自然语言对话测试以下功能：

- **天气查询功能**：询问不同城市的天气情况
- **时间查询功能**：询问当前时间

每个测试都包含多轮对话，以验证上下文的正确传递与处理。

## 定制测试

你可以修改 `openai_function_agent_client_test.py` 文件中的 `test_questions` 数组来测试不同的问题和对话场景。

## 故障排除

- 如果遇到连接问题，请确保服务器正在运行并监听正确的端口（默认为5003）
- 如果使用真实的 OpenAI API 遇到问题，请检查你的 API 密钥和网络连接
- 查看日志输出以获取详细的错误信息和调试帮助 