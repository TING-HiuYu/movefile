"""
文件分类器 GUI 界面模块

这是基于PySide6构建的现代化可视化界面，为文件分类器提供直观易用的图形用户界面。
该模块实现了可视化路径模板构建器，支持拖放操作、实时预览和智能交互功能。

主要功能：
1. 可视化模板编辑器：支持变量拖放、点击添加和智能文本输入
2. 实时目录预览：动态显示模板生成的目录结构
3. 文件处理界面：批量文件选择、进度显示和结果反馈
4. 插件配置界面：可视化的插件设置和参数配置
5. 智能交互组件：悬浮菜单、工具提示和快捷操作

界面特性：
- 现代化设计：遵循Material Design设计原则
- 响应式布局：自适应不同屏幕尺寸和分辨率
- 无障碍支持：键盘导航、屏幕阅读器兼容
- 国际化准备：支持多语言界面（当前为中文）

核心组件：
- VariableWidget: 可拖拽的变量标签组件
- TemplateButton: 模板中的变量和分隔符按钮
- FlexibleTextEdit: 智能文本输入框组件
- TemplateEditor: 基于链表的模板编辑器
- FileClassifierGUI: 主窗口和界面控制器

技术特色：
- 组件化设计：高度模块化和可复用的UI组件
- 状态管理：完整的界面状态同步和更新机制
- 性能优化：懒加载、虚拟化和缓存机制
- 错误处理：优雅的错误处理和用户反馈

Author: File Classifier Project
License: MIT
Version: 1.0.0
"""

from csv import Error
from hmac import new
from multiprocessing import process
from tkinter import N
from typing import Optional, Dict, Any, Callable
import sys
import re
import os
import tempfile
from unittest import result
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QScrollArea, QLineEdit,
                             QTextEdit, QFrame, QSplitter, QGroupBox, QGridLayout,
                             QMessageBox, QFileDialog, QProgressBar, QListWidget,
                             QListWidgetItem, QTreeWidget, QTreeWidgetItem, QMenu, QDialog)
from PySide6.QtCore import Qt, QMimeData, Signal, QThread, QTimer, QPoint
from PySide6.QtGui import QFont, QColor, QPalette, QDrag, QPainter, QPixmap, QCursor, QAction, QKeyEvent, QMouseEvent

# 导入项目模块
import module.config as config
import module.allocator as allocator
import module.file_manager as file_manager
from config_init_gui import ConfigInitDialog

# 全局UI配置常量
text_label_size = 80

# 统一的间隔和边距设置
UI_SPACING = {
    'component': 2,        # 模板组件之间的间隔
    'layout_small': 1,     # 小布局间隔
    'layout_normal': 5,    # 普通布局间隔
    'layout_large': 10,    # 大布局间隔
    'menu_item': 8,        # 菜单项间隔
    'button_padding': 8,   # 按钮内边距
    'container_margin': 10, # 容器外边距
    'text_input_margin': 25,  # 文本输入框的内边距
    'text_wrapper_margin': 30, # 文本包装器的额外边距
}

class VariableWidget(QLabel):
    """
    可拖拽的变量标签组件
    
    这是左侧变量面板中使用的交互式变量标签，用户可以通过点击
    将变量添加到模板中。提供了清晰的视觉反馈和直观的操作体验。
    
    功能特性：
    1. 点击交互：点击变量标签直接添加到模板
    2. 视觉反馈：悬停效果和状态指示
    3. 信息展示：完整的变量描述和用法说明
    4. GUI集成：支持插件的图形化配置界面
    
    设计特点：
    - 现代化外观：圆角边框和渐变色彩
    - 响应式设计：自适应内容长度和界面主题
    - 无障碍支持：工具提示和键盘导航
    - 状态管理：清晰的交互状态和视觉反馈
    
    样式规范：
    - 主色调：蓝色系，符合系统设计语言
    - 间距统一：使用全局间距配置常量
    - 字体规范：统一的字体族和字重设置
    """
    
    # 定义自定义信号：当变量被点击时发出
    clicked = Signal(str)
    
    def __init__(self, variable_name: str, description: str, gui_info: Optional[Dict[str, Any]] = None) -> None:
        """
        初始化变量标签组件
        
        Args:
            variable_name: 变量名称，如 'filename', 'primary_group'
            description: 变量的详细描述，用于工具提示和帮助信息
            gui_info: 可选的GUI元数据，用于支持插件的图形化配置
        
        GUI元数据格式：
        {
            'setting': callable,  # 设置函数，用于打开配置对话框
            'preview': callable,  # 预览函数，用于显示当前配置
            'reset': callable     # 重置函数，用于恢复默认设置
        }
        
        Note:
            - 组件创建后会自动设置样式和事件处理
            - GUI信息用于支持插件的高级配置功能
            - 工具提示会显示完整的变量描述信息
        """
        super().__init__(variable_name)
        self.variable_name = variable_name
        self.description = description
        self.gui_info = gui_info if gui_info is not None else {}
        
        # 设置样式
        self.setStyleSheet(f"""
            QLabel {{
                background-color: #E3F2FD;
                border: 2px solid #2196F3;
                border-radius: 6px;
                padding: {UI_SPACING['layout_normal']}px {UI_SPACING['container_margin']}px;
                margin: {UI_SPACING['component']}px;
                color: #1976D2;
                font-weight: bold;
            }}
            QLabel:hover {{
                background-color: #BBDEFB;
                border-color: #1976D2;
            }}
        """)
        
        self.setToolTip(f"{variable_name}: {description}")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        处理鼠标点击事件
        
        当用户点击变量标签时，发出clicked信号，通知模板编辑器
        添加相应的变量到当前模板中。
        
        Args:
            event: 鼠标事件对象，包含点击位置和按钮信息
        
        交互逻辑：
        - 左键点击：发出clicked信号，传递变量名
        - 其他按钮：调用父类处理，保持标准行为
        
        Note:
            - 只响应左键点击，避免误操作
            - 信号会被模板编辑器接收并处理
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.variable_name)
        super().mousePressEvent(event)


class TemplateButton(QPushButton):
    """
    模板编辑器中的变量或分隔符按钮组件
    
    这是模板编辑器的核心交互元素，代表模板中的一个变量或目录分隔符。
    提供智能的上下文菜单、自适应宽度和丰富的交互功能。
    
    按钮类型：
    1. variable: 变量按钮，显示为蓝色，代表一个模板变量
    2. separator: 分隔符按钮，显示为橙色，代表目录分隔符(/)
    
    核心功能：
    1. 自适应宽度：根据内容自动调整按钮宽度
    2. 悬浮菜单：提供上下文相关的操作选项
    3. 智能交互：支持插件GUI调用和配置
    4. 删除操作：安全的组件移除机制
    
    悬浮菜单功能：
    - 变量描述显示
    - 插件GUI功能调用
    - 组件删除操作
    - 帮助和文档链接
    
    交互设计：
    - 悬停延迟：300ms延迟显示菜单，避免误触发
    - 菜单持久：鼠标移动到菜单上时保持显示
    - 视觉反馈：清晰的悬停和按下状态
    - 键盘支持：完整的键盘导航功能
    
    样式规范：
    - 变量按钮：蓝色主题 (#409eff)
    - 分隔符按钮：橙色主题 (#e6a23c)
    - 圆角设计：4px圆角，现代化外观
    - 字体规范：Microsoft YaHei，12px，中等字重
    """
    
    def __init__(self, content: str, button_type: str, parent: Optional[QWidget] = None, 
                 parent_editor: Optional['TemplateEditor'] = None) -> None:
        """
        初始化模板按钮组件
        
        Args:
            content: 按钮显示的内容文本
            button_type: 按钮类型，'variable' 或 'separator'
            parent: 父级QWidget，用于样式继承和事件传播
            parent_editor: 模板编辑器实例的引用，用于智能交互
        
        初始化流程：
        1. 基础属性设置：内容、类型、父级引用
        2. 悬浮菜单系统：定时器和信号连接
        3. 尺寸计算：基于内容自动计算最佳宽度
        4. 样式应用：根据类型应用相应的视觉样式
        5. 事件绑定：连接点击事件和特殊处理逻辑
        
        Note:
            - parent_editor用于智能交互，如分隔符的智能插入
            - 悬浮菜单支持插件的GUI功能调用
            - 按钮宽度会根据字体测量自动调整
        """
        super().__init__(content, parent)
        self.content = content
        self.button_type = button_type  # 'variable' 或 'separator'
        self.parent_editor = parent_editor  # 引用父编辑器
        
        # 悬浮菜单相关（仅对变量按钮启用）
        self.hover_menu = None
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.show_hover_menu)
        self.menu_hide_timer = QTimer()
        self.menu_hide_timer.setSingleShot(True)
        self.menu_hide_timer.timeout.connect(self.hide_hover_menu)
        
        # 存储变量信息（用于悬浮菜单）
        self.variable_description = ""
        self.variable_gui_info = {}
        
        # 计算按钮宽度（基于内容）
        font_metrics = self.fontMetrics()
        text_width = font_metrics.horizontalAdvance(content)
        button_width = text_width + 20  # 左右padding各10px
        
        # 设置固定尺寸
        self.setFixedSize(button_width, 26)
        
        # 设置按钮样式
        if button_type == 'variable':
            self.setStyleSheet(f"""
                QPushButton {{
                    background: #409eff;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 4px {UI_SPACING['button_padding']}px;
                    font-family: 'Microsoft YaHei', sans-serif;
                    font-size: 12px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background: #66b1ff;
                }}
                QPushButton:pressed {{
                    background: #3a8ee6;
                }}
            """)
        else:  # separator
            self.setStyleSheet(f"""
                QPushButton {{
                    background: #e6a23c;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 4px {UI_SPACING['button_padding']}px;
                    font-family: 'Microsoft YaHei', sans-serif;
                    font-size: 12px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background: #ebb563;
                }}
                QPushButton:pressed {{
                    background: #cf9236;
                }}
            """)
        
        # 禁用按钮编辑但保留视觉效果
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # 添加工具提示
        if button_type == 'variable':
            self.setToolTip(f"变量: {content}")
        else:
            self.setToolTip("目录分隔符")
            
        # 连接点击事件（用于分隔符按钮的智能插入逻辑）
        if button_type == 'separator' and parent_editor:
            self.clicked.connect(lambda: self.handle_separator_click())
    
    def handle_separator_click(self):
        """处理分隔符按钮点击事件，智能插入文本输入框"""
        if self.parent_editor and hasattr(self.parent_editor, 'handle_button_click'):
            self.parent_editor.handle_button_click(self, None)
    
    def set_variable_info(self, description: str, gui_info: Optional[Dict[str, Any]] = None):
        """设置变量信息（用于悬浮菜单）"""
        self.variable_description = description
        self.variable_gui_info = gui_info if gui_info is not None else {}
        
    def enterEvent(self, event):
        """鼠标进入事件"""
        super().enterEvent(event)
        # 变量按钮和分隔符按钮都显示悬浮菜单
        if self.button_type in ['variable', 'separator']:
            self.hover_timer.start(300)  # 300ms后显示（提高灵敏度）
            
    def leaveEvent(self, event):
        """鼠标离开事件"""
        super().leaveEvent(event)
        # 取消显示菜单
        self.hover_timer.stop()
        # 延迟隐藏菜单，给用户时间移动到菜单上
        if self.hover_menu and self.hover_menu.isVisible():
            self.menu_hide_timer.start(200)  # 200ms后隐藏
            
    def show_hover_menu(self):
        """显示悬浮菜单"""
        if self.button_type not in ['variable', 'separator']:
            return
            
        if self.hover_menu:
            self.hover_menu.close()
            
        self.hover_menu = QMenu(self)
        self.hover_menu.setStyleSheet(f"""
            QMenu {{
                background-color: #353535;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px {UI_SPACING['button_padding']}px;
                border-radius: 3px;
            }}
            QMenu::item:selected {{
                background-color: #409eff;
            }}
            QMenu::item:disabled {{
                color: #888888;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: #555555;
                margin: {UI_SPACING['layout_small']}px {UI_SPACING['menu_item']}px;
            }}
        """)
        
        # 根据按钮类型显示不同内容
        if self.button_type == 'variable':
            # 获取变量名（去掉大括号）
            variable_name = self.content.strip('{}')
            
            # 添加变量描述
            if self.variable_description:
                desc_action = QAction(f"📝 {self.variable_description}", self)
            else:
                desc_action = QAction(f"📝 变量: {variable_name}", self)
            desc_action.setEnabled(False)  # 设为不可点击，仅用于显示
            self.hover_menu.addAction(desc_action)
            
            # 添加GUI信息（如果有的话）
            if self.variable_gui_info:
                self.hover_menu.addSeparator()
                
                # 直接显示所有GUI选项，不折叠
                for gui_key, gui_value in self.variable_gui_info.items():
                    gui_action = QAction(f"🎨 {gui_key}", self)
                    if gui_value is None:
                        gui_action.setText(f"🎨 {gui_key} (未实现)")
                        gui_action.setEnabled(False)
                    else:
                        gui_action.triggered.connect(lambda checked, key=gui_key: self.on_gui_action(key))
                    self.hover_menu.addAction(gui_action)
        
        elif self.button_type == 'separator':
            # 分隔符按钮的描述
            desc_action = QAction("📁 目录分隔符", self)
            desc_action.setEnabled(False)
            self.hover_menu.addAction(desc_action)
        
        # 添加删除选项
        self.hover_menu.addSeparator()
        delete_action = QAction("🗑️ 删除", self)
        delete_action.triggered.connect(self.on_delete_action)
        self.hover_menu.addAction(delete_action)
        
        # 菜单事件处理
        self.hover_menu.aboutToHide.connect(self.on_menu_about_to_hide)
        
        # 计算菜单位置（在按钮下方）
        pos = self.mapToGlobal(QPoint(0, self.height() + UI_SPACING['component']))
        self.hover_menu.popup(pos)
        
        # 取消隐藏定时器
        self.menu_hide_timer.stop()
        
    def hide_hover_menu(self):
        """隐藏悬浮菜单"""
        if self.hover_menu and self.hover_menu.isVisible():
            # 检查鼠标是否在菜单上
            cursor_pos = QCursor.pos()
            menu_rect = self.hover_menu.geometry()
            if not menu_rect.contains(cursor_pos):
                self.hover_menu.close()
                
    def on_menu_about_to_hide(self):
        """菜单即将隐藏时的处理"""
        self.menu_hide_timer.stop()
        
    def on_gui_action(self, gui_key: str):
        """处理GUI动作"""
        variable_name = self.content.strip('{}')
        
        # 查找主窗口
        main_window = self.parent_editor
        while main_window and not isinstance(main_window, FileClassifierGUI):
            main_window = main_window.parent()
        
        if main_window and hasattr(main_window, 'call_plugin_gui'):
            # 调用主窗口的插件GUI调用方法
            main_window.call_plugin_gui(variable_name, gui_key)
        else:
            QMessageBox.information(
                self, 
                "GUI 功能", 
                f"变量: {variable_name}\nGUI 功能: {gui_key}\n\n此功能尚未实现。"
            )
        
    def on_delete_action(self):
        """处理删除动作"""
         # 通知父编辑器删除此按钮
        if self.parent_editor:
            self.parent_editor.remove_component(self)
        else:
            # 兜底逻辑：直接从父容器中移除并删除
            parent_widget = self.parent()
            if parent_widget and isinstance(parent_widget, QWidget):
                layout = parent_widget.layout()
                if layout:
                    layout.removeWidget(self)
            self.deleteLater()


