"""
文件大小分类插件

这是一个智能文件大小分类器，根据文件的字节大小将文件归类到不同的尺寸分组中。
提供了实用的文件大小分级，便于基于文件大小进行文件组织和管理。

分类标准：
- tiny: < 1KB (1,024字节) - 小文本文件、配置文件
- small: < 1MB (1,048,576字节) - 一般文档、小图片  
- medium: < 10MB (10,485,760字节) - 大文档、高质量图片
- large: < 100MB (104,857,600字节) - 视频文件、软件安装包
- huge: ≥ 100MB - 大型视频、数据库文件、虚拟机镜像

功能特色：
1. 智能分级：基于实际使用场景的科学分级标准
2. 高性能：直接使用系统调用获取文件大小
3. 容错处理：文件不存在或无法访问时返回unknown
4. 跨平台：兼容所有主流操作系统

使用场景：
- 存储空间管理：按大小分类整理文件
- 备份策略：根据文件大小制定不同备份策略
- 传输优化：大文件和小文件采用不同传输方式
- 清理工具：快速定位占用空间较大的文件

分类依据：
分类标准基于现代文件系统的常见文件大小分布：
- 1KB以下：通常是系统文件、日志、小配置
- 1MB以下：办公文档、网页图片、小程序
- 10MB以下：高分辨率图片、PDF文档、音频
- 100MB以下：短视频、软件、压缩包
- 100MB以上：长视频、大型软件、数据文件

插件接口：
实现标准的文件分类器插件接口，提供file_size_classifier变量，
支持在路径模板中使用{file_size_classifier}或{size_category}。

Author: File Classifier Project
License: MIT
Version: 1.0.0
"""

import os
from typing import Literal


def file_size_classifier(filepath: str) -> Literal["tiny", "small", "medium", "large", "huge", "unknown"]:
    """
    根据文件大小对文件进行智能分类
    
    使用预定义的大小阈值将文件分类到相应的尺寸组中。
    分类标准基于实际使用场景和文件类型的常见大小分布。
    
    Args:
        filepath: 要分析的文件路径，可以是相对路径或绝对路径
        
    Returns:
        文件大小分类标识符：
        - "tiny": 小于1KB的微型文件
        - "small": 1KB到1MB的小文件
        - "medium": 1MB到10MB的中等文件  
        - "large": 10MB到100MB的大文件
        - "huge": 100MB以上的巨大文件
        - "unknown": 文件不存在或无法访问时的默认值
        
    分类详细说明：
    1. tiny (< 1KB): 配置文件、日志片段、小脚本
    2. small (1KB-1MB): 文档、网页、小图片、代码文件
    3. medium (1MB-10MB): 高质量图片、PDF、音频文件
    4. large (10MB-100MB): 视频片段、软件、压缩包
    5. huge (≥ 100MB): 长视频、数据库、虚拟机镜像
    
    性能特点：
    - 高效：直接使用os.path.getsize()系统调用
    - 安全：处理文件不存在或权限不足的情况
    - 准确：使用精确的字节计算，不是近似值
    
    错误处理：
    - 文件不存在：返回"unknown"
    - 权限不足：返回"unknown"  
    - 路径无效：返回"unknown"
    - 其他异常：记录错误并返回"unknown"
    
    Example:
        >>> size_class = file_size_classifier("small_doc.txt")  # 500字节
        >>> print(size_class)  # "tiny"
        >>> 
        >>> size_class = file_size_classifier("photo.jpg")  # 2MB
        >>> print(size_class)  # "medium"
        >>> 
        >>> size_class = file_size_classifier("movie.mp4")  # 150MB
        >>> print(size_class)  # "huge"
        
    Note:
        - 分类边界使用严格的小于比较，避免重叠
        - 1KB = 1024字节，1MB = 1024KB，采用二进制标准
        - 分类结果可直接用于路径模板和文件组织
    """
    try:
        if not os.path.exists(filepath):
            return "unknown"
        
        file_size = os.path.getsize(filepath)
        
        # 定义大小分类（字节）
        if file_size < 1024:  # < 1KB
            return "tiny"
        elif file_size < 1024 * 1024:  # < 1MB
            return "small"
        elif file_size < 10 * 1024 * 1024:  # < 10MB
            return "medium"
        elif file_size < 100 * 1024 * 1024:  # < 100MB
            return "large"
        else:  # >= 100MB
            return "huge"
    
    except Exception as e:
        print(f"计算文件大小分类时出错: {e}")
        return "unknown"

def init() -> None:
    """
    文件大小分类器插件初始化函数
    
    为插件的运行做必要的准备工作。当前版本不需要特殊的初始化操作，
    但保留此函数以维护插件接口的完整性和未来的扩展性。
    
    未来可能的初始化工作：
    - 自定义分类阈值的加载
    - 性能监控的启动
    - 缓存系统的初始化
    - 配置文件的读取
    """
    pass


def delete() -> None:
    """
    文件大小分类器插件清理函数
    
    在插件卸载时执行清理工作，释放占用的资源。
    确保插件可以干净地从系统中移除。
    
    当前版本无需特殊清理，但保留此函数以：
    - 维护插件接口的标准性
    - 为未来功能扩展预留空间
    - 确保插件生命周期的完整性
    
    可能的清理工作：
    - 保存统计信息
    - 释放缓存内存
    - 关闭配置文件
    - 清理临时数据
    """
    pass


def reload() -> None:
    """
    文件大小分类器插件重新加载函数
    
    支持插件的热重载功能，允许在不重启整个系统的情况下
    重新加载插件，这对开发和调试非常有用。
    
    重载时可能执行的操作：
    - 重新读取配置文件中的分类阈值
    - 刷新缓存的分类规则
    - 更新性能统计信息
    - 应用新的分类策略
    
    使用场景：
    - 插件开发过程中的调试
    - 运行时修改分类阈值
    - 性能优化后的验证
    - 配置更新的即时应用
    """
    pass


# 插件配置 - 新的数组格式
addon_variables = [
    {
        "name": "file_size_classifier",
        "description": "根据文件大小对文件进行分类：tiny(<1KB), small(<1MB), medium(<10MB), large(<100MB), huge(>=100MB), unknown(错误)",
        "method": file_size_classifier,
        "gui": {
        }
    },
]