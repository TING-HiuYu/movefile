"""
文件分类器核心模块包

该包包含文件分类器的核心功能模块，提供配置管理、文件操作、
分配策略和插件系统等基础功能。

模块结构：
- config: 配置管理模块，提供YAML配置文件的读写和验证
- file_manager: 文件管理模块，提供高效的文件复制和哈希校验功能  
- allocator: 分配器模块，负责路径模板解析和文件分类逻辑
- directory_tools: 插件包，包含各种文件分类策略插件

主要特性：
- 类型安全的配置管理
- 多线程文件复制优化
- 可扩展的插件架构
- 统一的错误处理机制

Author: File Classifier Project
License: MIT
"""

__version__ = "2.0.0"
__author__ = "File Classifier Project"

# 导出主要模块，便于外部导入
from . import config
from . import file_manager  
from . import allocator

__all__ = [
    "config",
    "file_manager", 
    "allocator"
]