class FlexibleTextEditWrapper(QWidget):
    """
    智能文本输入框包装器
    
    这是一个高级的文本输入组件，提供更优雅的用户交互体验。
    它解决了传统文本框在模板编辑中的交互问题，提供了更直观的
    编辑方式和更好的视觉反馈。
    
    核心特性：
    1. 空隙点击：点击空白区域激活输入框
    2. 智能展开：根据内容自动调整尺寸
    3. 悬停反馈：鼠标悬停时提供视觉提示
    4. 自动解析：输入内容自动解析为模板组件
    
    交互模式：
    - 默认状态：显示为透明占位按钮
    - 激活状态：展开为可编辑的文本输入框
    - 完成状态：自动解析内容并转换为组件
    
    解析功能：
    当用户完成输入时，会自动解析文本内容：
    - 识别变量：{variable_name} 格式
    - 识别分隔符：/ 字符
    - 混合内容：同时包含文本和变量的复杂内容
    
    布局策略：
    - 紧凑模式：最小占用空间，按需展开
    - 响应式：适应不同的容器宽度
    - 对齐一致：与其他组件保持视觉一致性
    
    样式设计：
    - 透明背景：与容器无缝集成
    - 悬停指示：虚线边框提示可点击区域
    - 平滑动画：状态切换时的流畅过渡效果
    """

    default_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                min-height: 28px;
                max-height: 28px;
                min-width: 10px;
                max-width: 10px;
                font-size: 10px;
                font-style: italic;
            }
    """

    hover_style = """
            QPushButton {
                        border-radius: 4px;
                        border: 1px dashed #777777;
                        background-color: rgba(255, 255, 255, 0.05);
                        color: #888888;
                    }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(UI_SPACING['component'], 0, UI_SPACING['component'], 0)
        self._layout.setSpacing(UI_SPACING['layout_small'])
        # 设置包装器为透明背景
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)
        # 创建文本输入框
        self.text_edit = FlexibleTextEdit(resetWarp=self.on_hover_leave)
        self._layout.addWidget(self.text_edit)
        
        # 创建透明的占位按钮，用于空隙点击
        self.placeholder_btn = QPushButton("")
        self.placeholder_btn.setFlat(True)
        self.placeholder_btn.clicked.connect(self.activate_input)
        self._layout.addWidget(self.placeholder_btn)
        
        # 设置固定尺寸
        self.setFixedSize(10, 28)
        
        # 连接信号
        self.text_edit.textChanged.connect(self.on_text_changed)
        self.text_edit.focusOutEvent = self.on_focus_out
        
        # 初始状态：显示占位按钮，隐藏输入框
        self.text_edit.hide()
        self.placeholder_btn.show()

    def mouseMoveEvent(self, event):
        """鼠标移动事件，用于悬停检测"""
        # 判断鼠标是否在包装器区域内
        if self.rect().contains(event.pos()):
            if not hasattr(self, '_is_hovering') or not self._is_hovering:
                self._is_hovering = True
                self.on_hover_enter()
        else:
            if hasattr(self, '_is_hovering') and self._is_hovering:
                self._is_hovering = False
                self.on_hover_leave()
        super().mouseMoveEvent(event)

    def on_hover_enter(self):
        """鼠标悬停进入时的处理"""
        if not self.text_edit.text():
            if not self._is_only_text_input():
                self.placeholder_btn.setText("点击输入")
                self.setFixedSize(text_label_size,28)  # 设置最小宽度
            self.placeholder_btn.setStyleSheet(self.hover_style)

    def on_hover_leave(self):
        """鼠标悬停离开时的处理"""
        if not self.text_edit.text() and not self.text_edit.hasFocus():
            # 检查是否只有一个文本输入框
            if self._is_only_text_input():
                # 如果是唯一的文本输入框，保持提示状态，不恢复小尺寸
                return
            
            self.setFixedSize(10,28)  # 设置最小宽度
            self.placeholder_btn.setStyleSheet(self.default_style)
            self.placeholder_btn.setText("")
    
    def _is_only_text_input(self):
        """检查当前是否只有一个文本输入框"""
        # 查找父级TemplateEditor
        parent_editor = self.find_parent_template_editor()
        if not parent_editor:
            return False
        
        # 统计文本输入框的数量
        text_input_count = 0
        for node in parent_editor.component_list:
            if node.component_type == 'text':
                text_input_count += 1
        
        return text_input_count == 1
            
    def enterEvent(self, event):
        """鼠标进入事件"""
        self._is_hovering = True
        self.on_hover_enter()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开事件"""
        self._is_hovering = False
        self.on_hover_leave()
        super().leaveEvent(event)
        
    def activate_input(self):
        """激活输入框"""
        self.placeholder_btn.hide()
        self.text_edit.show()
        font_metrics = self.text_edit.fontMetrics()
        # 调整包装器大小以适应输入框
        text_width = max(text_label_size, font_metrics.horizontalAdvance(self.text_edit.text()) + UI_SPACING['text_wrapper_margin'])
        self.setFixedSize(text_width, 28)
        self.text_edit.setFocus()
        self.text_edit.activate()  # 激活输入框以便输入
        
    def on_text_changed(self):
        """文本变化时的处理"""
        text = self.text_edit.text().strip()
        if text:
            font_metrics = self.fontMetrics()
            text_width = max(text_label_size, font_metrics.horizontalAdvance(self.text_edit.text()) + UI_SPACING['text_wrapper_margin'])
            self.setFixedSize(text_width, 28)
        else:
            # 延迟检查，避免在快速输入时闪烁
            QTimer.singleShot(100, self.check_empty_state)
            
    def check_empty_state(self):
        """检查空状态"""
        if not self.text_edit.text().strip() and not self.text_edit.hasFocus():
            self.show_placeholder()
            
    def show_placeholder(self):
        """显示占位按钮"""
        self.text_edit.hide()
        self.placeholder_btn.show()
        self.setFixedSize(10, 28) # 恢复小尺寸

    def on_focus_out(self, event):
        """失去焦点时的处理"""
        # 调用原始的 focusOutEvent（如果event不为None）
        if event is not None:
            super(FlexibleTextEdit, self.text_edit).focusOutEvent(event)
        
        if self._is_only_text_input():
            # 如果是唯一的文本输入框，保持提示状态，不恢复小尺寸
            return

        # 先调用 text_edit.deactivate() 让其调整大小
        self.text_edit.deactivate()
        
        # 然后同步包装器的大小，让它也缩短到合适的长度
        text = self.text_edit.text().strip()
        if text:
            font_metrics = self.fontMetrics()
            # 计算刚好包含文本的宽度，加上包装器的边距
            text_width = font_metrics.horizontalAdvance(text) + UI_SPACING['text_wrapper_margin']
            self.setFixedSize(text_width, 28)
        else:
            # 如果没有文本，设置为最小尺寸，为后续显示占位按钮做准备
            self.setFixedSize(10, 28)
        
        # 强制更新布局
        self.updateGeometry()
        parent = self.parent()
        if parent and isinstance(parent, QWidget):
            parent.updateGeometry()
            # 触发重绘以确保视觉效果正确
            parent.update()
        
        # 智能解析文本内容
        self.parse_and_split_text()
        
        if not text:
            QTimer.singleShot(50, self.show_placeholder)
    
    def text(self):
        """获取文本内容"""
        return self.text_edit.text()
        
    def setText(self, text):
        """设置文本内容"""
        self.text_edit.setText(text)
        if text.strip():
            self.activate_input()
        else:
            self.show_placeholder()
        
    def setPlaceholderText(self, text):
        """设置占位符文本"""
        self.text_edit.setPlaceholderText(text)

    def parse_and_split_text(self):
        """简化的文本解析，只负责分割和生成最基础的组件列表"""
        
        text = self.text_edit.text().strip()

        if not text:
            return
        
        strlist = list(text)

        index = 0

        if strlist and strlist[0] == '/':
            strlist.pop(0)  # 删除开头的斜杠
        if strlist and strlist[-1] == '/':
            strlist.pop()  # 删除结尾的斜杠
        while index < len(strlist):
            if strlist[index] == '/' and index + 1 < len(strlist) and strlist[index + 1] == '/':
                strlist.pop(index + 1)
                continue
            index += 1
        
        text = "".join(strlist)

        self.text_edit.setText(text)  # 更新文本框内容
            
        # 查找父级TemplateEditor
        parent_editor = self.find_parent_template_editor()
        if not parent_editor:
            return
            
        # 正则表达式匹配变量（{变量名}）和分隔符（/）
        pattern = r'(\{[^}]+\}|\/)'
        
        # 使用split但保留分隔符
        parts = re.split(pattern, text)
        
        # 如果只有一个部分且不包含变量或分隔符，则不需要切分
        if len(parts) <= 1:
            return
            
        # 找到当前文本框在链表中的位置
        current_node = parent_editor.component_list.find_node_by_widget(self)
        if not current_node:
            return
        
        # 获取可用变量清单（用于基本验证）
        available_variables = set()
        if parent_editor.allocator:
            try:
                variables_info = parent_editor.allocator.show_available_variables()
                for plugin_info in variables_info:
                    for var_info in plugin_info['variables']:
                        available_variables.add(var_info['name'])
            except:
                pass
        
        # 生成最基础的组件列表，不做复杂的验证和处理
        replacement_components = []
        
        for part in parts:
            if not part:  # 跳过空字符串
                continue
                
            if part.startswith('{') and part.endswith('}'):
                # 可能是变量，提取变量名
                variable_name = part[1:-1]
                
                if variable_name in available_variables:
                    # 有效变量，创建变量按钮
                    button = TemplateButton(part, "variable", parent_editor=parent_editor)
                    description, gui_info = parent_editor.get_variable_info(variable_name)
                    button.set_variable_info(description, gui_info)
                    replacement_components.append(('variable', button))
                else:
                    # 无效变量，作为普通文本处理（去掉大括号）
                    text_edit = FlexibleTextEditWrapper()
                    text_edit.text_edit.textChanged.connect(parent_editor.on_content_changed)
                    text_edit.setText(variable_name)  # 去掉大括号
                    replacement_components.append(('text', text_edit))
                    
            elif part == '/':
                # 分隔符
                button = TemplateButton("/", "separator", parent_editor=parent_editor)
                replacement_components.append(('separator', button))
                
            else:
                # 普通文本
                text_edit = FlexibleTextEditWrapper()
                text_edit.text_edit.textChanged.connect(parent_editor.on_content_changed)
                text_edit.setText(part)
                replacement_components.append(('text', text_edit))
        
        # 如果没有生成任何组件，直接返回
        if not replacement_components:
            return
        
        # 执行替换：用生成的组件列表替换当前文本框
        # 这会触发 __save_change，进而触发自动添加文本框和清洗逻辑
        parent_editor.replace_component_with_list(current_node, replacement_components)
    def find_parent_template_editor(self):
        """查找父级TemplateEditor"""
        parent = self.parent()
        while parent:
            if isinstance(parent, TemplateEditor):
                return parent
            parent = parent.parent()
        return None

    # ...existing code...


class FlexibleTextEdit(QLineEdit):
    """
    智能自适应文本输入框
    
    这是FlexibleTextEditWrapper的核心组件，提供智能的文本输入和
    尺寸自适应功能。专门针对模板编辑场景进行了优化。
    
    核心特性：
    1. 动态尺寸：根据内容长度自动调整宽度
    2. 智能激活：支持程序化激活和失活
    3. 视觉反馈：清晰的焦点状态和悬停效果
    4. 回调机制：与包装器的双向通信
    
    尺寸策略：
    - 最小尺寸：10px宽度，用于占位状态
    - 动态扩展：根据文本内容自动计算宽度
    - 最大限制：避免过宽影响布局
    
    交互流程：
    1. 初始状态：最小尺寸，不可见
    2. 激活状态：展开到合适宽度，获得焦点
    3. 输入过程：实时调整宽度适应内容
    4. 完成状态：失去焦点，触发内容解析
    
    样式设计：
    - 深色主题：适配整体界面风格
    - 圆角边框：现代化视觉效果
    - 高对比度：确保文本清晰可读
    - 动态边框：焦点状态的颜色变化
    
    键盘支持：
    - Enter键：完成输入并失去焦点
    - Escape键：取消输入并恢复原状
    - Tab键：在组件间导航
    """
    
    def __init__(self, parent: Optional[QWidget] = None, resetWarp: Optional[Callable] = None) -> None:
        """
        初始化智能文本输入框
        
        Args:
            parent: 父级Widget，用于样式继承
            resetWarp: 回调函数，用于通知包装器重置状态
        
        初始化内容：
        1. 基础属性设置
        2. 固定尺寸配置
        3. 样式表应用
        4. 事件连接设置
        
        Note:
            - resetWarp回调用于与包装器的状态同步
            - 初始尺寸设为最小，避免影响布局
        """
        super().__init__(parent)
        
        self.resetWarp = resetWarp  # 用于重置包装器大小的回调
        # 设置固定尺寸
        self.setFixedSize(10, 24)
        
        # 设置样式
        self.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid #555555;
                border-radius: 4px;
                font-family: 'Microsoft YaHei', sans-serif;
                font-size: 12px;
                padding-left: {UI_SPACING['button_padding']}px;
                padding-right: {UI_SPACING['button_padding']}px;
                color: #ffffff;
                background-color: #3c3c3c;
                selection-background-color: #409eff;
            }}
            QLineEdit:focus {{
                border: 1px solid #409eff;
                background-color: #404040;
            }}
            QLineEdit:hover {{
                border: 1px solid #666666;
            }}
        """)
        
        # 连接文本变化信号
        self.textChanged.connect(self.on_text_changed)
    
    def activate(self):
        """激活输入框"""
        self.setFocus()
        font_metrics = self.fontMetrics()
        # 调整输入框大小以适应内容
        text_width = max(text_label_size, font_metrics.horizontalAdvance(self.text()) + UI_SPACING['text_input_margin'])
        self.setFixedSize(text_width, 24)

    def deactivate(self):
        """失去焦点时调整宽度 - 缩短到刚好包含文本的合适长度"""
        text = self.text().strip()
        if text:
            font_metrics = self.fontMetrics()
            # 计算文本实际需要的宽度，加上少量边距
            text_width = font_metrics.horizontalAdvance(text) + UI_SPACING['text_input_margin']
            # 失去焦点后缩短到刚好合适的长度，不保持激活时的最小宽度
            self.setFixedSize(text_width, 24)
        else:
            # 如果没有文本，将宽度设置为0，让包装器控制显示
            self.setFixedSize(0, 24)
            if self.resetWarp:
                self.resetWarp()  # 如果没有文本，重置包装器大小
        
        # 触发布局更新，确保尺寸变化能立即生效
        self.updateGeometry()
        parent = self.parent()
        if parent and isinstance(parent, QWidget):
            parent.updateGeometry()

    def on_text_changed(self):
        """文本变化时动态调整宽度"""
        text = self.text()
        if text:
            font_metrics = self.fontMetrics()
            text_width = font_metrics.horizontalAdvance(text) + UI_SPACING['text_input_margin']
            text_width = max(text_width, text_label_size)  # 最小宽度为80px
            self.setFixedSize(text_width, 24)
        else:
            self.setFixedSize(text_label_size, 24)

    def keyPressEvent(self, event):
        """键盘按键事件处理"""
        from PySide6.QtCore import Qt
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # 按下回车键时触发文本解析
            parent_wrapper = self.parent()
            if isinstance(parent_wrapper, FlexibleTextEditWrapper):
                parent_wrapper.parse_and_split_text()
            self.clearFocus()  # 失去焦点，触发其他相关处理
        else:
            super().keyPressEvent(event)


