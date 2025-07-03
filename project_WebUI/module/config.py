"""
配置管理模块

提供类型安全的YAML配置文件读取、写入和验证功能。
该模块实现了一个验证字典类，确保配置项的类型正确性和数据完整性，
支持自动保存、插件配置管理和配置项类型验证。

主要特性：
- 类型安全的配置项验证
- 自动配置文件保存
- 插件配置独立管理
- 废弃配置项兼容处理
- 默认值自动填充

Author: File Classifier Project
License: MIT
"""

import yaml
import os
from typing import Dict, Any, Optional, Union, Type
from types import NoneType


class Config:
    """
    配置管理器主类
    
    负责应用程序配置的读取、写入、验证和管理。使用YAML格式存储配置，
    提供类型安全的配置操作接口，支持插件配置的独立管理。
    
    配置文件结构：
        - target_folder: 目标输出目录路径
        - hash_check_enable: 文件完整性校验算法
        - pathTemplate: 路径模板字符串
    """
    
    class ValidatedDict(Dict[str, Any]):
        """
        类型验证字典类
        
        继承自标准字典，增加了类型验证和自动保存功能。
        限制配置项键名为预定义集合，并在修改时验证值的类型。
        任何配置更改都会自动触发配置文件保存。
        
        特性：
        - 强制类型检查：每个配置项都有指定的数据类型
        - 自动保存：配置更改时立即写入文件
        - 键名限制：只允许预定义的配置项
        - 完整性验证：确保所有必需配置项都存在
        """
        
        # 允许的配置项及其对应的数据类型
        allowed_keys: Dict[str, Union[Type, tuple]] = {
            "target_folder": str,           # 目标文件夹路径 
            "hash_check_enable": str,       # 启用的哈希算法名称
            "pathTemplate": (str, NoneType), # 路径模板字符串，允许None
            "external_plugins_dir": str, # 外部插件目录
        }

        # 配置文件路径，默认为当前工作目录下的config.yaml
        __config_path: str = os.path.join(os.getcwd(), 'config.yaml')

        def __setitem__(self, key: str, value: Any) -> None:
            """
            设置配置项，包含类型验证和自动保存
            
            Args:
                key: 配置项键名，必须在allowed_keys中定义
                value: 配置项值，类型必须与allowed_keys中定义的类型匹配
                
            Raises:
                KeyError: 当键名不在允许的键列表中时抛出
                TypeError: 当值类型与期望类型不匹配时抛出
                
            Note:
                每次成功设置后都会自动触发__write_config()保存到文件
            """
            if key not in self.allowed_keys:
                raise KeyError(f"配置键 '{key}' 不在允许的键列表中。"
                             f"允许的键有: {list(self.allowed_keys.keys())}")
            
            expected_type = self.allowed_keys[key]
            if not isinstance(value, expected_type):
                # 处理类型名称显示
                if isinstance(expected_type, tuple):
                    type_names = [t.__name__ for t in expected_type]
                    type_name = " 或 ".join(type_names)
                else:
                    type_name = expected_type.__name__
                raise TypeError(f"配置键 '{key}' 的值必须是 {type_name} 类型，"
                              f"实际得到 {type(value).__name__} 类型")
            
            super().__setitem__(key, value)
            # 输出当前配置状态用于调试
            print(self)
            self.__write_config()

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """
            初始化验证字典
            
            Args:
                *args: 位置参数，通常是包含配置的字典
                **kwargs: 关键字参数形式的配置项
                
            Raises:
                KeyError: 当包含不允许的键或缺少必需的键时抛出
                TypeError: 当值类型不匹配时抛出
                
            Note:
                初始化完成后会自动调用__write_config()保存配置
            """
            super().__init__(*args, **kwargs)
            
            # 从位置参数和关键字参数中收集所有配置项
            all_items = {}
            if args and isinstance(args[0], dict):
                all_items.update(args[0])
            all_items.update(kwargs)
                    
            # 验证所有配置项的键名和类型
            for key, value in all_items.items():
                if key not in self.allowed_keys:
                    raise KeyError(f"配置键 '{key}' 不在允许的键列表中。"
                                 f"允许的键有: {list(self.allowed_keys.keys())}")
                
                expected_type = self.allowed_keys[key]
                if not isinstance(value, expected_type):
                    # 处理类型名称显示
                    if isinstance(expected_type, tuple):
                        type_names = [t.__name__ for t in expected_type]
                        type_name = " 或 ".join(type_names)
                    else:
                        type_name = expected_type.__name__
                    raise TypeError(f"配置键 '{key}' 的值必须是 {type_name} 类型，"
                                  f"实际得到 {type(value).__name__} 类型")
                
            # 检查是否包含所有必需的配置键
            for key in self.allowed_keys.keys():
                if key not in all_items:
                    raise KeyError(f"缺少必需的配置键 '{key}'")
            
            # 使用父类方法设置所有值，避免多次触发保存
            for key, value in all_items.items():
                super().__setitem__(key, value)
            self.__write_config()

        def __write_config(self) -> None:
            """
            将当前配置写入config.yaml文件
            
            该方法在配置发生任何更改时自动调用，确保配置的持久化存储。
            使用safe_dump确保输出格式的安全性和可读性。
            
            Raises:
                IOError: 当文件写入失败时可能抛出IO相关异常
            """
            try:
                with open(self.__config_path, 'w', encoding='utf-8') as yaml_file:
                    yaml.safe_dump(dict(self), yaml_file, 
                                 default_flow_style=False, 
                                 allow_unicode=True)
                    yaml_file.close()
            except Exception as e:
                print(f"警告: 保存配置文件失败: {e}")

    def __init__(self, **configs: Any) -> None:
        """
        初始化配置管理器
        
        尝试从config.yaml文件加载现有配置，如果文件不存在或格式错误，
        则创建包含默认值的新配置文件。支持通过关键字参数覆盖配置项。
        
        Args:
            **configs: 额外的配置项，将覆盖文件中的对应配置
            
        Raises:
            ValueError: 当配置文件不存在或格式错误时，会创建默认配置并抛出提示异常
            
        Note:
            - 首次运行时会创建默认配置文件
            - 配置文件损坏时会自动重置为默认值
            - 支持配置项的实时验证和类型检查
        """
        # 默认配置模板，确保系统基本可用性
        default_config: Dict[str, Any] = {
            "target_folder": '',                    # 空字符串表示需要用户配置
            "hash_check_enable": 'md5',                # 空字符串表示不启用校验
            "pathTemplate": "{filename}",            # 默认模板，仅使用文件名
            "external_plugins_dir": os.path.join(os.path.dirname(__file__), 'plugins'),          # 外部插件目录，默认为None
        }
        
        try:
            # 尝试读取现有配置文件
            with open('config.yaml', 'r', encoding='utf-8') as yaml_file:
                yaml_data = yaml.safe_load(yaml_file) or {}
                # 合并传入的配置项，允许运行时覆盖
                yaml_file.close()

            yaml_data.update(configs)
            print("111",yaml_data,"111")
            # 验证并创建ValidatedDict实例
            self.__config__ = Config.ValidatedDict(yaml_data)
                

        except FileNotFoundError:
            print("配置文件config.yaml未找到，正在创建默认配置文件...")
            # 合并默认配置和传入配置
            merged_config = default_config.copy()
            merged_config.update(configs)
            self.__config__ = Config.ValidatedDict(merged_config)
            raise ValueError("已创建初始配置文件config.yaml，请根据需要修改配置后重新运行")

        except (yaml.YAMLError, KeyError, TypeError) as e:
            print(f"配置文件格式错误: {e}")
            print("正在重置为默认配置...")
            # 合并默认配置和传入配置
            merged_config = default_config.copy()
            merged_config.update(configs)
            self.__config__ = Config.ValidatedDict(merged_config)
            raise ValueError("配置文件已重置为默认值，请检查config.yaml文件格式")

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置项值，支持默认值和废弃项兼容
        
        Args:
            key: 配置项键名
            default: 键不存在时返回的默认值
            
        Returns:
            Any: 配置项的值，如果不存在则返回默认值
            
        Note:
            - 自动处理废弃的配置项，提供向后兼容
            - 废弃项访问时会显示警告信息
            - 支持所有在allowed_keys中定义的配置项
            
        废弃的配置项：
            - seperate_by_suffix: 已由路径模板系统替代
            - seperate_by_date: 已由路径模板系统替代  
            - manual_devide: 已由路径模板系统替代
        """
        # 处理废弃配置项的兼容性映射
        deprecated_keys = {
            "seperate_by_suffix": False,    # 废弃：现在基于模板自动决定
            "seperate_by_date": False,      # 废弃：现在基于模板自动决定
            "manual_devide": False          # 废弃：现在基于模板自动决定
        }
        
        if key in deprecated_keys:
            print(f"警告: 配置项 '{key}' 已废弃。系统现在基于路径模板自动决定插件加载策略。")
            return deprecated_keys[key]
        
        return self.__config__.get(key, default)
    
    def set_config(self, key: str, value: Any) -> bool:
        """
        设置配置项的值
        
        Args:
            key: 配置项键名，必须在允许的键列表中
            value: 要设置的配置值，类型必须匹配预期类型
            
        Returns:
            bool: 设置成功返回True
            
        Raises:
            KeyError: 当键名不被允许时
            TypeError: 当值类型不匹配时
            
        允许的配置键及类型：
            - target_folder (str): 目标文件夹路径
            - hash_check_enable (str): 启用的哈希算法名称
            - pathTemplate (str|None): 路径模板字符串
        """
        self.__config__[key] = value
        return True
    
    # def get_plugin_config(self, plugin_name: str, default: Any = None) -> Any:
    #     """
    #     获取指定插件的配置数据
        
    #     Args:
    #         plugin_name: 插件名称，用作配置字典的键
    #         default: 插件配置不存在时返回的默认值
            
    #     Returns:
    #         Any: 插件的配置数据，可能是字典、列表或其他插件定义的数据结构
            
    #     Note:
    #         - 插件配置存储在pluginConfig字典中
    #         - 每个插件负责定义自己的配置结构
    #         - 不存在的插件配置返回默认值，不会抛出异常
    #     """
    #     plugin_configs = self.get_config("pluginConfig", {})
    #     return plugin_configs.get(plugin_name, default)
    
    # def set_plugin_config(self, plugin_name: str, config_data: Any) -> bool:
    #     """
    #     设置指定插件的配置数据
        
    #     Args:
    #         plugin_name: 插件名称
    #         config_data: 插件配置数据，结构由插件自行定义
            
    #     Returns:
    #         bool: 设置成功返回True
            
    #     Note:
    #         - 会自动更新pluginConfig字典并保存到文件
    #         - 支持任意插件自定义的配置结构
    #         - 配置立即持久化到config.yaml文件
    #     """
    #     # 获取当前的插件配置字典副本
    #     plugin_configs = self.get_config("pluginConfig", {}).copy()
        
    #     # 更新指定插件的配置
    #     plugin_configs[plugin_name] = config_data
        
    #     # 保存更新后的插件配置字典
    #     self.set_config("pluginConfig", plugin_configs)
    #     return True
    
    # def remove_plugin_config(self, plugin_name: str) -> bool:
    #     """
    #     移除指定插件的配置数据
        
    #     Args:
    #         plugin_name: 要移除配置的插件名称
            
    #     Returns:
    #         bool: 移除成功返回True，插件配置不存在也返回True
            
    #     Note:
    #         - 如果插件配置不存在，不会产生错误
    #         - 移除操作会立即持久化到配置文件
    #     """
    #     plugin_configs = self.get_config("pluginConfig", {}).copy()
        
    #     if plugin_name in plugin_configs:
    #         del plugin_configs[plugin_name]
    #         self.set_config("pluginConfig", plugin_configs)
        
    #     return True
    
    # def list_plugin_configs(self) -> Dict[str, Any]:
    #     """
    #     获取所有插件的配置数据
        
    #     Returns:
    #         Dict[str, Any]: 包含所有插件配置的字典，键为插件名，值为配置数据
            
    #     Note:
    #         - 返回的是配置的副本，修改不会影响实际配置
    #         - 如果没有任何插件配置，返回空字典
    #     """
    #     return self.get_config("pluginConfig", {}).copy()
    
    def get_path_template(self) -> str:
        """
        获取当前的路径模板字符串
        
        Returns:
            str: 当前保存的路径模板，如果未设置则返回默认模板"{filename}"
            
        Note:
            - 路径模板用于定义文件分类后的目录结构
            - 支持变量替换，如{year}/{month}/{filename}
            - 默认模板仅使用文件名，不创建子目录
        """
        return self.get_config("pathTemplate", "{filename}")
    
    def set_path_template(self, template: str) -> bool:
        """
        设置路径模板字符串
        
        Args:
            template: 新的路径模板字符串，支持变量占位符
            
        Returns:
            bool: 设置成功返回True
            
        Note:
            - 模板支持变量语法：{变量名}
            - 常用变量：{filename}, {year}, {month}, {day}, {extension}等
            - 模板示例："{year}/{month}/{filename}", "Documents/{basename}"
            - 设置后立即保存到配置文件
        """
        self.set_config("pathTemplate", template)
        return True