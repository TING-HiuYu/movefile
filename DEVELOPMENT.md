# 文件分类器开发文档

## 目录
1. [项目概述](#项目概述)
2. [架构设计](#架构设计)
3. [核心模块详解](#核心模块详解)
4. [插件系统](#插件系统)
5. [GUI界面设计](#gui界面设计)
6. [配置系统](#配置系统)
7. [文件操作系统](#文件操作系统)
8. [开发指南](#开发指南)
9. [API参考](#api参考)

## 项目概述

文件分类器是一个基于插件架构的智能文件分类和管理系统。它允许用户通过可视化界面构建文件分类规则，并自动将文件复制到相应的目录结构中。

### 设计目标
- **模块化**: 采用插件化架构，便于功能扩展
- **用户友好**: 提供直观的可视化界面
- **高性能**: 支持多线程文件操作和完整性验证
- **可配置**: 灵活的配置系统，支持持久化存储

### 技术栈
- **Python 3.8+**: 主要开发语言
- **PySide6**: GUI框架
- **PyYAML**: 配置文件处理
- **hashlib**: 文件完整性验证
- **concurrent.futures**: 多线程支持

## 架构设计

### 整体架构

```
┌─────────────────┐    ┌─────────────────┐
│   GUI Interface │    │   CLI Interface │
│    (gui.py)     │    │   (main.py)     │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     │
        ┌─────────────────────────┐
        │     Allocator Core      │
        │    (allocator.py)       │
        └─────────┬───────────────┘
                  │
     ┌────────────┼────────────┐
     │            │            │
┌────▼────┐  ┌───▼────┐  ┌────▼────┐
│ Config  │  │ Plugin │  │  File   │
│ Manager │  │ System │  │ Manager │
│         │  │        │  │         │
└─────────┘  └────────┘  └─────────┘
```

### 模块依赖关系

```
main.py
├── gui.py
│   ├── config_init_gui.py
│   └── module/
│       ├── allocator.py
│       ├── config.py
│       └── file_manager.py
└── module/
    ├── allocator.py
    ├── config.py
    ├── file_manager.py
    └── directory_tools/
        ├── file_date_read.py
        ├── file_size_classifier.py
        └── manual_grouping.py
```

## 核心模块详解

### Allocator (allocator.py)

文件分类器的核心控制器，负责协调各个组件的工作。

#### 主要职责
1. **插件管理**: 动态加载和管理插件
2. **模板解析**: 解析路径模板并生成目标路径
3. **文件分析**: 缓存文件分析结果，提高性能
4. **变量管理**: 管理所有可用的分类变量

#### 关键方法

```python
class Allocator:
    def __init__(self, target_folder: str, plugins_dir: Optional[str] = None)
    def execute(self, filepath: str) -> str
    def update_template(self, template: str) -> bool
    def show_available_variables(self) -> List[Dict[str, Any]]
    def interactive_template_setup(self) -> Optional[str]
```

#### 工作流程

1. **初始化阶段**:
   ```python
   # 注册基础变量（filename, ext等）
   self._register_base_variables()
   
   # 发现插件变量
   self._discover_plugin_variables()
   
   # 加载插件
   self._load_plugins()
   
   # 执行插件初始化
   self._execute_init_functions()
   ```

2. **执行阶段**:
   ```python
   def execute(self, filepath: str) -> str:
       # 分析文件（缓存结果）
       self._analyze_file(filepath)
       
       # 解析模板
       result = self._parse_template(self.current_template, filepath)
       
       # 生成完整路径
       return os.path.join(self.__dest_dir, result)
   ```

### Config (config.py)

配置管理系统，提供类型安全的配置读写操作。

#### 设计特点
- **类型验证**: 强制配置项类型检查
- **自动保存**: 配置更改时自动写入文件
- **插件配置**: 独立的插件配置管理

#### 配置结构

```python
class ValidatedDict:
    allowed_keys = {
        "target_folder": str,      # 目标文件夹路径
        "hash_check_enable": str,  # 启用的哈希算法
        "pluginConfig": dict,      # 插件配置字典
        "pathTemplate": str,       # 路径模板字符串
    }
```

#### 使用示例

```python
config = Config()

# 基本配置操作
config.set_config("target_folder", "/path/to/output")
target = config.get_config("target_folder")

# 插件配置操作
plugin_config = {
    "groups": [
        {
            "name": "图片文件",
            "strategies": [...]
        }
    ]
}
config.set_plugin_config("manual_grouping", plugin_config)
```

### File Manager (file_manager.py)

文件操作管理器，提供高效的文件复制和完整性验证功能。

#### 核心功能
- **多线程复制**: 大文件分块并行复制
- **完整性验证**: 支持多种哈希算法
- **进度显示**: 集成rich库显示复制进度

#### 实现原理

1. **多线程复制算法**:
   ```python
   # 计算分块策略
   num_chunks = min(max_workers, (file_size + chunk_size - 1) // chunk_size)
   base_chunk_size = file_size // num_chunks
   
   # 并行复制各个分块
   with ThreadPoolExecutor(max_workers=max_workers) as executor:
       futures = []
       for i in range(num_chunks):
           future = executor.submit(copy_chunk, start_pos, end_pos, i)
           futures.append(future)
   
   # 合并分块文件
   with open(target_path, 'wb') as target_file:
       for i in range(num_chunks):
           with open(f"{target_path}.part{i}", 'rb') as chunk_file:
               target_file.write(chunk_file.read())
   ```

2. **完整性验证**:
   ```python
   def get_hash(self, filepath: str) -> str:
       if self.__hash_func__ == "":
           return ""
       
       with rich.progress.open(filepath, 'rb') as f:
           hash = hashlib.new(self.__hash_func__)
           for chunk in iter(lambda: f.read(16384), b''):
               hash.update(chunk)
           return hash.hexdigest()
   ```

## 插件系统

### 插件架构

插件系统是本项目的核心特性，允许用户轻松扩展文件分类功能。

#### 插件接口

```python
# 插件注册格式
addon_variables = [
    {
        "name": "variable_name",        # 变量名
        "description": "变量描述",      # 变量说明
        "method": function_reference,   # 执行函数
        "gui": {                       # GUI集成
            "setting": gui_function,   # 设置界面函数
        }
    },
]
```

#### 生命周期函数

```python
def plugin_name_init():
    """插件初始化函数"""
    pass

def plugin_name_delete():
    """插件清理函数"""
    pass

def plugin_name_reload():
    """插件重新加载函数"""
    pass
```

### 内置插件解析

#### 1. 日期分组插件 (file_date_read.py)

**功能**: 基于文件时间戳进行分类

**提供变量**:
- `{year}`: 年份 (2024)
- `{month}`: 月份 (01-12)
- `{day}`: 日期 (01-31)
- `{date}`: 完整日期 (2024-01-15)

**实现原理**:
```python
def get_file_date(filepath: str) -> str:
    try:
        # 获取文件修改时间
        mtime = os.path.getmtime(filepath)
        date_obj = datetime.fromtimestamp(mtime)
        return date_obj.strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")
```

#### 2. 大小分组插件 (file_size_classifier.py)

**功能**: 根据文件大小进行分类

**分类规则**:
- tiny: < 1MB
- small: 1MB - 10MB
- medium: 10MB - 100MB
- large: 100MB - 1GB
- huge: > 1GB

**实现原理**:
```python
def classify_by_size(filepath: str) -> str:
    try:
        size = os.path.getsize(filepath)
        if size < 1024 * 1024:  # < 1MB
            return "tiny"
        elif size < 10 * 1024 * 1024:  # < 10MB
            return "small"
        # ... 其他分类
    except:
        return "unknown"
```

#### 3. 手动分组插件 (manual_grouping.py)

**功能**: 基于用户定义规则进行分类

**支持的匹配类型**:
- 包含字符串匹配
- 通配符匹配 (*, ?)
- 正则表达式匹配

**配置结构**:
```python
{
    "groups": [
        {
            "name": "图片文件",
            "strategies": [
                {
                    "type": "regex",
                    "pattern": r"\.(jpg|jpeg|png|gif)$",
                    "range_filter": ""
                }
            ]
        }
    ]
}
```

## GUI界面设计

### 界面架构

GUI采用分离式设计，主要包含以下组件：

1. **主窗口** (FileClassifierGUI)
2. **配置初始化对话框** (ConfigInitDialog)
3. **模板编辑器** (TemplateEditor)
4. **变量面板** (VariableWidget)

### 核心组件解析

#### TemplateEditor

模板编辑器是GUI的核心组件，实现了可视化的路径模板构建功能。

**主要特性**:
- 基于链表的组件管理
- 实时预览目录结构
- 智能文本框插入
- 组件验证和错误处理

**组件链表设计**:
```python
class TemplateComponentNode:
    def __init__(self, component_type: str, widget_instance):
        self.component_type = component_type  # 'variable', 'separator', 'text'
        self.widget_instance = widget_instance

class TemplateComponentList(list):
    def __save_change(self, new_list):
        # 1. 自动添加文本输入框
        expanded_list = self._auto_add_text_input_to_list(new_list)
        
        # 2. 清理和校验
        cleaned_list = self._clean_and_validate_list(expanded_list)
        
        # 3. 更新列表并重新渲染
        self.clear()
        self.extend(cleaned_list)
        self.template_editor.rerender()
```

#### 配置初始化对话框

首次运行时出现的配置向导，简化用户设置过程。

**功能**:
- 输出目录选择
- 完整性校验算法选择
- 配置验证和保存

**实现要点**:
```python
class ConfigInitDialog(QDialog):
    def save_config(self):
        # 验证输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 保存配置
        config_data = {
            "target_folder": output_dir,
            "hash_check_enable": hash_algorithm,
            "pathTemplate": "{filename}",
            "pluginConfig": {}
        }
        
        with open("config.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, allow_unicode=True)
```

## 配置系统

### 配置文件结构

```yaml
# config.yaml
target_folder: "/path/to/output"        # 输出目录
pathTemplate: "{type}/{year}/{filename}" # 路径模板
hash_check_enable: "sha256"             # 完整性校验算法
pluginConfig:                           # 插件配置
  manual_grouping:
    groups:
      - name: "图片文件"
        strategies:
          - type: "regex"
            pattern: "\\.(jpg|jpeg|png|gif)$"
            range_filter: ""
```

### 配置验证机制

配置系统采用严格的类型验证：

```python
class ValidatedDict(Dict[str, Any]):
    allowed_keys: Dict[str, type] = {
        "target_folder": str,
        "hash_check_enable": str,
        "pluginConfig": dict,
        "pathTemplate": str,
    }
    
    def __setitem__(self, key: str, value: Any):
        # 验证键名
        if key not in self.allowed_keys:
            raise KeyError(f"配置键 '{key}' 不被允许")
        
        # 验证类型
        if not isinstance(value, self.allowed_keys[key]):
            raise TypeError(f"类型不匹配")
        
        # 保存配置
        super().__setitem__(key, value)
        self.__write_config()
```

## 文件操作系统

### 多线程复制策略

针对不同大小的文件采用不同的复制策略：

1. **小文件** (< 2MB): 单线程直接复制
2. **大文件** (≥ 2MB): 多线程分块复制

### 完整性验证

支持多种哈希算法：
- MD5
- SHA1
- SHA256
- SHA512

验证流程：
1. 复制前计算源文件哈希
2. 复制完成后计算目标文件哈希
3. 比较哈希值，不匹配则删除目标文件

## 开发指南

### 开发环境设置

```bash
# 1. 克隆项目
git clone <repository-url>
cd file-classifier

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行项目
python main.py --mode gui
```

### 代码规范

1. **文档字符串**: 所有公共函数必须有文档字符串
2. **类型提示**: 使用类型提示提高代码可读性
3. **错误处理**: 适当的异常处理和日志记录
4. **测试**: 为新功能编写单元测试

### 插件开发流程

1. **创建插件文件**: 在 `module/directory_tools/` 下创建新的 `.py` 文件
2. **实现分类函数**: 编写接受文件路径并返回分类结果的函数
3. **注册变量**: 通过 `addon_variables` 列表注册插件
4. **测试插件**: 在GUI中测试插件功能
5. **编写文档**: 为插件编写使用说明

### 调试技巧

1. **启用调试模式**: 在代码中添加 `print` 语句进行调试
2. **使用IDE调试器**: 推荐使用PyCharm或VSCode进行断点调试
3. **查看日志**: 检查控制台输出的错误信息
4. **测试模板**: 使用"测试模板"功能验证分类逻辑

## API参考

### Allocator API

```python
class Allocator:
    def __init__(self, target_folder: str, plugins_dir: Optional[str] = None):
        """初始化分类器"""
        
    def execute(self, filepath: str) -> str:
        """执行文件分类，返回目标路径"""
        
    def update_template(self, template: str) -> bool:
        """更新路径模板"""
        
    def show_available_variables(self) -> List[Dict[str, Any]]:
        """获取所有可用变量信息"""
        
    def get_file_data(self, filepath: str) -> Dict[str, Any]:
        """获取文件分析数据"""
        
    def clear_cache(self):
        """清空文件分析缓存"""
```

### Config API

```python
class Config:
    def get_config(self, key: str) -> Any:
        """获取配置项"""
        
    def set_config(self, key: str, value: Any):
        """设置配置项"""
        
    def get_plugin_config(self, plugin_name: str, default: Any = None) -> Any:
        """获取插件配置"""
        
    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]):
        """设置插件配置"""
        
    def get_path_template(self) -> str:
        """获取路径模板"""
        
    def set_path_template(self, template: str):
        """设置路径模板"""
```

### FileManager API

```python
class current_copying_instance:
    def __init__(self, source_file_path: str):
        """初始化文件复制实例"""
        
    def copy_initiator(self, destinations: Tuple[str, ...]) -> bool:
        """启动文件复制到多个目标位置"""
        
    def get_hash(self, filepath: str) -> str:
        """计算文件哈希值"""
```

---

## 人工智能声明

本文档由AI生成，将随着项目的发展持续更新。如有疑问或建议，请提交Issue或Pull Request。
