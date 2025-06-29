"""
配置管理模块

提供 YAML 配置文件的读取、写入和验证功能。
支持配置项类型验证和默认值设置。
"""

import yaml
import os
from typing import Dict, Any

class Config:
    """
    配置管理类
    
    管理应用程序的配置信息，支持从 YAML 文件读取配置，
    并提供配置项的类型验证和自动保存功能。
    """
    
    class ValidatedDict(Dict[str, Any]):
        """
        验证字典类
        
        限制键名为预定义集合，并在修改前验证值的类型。
        自动保存配置更改到 YAML 文件。
        """
        # 允许的配置项及其类型
        allowed_keys: Dict[str, type] = {
            "target_folder": str,      # 目标文件夹路径
            "hash_check_enable": str,  # 启用的哈希算法
            "seperate_by_suffix": bool,  # 是否按后缀分离
            "seperate_by_date": bool,    # 是否按日期分离
            "manual_devide": bool,       # 是否手动分组
        }

        __config_path: str = os.path.join(os.getcwd(), "config.yaml")

        def __setitem__(self, key: str, value: Any):
            """
            设置配置项
            
            Args:
                key: 配置项键名
                value: 配置项值
                
            Raises:
                KeyError: 如果键名不在允许的键列表中
                TypeError: 如果值类型与期望类型不匹配
            """
            if key not in self.allowed_keys:
                raise KeyError(f"配置键 '{key}' 不被允许。允许的键有: {list(self.allowed_keys.keys())}")
            if not isinstance(value, self.allowed_keys[key]):
                raise TypeError(f"配置键 '{key}' 的值必须是 {self.allowed_keys[key].__name__} 类型，实际得到 {type(value).__name__}")
            super().__setitem__(key, value)
            print(self)
            self.__write_config()

        def __init__(self, *args: Any, **kwargs: Any):
            """
            初始化验证字典
            
            Args:
                *args: 位置参数
                **kwargs: 关键字参数
                
            Raises:
                KeyError: 如果键名不被允许或缺少必需的键
                TypeError: 如果值类型不匹配
            """
            super().__init__(*args, **kwargs)
            
            # 从位置参数和关键字参数中获取所有键值对
            all_items = {}
            if args and isinstance(args[0], dict):
                all_items.update(args[0])
            all_items.update(kwargs)
            
            # 验证所有项目
            for key, value in all_items.items():
                if key not in self.allowed_keys:
                    raise KeyError(f"配置键 '{key}' 不被允许。允许的键有: {list(self.allowed_keys.keys())}")
                if not isinstance(value, self.allowed_keys[key]):
                    raise TypeError(f"配置键 '{key}' 的值必须是 {self.allowed_keys[key].__name__} 类型，实际得到 {type(value).__name__}")
                
            # 检查是否所有必需的键都存在
            for key in self.allowed_keys.keys():
                if key not in all_items:
                    raise KeyError(f"缺少必需的配置键 '{key}'")
            
            # 使用父类的 __setitem__ 设置所有值，避免多次触发 __write_config
            for key, value in all_items.items():
                super().__setitem__(key, value)
            self.__write_config()

        def __write_config(self) -> None:
            """
            将当前配置写入 'config.yaml' 文件
            
            此方法用于保存对配置的任何更改。
            """
            with open(self.__config_path, 'w') as yaml_file:
                yaml.safe_dump(dict(self), yaml_file, default_flow_style=False)
                yaml_file.close()

    def __init__(self):
        """
        初始化配置管理器
        
        尝试从 'config.yaml' 文件加载配置设置。
        如果文件不存在或格式错误，则使用默认配置值。
        
        Raises:
            FileNotFoundError: 如果找不到 'config.yaml' 文件，将记录消息并应用默认值
            KeyError/TypeError: 如果 'config.yaml' 文件包含缺失的键或类型不匹配，
                将记录错误消息并应用默认值，确保配置保持有效，防止运行时问题
        """

        # 默认配置值
        default_config: Dict[str, Any] = {
            "target_folder": os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves"),
            "hash_check_enable": 'md5',
            "seperate_by_suffix": True,
            "seperate_by_date": True,
            "manual_devide": False
        }
        
        try:
            with open('config.yaml', 'r') as yaml_file:
                self.__config__ = Config.ValidatedDict(yaml.safe_load(yaml_file))
                yaml_file.close()

        except FileNotFoundError:
            print("配置文件未找到，使用默认配置。")
            self.__config__ = Config.ValidatedDict(default_config)

        except KeyError or TypeError:
            print("配置文件格式错误，使用默认配置。")
            self.__config__ = Config.ValidatedDict(default_config)

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        根据键获取配置值
        
        Args:
            key: 配置项键名
            default: 如果找不到键时返回的默认值
            
        Returns:
            与键关联的配置值，如果找不到键则返回默认值
            
        允许的配置键：
            - target_folder (str): 目标文件夹路径
            - hash_check_enable (str): 启用的哈希算法
            - seperate_by_suffix (bool): 是否按后缀分离
            - seperate_by_date (bool): 是否按日期分离
            - manual_devide (bool): 是否手动分组
        """
        return self.__config__.get(key, default)
    
    def set_config(self, key: str, value: Any) -> bool:
        """
        设置配置项的值
        
        Args:
            key: 配置项键名
            value: 要设置的配置值
            
        Returns:
            设置成功返回 True
            
        允许的配置键：
            - target_folder (str): 目标文件夹路径
            - hash_check_enable (str): 启用的哈希算法
            - seperate_by_suffix (bool): 是否按后缀分离
            - seperate_by_date (bool): 是否按日期分离
            - manual_devide (bool): 是否手动分组
        """
        self.__config__[key] = value
        return True