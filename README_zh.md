# A2A SDK

Agent to Agent Protocol Python SDK - 支持 Python 3.8-3.13 的工具库

*[English](README.md)*

## 安装

使用 pip 安装：

```bash
pip install pya2a
```

## 功能特点

- 实现 Agent to Agent Protocol 的客户端和服务端
- 支持任务发送、获取、取消等操作
- 支持推送通知配置
- 支持流式响应
- 兼容 Python 3.8-3.13

## 使用示例

### 客户端示例

```python
import asyncio
from a2a.client import A2AClient
from a2a.types import Message, TextPart

async def main():
    client = A2AClient(url="http://example.com/agent")
    
    # 创建任务
    task_response = await client.send_task({
        "id": "task-123",
        "message": Message(
            role="user",
            parts=[TextPart(text="你好，这是一个测试")]
        )
    })
    
    print(f"任务创建成功: {task_response.result.id}")
    
    # 获取任务
    task = await client.get_task({"id": "task-123"})
    print(f"任务状态: {task.result.status.state}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 流式响应示例

```python
import asyncio
from a2a.client import A2AClient
from a2a.types import Message, TextPart

async def main():
    client = A2AClient(url="http://example.com/agent")
    
    # 发送流式任务请求
    async for response in client.send_task_streaming({
        "id": "task-123",
        "message": Message(
            role="user",
            parts=[TextPart(text="请生成一个长文本")]
        )
    }):
        if response.result:
            print(response.result)

if __name__ == "__main__":
    asyncio.run(main())
```

## 开发设置

1. 克隆仓库：

```bash
git clone https://github.com/your-username/a2a.git
cd a2a
```

2. 安装 Poetry（如果尚未安装）：

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. 安装依赖：

```bash
poetry install
```

4. 激活虚拟环境：

```bash
poetry shell
```

## 测试

使用 pytest 运行测试：

```bash
poetry run pytest
```

### 多Python版本测试

本项目支持Python 3.8-3.13多版本测试。有以下几种方式：

#### 1. 使用tox（推荐）

首先安装tox和tox-poetry插件：

```bash
pip install tox tox-poetry
```

然后运行测试：

```bash
tox
```

这将在`tox.ini`中配置的所有Python版本上运行测试。

#### 2. 使用脚本

我们提供了一个脚本来自动在多个Python版本上运行测试：

```bash
./scripts/run_tests_multi_python.sh
```

此脚本需要pyenv已安装，并且已安装了相应的Python版本。

#### 3. GitHub Actions

当您提交代码到仓库时，GitHub Actions会自动在多个Python版本上运行测试。您可以在GitHub仓库的Actions标签页中查看结果。

## 贡献指南

欢迎提交 Pull Requests！请确保提交前：

1. 更新测试以反映您的更改
2. 更新文档
3. 您的代码通过所有测试
4. 使用 Black 格式化代码
5. 使用 Ruff 进行代码检查

## 代码来源

本SDK的初始代码源自Google A2A项目样例中的common部分。

## 许可证

MIT 