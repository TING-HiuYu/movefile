import yaml
import os
import inspect
from typing import Tuple, Dict, Any, Optional

def _get_caller_details() -> Optional[Tuple[str, str]]:
    """
    通过回溯调用栈，获取调用者的详细信息。

    Returns:
        一个元组，包含 (配置文件绝对路径, 插件名)，如果查找失败则返回 None。
    """
    try:
        # 遍历调用栈
        for frame_info in inspect.stack():
            caller_path = frame_info.filename
            # 确保我们找到的不是这个配置文件本身
            if os.path.abspath(caller_path) != os.path.abspath(__file__):
                # 获取调用者（插件）的绝对路径
                caller_dir = os.path.dirname(os.path.abspath(caller_path))
                # 从文件名中提取插件名 (e.g., "my_plugin.py" -> "my_plugin")
                plugin_name = os.path.splitext(os.path.basename(caller_path))[0]
                # 配置文件与插件在同一目录
                config_path = os.path.join(caller_dir, "pluginConfig.yaml")
                return config_path, plugin_name
    except Exception as e:
        print(f"错误: 无法通过调用栈获取插件信息: {e}")
    return None

def load_config() -> Dict[str, Any]:
    """
    加载调用此函数的插件的配置。
    函数会自动识别插件名并找到对应的配置文件。

    Returns:
        包含该插件配置的字典，如果未找到则为空字典。
    """
    details = _get_caller_details()
    if not details:
        return {}
    
    config_path, plugin_name = details
    
    # 如果配置文件不存在，直接返回空字典
    if not os.path.exists(config_path):
        return {}
        
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            # 加载整个文件，以支持多个插件共享一个配置文件（虽然目前设计是一个插件一个文件）
            all_configs = yaml.safe_load(file) or {}
            # 返回属于该插件的配置部分
            return all_configs.get(plugin_name, {})
    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"错误: 读取或解析插件配置文件 {config_path} 时出错: {e}")
        return {}

def save_config(config_data: dict) -> bool:
    """
    保存调用此函数的插件的配置。
    函数会自动识别插件名并将配置数据保存到对应的配置文件中。

    Args:
        config_data (dict): 要为该插件保存的配置数据。

    Returns:
        bool: 是否保存成功。
    """
    details = _get_caller_details()
    if not details:
        return False
        
    config_path, plugin_name = details
    
    try:
        # 读取现有的所有配置
        existing_configs = {}
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as file:
                # 使用 safe_load 防止空文件或格式错误时崩溃
                loaded = yaml.safe_load(file)
                if isinstance(loaded, dict):
                    existing_configs = loaded
        
        # 更新当前插件的配置
        existing_configs[plugin_name] = config_data
        
        # 将更新后的完整配置写回文件
        with open(config_path, 'w', encoding='utf-8') as file:
            yaml.safe_dump(existing_configs, file, allow_unicode=True, sort_keys=False)
        return True
    except Exception as e:
        print(f"错误: 保存插件配置到 {config_path} 失败: {e}")
        return False

# 注意：由于此模块依赖于从外部调用来确定路径，
# __name__ == "__main__" 中的直接测试将无法正确模拟插件调用场景。
# 真实的测试需要从另一个文件中导入并调用这些函数。