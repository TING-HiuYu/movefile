# 使用示例

## 快速开始

### 1. 基本文件分类

```python
from module.allocator import Allocator
from module.config import Config

# 创建分类器
config = Config()
allocator = Allocator(config.get_config("target_folder"))

# 设置简单模板
allocator.update_template("{extension[1:]}/{filename}")

# 分析文件
result = allocator.execute("example.pdf")
print(result)  # 输出: /target/pdf/example.pdf
```

### 2. 交互式模板设置

```python
# 使用交互式界面设置模板
template = allocator.interactive_template_setup()
```

界面会显示：
```
=== 文件分类器 - 可用变量列表 ===

插件: file_date_read
描述: 文件日期读取插件
可用变量:
  - file_date_read: 获取文件的日期，优先使用 EXIF 信息

插件: file_size_classifier  
描述: 文件大小分类插件
可用变量:
  - file_size_classifier: 根据文件大小分类

请输入路径模板: {file_date_read}/{file_size_classifier}/{filename}
```

### 3. 高级模板语法

```python
# 日期 + 大小分类
allocator.update_template("{file_date_read}/{file_size_classifier}/{filename}")

# 使用默认值
allocator.update_template("{primary_group:未分类}/{filename}")

# 数组访问
allocator.update_template("{manual_group[0]}/{basename}-{file_date_read}.{extension}")

# 复杂模板
allocator.update_template("Archives/{file_date_read}/{file_size_classifier}/{basename}-backup.{extension}")
```

### 4. 批量处理文件

```python
files = [
    "/path/to/photo1.jpg",
    "/path/to/document.pdf", 
    "/path/to/video.mp4"
]

# 批量执行
results = allocator.batch_execute(files)
for original, target in zip(files, results):
    print(f"{original} -> {target}")
```

### 5. 手动分组设置

```python
from module.directory_tools.manual_grouping import setup_global_grouping_rules

# 设置分组规则
rules = {
    "工作文档": ["*.doc", "*.pdf", "*report*"],
    "图片": ["*.jpg", "*.png", "IMG*"],
    "视频": ["*.mp4", "*.avi"]
}

setup_global_grouping_rules(rules)

# 使用手动分组
allocator.update_template("{manual_group[0]:其他}/{filename}")
```

### 6. 文件复制

```python
from module.file_manager import current_copying_instance

source_file = "/path/to/source.jpg"
target_path = allocator.execute(source_file)

# 创建复制实例
copier = current_copying_instance(source_file)

# 执行复制（支持多目标）
success = copier.copy_initiator((target_path,))

if success:
    print("文件复制成功！")
else:
    print("文件复制失败！")
```

### 7. 插件管理

```python
# 查看可用变量
variables = allocator.show_available_variables()
for plugin in variables:
    print(f"插件: {plugin['plugin_name']}")
    for var in plugin['variables']:
        print(f"  - {var['name']}: {var['description']}")

# 重新加载插件
allocator.reload_plugin("file_date_read")

# 重新加载所有插件
allocator.reload_all_plugins()

# 查看当前状态
print(allocator.show_current_status())
```

### 8. 配置管理

```python
from module.config import Config

config = Config()

# 查看当前配置
print("目标文件夹:", config.get_config("target_folder"))
print("哈希验证:", config.get_config("hash_check_enable"))

# 修改配置
config.set_config("target_folder", "/new/target/path")
config.set_config("hash_check_enable", "sha256")
```

## 模板语法参考

### 基础变量
- `{filename}`: 完整文件名 (如: document.pdf)
- `{basename}`: 文件名不含扩展名 (如: document)  
- `{extension}`: 扩展名含点号 (如: .pdf)
- `{ext}`: 扩展名不含点号 (如: pdf)

### 插件变量
- `{file_date_read}`: 文件日期 (YYYY-MM-DD)
- `{file_size_classifier}`: 大小分类 (tiny/small/medium/large/huge)
- `{manual_group}`: 手动分组结果 (数组)

### 高级语法
- `{variable:default}`: 默认值
- `{array[0]}`: 数组第一个元素
- `{array[1]:backup}`: 数组第二个元素，如果不存在使用默认值

### 完整示例模板

```python
# 按日期和类型分类
"{file_date_read}/{extension[1:]}/{filename}"

# 按大小和分组分类  
"{file_size_classifier}/{manual_group[0]:其他}/{filename}"

# 复杂分类策略
"Archive/{file_date_read}/{file_size_classifier}/{manual_group[0]:未分类}/{basename}-{file_date_read}.{extension}"

# 照片专用
"Photos/{file_date_read}/IMG-{basename}.{extension}"

# 文档专用
"Documents/{manual_group[0]:其他文档}/{file_date_read}/{filename}"
```

## 错误处理

```python
try:
    result = allocator.execute("nonexistent.file")
except FileNotFoundError:
    print("文件不存在")
except Exception as e:
    print(f"处理错误: {e}")

# 检查模板有效性
template = "{unknown_variable}/{filename}"
used_vars = allocator.parse_template_variables(template)
available_vars = set()
for plugin in allocator.show_available_variables():
    for var in plugin['variables']:
        available_vars.add(var['name'])

unknown_vars = used_vars - available_vars
if unknown_vars:
    print(f"警告: 未知变量 {unknown_vars}")
```
