#!/usr/bin/env python3
"""
文件大小分类插件 - 新架构版本

这是一个智能文件大小分类器，根据文件的字节大小将文件归类到不同的尺寸分组中。
提供了实用的文件大小分级，便于基于文件大小进行文件组织和管理。

分类标准：
- tiny: < 1KB (1,024字节) - 小文本文件、配置文件
- small: < 1MB (1,048,576字节) - 一般文档、小图片  
- medium: < 10MB (10,485,760字节) - 大文档、高质量图片
- large: < 100MB (104,857,600字节) - 视频文件、软件安装包
- huge: ≥ 100MB - 大型视频、数据库文件、虚拟机镜像

新架构特性：
- 自维护配置：插件独立管理自己的config.yaml文件
- 可自定义阈值：支持通过配置修改分类边界
- Web UI支持：提供现代化的Web配置界面
- API接口：支持通过Web API进行配置和测试
- 热重载：支持配置的实时更新和应用

Author: File Classifier Project
License: MIT
Version: 2.0
"""

import os
import yaml
from typing import Literal, Dict, Any, Union
from pathlib import Path


class FileSizeClassifierPlugin:
    """文件大小分类插件类"""
    
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
                return self.get_default_config()
        else:
            # 创建默认配置
            default_config = self.get_default_config()
            self.save_config(default_config)
            return default_config
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "enabled": True,
            "thresholds": {
                "tiny": 1024,        # 1KB
                "small": 1048576,    # 1MB
                "medium": 10485760,  # 10MB
                "large": 104857600   # 100MB
            },
            "labels": {
                "tiny": "微型文件",
                "small": "小文件", 
                "medium": "中等文件",
                "large": "大文件",
                "huge": "巨型文件",
                "unknown": "未知"
            },
            "description": "文件大小分类插件，根据文件大小自动分类"
        }
    
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
    
    def file_size_classifier(self, filepath: str) -> Literal["tiny", "small", "medium", "large", "huge", "unknown"]:
        """
        根据文件大小对文件进行智能分类
        
        Args:
            filepath: 要分析的文件路径
            
        Returns:
            文件大小分类标识符
        """
        if not self.config.get("enabled", True):
            return "unknown"
        
        try:
            if not os.path.exists(filepath):
                return "unknown"
            
            file_size = os.path.getsize(filepath)
            thresholds = self.config.get("thresholds", self.get_default_config()["thresholds"])
            
            # 根据阈值分类
            if file_size < thresholds.get("tiny", 1024):
                return "tiny"
            elif file_size < thresholds.get("small", 1048576):
                return "small"
            elif file_size < thresholds.get("medium", 10485760):
                return "medium"
            elif file_size < thresholds.get("large", 104857600):
                return "large"
            else:
                return "huge"
        
        except Exception as e:
            print(f"计算文件大小分类时出错: {e}")
            return "unknown"

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
            
            thresholds = new_config.get("thresholds", {})
            if not isinstance(thresholds, dict):
                raise ValueError("thresholds 必须是字典")
            
            # 验证阈值数据类型和大小关系
            required_thresholds = ["tiny", "small", "medium", "large"]
            for key in required_thresholds:
                if key not in thresholds:
                    raise ValueError(f"缺少阈值配置: {key}")
                if not isinstance(thresholds[key], int) or thresholds[key] <= 0:
                    raise ValueError(f"阈值 {key} 必须是正整数")
            
            # 验证阈值大小关系
            if not (thresholds["tiny"] < thresholds["small"] < thresholds["medium"] < thresholds["large"]):
                raise ValueError("阈值大小关系错误，必须满足: tiny < small < medium < large")
            
            labels = new_config.get("labels", {})
            if not isinstance(labels, dict):
                raise ValueError("labels 必须是字典")
            
            success = self.save_config(new_config)
            return {"success": success, "message": "配置更新成功" if success else "配置保存失败"}
        except Exception as e:
            return {"success": False, "message": f"配置更新失败: {str(e)}"}
    
    def test_file_size(self, filepath: str) -> Dict[str, Any]:
        """测试文件大小分类"""
        try:
            if not os.path.exists(filepath):
                return {"success": False, "message": "文件不存在"}
            
            file_size = os.path.getsize(filepath)
            result = self.file_size_classifier(filepath)
            
            # 获取分类信息
            thresholds = self.config.get("thresholds", self.get_default_config()["thresholds"])
            labels = self.config.get("labels", self.get_default_config()["labels"])
            
            # 计算与各阈值的关系
            threshold_info = {}
            for name, threshold in thresholds.items():
                threshold_info[name] = {
                    "threshold": threshold,
                    "threshold_formatted": self.format_file_size(threshold),
                    "under_threshold": file_size < threshold
                }
            
            return {
                "success": True,
                "result": result,
                "label": labels.get(result, result),
                "file_size": file_size,
                "file_size_formatted": self.format_file_size(file_size),
                "threshold_info": threshold_info,
                "message": "测试成功"
            }
        except Exception as e:
            return {"success": False, "message": f"测试失败: {str(e)}"}
    
    def format_file_size(self, bytes_size: int) -> str:
        """格式化文件大小显示"""
        if bytes_size == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(bytes_size)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.2f} {units[unit_index]}"


# 全局插件实例
_plugin_instance = FileSizeClassifierPlugin()

# 向后兼容的函数接口
def file_size_classifier(filepath: str) -> Literal["tiny", "small", "medium", "large", "huge", "unknown"]:
    """向后兼容的函数接口"""
    return _plugin_instance.file_size_classifier(filepath)

def init() -> None:
    """插件初始化函数"""
    global _plugin_instance
    _plugin_instance = FileSizeClassifierPlugin()

def delete() -> None:
    """插件清理函数"""
    pass

def reload() -> None:
    """插件重新加载函数"""
    global _plugin_instance
    _plugin_instance = FileSizeClassifierPlugin()

# Web API 函数（供主程序调用）
def get_plugin_config() -> Dict[str, Any]:
    """获取插件配置"""
    return _plugin_instance.get_plugin_config()

def update_plugin_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """更新插件配置"""
    return _plugin_instance.update_plugin_config(config)

def test_file_size(filepath: str) -> Dict[str, Any]:
    """测试文件大小分类"""
    return _plugin_instance.test_file_size(filepath)

# 插件注册信息
addon_variables = [
    {
        "name": "文件大小分类",
        "description": "根据文件大小对文件进行分类：tiny(<1KB), small(<1MB), medium(<10MB), large(<100MB), huge(>=100MB), unknown(错误)",
        "method": file_size_classifier,
        "webui": {
            "enabled": True,
            "apis": ["get_plugin_config", "update_plugin_config", "test_file_size"]
        }
    },
]
