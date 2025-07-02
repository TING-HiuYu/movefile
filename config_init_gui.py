#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置初始化图形界面模块

这是文件分类器首次运行时的配置向导，提供用户友好的图形界面
帮助用户完成基础配置。该模块确保用户在开始使用前完成必要的设置。

主要功能：
1. 输出目录选择：用户选择文件分类后的存储目录
2. 完整性校验配置：选择哈希算法或禁用校验
3. 配置验证：确保用户输入的配置有效可用
4. 一键保存：自动保存配置到系统配置文件

界面特色：
- 现代化设计：清晰的分组布局和视觉层次
- 用户引导：详细的说明文字和操作提示
- 智能验证：实时检查用户输入的有效性
- 错误处理：友好的错误提示和修正建议

技术特性：
- 模态对话框：确保用户完成配置再继续
- 自适应布局：支持不同的屏幕尺寸
- 键盘导航：完整的键盘操作支持
- 系统集成：与操作系统文件对话框集成

Author: File Classifier Project
License: MIT
Version: 1.0.0
"""

import os
import sys
import hashlib
from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QFileDialog, QMessageBox, QGroupBox, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class ConfigInitDialog(QDialog):
    """
    配置初始化对话框类
    
    这是首次运行时显示的配置向导，引导用户完成基础设置。
    提供直观的图形界面和详细的配置选项说明。
    
    配置项目：
    1. 输出目录：文件分类后的存储位置
    2. 完整性校验：文件传输时的校验算法选择
    
    界面组件：
    - 标题区域：应用名称和配置说明
    - 输出目录组：目录选择和浏览按钮
    - 校验算法组：算法选择和相关说明
    - 操作按钮：确定、取消和帮助按钮
    
    交互流程：
    1. 显示欢迎信息和配置说明
    2. 用户选择输出目录
    3. 用户选择校验算法
    4. 验证配置有效性
    5. 保存配置并关闭对话框
    
    验证机制：
    - 目录有效性：检查目录是否存在和可写
    - 算法可用性：验证选择的哈希算法是否支持
    - 配置完整性：确保所有必需项都已配置
    """
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        初始化配置对话框
        
        Args:
            parent: 父窗口，用于模态显示和样式继承
        
        初始化流程：
        1. 基础属性设置
        2. 界面组件创建
        3. 默认值配置
        4. 事件绑定设置
        """
        super().__init__(parent)
        self.output_dir = ""
        self.integrity_check_algorithm = ""
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("配置初始化 - 文件分类器")
        # self.setFixedSize(500, 300)
        self.setFixedWidth(500)
        self.setModal(True)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("首次运行配置")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 说明文字
        desc_label = QLabel("请配置以下设置以继续使用文件分类器：")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("color: #666666; margin-bottom: 10px;")
        main_layout.addWidget(desc_label)
        
        # 输出目录设置组
        output_group = QGroupBox("输出目录设置")
        output_layout = QVBoxLayout(output_group)
        
        # 输出目录说明
        output_desc = QLabel("选择文件分类后的存储目录：")
        output_layout.addWidget(output_desc)
        
        # 输出目录选择行
        output_row = QHBoxLayout()
        
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("点击\"浏览\"选择目录...")
        self.output_dir_edit.setReadOnly(True)
        self.output_dir_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)
        output_row.addWidget(self.output_dir_edit)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self.browse_output_directory)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #606060;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #707070;
            }
            QPushButton:pressed {
                background-color: #505050;
            }
        """)
        output_row.addWidget(browse_btn)
        
        output_layout.addLayout(output_row)
        main_layout.addWidget(output_group)
        
        # 完整性校验设置组
        integrity_group = QGroupBox("完整性校验设置")
        integrity_layout = QVBoxLayout(integrity_group)
        
        # 完整性校验说明
        integrity_desc = QLabel("选择文件完整性校验算法（可选）：")
        integrity_layout.addWidget(integrity_desc)
        
        # 算法选择下拉框
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
        """)
        
        # 填充可用的哈希算法
        self.populate_algorithms()
        
        integrity_layout.addWidget(self.algorithm_combo)
        
        # 算法说明
        algo_help = QLabel("• 选择\"不校验\"可跳过完整性检查，提高处理速度\n• 为保证数据安全不推荐不校验")
        algo_help.setStyleSheet("color: #666666; font-size: 11px; margin-top: 5px;")
        integrity_layout.addWidget(algo_help)
        
        main_layout.addWidget(integrity_group)
        
        # 按钮行
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        buttons_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept_config)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        buttons_layout.addWidget(ok_btn)
        
        main_layout.addLayout(buttons_layout)
        
        # 设置默认值
        self.set_default_values()
        
    def populate_algorithms(self):
        """填充可用的哈希算法"""
        # 添加"不校验"选项
        self.algorithm_combo.addItem("不校验", "")
        
        # 获取系统支持的哈希算法
        available_algorithms = sorted(hashlib.algorithms_available)
        
        # 常用算法优先显示
        preferred_algorithms = ['md5', 'sha1', 'sha256', 'sha512']
        
        # 先添加常用算法
        for algo in preferred_algorithms:
            if algo in available_algorithms:
                self.algorithm_combo.addItem(algo.upper(), algo)
                
        # 添加分隔符（如果需要的话）
        if len(available_algorithms) > len(preferred_algorithms):
            self.algorithm_combo.insertSeparator(self.algorithm_combo.count())
            
        # 添加其他算法
        for algo in available_algorithms:
            if algo not in preferred_algorithms:
                self.algorithm_combo.addItem(algo.upper(), algo)
                
    def set_default_values(self):
        """设置默认值"""
        # 设置默认算法为SHA256
        sha256_index = self.algorithm_combo.findData("sha256")
        if sha256_index >= 0:
            self.algorithm_combo.setCurrentIndex(sha256_index)
        else:
            # 如果没有SHA256，选择"不校验"
            self.algorithm_combo.setCurrentIndex(0)
            
    def browse_output_directory(self):
        """浏览选择输出目录"""
        current_dir = self.output_dir_edit.text() or os.path.expanduser("~")
        
        selected_dir = QFileDialog.getExistingDirectory(
            self, 
            "选择输出目录", 
            current_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if selected_dir:
            self.output_dir_edit.setText(selected_dir)
            
    def accept_config(self):
        """确认配置"""
        # 验证输出目录
        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "错误", "请选择输出目录！")
            return
            
        # 尝试创建目录（如果不存在）
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法创建输出目录：{str(e)}")
            return
            
        # 检查目录是否可写
        if not os.access(output_dir, os.W_OK):
            QMessageBox.critical(self, "错误", "输出目录不可写，请选择其他目录！")
            return
            
        # 获取选择的算法
        algorithm = self.algorithm_combo.currentData()
        
        # 保存配置
        if self.save_config(output_dir, algorithm):
            self.output_dir = output_dir
            self.integrity_check_algorithm = algorithm
            self.accept()
        else:
            QMessageBox.critical(self, "错误", "保存配置失败！")
            
    def save_config(self, output_dir: str, algorithm: str) -> bool:
        """保存配置到配置文件"""
        try:
            # 导入配置模块
            import module.config as config

            # 创建配置实例
            config.Config(target_folder=output_dir, hash_check_enable=algorithm)
            
            return True
            
        except Exception as e:
            print(f"保存配置时出错: {e}")
            return False
            
    def get_config(self) -> tuple:
        """获取配置结果"""
        return self.output_dir, self.integrity_check_algorithm
        
    @staticmethod
    def show_config_dialog(parent=None) -> tuple:
        """显示配置对话框并返回结果"""
        dialog = ConfigInitDialog(parent)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_config()
        else:
            return None, None


if __name__ == "__main__":
    # 测试代码
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    output_dir, algorithm = ConfigInitDialog.show_config_dialog()
    
    if output_dir:
        print(f"输出目录: {output_dir}")
        print(f"完整性校验算法: {algorithm if algorithm else '不校验'}")
    else:
        print("用户取消了配置")
        
    sys.exit()