class TemplateComponentNode:
    """
    模板组件节点
    """
    def __init__(self, component_type: str, widget_instance):
        self.component_type = component_type  # 'variable', 'separator', 'text'
        self.widget_instance = widget_instance


class TemplateComponentList(list):
    """
    模板组件列表，基于 Python 原生 list 实现
    """
    def __init__(self, template_editor=None):
        super().__init__()
        self.template_editor = template_editor  # 引用父编辑器用于重新渲染

    def __save_change(self, new_list):
        """
        保存更改到链表，统一处理清理、校验、合并和渲染
        优化顺序：先假设输入合法，执行自动添加，再执行清洗
        """
        # 1. 先进行文本输入框自动添加（假设输入合法）
        expanded_list = self._auto_add_text_input_to_list(new_list)
        
        # 2. 再进行清理和校验（包括合并连续文本框、清理非法分隔符等）
        cleaned_list = self._clean_and_validate_list(expanded_list)
        
        # 3. 更新当前列表
        self.clear()
        self.extend(cleaned_list)
        
        # 4. 触发重新渲染
        if self.template_editor:
            self.template_editor.rerender()
    
    def _auto_add_text_input_to_list(self, input_list):
        """
        对输入列表自动添加必要的文本输入框（不修改当前列表）
        返回新的列表
        """
        if not self.template_editor:
            return input_list
        
        result_list = list(input_list)  # 创建副本
        i = 0
        
        while i < len(result_list):
            current_node = result_list[i]
            
            # 检查当前节点前是否需要文本输入框
            if current_node.component_type in ['variable', 'separator']:
                # 检查前一个节点
                if i == 0 or result_list[i - 1].component_type != 'text':
                    # 需要在前面插入文本输入框
                    text_edit = self._create_text_input()
                    new_node = TemplateComponentNode('text', text_edit)
                    result_list.insert(i, new_node)
                    i += 1  # 调整索引，因为插入了新节点
                
                # 检查后一个节点
                if i == len(result_list) - 1 or result_list[i + 1].component_type != 'text':
                    # 需要在后面插入文本输入框
                    text_edit = self._create_text_input()
                    new_node = TemplateComponentNode('text', text_edit)
                    result_list.insert(i + 1, new_node)
            
            i += 1
        
        # 确保列表不为空，至少有一个文本输入框
        if len(result_list) == 0:
            text_edit = self._create_text_input("输入路径前缀")
            new_node = TemplateComponentNode('text', text_edit)
            result_list.append(new_node)
        
        return result_list
    
    def _create_text_input(self, placeholder="输入路径"):
        """创建文本输入框的辅助方法"""
        if not self.template_editor:
            return None
            
        text_edit = FlexibleTextEditWrapper()
        text_edit.setPlaceholderText(placeholder)
        text_edit.text_edit.textChanged.connect(self.template_editor.on_content_changed)
        return text_edit
    
    def clear_all(self):
        """清空所有组件（公开方法）- 逐个删除确保实例正确卸载"""
        # 先获取所有节点的副本，避免在遍历时修改列表
        nodes_to_remove = list(self)
        
        # 逐个删除每个节点，确保widget实例被正确删除
        for node in nodes_to_remove:
            try:
                # 手动删除widget实例
                if node.widget_instance:
                    if self.template_editor:
                        # 从布局中移除
                        self.template_editor.template_layout.removeWidget(node.widget_instance)
                    # 删除Qt对象
                    node.widget_instance.deleteLater()
            except Exception as e:
                print(f"删除节点时出错: {e}")
        
        # 清空列表
        self.clear()
        
        # 添加一个新的初始文本输入框
        if self.template_editor:
            text_edit = self._create_text_input("输入路径前缀")
            if text_edit:
                new_node = TemplateComponentNode('text', text_edit)
                self.append(new_node)
                # 直接添加到布局中
                self.template_editor.template_layout.addWidget(text_edit)
                text_edit.on_hover_enter()
                text_edit.setFixedSize(400, 28)  # 设置初始小尺寸
                text_edit.placeholder_btn.setFixedSize(400, 28)  # 确保占位按钮大小一致
                text_edit.placeholder_btn.setText("在此输入路径文本或点击左侧按钮添加路径变量")
                # 触发重新渲染以确保UI同步
                self.template_editor.rerender()
    
    def insert_node(self, target_node, component_type: str, widget_instance, position='after'):
        """
        统一的插入方法，支持前插和后插
        
        Args:
            target_node: 目标节点
            component_type: 组件类型
            widget_instance: widget实例
            position: 'before' 或 'after'
        
        Returns:
            bool: 插入是否成功
        """
        try:
            new_list = list(self)  # 创建副本
            target_index = new_list.index(target_node)
            new_node = TemplateComponentNode(component_type, widget_instance)
            
            if position == 'before':
                new_list.insert(target_index, new_node)
            else:  # 'after'
                new_list.insert(target_index + 1, new_node)
                      
            self.__save_change(new_list)
            return True
        except Exception as e:
            print(f"插入节点时出错: {e}")
            return False 

    def replace_with_component_list(self, target_node, replacement_components, layout_manager=None):
        """
        用组件列表替换指定节点
        
        Args:
            target_node: 要替换的目标节点
            replacement_components: 替换的组件列表，格式为 [(component_type, widget_instance), ...]
            layout_manager: 布局管理器，用于处理widget的布局操作
        
        Returns:
            bool: 替换是否成功
        """
        try:
            new_list = list(self)  # 创建副本

            if not target_node or not replacement_components:
                return False
            
            # 找到目标节点在列表中的索引
            try:
                target_index = new_list.index(target_node)
            except ValueError:
                return False
            
            # 移除目标节点
            new_list.pop(target_index)
            
            # 在目标位置插入新组件
            for i, (component_type, widget_instance) in enumerate(replacement_components):
                new_node = TemplateComponentNode(component_type, widget_instance)
                new_list.insert(target_index + i, new_node)
            
            self.__save_change(new_list)
            return True
        
        except Exception as e:
            print(f"替换组件列表时出错: {e}")
            return False
    
    def append_node(self, component_type: str, widget_instance):
        """在列表末尾添加节点（重命名以避免与 list.append 冲突）"""
        try:
            new_list = list(self)  # 创建副本
            new_node = TemplateComponentNode(component_type, widget_instance)
            new_list.append(new_node)
            
            self.__save_change(new_list)
            return True
        except Exception as e:
            print(f"添加节点时出错: {e}")
            return False

    def insert_after(self, target_node, component_type: str, widget_instance):
        """在指定节点后插入新节点（兼容性方法，内部调用insert_node）"""
        return self.insert_node(target_node, component_type, widget_instance, 'after')
    
    def insert_before(self, target_node, component_type: str, widget_instance):
        """在指定节点前插入新节点（兼容性方法，内部调用insert_node）"""
        return self.insert_node(target_node, component_type, widget_instance, 'before')
    
    def remove_node(self, target_node):
        """移除指定节点（重命名以区分 list.remove）"""
        try:
            new_list = list(self)  # 创建副本
            new_list.remove(target_node)
            self.__save_change(new_list)
            return True
        except Exception as e:
            print(f"移除节点时出错: {e}")
            return False
    
    def find_node_by_widget(self, widget_instance):
        """根据widget实例查找节点"""
        for node in self:
            if node.widget_instance == widget_instance:
                return node
        return None
    
    def to_list(self) -> list:
        """转换为普通列表（用于遍历）- 兼容性方法"""
        return list(self)
    
    def to_str(self) -> str:
        """转换为字符串表示"""
        result = ""
        for node in self:
            try:
                if node.component_type == 'text':
                    # 文本框有text()方法
                    if hasattr(node.widget_instance, 'text'):
                        text = node.widget_instance.text()
                        if text:
                            result += text
                elif node.component_type in ['variable', 'separator']:
                    # 按钮有content属性
                    if hasattr(node.widget_instance, 'content'):
                        result += node.widget_instance.content
            except RuntimeError:
                # Qt对象已被删除，跳过
                continue
        
        # 清理连续的分隔符
        while "//" in result:
            result = result.replace("//", "/")
            
        return result
    
    def _clean_and_validate_list(self, input_list: list) -> list:
        """
        清理和校验组件列表
        - 移除无效的组件
        - 处理开头的分隔符
        - 清理空的文本框
        - 合并连续的文本框
        """
        cleaned_list = []
        for item in input_list:
            if item and item.widget_instance:
                cleaned_list.append(item)
        
        if not cleaned_list:
            return []
        
        # 添加两个占位符，确保列表不会超出索引
        cleaned_list.append(TemplateComponentNode('placeholder', None))
        cleaned_list.append(TemplateComponentNode('placeholder', None))
        
        # 第一步：处理开头分隔符
        for index, node in enumerate(cleaned_list):
            if node.component_type == 'placeholder':
                break
            elif node.component_type == 'text' and hasattr(node.widget_instance, 'text') and node.widget_instance.text().strip() == "":
                continue
            elif node.component_type == 'variable' or (node.component_type == 'text' and hasattr(node.widget_instance, 'text') and node.widget_instance.text().strip() != ""):
                break
            elif node.component_type == 'separator':
                cleaned_list.pop(index)
                break
        
        # 第二步：处理连续分隔符和空文本框，合并连续文本框
        index = 0
        while index < len(cleaned_list):
            if cleaned_list[index].component_type == 'placeholder':
                # 跳过占位符
                index += 1
                continue

            if not cleaned_list[index] or not cleaned_list[index].widget_instance:
                index += 1
                continue
                
            if cleaned_list[index].component_type == "separator":
                if (index + 2 < len(cleaned_list) and
                    cleaned_list[index + 1].component_type == "text" and 
                    hasattr(cleaned_list[index + 1].widget_instance, 'text') and
                    cleaned_list[index + 1].widget_instance.text().strip() == "" and
                    cleaned_list[index + 2].component_type == "separator"):
                    # 如果分隔符后面是空文本框和另一个分隔符，移除后面的分隔符
                    cleaned_list.pop(index + 2)
                    
            if cleaned_list[index].component_type == "text":
                if (index + 1 < len(cleaned_list) and 
                    cleaned_list[index + 1].component_type == "text"):
                    try:
                        # 合并连续的文本框
                        current_text = cleaned_list[index].widget_instance.text() if hasattr(cleaned_list[index].widget_instance, 'text') else ''
                        next_text = cleaned_list[index + 1].widget_instance.text() if hasattr(cleaned_list[index + 1].widget_instance, 'text') else ''
                        merged_text = current_text + next_text
                        
                        cleaned_list[index].widget_instance.setText(merged_text)
                        # 移除下一个文本框
                        cleaned_list.pop(index + 1)
                        continue  # 不增加index，继续检查当前位置
                    except RuntimeError:
                        # widget已被删除，跳过
                        cleaned_list.pop(index + 1)
                        continue
                        
            index += 1

        # 移除最后两个占位符
        return cleaned_list[:-2]

    @property
    def size(self):
        """获取列表大小（兼容性属性）"""
        return len(self)

