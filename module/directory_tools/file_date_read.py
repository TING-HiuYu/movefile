"""
文件日期读取插件

从文件中提取日期信息，优先使用 EXIF 数据，
如果没有则使用文件的修改时间。
"""

import exifread
import os
import sys
import io
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime


def file_date_read(filepath: str) -> str:
    """
    获取文件的日期
    
    Args:
        filepath: 文件路径
        
    Returns:
        文件日期（YYYY-MM-DD 格式）
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


def init():
    """插件初始化函数"""
    pass


def delete():
    """插件清理函数"""
    pass


def reload():
    """插件重新加载函数"""
    pass


# 插件变量注册 - 修复拼写错误
addon_variables = {
    "file_date_read": file_date_read,
}

# 插件变量描述字典
addon_variables_description = {
    "file_date_read": "获取文件的日期，优先使用 EXIF 信息，如果没有则使用文件的修改时间",
}