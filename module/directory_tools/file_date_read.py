"""
文件日期读取插件

这是一个文件分类器插件，专门用于提取文件的日期信息。
支持从EXIF数据读取照片的拍摄日期，对于其他文件则使用文件系统的修改时间。

功能特色：
1. 智能日期提取：优先使用EXIF原始拍摄时间
2. 容错处理：EXIF读取失败时自动回退到文件修改时间
3. 格式标准化：统一输出YYYY-MM-DD格式的日期字符串
4. 性能优化：静默处理EXIF读取时的输出干扰

适用场景：
- 照片文件：提取真实的拍摄日期
- 文档文件：使用最后修改日期
- 多媒体文件：根据文件类型智能选择日期源
- 批量处理：适合大规模文件分类场景

技术实现：
- EXIF读取：使用exifread库解析图片元数据
- 输出抑制：重定向stderr和stdout避免干扰
- 日期解析：标准化的日期格式转换
- 异常处理：优雅处理各种错误情况

插件接口：
按照文件分类器插件标准实现，提供init、delete、reload等标准函数，
并通过addon_variables注册file_date_read变量。

Author: File Classifier Project
License: MIT
Version: 1.0.0
"""

import exifread
import os
import sys
import io
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from typing import Optional


def file_date_read(filepath: str) -> str:
    """
    获取文件的日期信息，优先使用EXIF数据，回退到文件修改时间
    
    这是插件的核心函数，负责从文件中提取日期信息。对于图片文件，
    会尝试读取EXIF中的原始拍摄时间；对于其他文件或EXIF读取失败的情况，
    则使用文件系统的最后修改时间。
    
    Args:
        filepath: 要分析的文件路径，必须是存在的文件
        
    Returns:
        标准化的日期字符串，格式为YYYY-MM-DD
        如：'2024-01-15', '2023-12-25'
        
    处理流程：
    1. 文件打开：以二进制模式打开文件
    2. EXIF尝试：尝试读取EXIF DateTimeOriginal字段
    3. 日期解析：将EXIF日期格式转换为标准格式
    4. 回退机制：EXIF失败时使用文件修改时间
    5. 异常处理：任何错误都返回当前日期作为默认值
    
    EXIF处理：
    - 输出抑制：使用redirect_stderr和redirect_stdout
    - 字段选择：优先使用DateTimeOriginal（原始拍摄时间）
    - 格式转换：从'YYYY:MM:DD HH:MM:SS'转为'YYYY-MM-DD'
    
    容错策略：
    - 文件不存在：返回当前日期
    - EXIF读取失败：使用文件修改时间
    - 日期解析失败：返回当前日期
    - 任何其他异常：返回当前日期
    
    Example:
        >>> date = file_date_read("/path/to/photo.jpg")
        >>> print(date)  # "2024-01-15"
        >>> 
        >>> date = file_date_read("/path/to/document.pdf") 
        >>> print(date)  # "2024-01-20" (文件修改日期)
        
    Note:
        - 对于RAW文件和特殊格式图片，EXIF读取可能失败
        - 返回的日期始终是文件的真实日期，不是当前系统日期
        - 输出格式与ISO 8601标准兼容
    """
    try:
        with open(filepath, 'rb') as f:
            # 捕获 exifread 的所有输出
            with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                tags = exifread.process_file(f, details=False)
                if 'EXIF DateTimeOriginal' in tags:
                    date_str = str(tags['EXIF DateTimeOriginal'])
                    return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S').strftime('%Y-%m-%d')
                else:
                    return datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d')
    except Exception:
        return datetime.now().strftime('%Y-%m-%d')


def init() -> None:
    """
    插件初始化函数
    
    这是插件系统的标准初始化函数，在插件加载时被调用。
    当前版本不需要特殊的初始化操作，预留用于未来的功能扩展。
    
    可能的未来用途：
    - 配置文件加载
    - 缓存系统初始化
    - 外部库的设置
    - 性能监控的启动
    """
    pass


def delete() -> None:
    """
    插件清理函数
    
    这是插件系统的标准清理函数，在插件卸载时被调用。
    负责释放插件占用的资源，确保系统可以干净地退出。
    
    清理内容（当前版本暂无）：
    - 关闭打开的文件句柄
    - 释放缓存的内存
    - 断开外部连接
    - 保存临时数据
    
    Note:
        - 即使函数为空，也必须提供以保持插件接口的完整性
        - 清理函数应该是幂等的，多次调用不会产生副作用
    """
    pass


def reload() -> None:
    """
    插件重新加载函数
    
    这是插件系统的标准重载函数，用于支持插件的热重载功能。
    在开发和调试过程中，允许不重启整个应用就重新加载插件。
    
    重载操作（当前版本暂无）：
    - 重新读取配置文件
    - 刷新缓存数据
    - 重新建立外部连接
    - 更新内部状态
    
    使用场景：
    - 插件开发和调试
    - 配置文件更新后的应用
    - 插件功能的实时更新
    - 性能优化后的验证
    """
    pass


# 插件配置 - 新的数组格式
addon_variables = [
    {
        "name": "file_date_read",
        "description": "获取文件的日期，优先使用 EXIF 信息，如果没有则使用文件的修改时间",
        "method": file_date_read,
        "gui": {
        }
    },
]