class TemplateEditor(QWidget):
    """
    基于链表的智能模板编辑器
    
    这是文件分类器的核心界面组件，提供了可视化的路径模板编辑功能。
    采用链表数据结构管理模板组件，支持复杂的编辑操作和智能交互。
    
    核心特性：
    1. 链表架构：高效的组件管理和操作
    2. 智能插入：自动在合适位置插入文本输入框
    3. 实时预览：模板变化时自动更新预览
    4. 持久化：自动保存和恢复模板配置
    
    组件类型：
    - 变量按钮：代表模板变量，如 {filename}
    - 分隔符按钮：代表目录分隔符 /
    - 文本输入框：用于输入自定义文本和路径
    
    链表管理：
    使用TemplateComponentList管理所有组件，支持：
    - 高效插入：O(1)时间复杂度的组件插入
    - 智能删除：安全的组件移除和内存管理
    - 状态同步：组件状态与界面显示的同步
    
    交互设计：
    - 拖拽支持：从变量面板拖拽变量到模板
    - 点击添加：点击变量直接添加到当前位置
    - 上下文菜单：右键显示组件相关操作
    - 键盘导航：完整的键盘操作支持
    
    信号系统：
    - template_changed：模板内容发生变化时发出
    - 组件信号：各个组件的交互信号
    - 状态通知：编辑状态和错误信息的通知
    
    数据绑定：
    与后端Allocator实例紧密集成，实现：
    - 变量验证：检查变量是否有对应插件
    - 模板解析：实时验证模板语法
    - 配置同步：自动保存到配置文件
    """
    
    # 定义自定义信号：模板内容变化时发出
    template_changed = Signal()
    
    def __init__(self, allocator_instance: Optional['allocator.Allocator'] = None) -> None:
        """
        初始化模板编辑器
        
        Args:
            allocator_instance: 文件分类器实例，用于变量验证和模板解析
        
        初始化流程：
        1. 组件列表初始化：创建链表管理器
        2. 分类器绑定：建立与后端的连接
        3. 配置系统：初始化配置管理
        4. 界面构建：创建基础UI结构
        5. 模板恢复：从配置加载已保存的模板
        
        Note:
            - allocator_instance用于变量验证和插件信息获取
            - 配置系统用于模板的持久化存储
            - 初始化失败不会影响基础功能的使用
        """
        super().__init__()
        self.component_list = TemplateComponentList(template_editor=self)  # 传递自身引用
        self.allocator = allocator_instance  # 存储allocator实例以获取变量信息
        self.config = None  # 配置实例，用于模板持久化
        
        # 初始化配置实例
        try:
            import module.config as config
            self.config = config.Config()
        except:
            self.config = None
            
        self.init_ui()
        
    def rerender(self) -> None:
        """
        重新渲染模板组件列表到界面
        
        这是视图同步的核心方法，负责将链表中的组件重新排列到界面布局中。
        通常在组件添加、删除或重排序后调用，确保界面与数据的一致性。
        
        重渲染流程：
        1. 清理现有布局：移除所有组件但不删除对象
        2. 验证组件有效性：检查组件是否仍然可用
        3. 重新添加组件：按链表顺序添加到布局
        4. 异常处理：跳过无效组件，保证渲染完整性
        
        安全特性：
        - 对象保护：不会删除组件对象，只是重新排列
        - 异常容错：单个组件错误不影响整体渲染
        - 状态保持：组件的内部状态得以保留
        
        性能考虑：
        - 增量更新：只处理变化的部分（未来优化）
        - 批量操作：避免频繁的单个组件操作
        - 延迟渲染：合并多次变更为一次渲染
        
        Note:
            - 调用此方法会触发界面重绘
            - 高频调用可能影响性能，建议批量更新
            - 渲染过程中界面可能出现短暂闪烁
        """
        # 清除现有的所有组件（但不删除对象）
        while self.template_layout.count():
            child = self.template_layout.takeAt(0)
            # 不要设置parent为None，这会删除对象
        
        # 重新添加所有组件到布局中
        for node in self.component_list:
            if node.widget_instance:
                # 检查widget是否还有效
                try:
                    # 先检查widget是否仍然存在
                    if hasattr(node.widget_instance, 'isVisible'):
                        self.template_layout.addWidget(node.widget_instance)
                        # 确保widget可见
                        node.widget_instance.show()
                    if node.component_type == 'text':
                        # 调用包装器的失去焦点处理，确保完整的状态同步
                        node.widget_instance.on_focus_out(None)  # 传入None作为event参数
                
                except RuntimeError:
                    # 如果widget已经被删除，跳过
                    continue
        
        # 触发模板变化信号（用于更新预览等）
        self.template_changed.emit()
        
    def init_ui(self):
        """初始化界面"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setMinimumHeight(80)
        scroll_area.setMaximumHeight(120)
        
        # 模板容器
        self.template_container = QWidget()
        self.template_layout = QHBoxLayout(self.template_container)
        self.template_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)  # 左对齐
        self.template_layout.setContentsMargins(UI_SPACING['container_margin'], UI_SPACING['container_margin'], UI_SPACING['container_margin'], UI_SPACING['container_margin'])
        self.template_layout.setSpacing(UI_SPACING['component'])  # 组件间的统一间隔
        
        # 设置容器样式（深灰色背景，Element UI风格）
        self.template_container.setStyleSheet(f"""
            QWidget {{
                background-color: #2c2c2c;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                margin: {UI_SPACING['component']}px;
            }}
        """)
        
        scroll_area.setWidget(self.template_container)
        self.main_layout.addWidget(scroll_area)
        
        # 延迟初始化模板，确保在配置加载后进行
        QTimer.singleShot(10, self.init_template_from_config)
        
    def init_template_from_config(self):
        """根据配置初始化模板"""
        if not self.config:
            # 如果没有配置，添加默认文本输入框
            self.add_initial_text_input()
            return
        
        try:
            template = self.config.get_path_template()
            
            # 如果模板是默认的 {filename}，只添加一个空文本框
            if not template or template == "{filename}":
                self.add_initial_text_input()
                return
            
            # 对于其他模板，移除末尾的{filename}部分，因为这是自动添加的
            if template.endswith('{filename}'):
                template = template[:-10]  # 移除'{filename}'
                if template.endswith('/'):
                    template = template[:-1]  # 移除末尾的'/'
            
            # 如果还有模板内容，则设置到文本框并解析
            if template.strip():
                # 添加初始文本框
                self.add_initial_text_input()
                # 获取初始文本框并设置模板内容
                if len(self.component_list) > 0:
                    first_node = self.component_list[0]
                    if first_node.component_type == 'text':
                        text_widget = first_node.widget_instance
                        text_widget.setText(template)
                        text_widget.activate_input()
                        # 延迟触发解析
                        QTimer.singleShot(50, lambda: text_widget.parse_and_split_text())
            else:
                # 如果模板内容为空，添加默认文本框
                self.add_initial_text_input()
                
        except Exception as e:
            print(f"初始化模板失败: {e}")
            # 出错时添加默认文本框
            self.add_initial_text_input()
        
    def add_initial_text_input(self):
        """添加初始文本输入框"""
        text_edit = FlexibleTextEditWrapper()
        text_edit.setPlaceholderText("输入路径前缀")
        text_edit.text_edit.textChanged.connect(self.on_content_changed)
        
        # 检查是否是第一个（也是唯一的）文本输入框
        is_first_and_only = len(self.component_list) == 0
        
        # 添加到列表（自动触发渲染）
        self.component_list.append_node('text', text_edit)
        
        # 如果是第一个输入框，激活特殊状态
        if is_first_and_only:
            # 延迟执行，确保widget已经完全创建和渲染
            QTimer.singleShot(50, lambda: self._setup_first_input_box(text_edit))
    
    def _setup_first_input_box(self, text_edit: FlexibleTextEditWrapper):
        """设置第一个输入框的特殊状态"""
        # 激活 hover 状态并设置提示文本
        text_edit.on_hover_enter()
        text_edit.setFixedSize(400, 28)  # 设置初始小尺寸
        text_edit.placeholder_btn.setFixedSize(400, 28)  # 确保占位按钮大小一致
        text_edit.placeholder_btn.setText("在此输入路径文本或点击左侧按钮添加路径变量")
        
    def get_variable_info(self, variable_name: str) -> tuple:
        """获取变量的描述和GUI信息"""
        if not self.allocator:
            return "", {}
            
        try:
            variables_info = self.allocator.show_available_variables()
            for plugin_info in variables_info:
                for var_info in plugin_info['variables']:
                    if var_info['name'] == variable_name:
                        return var_info['description'], plugin_info.get('gui', {})
        except:
            pass
        return "", {}
        
    def insert_variable(self, variable_name: str) -> None:
        """
        插入变量按钮到模板编辑器
        
        这是变量添加的核心方法，负责创建变量按钮组件并将其
        添加到模板链表中。支持智能文本框插入和变量信息绑定。
        
        Args:
            variable_name: 要插入的变量名，如 'filename', 'primary_group'
        
        处理流程：
        1. 创建变量按钮：使用TemplateButton创建可交互按钮
        2. 获取变量信息：从allocator获取变量描述和GUI配置
        3. 绑定信息：将变量信息绑定到按钮，支持悬浮菜单
        4. 事件连接：设置按钮的点击事件处理
        5. 添加到链表：使用链表管理器添加组件
        
        智能特性：
        - 自动文本框：在合适位置自动插入文本输入框
        - 信息绑定：显示完整的变量描述和用法
        - GUI集成：支持插件的图形化配置功能
        - 位置优化：智能选择最佳插入位置
        
        交互设计：
        - 即时反馈：插入后立即显示在界面
        - 上下文菜单：支持变量的配置和删除
        - 拖拽支持：支持从变量面板拖拽插入
        
        Note:
            - 插入的变量会自动格式化为 {variable_name} 格式
            - 变量信息从allocator实例获取，确保准确性
            - 支持复杂的GUI配置和插件交互
        """
        # 创建变量按钮
        button = TemplateButton(f"{{{variable_name}}}", "variable", parent_editor=self)
        
        # 获取并设置变量信息
        description, gui_info = self.get_variable_info(variable_name)
        button.set_variable_info(description, gui_info)
        
        # 将按钮的点击事件连接到智能插入逻辑
        button.mousePressEvent = lambda event: self.handle_button_click(button, event)
        
        # 在列表末尾添加变量按钮（自动处理文本输入框）
        self.component_list.append_node('variable', button)
        
    def insert_separator(self):
        """插入分隔符按钮，并智能处理文本输入框"""
        # 创建分隔符按钮
        button = TemplateButton("/", "separator", parent_editor=self)
        
        # 在列表末尾添加分隔符按钮（自动处理文本输入框）
        self.component_list.append_node('separator', button)
        
    def handle_button_click(self, button, event):
        """处理按钮点击事件，智能插入文本输入框"""
        # 这个方法现在主要用于兼容性，实际的文本框插入由链表自动处理
        pass
            
    def insert_widget_before(self, reference_widget, new_widget):
        """在指定widget前插入新widget到布局中"""
        # 找到reference_widget在布局中的索引
        layout = self.template_layout
        for i in range(layout.count()):
            if layout.itemAt(i).widget() == reference_widget:
                layout.insertWidget(i, new_widget)
                break
                
    def insert_widget_after(self, reference_widget, new_widget):
        """在指定widget后插入新widget到布局中"""
        # 找到reference_widget在布局中的索引
        layout = self.template_layout
        for i in range(layout.count()):
            if layout.itemAt(i).widget() == reference_widget:
                layout.insertWidget(i + 1, new_widget)
                break
                
    def get_template(self) -> str:
        """
        获取当前编辑器中的完整模板字符串
        
        遍历链表中的所有组件，提取它们的内容并拼接成完整的模板字符串。
        这是模板编辑器与外部系统交互的主要接口。
        
        Returns:
            完整的模板字符串，如 "{primary_group}/{filename}.{ext}"
            
        提取规则：
        1. 变量组件：提取变量名，保持 {variable} 格式
        2. 分隔符组件：提取分隔符字符，通常是 "/"
        3. 文本组件：提取用户输入的文本内容
        4. 空组件：跳过空的或无效的组件
        
        安全处理：
        - 异常捕获：处理已删除的Qt对象
        - 空值过滤：忽略空文本和无效组件
        - 状态检查：验证组件的有效性
        
        使用场景：
        - 模板保存：获取模板用于配置存储
        - 模板验证：检查模板语法的有效性
        - 预览生成：为目录预览提供模板
        - 后端通信：传递给Allocator进行处理
        
        Example:
            编辑器包含：[{filename}, "/", {ext}]
            返回："filename}/{ext}"
            
        Note:
            - 返回的字符串已经过清理，移除了多余的空格
            - 不包含界面特定的格式信息
            - 可以直接用于模板解析和路径生成
        """
        template_parts = []
        
        # 遍历列表获取模板内容
        for node in self.component_list:
            try:
                if node.component_type == 'variable' or node.component_type == 'separator':
                    if hasattr(node.widget_instance, 'content'):
                        template_parts.append(node.widget_instance.content)
                elif node.component_type == 'text':
                    # 安全检查widget是否仍然有效
                    if hasattr(node.widget_instance, 'text'):
                        text = node.widget_instance.text().strip()
                        if text:
                            template_parts.append(text)
            except RuntimeError:
                # Qt对象已被删除，跳过
                continue
        
        result = "".join(template_parts)
        
        # 确保末尾有 {filename}（但不在开头添加分隔符）
        if not result.endswith('{filename}'):
            # 如果结果为空，直接返回 {filename}
            if not result:
                result = '{filename}'
            else:
                # 如果结果不为空且不以 / 结尾，添加 /
                if not result.endswith('/'):
                    result += '/'
                result += '{filename}'
            
        return result
        
    def clear_template(self):
        """清空模板（通过链表方法统一处理）"""
        # 使用链表的公开清空方法，会自动触发 __save_change 和 rerender
        # _auto_add_text_input_to_list 会确保至少有一个文本输入框
        self.component_list.clear_all()
        
    def remove_component(self, widget_instance):
        """移除组件（通过链表方法统一处理）"""
        # 从列表中查找要移除的节点
        node_to_remove = self.component_list.find_node_by_widget(widget_instance)
        if not node_to_remove:
            return
        
        # 使用链表的统一移除方法，会自动触发 __save_change
        success = self.component_list.remove_node(node_to_remove)
        
        if success:
            # 手动删除widget实例（因为rerender不会删除已移除的widget）
            try:
                widget_instance.deleteLater()
            except:
                pass

    def on_content_changed(self):
        """内容变化时的处理"""
        # 发射自定义信号
        self.template_changed.emit()
        
    def get_widget_layout_index(self, widget):
        """获取widget在布局中的索引"""
        layout = self.template_layout
        for i in range(layout.count()):
            if layout.itemAt(i).widget() == widget:
                return i
        return -1
    
    def replace_component_with_list(self, target_node, replacement_components):
        """用组件列表替换指定节点（通过链表方法统一处理）"""
        if not target_node or not replacement_components:
            return
        
        # 使用链表的替换方法，会自动触发 __save_change 和 rerender
        success = self.component_list.replace_with_component_list(target_node, replacement_components)
        
        if success:
            # 手动删除被替换的widget实例（因为rerender不会删除已移除的widget）
            try:
                target_node.widget_instance.deleteLater()
            except:
                pass
    
    def save_template_to_config(self):
        """将当前模板保存到配置文件"""
        if not self.config:
            return
        
        try:
            template = self.get_template()
            if template:
                self.config.set_path_template(template)
        except Exception as e:
            print(f"保存模板失败: {e}")
    
    def load_template_from_config(self):
        """从配置文件加载模板，直接设置到文本框并激活解析功能"""
        if not self.config:
            return
        
        try:
            template = self.config.get_path_template()
            if template and template != "{filename}":  # 如果不是默认模板
                # 移除末尾的{filename}部分，因为这是自动添加的
                if template.endswith('{filename}'):
                    template = template[:-10]  # 移除'{filename}'
                    if template.endswith('/'):
                        template = template[:-1]  # 移除末尾的'/'
                
                # 如果还有模板内容，则设置到初始文本框并激活解析
                if template.strip():
                    # 获取初始文本框
                    if len(self.component_list) > 0:
                        first_node = self.component_list[0]
                        if first_node.component_type == 'text':
                            text_widget = first_node.widget_instance
                            # 设置模板字符串到文本框
                            text_widget.setText(template)
                            text_widget.activate_input()
                            # 延迟触发解析，确保界面已经完全初始化
                            QTimer.singleShot(100, lambda: text_widget.parse_and_split_text())
        except Exception as e:
            print(f"加载模板失败: {e}")
    
    def set_template(self, template: str):
        """设置模板内容，通过文本框解析的方式构建界面"""
        if not template:
            return
        
        # 清空当前模板
        self.clear_template()
        
        # 移除末尾的{filename}部分，因为这是自动添加的
        if template.endswith('{filename}'):
            template = template[:-10]  # 移除'{filename}'
            if template.endswith('/'):
                template = template[:-1]  # 移除末尾的'/'
        
        # 如果还有模板内容，则设置到初始文本框并激活解析
        if template.strip():
            # 获取初始文本框
            if len(self.component_list) > 0:
                first_node = self.component_list[0]
                if first_node.component_type == 'text':
                    text_widget = first_node.widget_instance
                    # 设置模板字符串到文本框
                    text_widget.setText(template)
                    text_widget.activate_input()
                    # 触发解析
                    text_widget.parse_and_split_text()
        

        
    @staticmethod
    def validate_template_structure(func):
        """
        装
        在链表修改操作后自动验证，如果不合法则回滚并提示用户
        """
        def wrapper(self, *args, **kwargs):
            # 保存当前链表状态（用于回滚）
            original_state = self._backup_component_list()
            
            try:
                # 执行原始操作
                result = func(self, *args, **kwargs)
                
                # 验证新的链表结构
                validation_result = self._validate_current_template()
                
                if validation_result['valid']:
                    # 验证通过，返回结果
                    return result
                else:
                    # 验证失败，回滚并提示用户
                    self._restore_component_list(original_state)
                    QMessageBox.warning(
                        self,
                        "模板结构错误",
                        validation_result['message']
                    )
                    return None
                    
            except Exception as e:
                # 如果出现异常，也要回滚
                self._restore_component_list(original_state)
                QMessageBox.critical(
                    self,
                    "操作失败",
                    f"操作过程中出现错误: {str(e)}"
                )
                return None
                
        return wrapper
    
    def _backup_component_list(self):
        """备份当前组件列表状态"""
        backup = []
        for node in self.component_list:
            # 备份节点信息
            backup.append({
                'type': node.component_type,
                'widget': node.widget_instance,
                'text': node.widget_instance.text() if hasattr(node.widget_instance, 'text') else '',
                'content': getattr(node.widget_instance, 'content', '')
            })
        return backup
    
    def _restore_component_list(self, backup_state):
        """从备份恢复组件列表状态"""
        # 清除当前所有组件
        for node in list(self.component_list):  # 创建副本避免修改时的迭代问题
            self.template_layout.removeWidget(node.widget_instance)
            node.widget_instance.deleteLater()
        
        # 清空列表
        self.component_list.clear()
        
        # 从备份恢复
        for item in backup_state:
            if item['type'] == 'text':
                text_edit = FlexibleTextEditWrapper()
                text_edit.setText(item['text'])
                text_edit.text_edit.textChanged.connect(self.on_content_changed)
                
                if self.component_list.append_node('text', text_edit):
                    self.template_layout.addWidget(text_edit)
                
            elif item['type'] == 'variable':
                button = TemplateButton(item['content'], "variable", parent_editor=self)
                button.mousePressEvent = lambda event, btn=button: self.handle_button_click(btn, event)
                
                if self.component_list.append_node('variable', button):
                    self.template_layout.addWidget(button)
                
            elif item['type'] == 'separator':
                button = TemplateButton("/", "separator", parent_editor=self)
                button.mousePressEvent = lambda event, btn=button: self.handle_button_click(btn, event)
                
                if self.component_list.append_node('separator', button):
                    self.template_layout.addWidget(button)
    
    def _validate_current_template(self):
        """验证当前模板结构的合法性"""
        # 遍历列表检查结构
        for position, node in enumerate(self.component_list):
            current_type = node.component_type
            prev_type = self.component_list[position - 1].component_type if position > 0 else None
            
            # 规则1: 不能在模板开头使用分隔符
            if position == 0 and current_type == 'separator':
                return {
                    'valid': False,
                    'message': "不能在模板开头插入分隔符 (/)。\n\n路径模板应该以文件夹名或变量开始，例如：\n• Documents\n• {primary_group}\n• 图片文件"
                }
            
            # 规则2: 不能连续使用分隔符
            if prev_type == 'separator' and current_type == 'separator':
                return {
                    'valid': False,
                    'message': "不能连续插入多个分隔符 (/)。\n\n每两个分隔符之间必须有文件夹名或变量，例如：\n• folder1/folder2\n• {year}/{month}\n• Documents/{primary_group}"
                }
            
            # 规则3: 分隔符前后不能是空的文本框
            if current_type == 'separator':
                # 检查前一个组件（如果是文本框且为空）
                if (prev_type == 'text' and 
                    position > 0 and
                    hasattr(self.component_list[position - 1].widget_instance, 'text') and
                    not self.component_list[position - 1].widget_instance.text().strip()):
                    return {
                        'valid': False,
                        'message': "分隔符前的路径段为空，请先输入文件夹名称或添加变量。"
                    }
                
                # 检查后一个组件（如果是文本框且为空）
                if (position < len(self.component_list) - 1 and 
                    self.component_list[position + 1].component_type == 'text' and
                    hasattr(self.component_list[position + 1].widget_instance, 'text') and
                    not self.component_list[position + 1].widget_instance.text().strip()):
                    return {
                        'valid': False,
                        'message': "分隔符后的路径段为空，请输入文件夹名称或添加变量。"
                    }
            
            # 规则4: 文本框与分隔符的组合检查
            if prev_type == 'text' and current_type == 'separator':
                # 检查前面的文本框是否为空
                if (position > 0 and
                    hasattr(self.component_list[position - 1].widget_instance, 'text') and
                    not self.component_list[position - 1].widget_instance.text().strip()):
                    return {
                        'valid': False,
                        'message': "当前路径段为空，请先输入文件夹名称或添加变量，然后再插入分隔符。"
                    }
        
        # 所有检查通过
        return {'valid': True, 'message': ''}


class FileCopyWorker(QThread):
    """
    文件复制工作线程
    """
    progress = Signal(int)
    finished = Signal(bool, str)
    
    def __init__(self, source_files, allocator_instance):
        super().__init__()
        self.source_files = source_files
        self.allocator = allocator_instance
        
    def run(self):
        try:
            total_files = len(self.source_files)
            successful = 0
            
            for i, source_file in enumerate(self.source_files):
                try:
                    # 生成目标路径
                    destination_path = self.allocator.execute(source_file)
                    
                    # 复制文件
                    copier = file_manager.current_copying_instance(source_file)
                    if copier.copy_initiator((destination_path,)):
                        successful += 1
                    
                    # 更新进度
                    progress_percent = int((i + 1) / total_files * 100)
                    self.progress.emit(progress_percent)
                    
                except Exception as e:
                    print(f"处理文件 {source_file} 时出错: {e}")
                    continue
            
            success_rate = successful / total_files if total_files > 0 else 0
            message = f"完成! 成功处理 {successful}/{total_files} 个文件"
            self.finished.emit(success_rate > 0.8, message)
            
        except Exception as e:
            self.finished.emit(False, f"处理过程中出现错误: {str(e)}")


class FileClassifierGUI(QMainWindow):
    """
    文件分类器主界面类
    
    这是应用程序的主窗口控制器，负责整个图形用户界面的管理和协调。
    集成了模板编辑、变量选择、文件处理和系统配置等所有功能模块。
    
    主要职责：
    1. 界面布局管理：创建和组织各个功能面板
    2. 用户交互处理：响应用户操作和事件
    3. 数据流控制：协调界面与后端的数据交换
    4. 状态同步：维护界面状态的一致性
    5. 错误处理：提供用户友好的错误反馈
    
    界面结构：
    - 左侧面板：变量选择和插件配置
    - 右侧面板：模板编辑和目录预览
    - 底部面板：文件处理和进度显示
    
    设计模式：
    - MVC架构：清晰的模型-视图-控制器分离
    - 组件化：高度模块化的UI组件
    - 事件驱动：基于信号槽的松耦合通信
    """
    
    def __init__(self) -> None:
        """
        初始化主窗口
        
        执行完整的初始化流程，包括分类器初始化和界面构建。
        如果分类器初始化失败，会显示配置向导帮助用户完成设置。
        """
        super().__init__()
        self.allocator: Optional['allocator.Allocator'] = None  # 文件分类器实例
        self.init_allocator()
        self.init_ui()
        
    def init_allocator(self):
        """初始化文件分类器"""
        try:
            import module.config as config
            import module.allocator as allocator
            config_instance = config.Config()
            target_folder = config_instance.get_config("target_folder")
            self.allocator = allocator.Allocator(target_folder)
        except Exception as e:
            dialog = ConfigInitDialog(self)
            result = dialog.exec()
            if result == QDialog.DialogCode.Rejected:
                # 如果用户完成了配置初始化，重新尝试加载分类器
                sys.exit(1)
            elif result == QDialog.DialogCode.Accepted:
                self.init_allocator()
            
    def init_ui(self) -> None:
        """
        初始化主窗口的用户界面
        
        构建完整的应用程序界面，包括所有功能面板和交互组件。
        采用分割器布局，提供可调整的左右面板结构。
        
        界面结构：
        - 窗口主体：1200x800像素，居中显示
        - 分割器布局：左右两个可调整大小的面板
        - 左侧面板：变量选择和插件配置
        - 右侧面板：模板编辑和目录预览
        
        组件创建顺序：
        1. 窗口基础设置：标题、尺寸、位置
        2. 中央容器：主要内容区域
        3. 分割器布局：左右面板分割
        4. 模板编辑器：核心编辑组件（优先创建）
        5. 变量面板：左侧功能面板
        6. 模板面板：右侧功能面板
        7. 布局配置：面板比例和约束
        
        设计原则：
        - 左轻右重：左侧面板较窄，右侧面板较宽
        - 响应式：面板可根据内容调整大小
        - 无障碍：支持键盘导航和屏幕阅读器
        - 一致性：统一的间距和视觉风格
        
        创建顺序说明：
        模板编辑器需要优先创建，因为变量面板的某些功能
        需要引用模板编辑器实例进行交互。
        
        Note:
            - 界面创建过程中可能需要较长时间
            - 组件创建失败会影响相关功能但不会阻止启动
            - 布局配置会在所有组件创建完成后进行
        """
        self.setWindowTitle("文件分类器 - 可视化模板构建器")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # 首先创建模板编辑器（在创建变量面板之前）
        self.template_editor = TemplateEditor(self.allocator)
        
        # 左侧：变量面板
        self.create_variables_panel(splitter)
        
        # 右侧：模板编辑和预览面板
        self.create_template_panel(splitter)
        
        # 设置分割器比例
        splitter.setSizes([400, 800])
        
        # 状态栏
        self.statusBar().showMessage("准备就绪")
        
    def call_plugin_gui(self, variable_name: str, gui_key: str):
        """调用插件的GUI功能"""
        if not self.allocator:
            QMessageBox.warning(self, "错误", "分类器未初始化")
            return
            
        try:
            # 获取所有可用变量信息
            variables_info = self.allocator.show_available_variables()
            
            # 查找包含该变量的插件
            target_plugin = None
            for plugin_info in variables_info:
                for var_info in plugin_info['variables']:
                    if var_info['name'] == variable_name:
                        target_plugin = plugin_info
                        break
                if target_plugin:
                    break
            
            if not target_plugin:
                QMessageBox.warning(self, "错误", f"未找到变量 '{variable_name}' 对应的插件")
                return
            
            # 获取插件的GUI信息
            gui_info = target_plugin.get('gui', {})
            if gui_key not in gui_info:
                QMessageBox.warning(self, "错误", f"插件 '{target_plugin['plugin_name']}' 没有 '{gui_key}' 功能")
                return
            
            # 调用插件的GUI功能
            gui_function = gui_info[gui_key]
            if gui_function is None:
                QMessageBox.information(self, "提示", f"功能 '{gui_key}' 尚未实现")
                return
            
            if callable(gui_function):
                # 调用插件的GUI函数，传递主窗口作为父窗口
                result = gui_function(parent=self)
                if result:
                    self.statusBar().showMessage(f"已完成 {target_plugin['plugin_name']} 的 {gui_key} 配置")
            else:
                QMessageBox.warning(self, "错误", f"功能 '{gui_key}' 不是可调用的函数")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"调用插件GUI时发生错误: {str(e)}")
    
    def create_variables_panel(self, parent):
        """创建变量选择面板"""
        # 变量面板使用QGroupBox统一样式
        variables_group = QGroupBox("可用变量")
        variables_layout = QVBoxLayout(variables_group)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 变量容器
        variables_container = QWidget()
        container_layout = QVBoxLayout(variables_container)
        
        # 获取并显示变量
        self.load_variables(container_layout)
        
        # 添加分隔符按钮
        separator_btn = QPushButton("添加目录分隔符 (/)")
        separator_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFF3E0;
                border: 2px solid #FF9800;
                border-radius: 6px;
                padding: {UI_SPACING['button_padding']}px;
                margin: {UI_SPACING['layout_normal']}px;
                color: #F57C00;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #FFE0B2;
            }}
            QPushButton:pressed {{
                background-color: #FFCC02;
            }}
        """)
        separator_btn.clicked.connect(self.template_editor.insert_separator)
        container_layout.addWidget(separator_btn)
        
        # 添加弹性空间
        container_layout.addStretch()
        
        scroll_area.setWidget(variables_container)
        variables_layout.addWidget(scroll_area)
        
        parent.addWidget(variables_group)
        
    def load_variables(self, layout):
        """加载并显示变量"""
        try:
            if not self.allocator:
                error_label = QLabel("分类器未初始化")
                error_label.setStyleSheet("color: red; padding: 10px;")
                layout.addWidget(error_label)
                return
                
            variables_info = self.allocator.show_available_variables()
            
            for plugin_info in variables_info:
                # 插件组标题
                group_box = QGroupBox(f"{plugin_info['plugin_name']} - {plugin_info['description']}")
                group_box.setStyleSheet("""
                    QGroupBox {
                        font-weight: bold;
                        border: 2px solid #CCC;
                        border-radius: 5px;
                        margin-top: 10px;
                        padding-top: 10px;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        left: 10px;
                        padding: 0 5px 0 5px;
                    }
                """)
                
                group_layout = QVBoxLayout(group_box)
                
                # 获取插件的GUI信息
                plugin_gui_info = plugin_info.get('gui', {})
                
                # 添加变量
                for var_info in plugin_info['variables']:
                    var_widget = VariableWidget(
                        var_info['name'], 
                        var_info['description'],
                        plugin_gui_info  # 传递GUI信息
                    )
                    var_widget.clicked.connect(self.template_editor.insert_variable)
                    group_layout.addWidget(var_widget)
                
                layout.addWidget(group_box)
                
        except Exception as e:
            error_label = QLabel(f"加载变量时出错: {str(e)}")
            error_label.setStyleSheet("color: red; padding: 10px;")
            layout.addWidget(error_label)
            
    def create_template_panel(self, parent):
        """创建模板编辑和预览面板"""
        template_widget = QWidget()
        template_layout = QVBoxLayout(template_widget)
        
        # 输出目录选择器
        output_group = QGroupBox("输出目录设置")
        output_layout = QHBoxLayout(output_group)
        
        # 目录输入框
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("选择输出目录...")
        
        # 设置当前目录
        try:
            config_instance = config.Config()
            current_target = config_instance.get_config("target_folder")
            self.output_dir_edit.setText(current_target)
        except:
            self.output_dir_edit.setText("")
        
        self.output_dir_edit.textChanged.connect(self.on_output_dir_changed)
        output_layout.addWidget(self.output_dir_edit)
        
        # 浏览按钮
        browse_btn = QPushButton("浏览...")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self.browse_output_directory)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #606060;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #707070;
            }
            QPushButton:pressed {
                background-color: #505050;
            }
        """)
        output_layout.addWidget(browse_btn)
        
        template_layout.addWidget(output_group)
        
        # 模板编辑区使用QGroupBox
        template_group = QGroupBox("路径模板编辑器")
        template_editor_layout = QVBoxLayout(template_group)
        
        # 模板编辑器（已在 init_ui 中创建，这里只需要添加到布局）
        self.template_editor.template_changed.connect(self.on_template_changed)
        template_editor_layout.addWidget(self.template_editor)
        
        # 控制按钮行
        buttons_layout = QHBoxLayout()
        
        # 清空按钮
        clear_btn = QPushButton("清空模板")
        clear_btn.clicked.connect(self.template_editor.clear_template)
        buttons_layout.addWidget(clear_btn)
        
        # 测试按钮
        test_btn = QPushButton("测试模板")
        test_btn.clicked.connect(self.test_template)
        buttons_layout.addWidget(test_btn)
        
        # 设置模板按钮
        apply_btn = QPushButton("保存模板")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        apply_btn.clicked.connect(self.save_template)
        buttons_layout.addWidget(apply_btn)
        
        template_editor_layout.addLayout(buttons_layout)
        template_layout.addWidget(template_group)
        
        # 预览区域
        preview_group = QGroupBox("目录结构预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_tree = QTreeWidget()
        self.preview_tree.setHeaderLabel("预览目录结构")
        
        # 获取系统调色板
        palette = self.palette()
        
        # 使用系统主题色彩
        self.preview_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {palette.color(QPalette.ColorRole.Base).name()};
                alternate-background-color: {palette.color(QPalette.ColorRole.AlternateBase).name()};
                color: {palette.color(QPalette.ColorRole.Text).name()};
                border: 1px solid {palette.color(QPalette.ColorRole.Mid).name()};
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', monospace;
                selection-background-color: {palette.color(QPalette.ColorRole.Highlight).name()};
                selection-color: {palette.color(QPalette.ColorRole.HighlightedText).name()};
            }}
            QTreeWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {palette.color(QPalette.ColorRole.Mid).name()};
            }}
            QTreeWidget::item:selected {{
                background-color: {palette.color(QPalette.ColorRole.Highlight).name()};
                color: {palette.color(QPalette.ColorRole.HighlightedText).name()};
            }}
            QTreeWidget::item:hover {{
                background-color: {palette.color(QPalette.ColorRole.Light).name()};
            }}
            QTreeWidget::branch:has-siblings:!adjoins-item {{
                border-image: url(vline.png) 0;
            }}
            QTreeWidget::branch:has-siblings:adjoins-item {{
                border-image: url(branch-more.png) 0;
            }}
            QTreeWidget::branch:!has-children:!has-siblings:adjoins-item {{
                border-image: url(branch-end.png) 0;
            }}
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {{
                border-image: none;
                image: url(branch-closed.png);
            }}
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings  {{
                border-image: none;
                image: url(branch-open.png);
            }}
        """)
        
        preview_layout.addWidget(self.preview_tree)
        
        template_layout.addWidget(preview_group)
        
        # 文件处理区域
        file_group = QGroupBox("文件处理")
        file_layout = QVBoxLayout(file_group)
        
        # 文件选择按钮
        select_files_btn = QPushButton("选择要处理的文件")
        select_files_btn.clicked.connect(self.select_files)
        file_layout.addWidget(select_files_btn)
        
        # 选中文件列表
        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(150)
        file_layout.addWidget(self.files_list)
        
        # 处理区域
        process_layout = QHBoxLayout()

        # 哈希配置显示框
        hash_info_group = QGroupBox("完整性校验:")
        hash_info_layout = QHBoxLayout(hash_info_group)
        hash_info_group.setFixedWidth(200)

        hash_info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                padding: 0px;
            }
        """)


        hash_info_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hash_info_text = QLineEdit()
        hash_info_text.setReadOnly(True)

        # 加载哈希配置
        try:
            if hasattr(self, 'allocator') and self.allocator:
                config_instance = config.Config()
                self.__hash_func = config_instance.get_config("hash_check_enable")
                if self.__hash_func:
                    self.__hash_func = self.__hash_func.upper()
                    hash_info_text.setText(f"{self.__hash_func}")
                    hash_info_text.setStyleSheet("""
                        QLineEdit {
                            border: none;
                            background-color: transparent;
                            color: #90ee90;
                        }
                    """)
                else:
                    hash_info_text.setText("未启用")
                    hash_info_text.setStyleSheet("""
                        QLineEdit {
                            border: none;
                            background-color: transparent;
                            color: red;
                        }
                    """)
        except Exception as e:
            hash_info_text.setText(f"配置读取错误: {str(e)}")
        
        hash_info_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hash_info_text.setEnabled(False)

        process_btn = QPushButton("开始处理文件")
        process_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 10px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        process_btn.clicked.connect(self.process_files)

        process_btn.setFixedHeight(45)
        hash_info_group.setFixedSize(200, 45)

        hash_info_layout.addWidget(hash_info_text)
        process_layout.addWidget(process_btn)
        process_layout.addWidget(hash_info_group)

        file_layout.addLayout(process_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        file_layout.addWidget(self.progress_bar)
        
        template_layout.addWidget(file_group)
        
        # 添加弹性空间
        template_layout.addStretch()
        
        parent.addWidget(template_widget)
        
    def on_template_changed(self):
        """模板内容改变时的处理"""
        template = self.template_editor.get_template()
        if template:
            try:
                # 清空当前树
                self.preview_tree.clear()
                
                # 创建示例文件来展示目录结构
                sample_files = [
                    "document.pdf", "image.jpg", "video.mp4", 
                    "music.mp3", "archive.zip", "text.txt"
                ]
                
                # 构建目录结构预览
                self.build_directory_preview(template, sample_files)
                
                # 展开所有节点
                self.preview_tree.expandAll()
                
            except Exception as e:
                # 如果出错，创建一个错误节点
                error_item = QTreeWidgetItem(["模板解析错误: " + str(e)])
                error_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_MessageBoxCritical))
                self.preview_tree.addTopLevelItem(error_item)
        else:
            # 模板为空时显示提示
            self.preview_tree.clear()
            hint_item = QTreeWidgetItem(["在上方构建模板以查看目录结构预览..."])
            hint_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_MessageBoxInformation))
            self.preview_tree.addTopLevelItem(hint_item)
            
    def build_directory_preview(self, template: str, sample_files: list):
        """构建目录结构预览"""
        # 用于存储目录结构的字典
        dir_structure = {}
        
        for sample_file in sample_files:
            try:
                # 模拟生成目标路径
                target_path = self.simulate_path_generation(template, sample_file)
                
                # 解析路径层级
                path_parts = target_path.split('/')
                current_dict = dir_structure
                
                # 构建嵌套字典结构
                for i, part in enumerate(path_parts):
                    if part not in current_dict:
                        current_dict[part] = {}
                    if i == len(path_parts) - 1:
                        # 最后一级是文件
                        current_dict[part] = sample_file
                    else:
                        current_dict = current_dict[part]
                        
            except Exception as e:
                # 如果某个文件处理失败，创建错误节点
                error_item = QTreeWidgetItem([f"处理 {sample_file} 时出错: {str(e)}"])
                error_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_MessageBoxWarning))
                self.preview_tree.addTopLevelItem(error_item)
        
        # 将字典转换为树形控件
        self.dict_to_tree(dir_structure, self.preview_tree)
        
    def simulate_path_generation(self, template: str, sample_file: str) -> str:
        """模拟路径生成过程"""
        
        # 获取文件信息
        filename = os.path.basename(sample_file)
        name, ext = os.path.splitext(filename)
        ext = ext.lstrip('.')
        
        # 定义示例变量值
        sample_variables = {
            'filename': name,
            'ext': ext,
            'date': '2024-01',
            'year': '2024',
            'month': '01',
            'day': '15',
            'size': 'medium',
            'type': 'document' if ext in ['pdf', 'doc', 'txt'] else 
                   'image' if ext in ['jpg', 'png', 'gif'] else
                   'video' if ext in ['mp4', 'avi', 'mov'] else
                   'audio' if ext in ['mp3', 'wav', 'flac'] else 'other'
        }
        
        # 替换模板中的变量
        result = template
        for var_name, var_value in sample_variables.items():
            result = result.replace(f'{{{var_name}}}', str(var_value))
        
        return result
        
    def dict_to_tree(self, data_dict: dict, parent_widget):
        """将字典结构转换为树形控件"""
        for key, value in data_dict.items():
            if isinstance(value, dict):
                # 这是一个目录
                folder_item = QTreeWidgetItem([key])
                folder_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_DirIcon))
                parent_widget.addTopLevelItem(folder_item) if hasattr(parent_widget, 'addTopLevelItem') else parent_widget.addChild(folder_item)
                
                # 递归处理子目录
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, dict):
                        sub_folder_item = QTreeWidgetItem([sub_key])
                        sub_folder_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_DirIcon))
                        folder_item.addChild(sub_folder_item)
                        self.dict_to_tree_recursive(sub_value, sub_folder_item)
                    else:
                        # 这是文件
                        file_item = QTreeWidgetItem([sub_value])
                        file_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))
                        folder_item.addChild(file_item)
            else:
                # 这是一个文件
                file_item = QTreeWidgetItem([value])
                file_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))
                parent_widget.addTopLevelItem(file_item) if hasattr(parent_widget, 'addTopLevelItem') else parent_widget.addChild(file_item)
                
    def dict_to_tree_recursive(self, data_dict: dict, parent_item):
        """递归处理字典到树的转换"""
        for key, value in data_dict.items():
            if isinstance(value, dict):
                folder_item = QTreeWidgetItem([key])
                folder_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_DirIcon))
                parent_item.addChild(folder_item)
                self.dict_to_tree_recursive(value, folder_item)
            else:
                file_item = QTreeWidgetItem([value])
                file_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))
                parent_item.addChild(file_item)
            
    def test_template(self):
        """测试当前模板"""
        if not self.allocator:
            QMessageBox.warning(self, "错误", "分类器未初始化")
            return
            
        template = self.template_editor.get_template()
        if not template:
            QMessageBox.warning(self, "警告", "请先输入模板!")
            return
            
        # 选择测试文件
        test_file, _ = QFileDialog.getOpenFileName(
            self, "选择测试文件", "", "所有文件 (*.*)"
        )
        
        if test_file:
            try:
                # 更新分类器模板
                self.allocator.update_template(template)
                
                # 执行测试
                result = self.allocator.execute(test_file)
                
                QMessageBox.information(
                    self, "测试结果", 
                    f"源文件: {test_file}\n\n目标路径: {result}"
                )
                
            except Exception as e:
                QMessageBox.critical(self, "测试失败", f"测试模板时出错: {str(e)}")
                
    def save_template(self):
        """应用当前模板"""
        if not self.allocator:
            QMessageBox.warning(self, "错误", "分类器未初始化")
            return
            
        template = self.template_editor.get_template()
        if not template:
            QMessageBox.warning(self, "警告", "请先输入模板!")
            return
        
                # 应用模板
        try:
            self.allocator.update_template(template)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用模板失败: {str(e)}")
            return
        
        try:
            self.template_editor.save_template_to_config()
            QMessageBox.information(self, "成功", "模板已保存!")
            
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存模板时出错: {str(e)}")
            
    def select_files(self):
        """选择要处理的文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择要处理的文件", "", "所有文件 (*.*)"
        )
        
        if files:
            self.files_list.clear()
            for file_path in files:
                item = QListWidgetItem(file_path)
                self.files_list.addItem(item)
                
    def process_files(self):
        """处理选中的文件"""
        if not self.allocator:
            QMessageBox.warning(self, "错误", "分类器未初始化")
            return
            
        if self.files_list.count() == 0:
            QMessageBox.warning(self, "警告", "请先选择要处理的文件!")
            return
            
        template = self.template_editor.get_template()
        if not template:
            QMessageBox.warning(self, "警告", "请先设置模板!")
            return
        
        if not self.__hash_func:
            class RequestForcePermit(QDialog):
                def __init__(self, parent=None):
                    super(RequestForcePermit, self).__init__(parent)
                    self.setWindowTitle('完整性校验未启用!')
                    
                    # 创建布局
                    layout = QVBoxLayout(self)
                    
                    # 添加说明文本
                    label = QLabel('本软件为加速复制过程使用了文件分块的方法，此方法在不启用完整性校验的情况下有小概率导致文件损坏。检测到完整性校验功能未启用，是否选择继续复制文件？')
                    label.setWordWrap(True)
                    label.setFixedWidth(300)
                    layout.addWidget(label)
                    
                    # 创建按钮布局
                    button_layout = QHBoxLayout()
                    
                    okButton = QPushButton('继续复制', self)
                    okButton.clicked.connect(self.accept)
                    button_layout.addWidget(okButton)
                    
                    cancelButton = QPushButton('取消复制', self)
                    cancelButton.clicked.connect(self.reject)
                    button_layout.addWidget(cancelButton)
                    
                    layout.addLayout(button_layout)

            dialog = RequestForcePermit()

            result = dialog.exec()
            if result == QDialog.DialogCode.Rejected:
                return

            

        # 应用模板
        try:
            self.allocator.update_template(template)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用模板失败: {str(e)}")
            return
        
        # 保存模板到配置
        self.template_editor.save_template_to_config()
            
        # 获取文件列表
        source_files = []
        for i in range(self.files_list.count()):
            source_files.append(self.files_list.item(i).text())
            
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 开始处理
        self.copy_worker = FileCopyWorker(source_files, self.allocator)
        self.copy_worker.progress.connect(self.progress_bar.setValue)
        self.copy_worker.finished.connect(self.on_copy_finished)
        self.copy_worker.start()
        
        self.statusBar().showMessage("正在处理文件...")
        
    def on_copy_finished(self, success: bool, message: str):
        """文件复制完成处理"""
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, "完成", message)
        else:
            QMessageBox.warning(self, "注意", message)
            
        self.statusBar().showMessage("处理完成")

    def browse_output_directory(self):
        """浏览选择输出目录"""
        current_dir = self.output_dir_edit.text() or os.path.expanduser("~")
        
        selected_dir = QFileDialog.getExistingDirectory(
            self, 
            "选择输出目录", 
            current_dir
        )
        
        if selected_dir:
            self.output_dir_edit.setText(selected_dir)
            
    def on_output_dir_changed(self):
        """输出目录改变时的处理"""
        new_dir = self.output_dir_edit.text().strip()
        
        if not new_dir:
            return
            
        # 检查目录是否存在
        if not os.path.exists(new_dir):
            try:
                os.makedirs(new_dir, exist_ok=True)
                self.statusBar().showMessage(f"已创建目录: {new_dir}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法创建目录: {str(e)}")
                return
        
        # 更新配置
        try:
            config_instance = config.Config()
            config_instance.set_config("target_folder", new_dir)
            
            # 重新初始化allocator
            self.allocator = allocator.Allocator(new_dir)
            
            # 更新模板编辑器的allocator引用
            self.template_editor.allocator = self.allocator
            
            # 重新加载变量面板
            self.refresh_variables_panel()
            
            self.statusBar().showMessage(f"输出目录已设置为: {new_dir}")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"更新配置失败: {str(e)}")
            
    def refresh_variables_panel(self):
        """刷新变量面板"""
        # 这个方法可以在后续需要时实现，目前暂时为空
        pass
        

