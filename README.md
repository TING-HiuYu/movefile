# 智能文件分类器

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![GUI](https://img.shields.io/badge/GUI-PySide6-orange.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

一个基于插件架构的智能文件分类和管理系统

[功能特性](#功能特性) • [快速开始](#快速开始) • [使用说明](#使用说明) • [插件开发](#插件开发) • [开发文档](#开发文档)

</div>

---

## 功能特性

### 核心功能
- **插件化架构** - 支持自定义分类策略，轻松扩展功能
- **可视化界面** - 基于PySide6的现代化GUI，支持可视化模板构建
- **多线程复制** - 大文件高效复制，支持多线程并行处理
- **完整性校验** - 支持多种哈希算法(MD5/SHA1/SHA256/SHA512)验证文件完整性
- **灵活模板** - 可视化路径模板编辑器，实时预览目录结构

### 分类策略
- **日期分组** - 按文件创建/修改日期自动分类
- **大小分组** - 根据文件大小智能分类
- **手动分组** - 基于文件名模式的自定义分组规则
- **智能识别** - 支持通配符、正则表达式匹配

### 技术特性
- **配置持久化** - YAML格式配置文件，易于管理
- **双模式运行** - 支持GUI和命令行两种操作模式
- **高性能** - 多线程处理，适合批量文件操作
- **数据安全** - 文件完整性验证，确保数据不丢失

---

## 快速开始

### 系统要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)
- **内存**: 至少 512MB 可用内存
- **磁盘**: 至少 100MB 可用空间

### 安装

#### 方法一：克隆仓库
```bash
# 克隆项目
git clone https://github.com/yourusername/file-classifier.git
cd file-classifier

# 安装依赖
pip install -r requirements.txt
```

#### 方法二：直接下载
1. 下载项目压缩包并解压
2. 在项目目录中运行：
```bash
pip install -r requirements.txt
```

### 快速体验

#### GUI模式（推荐）
```bash
python main.py --mode gui
```

#### 命令行模式
```bash
python main.py --mode cli
```

---

## 使用说明

### GUI界面使用

#### 1. 初始配置
首次运行时，系统会弹出配置向导：
- 选择输出目录（文件将被分类到此目录）
- 选择完整性校验算法（可选MD5、SHA1、SHA256等）
- 点击"确定"保存配置

#### 2. 构建分类模板
在主界面左侧的"可用变量"面板中：
- 点击变量按钮添加动态路径元素
- 使用"添加目录分隔符 (/)"按钮创建目录层级
- 在文本框中输入固定的路径文本

**示例模板**：
```
图片文件/{year}/{month}/{filename}
```
将会创建如下目录结构：
```
图片文件/
├── 2024/
│   ├── 01/
│   │   ├── photo1.jpg
│   │   └── photo2.png
│   └── 02/
│       └── photo3.gif
```

#### 3. 预览和测试
- 模板编辑完成后，下方会自动显示目录结构预览
- 使用"测试模板"功能验证分类效果
- 点击"保存模板"应用配置

#### 4. 批量处理文件
- 点击"选择要处理的文件"选择需要分类的文件
- 查看状态指示器确认完整性校验设置
- 点击"开始处理文件"执行分类操作

### 命令行使用

```bash
# 启动命令行模式
python main.py --mode cli

# 按提示操作：
# 1. 设置路径模板
# 2. 选择要处理的文件
# 3. 确认并执行分类
```

### 配置文件

配置文件位于 `config.yaml`，主要配置项：

```yaml
# 输出目录
target_folder: /path/to/output

# 路径模板
pathTemplate: "{type}/{year}/{filename}"

# 完整性校验（可选：md5, sha1, sha256, sha512, 或空字符串表示不校验）
hash_check_enable: "sha256"

# 插件配置
pluginConfig:
  manual_grouping:
    groups:
      - name: "图片文件"
        strategies:
          - type: "regex"
            pattern: "\\.(jpg|jpeg|png|gif|bmp)$"
```

---

## 插件开发

### 插件架构

本系统采用插件化架构，每个插件都是独立的Python模块，位于 `module/directory_tools/` 目录下。插件通过 `addon_variables` 列表注册变量和功能。

### 创建新插件

#### 1. 基本插件结构
在 `module/directory_tools/` 目录下创建 `your_plugin.py`：

```python
#!/usr/bin/env python3
"""
Your Plugin - 插件描述
"""

def your_function(filepath: str) -> str:
    """
    插件主函数
    
    Args:
        filepath: 文件路径
        
    Returns:
        分类结果字符串
    """
    # 你的分类逻辑
    import os
    filename = os.path.basename(filepath)
    # 处理逻辑...
    return "分类结果"

# 注册插件变量
addon_variables = [
    {
        "name": "your_variable",
        "description": "变量描述",
        "method": your_function,
        "gui": {
            "setting": your_gui_function if GUI_AVAILABLE else None,
        }
    },
]
```

#### 2. 插件生命周期函数（可选）

```python
def your_plugin_init():
    """插件初始化函数"""
    print("插件初始化")

def your_plugin_delete():
    """插件清理函数"""
    print("插件清理")

def your_plugin_reload():
    """插件重新加载函数"""
    print("插件重新加载")
```

#### 3. GUI集成（可选）

```python
try:
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel
    GUI_AVAILABLE = True
    
    def your_gui_function(parent=None):
        """插件设置界面"""
        dialog = QDialog(parent)
        dialog.setWindowTitle("插件设置")
        layout = QVBoxLayout(dialog)
        
        label = QLabel("这是插件设置界面")
        layout.addWidget(label)
        
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button)
        
        return dialog.exec()
        
except ImportError:
    GUI_AVAILABLE = False
```

### 内置插件说明

#### 1. 日期分组插件 (`file_date_read.py`)
- 提供 `{year}`, `{month}`, `{day}`, `{date}` 等日期变量
- 基于文件的创建时间或修改时间进行分类
- 支持自定义日期格式

#### 2. 大小分组插件 (`file_size_classifier.py`)
- 提供 `{size}` 变量
- 将文件按大小分为：tiny, small, medium, large, huge
- 可自定义大小阈值

#### 3. 手动分组插件 (`manual_grouping.py`)
- 提供 `{manual_grouping}` 变量
- 支持基于文件名的自定义分组规则
- 支持包含字符串、通配符、正则表达式匹配
- 内置GUI配置界面

---

## 开发文档

### 项目结构

```
file-classifier/
├── main.py                 # 主程序入口
├── gui.py                  # GUI主界面
├── config_init_gui.py      # 配置初始化界面
├── config.yaml             # 配置文件
├── requirements.txt        # Python依赖
├── module/                 # 核心模块
│   ├── __init__.py
│   ├── allocator.py        # 文件分类器核心
│   ├── config.py           # 配置管理
│   ├── file_manager.py     # 文件操作管理
│   └── directory_tools/    # 插件目录
│       ├── __init__.py
│       ├── file_date_read.py      # 日期分组插件
│       ├── file_size_classifier.py # 大小分组插件
│       └── manual_grouping.py     # 手动分组插件
└── docs/                   # 文档目录
```

### 核心模块说明

#### Allocator (allocator.py)
文件分类器的核心类，负责：
- 插件的动态加载和管理
- 路径模板的解析和执行
- 文件分析数据的缓存管理
- 提供交互式模板设置功能

主要方法：
- `execute(filepath)` - 执行文件分类，返回目标路径
- `update_template(template)` - 更新路径模板
- `show_available_variables()` - 获取所有可用变量信息
- `interactive_template_setup()` - 命令行交互式模板设置

#### Config (config.py)
配置管理类，负责：
- YAML配置文件的读写操作
- 配置项的类型验证
- 插件配置的管理

主要方法：
- `get_config(key)` - 获取配置项
- `set_config(key, value)` - 设置配置项
- `get_plugin_config(plugin_name, default)` - 获取插件配置
- `set_plugin_config(plugin_name, config)` - 设置插件配置

#### FileManager (file_manager.py)
文件操作管理类，负责：
- 多线程文件复制
- 文件完整性校验
- 大文件的分块处理

主要方法：
- `copy_initiator(destinations)` - 启动文件复制到多个目标
- `get_hash(filepath)` - 计算文件哈希值

### 开发环境搭建

```bash
# 克隆仓库
git clone https://github.com/yourusername/file-classifier.git
cd file-classifier

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 安装开发依赖
pip install -r requirements.txt
```

### 代码规范

- 使用 PEP 8 代码风格
- 函数和类需要完整的文档字符串
- 变量名使用英文，注释使用中文
- 提交前运行测试确保功能正常

---

## 贡献指南

我们欢迎所有形式的贡献！

### 报告问题
- 使用 GitHub Issues 报告 bug
- 提供详细的错误信息和复现步骤
- 包含系统环境信息

### 功能建议
- 在 Issues 中提出新功能建议
- 详细描述功能需求和使用场景
- 欢迎提供设计思路

### 代码贡献
1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 插件贡献
- 开发新的分类插件
- 完善现有插件功能
- 提供插件使用文档

---

## 致谢

- 感谢所有贡献者的努力
- 基于 [PySide6](https://www.qt.io/qt-for-python) 构建GUI界面
- 使用 [PyYAML](https://pyyaml.org/) 处理配置文件
- 使用 [rich](https://github.com/Textualize/rich) 提供进度显示

---

## 联系我们

- 项目主页: [GitHub Repository](https://github.com/yourusername/file-classifier)
- 问题反馈: [GitHub Issues](https://github.com/yourusername/file-classifier/issues)

---

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## 生成式人工智能工具使用声明

本项目的部分代码，由生成式人工智能生成，并参与代码调试工作。
本文档由AI生成，将随着项目的发展持续更新。如有疑问或建议，请提交Issue或Pull Request。