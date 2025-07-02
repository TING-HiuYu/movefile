"""
文件分类策略插件包

该包包含各种文件分类策略的插件实现，每个插件都提供特定的
文件分组逻辑，支持灵活的文件分类需求。

插件架构：
- 标准化插件接口：所有插件遵循统一的函数签名规范
- 独立配置管理：每个插件可以有自己的配置参数
- GUI集成支持：插件可以提供可视化配置界面
- 热插拔能力：支持动态加载和卸载插件

当前插件：
- file_date_read: 基于文件修改时间的日期分类插件
- file_size_classifier: 基于文件大小的分类插件  
- manual_grouping: 基于策略组的手动分组插件

插件接口规范：
- 主函数：接受文件路径，返回分组标识列表
- 初始化函数：插件加载时的初始化逻辑
- 配置函数：可选的插件配置管理接口
- GUI设置：可选的图形配置界面

插件开发：
1. 实现标准的插件函数接口
2. 定义addon_variables列表声明插件信息
3. 可选实现GUI配置界面
4. 在directory_tools包中注册插件

Author: File Classifier Project
License: MIT
"""

__version__ = "2.0.0"
__author__ = "File Classifier Project"

# 插件模块列表，便于动态加载
__plugins__ = [
    "file_date_read",
    "file_size_classifier", 
    "manual_grouping"
]
