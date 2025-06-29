# 文件自动分类和管理系统

一个基于插件架构的智能文件分类系统，支持多种分类策略和灵活的路径模板配置。

## 🚀 主要特性

- **插件化架构**：可扩展的文件分析插件系统
- **智能分类**：支持按日期、大小、文件类型、手动规则等多维度分类
- **灵活模板**：支持复杂的路径模板语法，包括变量替换、数组访问、默认值等
- **高效复制**：多线程文件复制，支持大文件处理和完整性验证
- **配置管理**：YAML 配置文件，支持类型验证和自动保存

## 📁 项目结构

```
movefile/
├── main.py                    # 主程序入口
├── config.yaml                # 配置文件
├── README.md                  # 项目文档
└── module/                    # 核心模块
    ├── __init__.py
    ├── config.py               # 配置管理
    ├── allocator.py            # 文件分类器
    ├── file_manager.py         # 文件管理器
    └── directory_tools/        # 插件目录
        ├── __init__.py
        ├── file_date_read.py   # 日期提取插件
        ├── file_size_classifier.py  # 大小分类插件
        └── manual_grouping.py  # 手动分组插件
```

## 🛠️ 安装与配置

### 依赖要求

```bash
pip install PyYAML rich exifread tkinter
```

### 配置文件

编辑 `config.yaml` 文件设置系统参数：

```yaml
hash_check_enable: md5          # 哈希校验算法
manual_devide: false            # 是否启用手动分组
seperate_by_date: true          # 是否按日期分离
seperate_by_suffix: true        # 是否按文件后缀分离
target_folder: /path/to/target  # 目标文件夹路径
```

## 🚀 快速开始

### 基本使用

1. **运行程序**
   ```bash
   python main.py
   ```

2. **设置路径模板**
   程序会显示所有可用的变量和插件，然后提示您输入路径模板

3. **选择文件**
   使用图形界面选择要分类的文件

4. **自动处理**
   系统会根据模板自动分类并复制文件

### 路径模板语法

系统支持丰富的模板语法：

```python
# 基础变量
"{filename}"                    # 完整文件名
"{basename}"                    # 不含扩展名的文件名
"{extension}"                   # 文件扩展名

# 插件变量
"{file_date_read}"             # 文件日期 (YYYY-MM-DD)
"{file_size_classifier}"       # 文件大小分类
"{manual_group}"               # 手动分组

# 数组访问
"{manual_group[0]}"            # 第一个分组
"{manual_group[1]}"            # 第二个分组

# 默认值
"{primary_group:未分类}"        # 如果变量为空则使用默认值
"{manual_group[1]:备用分组}"    # 数组访问 + 默认值

# 组合示例
"{file_date_read}/{file_size_classifier}/{filename}"
"Documents/{basename}-{file_date_read}.{extension}"
```

## 🔌 插件系统

### 内置插件

1. **file_date_read**: 从 EXIF 或文件修改时间提取日期
2. **file_size_classifier**: 按文件大小分类 (tiny/small/medium/large/huge)
3. **manual_grouping**: 支持复杂规则的手动分组

### 创建自定义插件

在 `module/directory_tools/` 目录下创建新的 Python 文件：

```python
"""
自定义插件模板
"""

def my_custom_classifier(filepath: str) -> str:
    """
    自定义分类函数
    
    Args:
        filepath: 文件路径
        
    Returns:
        分类结果
    """
    # 你的分类逻辑
    return "分类结果"

def init():
    """插件初始化函数"""
    pass

def delete():
    """插件清理函数"""
    pass

def reload():
    """插件重新加载函数"""
    pass

# 注册插件变量
addon_variables = {
    "my_custom_classifier": my_custom_classifier,
}

# 变量描述
addon_variables_description = {
    "my_custom_classifier": "我的自定义分类器",
}
```

## 📋 API 文档

### Allocator 类

```python
from module.allocator import Allocator

# 创建分类器实例
allocator = Allocator(target_folder="/path/to/target")

# 交互式设置模板
template = allocator.interactive_template_setup()

# 执行文件分析
result = allocator.execute(filepath, template)

# 批量处理
results = allocator.batch_execute(filepaths, template)

# 重新加载插件
allocator.reload_plugin("plugin_name")
```

### Config 类

```python
from module.config import Config

# 创建配置实例
config = Config()

# 获取配置
value = config.get_config("key", default_value)

# 设置配置
config.set_config("key", value)
```

### FileManager 类

```python
from module.file_manager import current_copying_instance

# 创建复制实例
copier = current_copying_instance(source_path)

# 执行复制
success = copier.copy_initiator((destination1, destination2))

# 计算哈希
hash_value = copier.get_hash(filepath)
```

## 🛡️ 安全特性

- **完整性验证**：使用 MD5/SHA 哈希验证文件复制完整性
- **多线程安全**：支持并发文件处理
- **错误恢复**：自动清理失败的部分文件
- **配置验证**：严格的配置类型检查

## 🎯 使用场景

- **照片整理**：按拍摄日期自动分类照片
- **文档管理**：按文件类型和大小分类文档
- **下载整理**：自动分类下载文件夹中的文件
- **备份系统**：智能备份文件到不同目录

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [exifread](https://github.com/ianare/exifread) - EXIF 数据提取
- [rich](https://github.com/Textualize/rich) - 终端美化
- [PyYAML](https://pyyaml.org/) - YAML 配置解析

## 📞 联系方式

如有问题或建议，请通过 Issues 页面联系我们。

---

**注意**: 在使用前请确保已备份重要文件，虽然系统有完整性验证，但建议在重要数据上谨慎使用。
