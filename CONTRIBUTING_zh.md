# 贡献指南

*[English](CONTRIBUTING.md)*

感谢您对 A2A SDK 项目的关注！以下是参与贡献的指南。

## 开发环境设置

1. 克隆仓库

```bash
git clone https://github.com/your-username/a2a.git
cd a2a
```

2. 安装 Poetry (如果尚未安装)

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. 安装依赖

```bash
poetry install
```

4. 激活虚拟环境

```bash
poetry shell
```

## 开发工作流程

1. 创建新分支

```bash
git checkout -b feature/your-feature-name
```

2. 实现您的修改

请确保:
- 代码符合 PEP 8 规范
- 新功能添加了适当的测试
- 所有测试都通过
- 文档已更新

3. 代码格式化和检查

```bash
# 使用 black 格式化代码
poetry run black a2a tests examples

# 使用 isort 排序导入
poetry run isort a2a tests examples

# 使用 ruff 检查代码
poetry run ruff a2a tests examples

# 运行类型检查
poetry run mypy a2a
```

4. 运行测试

```bash
poetry run pytest
```

5. 提交您的更改

```bash
git add .
git commit -m "描述您的更改"
```

6. 推送代码并创建 Pull Request

```bash
git push origin feature/your-feature-name
```

然后在 GitHub 上创建 Pull Request。

## 发布流程

1. 更新版本号

在 `a2a/__init__.py` 文件中更新版本号。

2. 更新 CHANGELOG.md

3. 创建新的发布标签

```bash
git tag v0.1.0
git push origin v0.1.0
```

4. CI 系统将自动构建并发布到 PyPI

## 代码规范

- 遵循 PEP 8 编码规范
- 使用类型注解
- 编写清晰的文档字符串
- 为新功能添加测试
- 保持向后兼容

感谢您的贡献！ 