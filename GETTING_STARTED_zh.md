# A2A SDK 入门指南

*[English](GETTING_STARTED.md)*

本文档将帮助您开始使用 A2A SDK。

## 安装

### 使用 pip 安装

```bash
pip install a2a
```

### 使用 Poetry 安装

```bash
poetry add a2a
```

## 快速开始

下面是一个简单的例子，展示如何使用 A2A 客户端：

```python
import asyncio
from a2a import A2AClient
from a2a.types import Message, TextPart

async def main():
    # 初始化客户端
    client = A2AClient(url="http://example.com/agent")
    
    # 创建消息
    message = Message(
        role="user",
        parts=[TextPart(text="你好，这是一个测试")]
    )
    
    # 发送任务
    response = await client.send_task({
        "id": "task-123",
        "message": message.model_dump()
    })
    
    print(f"任务状态: {response.result.status.state}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 开发设置

如果您想参与开发：

1. 克隆仓库

```bash
git clone https://github.com/your-username/a2a.git
cd a2a
```

2. 安装开发依赖

```bash
# 使用 Poetry
poetry install

# 激活虚拟环境
poetry shell
```

3. 运行测试

```bash
pytest
```

4. 查看更多示例

请查看 `examples/` 目录中的示例文件。

## 配置 PyPI 发布

如果您想发布自己的版本：

1. 更新 `pyproject.toml` 中的信息
2. 更新版本号（在 `a2a/__init__.py` 中）
3. 创建发布标签：

```bash
git tag v0.1.0
git push origin v0.1.0
```

4. 使用 Poetry 发布：

```bash
poetry build
poetry publish
```

## 文档

更多详细文档请参考：
- [README.md](README.md) - 项目概述
- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南
- [examples/](examples/) - 示例目录 