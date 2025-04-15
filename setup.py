#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 注意：这个文件仅用于兼容性目的
# 推荐使用 pyproject.toml 和 Poetry 进行项目管理

import setuptools

if __name__ == "__main__":
    try:
        setuptools.setup(name="pya2a")
    except Exception:
        print(
            "请使用 Poetry 进行安装。\n"
            "参见: https://python-poetry.org/docs/#installation\n"
            "安装命令: pip install pya2a"
        ) 