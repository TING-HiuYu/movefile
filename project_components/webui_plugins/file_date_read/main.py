#!/usr/bin/env python3
"""
文件日期读取插件 - 新架构版本

这是一个文件分类器插件，专门用于提取文件的日期信息。
支持从EXIF数据读取照片的拍摄日期，对于其他文件则使用文件系统的修改时间。

功能特色：
1. 智能日期提取：优先使用EXIF原始拍摄时间
2. 容错处理：EXIF读取失败时自动回退到文件修改时间
3. 格式标准化：统一输出YYYY-MM-DD格式的日期字符串
4. 性能优化：静默处理EXIF读取时的输出干扰
5. Web UI支持：提供Web界面进行配置管理

新架构特性：
- 自维护配置：插件独立管理自己的config.yaml文件
- Web UI支持：提供现代化的Web配置界面
- API接口：支持通过Web API进行配置和测试
- 热重载：支持配置的实时更新和应用

Author: File Classifier Project
License: MIT
Version: 2.0
"""

import exifread
import os
import sys
import io
import yaml
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class FileDateReadPlugin:
    """文件日期读取插件类"""
    
    def __init__(self):
        """初始化插件"""
        self.plugin_dir = Path(__file__).parent
        self.config_file = self.plugin_dir / "config.yaml"
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """加载插件配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return {}
        else:
            # 创建默认配置
            default_config = {
                "enabled": True,
                "fallback_to_mtime": True,
                "date_format": "%Y-%m-%d",
                "description": "文件日期读取插件，优先使用EXIF信息，回退到文件修改时间"
            }
            self.save_config(default_config)
            return default_config
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """保存插件配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            self.config = config
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def file_date_read(self, filepath: str) -> str:
        """
        获取文件的日期信息，优先使用EXIF数据，回退到文件修改时间
        
        Args:
            filepath: 要分析的文件路径
            
        Returns:
            标准化的日期字符串，格式为YYYY-MM-DD
        """
        if not self.config.get("enabled", True):
            return datetime.now().strftime(self.config.get("date_format", "%Y-%m-%d"))
        
        try:
            with open(filepath, 'rb') as f:
                # 捕获 exifread 的所有输出
                with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                    tags = exifread.process_file(f, details=False)
                    if 'EXIF DateTimeOriginal' in tags:
                        date_str = str(tags['EXIF DateTimeOriginal'])
                        return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S').strftime(
                            self.config.get("date_format", "%Y-%m-%d")
                        )
                    elif self.config.get("fallback_to_mtime", True):
                        return datetime.fromtimestamp(os.path.getmtime(filepath)).strftime(
                            self.config.get("date_format", "%Y-%m-%d")
                        )
                    else:
                        return datetime.now().strftime(self.config.get("date_format", "%Y-%m-%d"))
        except Exception:
            if self.config.get("fallback_to_mtime", True):
                try:
                    return datetime.fromtimestamp(os.path.getmtime(filepath)).strftime(
                        self.config.get("date_format", "%Y-%m-%d")
                    )
                except Exception:
                    pass
            return datetime.now().strftime(self.config.get("date_format", "%Y-%m-%d"))

    # Web API 方法
    def get_plugin_config(self) -> Dict[str, Any]:
        """获取插件配置"""
        return self.config.copy()
    
    def update_plugin_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """更新插件配置"""
        try:
            # 验证配置
            if not isinstance(new_config.get("enabled"), bool):
                raise ValueError("enabled 必须是布尔值")
            if not isinstance(new_config.get("fallback_to_mtime"), bool):
                raise ValueError("fallback_to_mtime 必须是布尔值")
            if not isinstance(new_config.get("date_format"), str):
                raise ValueError("date_format 必须是字符串")
            
            # 测试日期格式
            try:
                datetime.now().strftime(new_config["date_format"])
            except Exception:
                raise ValueError("date_format 格式无效")
            
            success = self.save_config(new_config)
            return {"success": success, "message": "配置更新成功" if success else "配置保存失败"}
        except Exception as e:
            return {"success": False, "message": f"配置更新失败: {str(e)}"}
    
    def test_file_date(self, filepath: str) -> Dict[str, Any]:
        """测试文件日期读取"""
        try:
            if not os.path.exists(filepath):
                return {"success": False, "message": "文件不存在"}
            
            result = self.file_date_read(filepath)
            file_info = {
                "size": os.path.getsize(filepath),
                "mtime": datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 尝试读取EXIF信息
            exif_date = None
            try:
                with open(filepath, 'rb') as f:
                    with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                        tags = exifread.process_file(f, details=False)
                        if 'EXIF DateTimeOriginal' in tags:
                            exif_date = str(tags['EXIF DateTimeOriginal'])
            except Exception:
                pass
            
            return {
                "success": True,
                "result": result,
                "file_info": file_info,
                "exif_date": exif_date,
                "message": "测试成功"
            }
        except Exception as e:
            return {"success": False, "message": f"测试失败: {str(e)}"}


# 全局插件实例
_plugin_instance = FileDateReadPlugin()

# 向后兼容的函数接口
def file_date_read(filepath: str) -> str:
    """向后兼容的函数接口"""
    return _plugin_instance.file_date_read(filepath)

def init() -> None:
    """插件初始化函数"""
    global _plugin_instance
    _plugin_instance = FileDateReadPlugin()

def delete() -> None:
    """插件清理函数"""
    pass

def reload() -> None:
    """插件重新加载函数"""
    global _plugin_instance
    _plugin_instance = FileDateReadPlugin()

# Web API 函数（供主程序调用）
def get_plugin_config() -> Dict[str, Any]:
    """获取插件配置"""
    return _plugin_instance.get_plugin_config()

def update_plugin_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """更新插件配置"""
    return _plugin_instance.update_plugin_config(config)

def test_file_date(filepath: str) -> Dict[str, Any]:
    """测试文件日期读取"""
    return _plugin_instance.test_file_date(filepath)

# 插件注册信息
addon_variables = [
    {
        "name": "文件日期",
        "description": "获取文件的日期，优先使用 EXIF 信息，如果没有则使用文件的修改时间",
        "method": file_date_read,
        "webui": {
            "enabled": True,
            "apis": ["get_plugin_config", "update_plugin_config", "test_file_date"]
        }
    },
]
