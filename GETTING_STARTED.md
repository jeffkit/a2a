# Getting Started with A2A SDK

*[中文版](GETTING_STARTED_zh.md)*

This document will help you get started with the A2A SDK.

## Installation

### Using pip

```bash
pip install pya2a
```

### Using Poetry

```bash
poetry add pya2a
```

## Quick Start

Here's a simple example showing how to use the A2A client:

```python
import asyncio
from a2a.client import A2AClient
from a2a.types import Message, TextPart

async def main():
    # Initialize client
    client = A2AClient(url="http://example.com/agent")
    
    # Create message
    message = Message(
        role="user",
        parts=[TextPart(text="Hello, this is a test")]
    )
    
    # Send task
    response = await client.send_task({
        "id": "task-123",
        "message": message.model_dump()
    })
    
    print(f"Task status: {response.result.status.state}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Development Setup

If you want to participate in development:

1. Clone the repository

```bash
git clone https://github.com/your-username/a2a.git
cd a2a
```

2. Install development dependencies

```bash
# Using Poetry
poetry install

# Activate virtual environment
poetry shell
```

3. Run tests

```bash
pytest
```

4. View more examples

Check the example files in the `examples/` directory.

## Configuring PyPI Release

If you want to publish your own version:

1. Update information in `pyproject.toml`
2. Update version number (in `a2a/__init__.py`)
3. Create a release tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

4. Publish using Poetry:

```bash
poetry build
poetry publish
```

## Documentation

For more detailed documentation, please refer to:
- [README.md](README.md) - Project overview
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [examples/](examples/) - Examples directory 