def main() -> None:
    """
    应用程序主入口函数
    
    负责创建和启动GUI应用程序，包括样式设置、主题配置和窗口创建。
    采用深色主题设计，提供现代化的视觉体验。
    
    启动流程：
    1. QApplication创建：初始化Qt应用程序框架
    2. 样式设置：应用Fusion风格，现代化外观
    3. 主题配置：设置深色调色板和全局样式
    4. 主窗口创建：初始化FileClassifierGUI实例
    5. 窗口显示：显示主窗口并启动事件循环
    
    主题特色：
    - 深色基调：减少眼部疲劳，适合长时间使用
    - 高对比度：确保文本和界面元素清晰可见
    - 现代风格：圆角边框、渐变色彩和阴影效果
    - 一致性：统一的颜色方案和视觉语言
    
    颜色规范：
    - 主背景：#2c2c2c (深灰色)
    - 组件背景：#353535 (中灰色)
    - 文本颜色：#ffffff (白色)
    - 强调色：#42a5f5 (蓝色)
    - 边框色：#555555 (浅灰色)
    
    样式系统：
    - 全局样式表：统一的组件样式
    - 调色板：系统级别的颜色配置
    - 组件样式：针对特定组件的自定义样式
    
    错误处理：
    - 优雅退出：确保应用程序正常关闭
    - 资源清理：自动清理Qt资源和内存
    - 异常捕获：处理启动过程中的异常
    
    Note:
        - 此函数是应用程序的唯一入口点
        - 修改主题和样式请在此函数中进行
        - 应用程序退出时会自动执行清理工作
    """
    app = QApplication(sys.argv)
    
    # 设置应用程序样式为深灰色主题
    app.setStyle('Fusion')
    
    # 设置深灰色调色板
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(0, 0, 0))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
    app.setPalette(dark_palette)
    
    # 设置全局样式表
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2c2c2c;
            color: #ffffff;
        }
        QWidget {
            background-color: #2c2c2c;
            color: #ffffff;
        }
        QGroupBox {
            background-color: #353535;
            border: 1px solid #555555;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #ffffff;
        }
        QScrollArea {
            background-color: #2c2c2c;
            border: 1px solid #555555;
        }
        QListWidget {
            background-color: #353535;
            border: 1px solid #555555;
            color: #ffffff;
        }
        QStatusBar {
            background-color: #353535;
            color: #ffffff;
        }
    """)
    
    # 创建主窗口
    window = FileClassifierGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
