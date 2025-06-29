"""
文件大小分类插件

根据文件大小对文件进行分类：
- tiny: < 1KB
- small: < 1MB  
- medium: < 10MB
- large: < 100MB
- huge: >= 100MB
"""

import os


def file_size_classifier(filepath: str) -> str:
    """
    根据文件大小对文件进行分类
    
    Args:
        filepath: 文件路径
        
    Returns:
        文件大小分类字符串
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

def init():
    """插件初始化函数"""
    pass


def delete():
    """插件清理函数"""
    pass


def reload():
    """插件重新加载函数"""
    pass


# 插件配置 - 注册变量和函数（修复拼写错误）
addon_variables = {
    "file_size_classifier": file_size_classifier,
}

# 插件变量描述字典
addon_variables_description = {
    "file_size_classifier": "根据文件大小对文件进行分类：tiny(<1KB), small(<1MB), medium(<10MB), large(<100MB), huge(>=100MB), unknown(错误)",
}
