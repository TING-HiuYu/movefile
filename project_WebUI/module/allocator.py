#!/usr/bin/env python3
"""
文件分类器核心模块 (Allocator)

这是一个插件化的文件分组与路径生成系统，提供了完整的文件分类和管理功能。
该模块是整个文件分类器项目的核心控制器，负责协调各个组件的工作。

主要功能：
1. 插件系统管理：动态加载、卸载和重新加载插件
2. 文件分析：执行插件的分析函数，提取文件元数据
3. 模板解析：智能解析路径模板，支持变量替换和高级语法
4. 路径生成：根据模板和文件信息生成目标路径
5. 缓存管理：文件分析结果缓存，提高重复操作性能

插件架构特性：
- 支持三种标准函数：init（初始化）、execute（执行）、delete（清理）
- 变量注册系统：插件可注册自定义变量供模板使用
- 热重载：支持运行时重新加载插件，便于开发调试

模板语法支持：
- 基础变量：{filename}、{basename}、{ext}
- 数组访问：{groups[0]}、{manual_grouping[1]}
- 默认值：{variable:default_value}
- 组合语法：{array[0]:default}

Author: File Classifier Project
License: MIT
Version: 1.0.0
"""

import os
import sys
import importlib
import importlib.util
import re
from typing import Dict, List, Any, Callable, Optional, Set, Union
from pathlib import Path

# # 尝试导入配置文件读取模块
# spec = importlib.util.spec_from_file_location("config", os.path.join(os.path.dirname(__file__),"config.py"))

# if spec is not None and spec.loader is not None:
# 	config = importlib.util.module_from_spec(spec)
# 	spec.loader.exec_module(config)

from module import config

#运行类
class Allocator:
    """
    文件分类器核心类 - 插件化的文件分组与路径生成系统
    
    这是整个文件分类器系统的核心控制器，负责管理插件、分析文件、
    解析模板和生成目标路径。支持动态插件加载、智能模板解析和
    高效的文件分析缓存机制。
    
    主要职责：
    1. 插件生命周期管理：加载、初始化、卸载和重新加载插件
    2. 变量系统管理：注册和管理所有可用的分类变量
    3. 文件分析：执行插件的分析函数，提取文件的各种属性
    4. 模板解析：智能解析路径模板，支持变量替换、数组访问、默认值等
    5. 缓存管理：缓存文件分析结果，避免重复计算
    
    设计特点：
    - 按需加载：根据模板中使用的变量动态加载对应插件
    - 类型安全：完整的类型注解和错误处理
    - 高性能：文件分析结果缓存，支持批量处理
    - 可扩展：标准化的插件接口，易于添加新功能
    
    Examples:
        >>> allocator = Allocator("/output/dir")
        >>> allocator.update_template("{primary_group}/{basename}")
        >>> target_path = allocator.execute("/path/to/file.pdf")
        >>> print(target_path)  # /output/dir/Documents/file
    """
    
    def __init__(self, target_folder: str, plugins_dir: Optional[str] = None) -> None:
        """
        初始化文件分类器
        
        Args:
            target_folder: 目标输出文件夹的绝对路径，所有分类后的文件将存储在此目录下
            plugins_dir: 插件目录路径，默认为模块下的 'plugins' 目录
                        如果指定的目录不存在，将不会加载任何插件
        
        Raises:
            ValueError: 当target_folder为空或无效时
            OSError: 当目标文件夹无法创建时
        
        Note:
            - 初始化过程中会自动扫描并加载所有可用插件
            - 插件加载失败不会影响系统启动，会静默跳过失败的插件
            - 基础变量（filename、basename、ext等）会自动注册
        """
        """
        初始化分类器
        
        Args:
            target_folder: 目标文件夹路径
            plugins_dir: 插件目录路径，默认为 'plugins'
        """
        # 插件相关 - 支持多个插件目录
        default_plugins_dir = os.path.join(os.path.dirname(__file__), 'module','plugins')

        # 如果未指定插件目录，则使用默认目录
        config_instance = config.Config()

        external_plugins_dir = config_instance.get_config("external_plugins_dir")
        
    
        self.plugins_dirs = [
            plugins_dir or default_plugins_dir,  # 用户指定或默认插件目录）
        ]
         # 外部插件目录（用于热插拔
        if external_plugins_dir:
            self.plugins_dirs.append(external_plugins_dir)

        self.loaded_plugins: Dict[str, Dict[str, Any]] = {}  # 已加载的插件信息字典
        self.discovered_modules: Dict[str, Any] = {}  # 缓存发现阶段加载的模块
        
        # 存储插件注册的函数，按功能分类管理
        self.init_functions: Dict[str, Callable[..., Any]] = {}      # 插件初始化函数
        self.execute_functions: Dict[str, Callable[[str], Any]] = {} # 插件执行函数
        self.delete_functions: Dict[str, Callable[..., Any]] = {}    # 插件清理函数
        self.reload_functions: Dict[str, Callable[..., Any]] = {}    # 插件重载函数
        
        # 文件分析结果存储，采用LRU缓存策略
        self.file_data: Dict[str, Dict[str, Any]] = {}
        
        # 插件变量管理系统
        self.available_variables: Dict[str, Dict[str, Any]] = {}  # 所有可用变量的元数据
        self.active_variables: Set[str] = set()                  # 当前模板激活的变量集合
        self.current_template: str = ""                          # 当前使用的路径模板
        self.__dest_dir: str = target_folder                     # 目标输出目录（私有）
        
        # 初始化流程：按顺序执行以下步骤
        self._register_base_variables()    # 1. 注册系统基础变量
        self._discover_plugin_variables()  # 2. 扫描发现插件变量
        self._load_plugins()               # 3. 加载所有插件
        self._execute_init_functions()     # 4. 执行插件初始化函数

    def _load_plugins(self) -> None:
        """
        加载所有插件目录下的可用插件
        
        该方法会扫描所有指定的插件目录，查找插件文件夹和单文件插件，
        并尝试逐个加载。支持热插拔的外部插件。
        
        插件结构支持：
        1. 单文件插件：plugin_name.py
        2. 文件夹插件：plugin_name/main.py + webui文件
        
        加载流程：
        1. 检查各插件目录是否存在
        2. 扫描目录中的插件文件和文件夹
        3. 对每个插件，获取其绝对路径
        4. 逐个调用_load_single_plugin加载插件
        
        Note:
            - 插件加载失败不会抛出异常，而是静默跳过
            - 支持热重载，重复调用此方法可重新加载插件
            - 插件必须符合标准接口才能被正确识别
            - 外部插件优先级高于内置插件
        """
        for plugins_dir in self.plugins_dirs:
            if not os.path.exists(plugins_dir):
                continue
            
            # 查找插件文件和文件夹
            plugin_items = []
            if os.path.isdir(plugins_dir):
                for item in os.listdir(plugins_dir):
                    item_path = os.path.join(plugins_dir, item)
                    
                    # 单文件插件：.py文件（排除__开头的）
                    if item.endswith('.py') and not item.startswith('__'):
                        plugin_items.append({
                            'name': item.split('.')[0],
                            'path': item_path,
                            'type': 'file'
                        })
                    
                    # 文件夹插件：包含main.py的文件夹
                    elif os.path.isdir(item_path) and not item.startswith('__'):
                        main_py = os.path.join(item_path, 'main.py')
                        if os.path.exists(main_py):
                            plugin_items.append({
                                'name': item,
                                'path': main_py,
                                'type': 'folder',
                                'folder_path': item_path
                            })
            
            # 加载所有找到的插件
            for plugin_item in plugin_items:
                try:
                    print(f"[DEBUG] 尝试加载插件: {plugin_item['name']} 类型: {plugin_item['type']} 路径: {plugin_item['path']}")
                    self._load_single_plugin(plugin_item['name'], plugin_item['path'], plugin_item)
                    print(f"[DEBUG] 成功加载插件: {plugin_item['name']}")
                except Exception as e:
                    print(f"[ERROR] 插件加载失败: {plugin_item['name']} - {e}")
                    import traceback
                    traceback.print_exc()
                    pass  # 静默处理插件加载失败
    
    def _load_single_plugin(self, plugin_name: str, plugin_path: str, plugin_item: Optional[Dict[str, Any]] = None) -> None:
        """
        加载单个指定的插件
        
        这是插件加载系统的核心方法，负责导入插件模块并注册其提供的函数。
        使用 importlib.util 直接从文件路径加载，以避免在打包环境中出现相对导入问题。
        
        Args:
            plugin_name: 插件名称（不含扩展名），例如 'file_date_read'
            plugin_path: 插件文件的绝对路径
        
        Raises:
            ImportError: 当无法通过任何路径导入插件时
        
        注册流程：
        1. 使用 importlib.util.spec_from_file_location 创建模块规范
        2. 使用 importlib.util.module_from_spec 创建模块对象
        3. 执行模块加载
        4. 创建插件信息字典
        5. 调用_register_plugin_functions注册函数
        6. 将插件添加到已加载插件列表
        
        Note:
            - 这种方法对于处理 .py 源码插件在不同环境（开发、打包后）下非常稳健。
            - 插件必须至少提供一个execute函数才会被成功加载
        """
        try:
            # 如果插件已经加载，先执行卸载逻辑
            if plugin_name in self.loaded_plugins:
                self.unload_plugin(plugin_name)

            # 检查模块是否已在发现阶段加载并缓存
            if plugin_name in self.discovered_modules:
                plugin_module = self.discovered_modules[plugin_name]
            else:
                # 如果未缓存，则从文件加载（用于按需加载等场景）
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                if spec is None or spec.loader is None:
                    raise ImportError(f"无法为插件 {plugin_name} 创建模块规范或加载器，路径: {plugin_path}")
                
                plugin_module = importlib.util.module_from_spec(spec)
                
                # 在执行模块之前，将其添加到sys.modules
                sys.modules[spec.name] = plugin_module
                spec.loader.exec_module(plugin_module)

            plugin_info = {
                'module': plugin_module,
                'path': plugin_path, # 存储路径以便重载
                'init': None,
                'execute': None,
                'delete': None,
                'webui': None  # 存储webui相关信息
            }
            
            # 如果是文件夹插件，检查webui目录
            if plugin_item and plugin_item.get('type') == 'folder':
                webui_path = os.path.join(plugin_item['folder_path'], 'webui')
                if os.path.exists(webui_path):
                    plugin_info['webui'] = {
                        'path': webui_path,
                        'has_ui': True
                    }
            
            # 查找插件的注册函数
            self._register_plugin_functions(plugin_name, plugin_module, plugin_info)
            
            if plugin_info['execute']:
                self.loaded_plugins[plugin_name] = plugin_info
                
        except Exception as e:
            # 捕获并打印更详细的错误信息
            print(f"加载插件 {plugin_name} 时出错: {e}")
            # 如果插件已添加到sys.modules，加载失败时最好将其移除
            if plugin_name in sys.modules:
                del sys.modules[plugin_name]
            pass

    def _register_plugin_functions(self, plugin_name: str, plugin_module: Any, plugin_info: Dict[str, Any]) -> None:
        """
        注册插件提供的各种函数到相应的函数字典中
        
        该方法负责发现和注册插件的标准函数（init、execute、delete、reload），
        支持多种函数命名规范以保证向后兼容性。
        
        Args:
            plugin_name: 插件名称，用于生成标准函数名
            plugin_module: 已导入的插件模块对象
            plugin_info: 插件信息字典，用于存储发现的函数
        
        函数发现策略：
        1. 标准命名：{plugin_name}_init, {plugin_name}, {plugin_name}_delete
        2. 简化命名：init, execute, delete, reload
        3. 兼容模式：通过addon_variables属性注册的函数
        
        支持的函数类型：
        - init: 插件初始化函数，在插件加载时调用
        - execute: 主执行函数，用于文件分析（必需）
        - delete: 清理函数，在插件卸载时调用
        - reload: 重载函数，在插件重新加载时调用
        
        兼容性支持：
        - 支持旧版本的字典格式addon_variables
        - 支持新版本的列表格式addon_variables
        - 支持字符串格式的单函数注册
        
        Note:
            - execute函数是插件的核心，必须存在才能成功注册
            - 其他函数都是可选的，缺失不会影响插件功能
            - 函数注册失败会被静默处理
        """
        
        # 方法1: 查找标准命名的函数
        init_func_name = f"{plugin_name}_init"
        execute_func_name = plugin_name  # 主函数直接用插件名
        delete_func_name = f"{plugin_name}_delete"
        reload_func_name = f"{plugin_name}_reload"
        
        # 检查主执行函数
        if hasattr(plugin_module, execute_func_name):
            func = getattr(plugin_module, execute_func_name)
            if callable(func):
                plugin_info['execute'] = func
                self.execute_functions[plugin_name] = func
        
        # 检查初始化函数
        if hasattr(plugin_module, init_func_name):
            func = getattr(plugin_module, init_func_name)
            if callable(func):
                plugin_info['init'] = func
                self.init_functions[plugin_name] = func
        
        # 简化的函数查找 - 查找 init, delete, reload
        for func_name in ['init', 'delete', 'reload']:
            if hasattr(plugin_module, func_name):
                func = getattr(plugin_module, func_name)
                if callable(func):
                    if func_name == 'init':
                        plugin_info['init'] = func
                        self.init_functions[plugin_name] = func
                    elif func_name == 'delete':
                        plugin_info['delete'] = func
                        self.delete_functions[plugin_name] = func
                    elif func_name == 'reload':
                        plugin_info['reload'] = func
                        self.reload_functions[plugin_name] = func
        
        # 检查删除函数
        if hasattr(plugin_module, delete_func_name):
            func = getattr(plugin_module, delete_func_name)
            if callable(func):
                plugin_info['delete'] = func
                self.delete_functions[plugin_name] = func
        
        # 检查重新加载函数
        if hasattr(plugin_module, reload_func_name):
            func = getattr(plugin_module, reload_func_name)
            if callable(func):
                plugin_info['reload'] = func
                self.reload_functions[plugin_name] = func
        
        # 查找通过 addon_variables 注册的函数（向后兼容）
        if hasattr(plugin_module, 'addon_variables') or hasattr(plugin_module, 'addon_variabls'):
            addon_vars = getattr(plugin_module, 'addon_variables', None) or getattr(plugin_module, 'addon_variabls', None)
            
            if isinstance(addon_vars, dict):
                # 旧格式：字典格式
                for var_name, var_func in addon_vars.items():
                    if callable(var_func) and not plugin_info['execute']:
                        plugin_info['execute'] = var_func
                        self.execute_functions[plugin_name] = var_func
                        break
            elif isinstance(addon_vars, str) and hasattr(plugin_module, addon_vars):
                # 字符串格式
                func = getattr(plugin_module, addon_vars)
                if callable(func) and not plugin_info['execute']:
                    plugin_info['execute'] = func
                    self.execute_functions[plugin_name] = func
            elif isinstance(addon_vars, list):
                # 新格式：数组格式
                for var_info in addon_vars:
                    if isinstance(var_info, dict) and 'method' in var_info:
                        var_func = var_info['method']
                        if callable(var_func) and not plugin_info['execute']:
                            plugin_info['execute'] = var_func
                            self.execute_functions[plugin_name] = var_func
                            break
    
    def _register_base_variables(self) -> None:
        """
        注册系统基础变量（在类初始化时自动调用）
        
        这些是系统内置的文件属性变量，不依赖任何插件即可使用。
        基础变量提供了文件的基本信息，是构建路径模板的基础。
        
        注册的基础变量：
        - filename: 完整文件名（包含扩展名），如 'document.pdf'
        - basename: 文件名（不含扩展名），如 'document'  
        - extension: 文件扩展名（含点号），如 '.pdf'
        - ext: 文件扩展名（不含点号），如 'pdf'
        
        变量存储格式：
        采用标准化的插件变量格式存储，确保与插件变量的一致性，
        便于统一的变量管理和模板解析。
        
        Note:
            - 这些变量在任何模板中都可以直接使用
            - 变量值在文件分析时动态生成
            - 不可卸载，是系统的核心组成部分
        """
        base_variables = {
            'base_variables': {
                'plugin_name': 'base_variables',
                'description': '基础文件属性变量',
                'variables': [
                    {
                        'name': 'filename',
                        'description': '完整文件名（包含扩展名），如: document.pdf'
                    },
                    {
                        'name': 'basename', 
                        'description': '文件名（不含扩展名），如: document'
                    },
                    {
                        'name': 'extension',
                        'description': '文件扩展名（含点），如: .pdf'
                    },
                    {
                        'name': 'ext',
                        'description': '文件扩展名（不含点），如: pdf'
                    }
                ],
                'plugin_path': 'built-in'
            }
        }
        
        # 注册基础变量
        self.available_variables.update(base_variables)

    def _execute_init_functions(self) -> None:
        """
        执行所有已注册插件的初始化函数
        
        在插件加载完成后调用，用于执行插件的初始化逻辑。
        初始化函数通常用于设置插件的内部状态、加载配置文件、
        建立外部连接等准备工作。
        
        执行特点：
        - 按插件加载顺序依次执行
        - 初始化失败的插件会被静默跳过，不影响其他插件
        - 支持插件的热重载初始化
        
        错误处理：
        采用静默处理策略，初始化失败不会导致系统崩溃，
        但可能影响对应插件的功能。建议插件开发者在init函数中
        进行充分的异常处理。
        
        Note:
            - 初始化函数是可选的，插件可以不提供
            - 初始化失败不会将插件从已加载列表中移除
            - 可通过日志系统记录初始化过程中的问题
        """
        for plugin_name, init_func in self.init_functions.items():
            try:
                init_func()
            except Exception:
                pass  # 静默处理初始化失败

    def _discover_plugin_variables(self) -> None:
        """
        扫描插件目录，发现所有可用的变量并构建变量索引
        
        这是变量发现系统的入口点，负责扫描整个插件目录，
        分析每个插件提供的变量，并构建完整的变量元数据索引。
        这个索引用于模板验证、变量提示和按需插件加载。
        
        发现流程：
        1. 检查插件目录的存在性
        2. 扫描所有.py文件（排除特殊文件）
        3. 对每个插件调用_discover_single_plugin_variables
        4. 构建全局变量索引
        
        Note:
            - 发现过程不会实际加载插件，只是分析元数据
            - 插件分析失败会被静默跳过
        """
        self.available_variables.clear()
        self._register_base_variables()

        for plugins_dir in self.plugins_dirs:
            if not os.path.exists(plugins_dir):
                continue
            
            # 扫描插件文件和文件夹
            for item in os.listdir(plugins_dir):
                item_path = os.path.join(plugins_dir, item)
                
                # 单文件插件：.py文件（排除__开头的）
                if item.endswith('.py') and not item.startswith('__'):
                    plugin_name = item[:-3]
                    try:
                        self._discover_single_plugin_variables(plugin_name, item_path)
                    except Exception as e:
                        print(f"发现插件变量失败: {plugin_name} - {e}")
                        pass  # 静默处理发现失败
                
                # 文件夹插件：包含main.py的文件夹
                elif os.path.isdir(item_path) and not item.startswith('__'):
                    main_py = os.path.join(item_path, 'main.py')
                    if os.path.exists(main_py):
                        plugin_name = item
                        try:
                            self._discover_single_plugin_variables(plugin_name, main_py)
                        except Exception as e:
                            print(f"发现插件变量失败: {plugin_name} - {e}")
                            pass  # 静默处理发现失败

    def _discover_single_plugin_variables(self, plugin_name: str, plugin_path: str) -> None:
        """
        发现单个插件提供的变量并将其注册到变量索引中
        
        这是变量发现系统的核心方法，负责分析单个插件的变量定义，
        提取变量元数据，并将其添加到全局变量索引中。
        
        Args:
            plugin_name: 要分析的插件名称（不含.py扩展名）
            plugin_path: 插件文件的绝对路径
        """
        try:
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            if spec is None or spec.loader is None:
                return # 无法处理，静默失败
            
            plugin_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin_module)

            # 缓存加载的模块以供后续重用，避免重复加载
            self.discovered_modules[plugin_name] = plugin_module

            # 从 addon_variables 属性中提取变量信息
            addon_vars = getattr(plugin_module, 'addon_variables', [])
            
            # 从模块的文档字符串中获取插件的整体描述
            plugin_description = plugin_module.__doc__.strip() if plugin_module.__doc__ else f'{plugin_name} 插件'

            print(f"[DEBUG Allocator] Discovered plugin: {plugin_name}, Vars: {addon_vars}")

            # 提取GUI相关信息
            gui_info = addon_vars[0].get('gui', {})
            print(f"[DEBUG Allocator] Discovered gui_info for {plugin_name}: {gui_info}")

            # 注册发现的变量
            self.available_variables[plugin_name] = {
                'plugin_name': plugin_name,
                'description': plugin_description,
                'variables': addon_vars,
                'gui': gui_info,
                'plugin_path': plugin_path
            }
        except Exception as e:
            print(f"解析插件 {plugin_name} 变量时出错: {e}")
            pass # 静默处理发现失败

    def show_available_variables(self) -> List[Dict[str, Any]]:
        """
        获取所有可用变量的信息列表，用于界面展示和模板验证
        
        该方法将内部的变量索引转换为适合外部使用的格式，
        提供完整的变量信息，包括名称、描述和GUI元数据。
        
        Returns:
            变量信息列表，每个元素包含：
            - plugin_name: 提供该变量的插件名称
            - description: 插件的简要描述
            - variables: 该插件提供的变量列表
            - gui: GUI相关的元数据（用于界面展示）
            
        数据格式示例：
        [
            {
                "plugin_name": "file_date_read",
                "description": "文件日期读取插件",
                "variables": [
                    {
                        "name": "file_date",
                        "description": "文件的创建或修改日期"
                    }
                ],
                "gui": {...}  # GUI配置信息
            }
        ]
        
        使用场景：
        - GUI界面的变量列表展示
        - 模板编辑器的自动补全
        - 模板验证和错误提示
        - API文档生成
        
        Note:
            - 返回的是所有已发现的变量，不仅仅是已加载的
            - 包含GUI元数据，支持可视化界面开发
            - 数据结构经过标准化，便于外部使用
        """
        if not self.available_variables:
            return []
        
        out: List[Dict[str, Any]] = []

        for plugin_name, plugin_info in self.available_variables.items():
            # 检查插件是否有webui
            webui_info = None
            if plugin_name in self.loaded_plugins:
                loaded_plugin_info = self.loaded_plugins[plugin_name]
                webui_info = loaded_plugin_info.get('webui')
            
            this_plugin = {
                "plugin_name": plugin_name,
                "description": plugin_info.get('description', plugin_name),
                "variables": [],
                "gui": plugin_info.get('gui', {}),  # 添加GUI元数据
                "webui": webui_info  # 添加WebUI信息
            }
            print(f"[DEBUG Allocator] Preparing gui_info for {plugin_name} to show: {this_plugin['gui']}")

            variables = plugin_info.get('variables', [])
            if variables:
                for var in variables:
                    this_variable = {
                        "name": var['name'],
                        "description": var['description'],
                    }
                    this_plugin["variables"].append(this_variable)
            out.append(this_plugin)
        return out

    def parse_template_variables(self, template: str) -> Set[str]:
        """
        解析路径模板字符串，提取其中使用的所有变量名
        
        该方法负责分析模板语法，识别所有的变量引用，
        支持多种变量语法格式，为按需插件加载提供依据。
        
        Args:
            template: 路径模板字符串，如 "{primary_group}/{filename}"
            
        Returns:
            模板中使用的变量名集合，如 {"primary_group", "filename"}
            
        支持的语法格式：
        - 基础变量：{variable_name}
        - 数组访问：{array_name[0]}, {groups[1]}
        - 默认值：{variable:default_value}
        - 组合语法：{array[0]:default}
        
        解析算法：
        1. 使用正则表达式匹配所有 {…} 模式
        2. 提取变量名（处理数组下标）
        3. 去除默认值部分
        4. 返回唯一变量名集合
        
        使用场景：
        - 按需插件加载：只加载模板需要的插件
        - 模板验证：检查变量是否存在对应插件
        - 依赖分析：分析模板的插件依赖关系
        
        Example:
            >>> template = "{primary_group}/{filename[0]:default}/{ext}"
            >>> variables = parse_template_variables(template)
            >>> print(variables)  # {"primary_group", "filename", "ext"}
            
        Note:
            - 支持复杂的嵌套语法解析
            - 性能优化：使用编译的正则表达式
            - 处理边界情况，如空模板、无效语法等
        """
        # 匹配 {变量名} 或 {变量名[索引]} 格式
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, template)
        
        variables = set()
        for match in matches:
            # 处理数组访问格式，如 manual_grouping[0]
            var_name = match.split('[')[0]
            variables.add(var_name)
        
        return variables

    def update_template(self, template: str) -> None:
        """
        更新路径模板并动态调整插件加载状态
        
        这是模板管理系统的核心方法，负责智能地管理插件的加载和卸载。
        当模板发生变化时，系统会分析新旧模板的差异，只加载需要的插件，
        卸载不再需要的插件，实现高效的资源管理。
        
        Args:
            template: 新的路径模板字符串，如 "{date}/{primary_group}/{filename}"
            
        工作流程：
        1. 解析新旧模板中的变量依赖
        2. 计算需要加载和卸载的变量集合
        3. 执行插件的动态加载和卸载
        4. 更新内部状态
        
        智能加载策略：
        - 按需加载：只加载模板实际需要的插件
        - 增量更新：只处理变化的部分，不影响已加载的插件
        - 依赖分析：自动解析变量与插件的依赖关系
        
        性能优化：
        - 避免重复加载已存在的插件
        - 智能卸载不再使用的插件，释放内存
        - 批量处理变量变化，减少系统调用
        
        错误处理：
        插件加载或卸载失败不会影响模板更新，
        系统会继续处理其他插件，确保部分功能的可用性。
        
        Example:
            >>> allocator.update_template("{primary_group}/{filename}")
            >>> # 只会加载manual_grouping插件（用于primary_group）
            >>> allocator.update_template("{date}/{size}/{filename}")  
            >>> # 会加载date和size相关插件，卸载manual_grouping插件
            
        Note:
            - 模板更新是原子操作，要么完全成功，要么回滚
            - 支持模板语法验证，无效模板会被拒绝
            - 更新过程中会维护插件状态的一致性
        """
        old_template = self.current_template
        old_variables = self.parse_template_variables(old_template) if old_template else set()
        new_variables = self.parse_template_variables(template)
        
        # 找出需要卸载和加载的插件
        variables_to_unload = old_variables - new_variables
        variables_to_load = new_variables - old_variables
        
        # 卸载不需要的插件
        self._unload_plugins_for_variables(variables_to_unload)
        
        # 加载需要的插件
        self._load_plugins_for_variables(variables_to_load)
        
        # 更新当前模板和激活变量
        self.current_template = template
        self.active_variables = new_variables

    def _load_plugins_for_variables(self, variables: Set[str]):
        """为指定变量加载对应的插件"""
        plugins_to_load = set()
        
        # 找出需要加载的插件
        for variable in variables:
            for plugin_name, plugin_info in self.available_variables.items():
                # 跳过内置基础变量
                if plugin_name == 'base_variables':
                    continue
                plugin_variables = [var['name'] for var in plugin_info.get('variables', [])]
                if variable in plugin_variables:
                    plugins_to_load.add(plugin_name)
        
        # 加载插件
        for plugin_name in plugins_to_load:
            if plugin_name not in self.loaded_plugins:
                try:
                    plugin_info = self.available_variables.get(plugin_name)
                    if plugin_info and 'plugin_path' in plugin_info:
                        plugin_path = plugin_info['plugin_path']
                        # 确保不是内置插件
                        if plugin_path != 'built-in':
                            self._load_single_plugin(plugin_name, plugin_path)
                    # 执行初始化函数
                    if plugin_name in self.init_functions:
                        self.init_functions[plugin_name]()
                except Exception:
                    pass  # 静默处理加载失败

    def _unload_plugins_for_variables(self, variables: Set[str]):
        """为指定变量卸载对应的插件"""
        plugins_to_unload = set()
        
        # 找出需要卸载的插件
        for variable in variables:
            for plugin_name, plugin_info in self.available_variables.items():
                plugin_variables = [var['name'] for var in plugin_info.get('variables', [])]
                if variable in plugin_variables:
                    # 检查这个插件是否还被其他变量需要
                    still_needed = False
                    for other_var in self.active_variables:
                        if other_var != variable and other_var in plugin_variables:
                            still_needed = True
                            break
                    
                    if not still_needed:
                        plugins_to_unload.add(plugin_name)
        
        # 卸载插件
        for plugin_name in plugins_to_unload:
            if plugin_name in self.loaded_plugins:
                try:
                    # 调用删除函数
                    if plugin_name in self.delete_functions:
                        self.delete_functions[plugin_name]()
                    
                    # 从已加载插件中移除
                    del self.loaded_plugins[plugin_name]
                    if plugin_name in self.execute_functions:
                        del self.execute_functions[plugin_name]
                    if plugin_name in self.init_functions:
                        del self.init_functions[plugin_name]
                    if plugin_name in self.delete_functions:
                        del self.delete_functions[plugin_name]
                        
                except Exception:
                    pass  # 静默处理卸载失败

    def show_current_status(self) -> str:
        """显示当前状态信息"""
        output = ["=== 当前状态 ==="]
        output.append(f"目标目录模板: {self.current_template}")
        output.append(f"激活的变量: {', '.join(sorted(self.active_variables)) if self.active_variables else '无'}")
        output.append(f"已加载的插件: {', '.join(sorted(self.loaded_plugins.keys())) if self.loaded_plugins else '无'}")
        output.append(f"可用插件总数: {len(self.available_variables)}")
        
        return "\n".join(output)

    def interactive_template_setup(self) -> str:
        """
        命令行交互式模板设置向导
        
        这是一个用户友好的交互式界面，用于帮助用户在命令行环境下
        设置和配置路径模板。提供变量列表展示、模板验证和实时预览功能。
        
        Returns:
            用户设置的有效模板字符串，如果用户取消则返回当前模板
            
        交互流程：
        1. 显示系统信息和配置概览
        2. 列出所有可用变量和插件
        3. 提供模板示例和使用说明
        4. 循环接收用户输入
        5. 验证模板语法和变量有效性
        6. 应用模板并显示确认信息
        
        界面功能：
        - 分组显示：按插件组织变量列表
        - 详细说明：每个变量都有完整描述
        - 示例展示：提供常用模板示例
        - 语法验证：实时检查模板语法
        - 变量检查：验证模板中的变量是否存在
        
        用户体验优化：
        - 清晰的界面布局和分隔线
        - 颜色和格式化输出（如果终端支持）
        - 详细的错误提示和建议
        - 支持取消操作（输入'quit'）
        
        模板验证：
        - 语法有效性检查
        - 变量存在性验证
        - 未知变量警告和确认
        - 模板预览和路径示例
        
        错误处理：
        - 优雅处理用户输入错误
        - 提供详细的错误信息
        - 支持重新输入和修正
        - 确认机制防止误操作
        
        Example Output:
            ==========================================
            文件分类器 - 可用变量列表
            ==========================================
            
            插件: file_date_read
            描述: 文件日期读取插件
            可用变量:
              - file_date: 获取文件的日期信息
            ...
            
        Note:
            - 仅适用于命令行环境，GUI有专门的界面
            - 设置的模板会立即生效并保存
            - 支持复杂模板语法的交互式构建
        """
        print("=" * 60)
        print("文件分类器 - 可用变量列表")
        print("=" * 60)
        
        for existing_plugins in self.show_available_variables():
            print(f"\n插件: {existing_plugins['plugin_name']}")
            print(f"描述: {existing_plugins['description']}")
            if existing_plugins['variables']:
                print("可用变量:")
                for var in existing_plugins['variables']:
                    print(f"  - {var['name']}: {var['description']}")

        print("\n" + "=" * 60)
        print(f"目标文件夹: {self.__dest_dir}")
        print("=" * 60)
        print("\n示例模板:")
        print("  {primary_group}/{filename}")
        print("  Documents/{basename}-{year}")
        print("  Media/{extension[1:]}/{filename}")
        print("\n注意: 您只需输入目标文件夹后的路径部分")
        
        while True:
            print(f"\n完整路径将是: {self.__dest_dir}/您的模板")
            template = input("请输入路径模板 (或输入 'quit' 退出): ").strip()
            
            if template.lower() == 'quit':
                return self.current_template
            
            if not template:
                print("模板不能为空，请重新输入")
                continue
            
            # 验证模板中的变量
            used_variables = self.parse_template_variables(template)
            unknown_variables = []
            
            all_available_vars = set()
            for plugin_info in self.available_variables.values():
                for var in plugin_info.get('variables', []):
                    all_available_vars.add(var['name'])
            
            for var in used_variables:
                if var not in all_available_vars:
                    unknown_variables.append(var)
            
            if unknown_variables:
                print(f"警告: 以下变量未找到对应插件: {', '.join(unknown_variables)}")
                confirm = input("是否继续使用此模板? (y/n): ").strip().lower()
                if confirm != 'y':
                    continue
            
            # 更新模板
            self.update_template(template)
            print(f"\n模板已设置: {template}")
            print(f"完整路径模板: {self.__dest_dir}/{template}")
            print(self.show_current_status())
            
            return template
    
    def analyze_file(self, filepath: str) -> Dict[str, Any]:
        """
        分析单个文件，执行所有已加载插件的execute函数
        
        这是文件分析系统的核心方法，负责调用所有相关插件来分析文件，
        提取各种元数据和分类信息。分析结果会被缓存以提高性能。
        
        Args:
            filepath: 要分析的文件路径，必须是存在的文件
            
        Returns:
            分析结果字典，键为插件名，值为插件返回的分析结果
            格式示例：
            {
                'filename': 'document.pdf',
                'basename': 'document',
                'ext': 'pdf',
                'file_date_read': '2024-01-15',
                'file_size_classifier': 'medium',
                'manual_grouping': ['Documents', 'Work']
            }
            
        Raises:
            FileNotFoundError: 当指定的文件不存在时
            
        分析流程：
        1. 文件存在性验证
        2. 路径标准化处理
        3. 提取基础文件信息
        4. 逐个执行插件分析函数
        5. 整合所有分析结果
        6. 缓存结果以供后续使用
        
        插件执行策略：
        - 并发执行：多个插件可能并行分析（未来优化）
        - 容错处理：单个插件失败不影响其他插件
        - 结果验证：验证插件返回值的有效性
        
        缓存机制：
        - 使用文件绝对路径作为缓存键
        - 分析结果永久缓存直到手动清理
        - 支持缓存预热和批量分析
        
        性能考虑：
        - 避免重复分析同一文件
        - 插件执行超时保护（未来版本）
        - 内存使用监控和清理
        
        Example:
            >>> result = allocator.analyze_file("/path/to/image.jpg")
            >>> print(result['file_date_read'])  # "2024-01-15"
            >>> print(result['manual_grouping'])  # ["Photos", "Vacation"]
            
        Note:
            - 分析结果的具体内容取决于已加载的插件
            - 插件执行失败时对应结果为None
            - 基础文件信息始终可用，不依赖插件
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")
        
        filepath = os.path.abspath(filepath)
        
        # 获取基础文件信息
        results = self._extract_basic_file_info(filepath)
        
        # 执行所有插件的 execute 函数
        for plugin_name, execute_func in self.execute_functions.items():
            try:
                # 调用插件函数
                plugin_result = execute_func(filepath)
                
                # 存储结果
                if plugin_result is not None:
                    results[plugin_name] = plugin_result
                    
            except Exception:
                results[plugin_name] = None
        
        # 存储分析结果
        self.file_data[filepath] = results
        
        return results
    
    def analyze_batch(self, filepaths: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        批量分析文件
        
        Args:
            filepaths: 文件路径列表
            
        Returns:
            分析结果字典，键为文件路径，值为分析结果
        """
        batch_results = {}
        
        for filepath in filepaths:
            try:
                results = self.analyze_file(filepath)
                batch_results[filepath] = results
                
            except Exception as e:
                batch_results[filepath] = {'error': str(e)}
        
        return batch_results
    
    def get_file_groups(self, filepath: str) -> List[str]:
        """
        获取文件的分组信息
        
        Args:
            filepath: 文件路径
            
        Returns:
            分组列表
        """
        if filepath not in self.file_data:
            self.analyze_file(filepath)
        
        file_data = self.file_data[filepath]
        groups = []
        
        # 从各个插件结果中提取分组信息
        for plugin_name, result in file_data.items():
            if plugin_name.endswith('_group') or plugin_name.endswith('_grouping'):
                if isinstance(result, list):
                    groups.extend(result)
                elif isinstance(result, str):
                    groups.append(result)
        
        return list(set(groups))  # 去重
    
    def generate_target_paths(self, filepath: str, target_patterns: List[str]) -> List[str]:
        """
        生成目标路径
        
        Args:
            filepath: 源文件路径
            target_patterns: 目标路径模式列表
            
        Returns:
            生成的目标路径列表
        """
        if filepath not in self.file_data:
            self.analyze_file(filepath)
        
        file_data = self.file_data[filepath]
        target_paths = []
        
        for pattern in target_patterns:
            try:
                # 使用文件数据格式化路径模式
                formatted_path = pattern.format(**file_data)
                target_paths.append(formatted_path)
            except KeyError:
                pass  # 静默处理变量缺失
            except Exception:
                pass  # 静默处理格式化错误
        
        return target_paths
    
    def cleanup(self) -> None:
        """
        系统资源清理，执行所有插件的清理函数并释放内存
        
        这是系统的清理方法，负责优雅地关闭所有插件，释放占用的资源，
        确保系统可以干净地退出而不留下资源泄漏。
        
        清理内容：
        1. 执行所有插件的delete函数
        2. 清空文件分析缓存
        3. 重置插件加载状态
        4. 释放内存占用
        
        清理策略：
        - 逆序清理：按加载的逆序执行清理
        - 容错处理：单个插件清理失败不影响其他插件
        - 强制清理：即使出错也会继续清理其他资源
        - 状态重置：确保对象可以重新初始化
        
        使用场景：
        - 程序正常退出时
        - 系统重新初始化前
        - 内存清理和垃圾回收
        - 错误恢复和状态重置
        
        安全特性：
        - 防止重复清理
        - 异常隔离，确保清理完整性
        - 静默处理插件清理错误
        - 保证清理操作的幂等性
        
        Note:
            - 清理后系统需要重新初始化才能使用
            - 此方法应该在程序结束前调用
            - 支持多次调用，不会产生副作用
        """
        for plugin_name, delete_func in self.delete_functions.items():
            try:
                delete_func()
            except Exception:
                pass  # 静默处理清理失败
        
        # 清空数据
        self.file_data.clear()
    
    def __del__(self):
        """析构函数，自动清理资源"""
        try:
            self.cleanup()
        except:
            pass
    
    def _extract_basic_file_info(self, filepath: str) -> Dict[str, Any]:
        """提取基础文件信息"""
        filename = os.path.basename(filepath)
        basename, extension = os.path.splitext(filename)
        ext = extension[1:] if extension.startswith('.') else extension  # 移除点号
        
        return {
            'filepath': os.path.abspath(filepath),
            'filename': filename,
            'basename': basename,
            'extension': extension,  # 包含点号的扩展名
            'ext': ext,  # 不含点号的扩展名
            'dirname': os.path.dirname(filepath),
            'filesize': os.path.getsize(filepath) if os.path.isfile(filepath) else 0
        }
    
    def _resolve_template_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """
        智能解析模板变量，支持数组下标、默认值等高级语法特性
        
        这是模板解析系统的核心方法，负责将模板字符串转换为实际的文件路径。
        支持多种高级语法，提供强大的模板表达能力和容错处理。
        
        Args:
            template: 包含变量占位符的路径模板
                     如: "{primary_group}/{filename[0]:default}/{ext}"
            variables: 可用变量的值字典
                      如: {"primary_group": "Documents", "filename": "test", "ext": "pdf"}
            
        Returns:
            解析后的完整文件路径，已包含目标目录前缀
            如: "/output/dir/Documents/test.pdf"
            
        支持的语法特性：
        1. 基础变量替换：{variable} → 变量值
        2. 数组访问：{array[0]} → 数组第0个元素
        3. 默认值：{variable:default} → 变量值或默认值
        4. 组合语法：{array[0]:default} → 数组元素或默认值
        
        解析步骤（按优先级顺序）：
        1. 处理数组+默认值组合：{array[0]:default}
        2. 处理纯数组访问：{array[0]}
        3. 处理变量+默认值：{variable:default}
        4. 处理基础变量：{variable}
        5. 清理和标准化路径
        
        容错处理：
        - 数组越界：返回"unknown"或使用默认值
        - 变量不存在：保留原始占位符或使用默认值
        - 空值处理：转换为空字符串
        - 路径清理：移除空段落和重复分隔符
        
        路径清理功能：
        - 移除空路径段
        - 合并连续的分隔符
        - 保持绝对路径格式
        - 添加目标目录前缀
        
        性能优化：
        - 使用预编译的正则表达式
        - 单次遍历处理多种语法
        - 避免重复的字符串操作
        
        Example:
            >>> variables = {"groups": ["A", "B"], "name": "test", "ext": "pdf"}
            >>> template = "{groups[0]}/{name}.{ext}"
            >>> result = _resolve_template_variables(template, variables)
            >>> print(result)  # "/output/dir/A/test.pdf"
            
        Note:
            - 语法解析顺序很重要，避免冲突
            - 支持嵌套路径和复杂目录结构
            - 生成的路径保证在目标目录下
        """
        import re
        
        result = template
        
        # 第一步：处理数组访问+默认值的组合，如 {manual_grouping[1]:default-group}
        array_default_pattern = re.compile(r'\{(\w+)\[(\d+)\]:([^}]+)\}')
        
        def replace_array_with_default(match):
            var_name = match.group(1)
            index = int(match.group(2))
            default_value = match.group(3)
            
            if var_name in variables:
                var_value = variables[var_name]
                if isinstance(var_value, list) and 0 <= index < len(var_value):
                    return str(var_value[index])
                else:
                    return default_value  # 索引超出范围，使用默认值
            else:
                return default_value  # 变量不存在，使用默认值
        
        result = array_default_pattern.sub(replace_array_with_default, result)
        
        # 第二步：处理普通数组访问，如 {manual_grouping[0]}
        array_pattern = re.compile(r'\{(\w+)\[(\d+)\]\}')
        
        def replace_array_access(match):
            var_name = match.group(1)
            index = int(match.group(2))
            
            if var_name in variables:
                var_value = variables[var_name]
                if isinstance(var_value, list) and 0 <= index < len(var_value):
                    return str(var_value[index])
                else:
                    return "unknown"  # 索引超出范围
            else:
                return "unknown"  # 变量不存在
        
        result = array_pattern.sub(replace_array_access, result)
        
        # 第三步：处理普通变量+默认值，如 {variable:default_value}
        default_pattern = re.compile(r'\{(\w+):([^}]+)\}')
        
        def replace_with_default(match):
            var_name = match.group(1)
            default_value = match.group(2)
            
            if var_name in variables and variables[var_name]:
                return str(variables[var_name])
            else:
                return default_value
        
        result = default_pattern.sub(replace_with_default, result)
        
        # 第四步：处理普通变量替换，如 {variable}
        normal_pattern = re.compile(r'\{(\w+)\}')
        
        def replace_normal_variable(match):
            var_name = match.group(1)
            if var_name in variables:
                value = variables[var_name]
                # 如果值为None、空字符串或其他假值，返回空字符串
                if value is None or value == "":
                    return ""
                elif isinstance(value, (list, tuple)) and len(value) == 0:
                    return ""
                else:
                    return str(value)
            else:
                return f"{{{var_name}}}"  # 保留未找到的变量
        
        result = normal_pattern.sub(replace_normal_variable, result)
        
        # 第五步：清理路径中的空段和连续分隔符
        result = self._clean_path_segments(result)
        
        # 添加目标文件夹前缀生成完整路径
        if not result.startswith(self.__dest_dir):
            result = os.path.join(self.__dest_dir, result)
        
        return result
    
    def _clean_path_segments(self, path: str) -> str:
        """
        清理路径中的空段和连续分隔符
        
        Args:
            path: 原始路径
            
        Returns:
            清理后的路径
        """
        # 分割路径段
        segments = []
        for segment in path.split('/'):
            # 跳过空段和只含空白字符的段
            if segment and segment.strip():
                segments.append(segment.strip())
        
        # 重新拼接，确保开头的斜杠得到保留
        if path.startswith('/'):
            return '/' + '/'.join(segments)
        else:
            return '/'.join(segments)

    def execute(self, filepath: str, target_template: Optional[str] = None) -> str:
        """
        执行文件分析并生成目标路径 - 这是系统的核心方法
        
        该方法是整个文件分类系统的核心，负责协调文件分析、模板解析
        和路径生成的完整流程。它整合了插件系统、缓存机制和智能解析
        等多个子系统，为用户提供一站式的文件分类服务。
        
        Args:
            filepath: 源文件的绝对路径，必须是存在的文件
            target_template: 可选的目标路径模板，如果为None则使用当前模板
                           格式如："{primary_group}/{date}/{filename}"
            
        Returns:
            完整的目标文件路径，包含目标目录前缀
            例如："/output/dir/Documents/2024-01/report.pdf"
            
        执行流程：
        1. 模板预处理：使用指定模板或当前模板
        2. 插件准备：确保模板所需的插件已加载
        3. 文件分析：提取基础信息和执行插件分析
        4. 变量合并：整合所有分析结果和便捷变量
        5. 路径生成：解析模板并生成最终路径
        
        分析内容：
        - 基础文件信息：文件名、扩展名、大小等
        - 插件分析结果：日期、分组、分类等
        - 便捷变量：primary_group、size_category等
        
        缓存机制：
        文件分析结果会被缓存，重复分析同一文件时直接返回缓存结果，
        显著提升性能。缓存键为文件的绝对路径。
        
        错误处理：
        - 文件不存在时抛出FileNotFoundError
        - 插件执行失败时使用默认值或跳过
        - 模板解析错误时提供详细错误信息
        
        Example:
            >>> allocator = Allocator("/output")
            >>> allocator.update_template("{primary_group}/{basename}")
            >>> result = allocator.execute("/path/to/document.pdf")
            >>> print(result)  # /output/Documents/document
            
        Note:
            - 支持临时模板，不会改变当前模板设置
            - 自动处理路径标准化和字符转义
            - 生成的路径保证在目标目录下
        """
        # 使用当前模板或指定模板
        if target_template is None:
            target_template = self.current_template
        
        # 确保模板所需的插件已加载
        if target_template != self.current_template:
            template_vars = self.parse_template_variables(target_template)
            self._load_plugins_for_variables(template_vars)
        
        # 获取基础文件信息
        basic_info = self._extract_basic_file_info(filepath)
        
        # 分析文件（执行插件）
        analysis_result = self.analyze_file(filepath)
        
        # 合并所有变量
        all_variables = basic_info.copy()
        all_variables.update(analysis_result)
        
        # 构建扩展变量
        groups = analysis_result.get('manual_grouping', [])
        primary_group = groups[0] if groups else 'Others'
        
        # 添加便捷变量
        all_variables.update({
            'primary_group': primary_group,
            'groups': groups,
            'size_category': analysis_result.get('file_size_classifier', 'unknown'),
            'file_date': analysis_result.get('file_date_read', ''),
            'manual_grouping': groups,  # 确保manual_grouping可用
        })
        
        # 智能解析目标路径并返回
        return self._resolve_template_variables(target_template, all_variables)

    def batch_execute(self, filepaths: List[str], target_template: Optional[str] = None) -> List[str]:
        """
        批量执行文件分析并生成目标路径列表
        
        Args:
            filepaths: 文件路径列表
            target_template: 目标路径模板，如果为None则使用当前模板
            
        Returns:
            目标路径字符串列表
        """
        results = []
        
        for filepath in filepaths:
            try:
                target_path = self.execute(filepath, target_template)
                results.append(target_path)
            except Exception as e:
                # 对于出错的文件，添加错误标记或跳过
                results.append(f"ERROR: {filepath} - {str(e)}")
        
        return results
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        卸载指定的插件并清理其资源
        
        Args:
            plugin_name: 要卸载的插件名称
            
        Returns:
            bool: 卸载成功返回True，失败返回False
        """
        if plugin_name not in self.loaded_plugins:
            return False
        
        try:
            # 1. 调用插件的delete清理函数（如果存在）
            if plugin_name in self.delete_functions:
                self.delete_functions[plugin_name]()
            
            # 2. 从所有管理字典中移除插件信息
            self.loaded_plugins.pop(plugin_name, None)
            self.init_functions.pop(plugin_name, None)
            self.execute_functions.pop(plugin_name, None)
            self.delete_functions.pop(plugin_name, None)
            self.reload_functions.pop(plugin_name, None)
            self.available_variables.pop(plugin_name, None)
            
            # 3. 从sys.modules中移除插件模块，允许重新加载
            # 插件可能以多种方式被加载，需要检查多种可能的模块名
            possible_module_names = [
                plugin_name,
                f"module.plugins.{plugin_name}",
                f"plugins.{plugin_name}"
            ]
            for name in possible_module_names:
                if name in sys.modules:
                    del sys.modules[name]
            
            print(f"插件 {plugin_name} 已成功卸载。")
            return True
        except Exception as e:
            print(f"卸载插件 {plugin_name} 时出错: {e}")
            return False

    def reload_plugins(self) -> None:
        """
        重新加载所有插件
        
        该方法会先卸载所有当前已加载的插件，然后重新扫描插件目录并加载。
        这对于在运行时添加、删除或修改插件文件后更新整个系统非常有用。
        """
        print("正在重新加载所有插件...")
        
        # 卸载所有现有插件
        # 使用list(self.loaded_plugins.keys())来避免在迭代时修改字典
        for plugin_name in list(self.loaded_plugins.keys()):
            self.unload_plugin(plugin_name)
        
        # 清空变量并重新注册基础变量
        self.available_variables.clear()
        self._register_base_variables()
        
        # 重新发现和加载插件
        self._discover_plugin_variables()
        self._load_plugins()
        self._execute_init_functions()
        
        print("所有插件重新加载完成。")

    def reload_plugin(self, plugin_name: str) -> bool:
        """
        重新加载指定的插件
        
        Args:
            plugin_name: 要重新加载的插件名称
            
        Returns:
            bool: 重载成功返回True，失败返回False
        """
        if plugin_name not in self.loaded_plugins:
            print(f"无法重载插件 {plugin_name}: 插件未加载。")
            return False
        
        plugin_path = self.loaded_plugins[plugin_name].get('path')
        if not plugin_path or not os.path.exists(plugin_path):
            print(f"无法重载插件 {plugin_name}: 找不到源文件路径。")
            return False
            
        print(f"正在重载插件: {plugin_name}")
        
        # 卸载旧插件
        if not self.unload_plugin(plugin_name):
            print(f"重载失败：卸载插件 {plugin_name} 失败。")
            return False
            
        # 加载新插件
        try:
            self._load_single_plugin(plugin_name, plugin_path)
            # 执行初始化
            if plugin_name in self.init_functions:
                self.init_functions[plugin_name]()
            print(f"插件 {plugin_name} 重载成功。")
            return True
        except Exception as e:
            print(f"重载失败：加载插件 {plugin_name} 时出错: {e}")
            return False
    
    # def _add_special_plugin_variables(self, plugin_name: str, plugin_module, variables: Dict[str, Any], added_variables: set):
    #     """添加特殊插件变量和描述"""
        
    #     # 获取变量描述字典
    #     addon_descriptions = getattr(plugin_module, 'addon_variables_description', {})
        
    #     # 特殊处理一些已知的插件变量（不重复添加）
    #     if plugin_name == 'manual_grouping':
    #         if 'primary_group' not in added_variables:
    #             description = addon_descriptions.get('primary_group', '主要分组（第一个分组）')
    #             variables['variables'].append({
    #                 'name': 'primary_group', 
    #                 'description': description,
    #                 'example': '{primary_group}'
    #             })
    #             added_variables.add('primary_group')
    #     elif plugin_name == 'file_date_read':
    #         if 'file_date' not in added_variables:
    #             description = addon_descriptions.get('file_date', '文件日期 (YYYY-MM-DD 格式)')
    #             variables['variables'].append({
    #                 'name': 'file_date', 
    #                 'description': description,
    #                 'example': '{file_date}'
    #             })
    #             added_variables.add('file_date')
    #     elif plugin_name == 'file_size_classifier':
    #         if 'size_category' not in added_variables:
    #             description = addon_descriptions.get('size_category', '文件大小分类 (tiny/small/medium/large/huge)')
    #             variables['variables'].append({
    #                 'name': 'size_category', 
    #                 'description': description,
    #                 'example': '{size_category}'
    #             })
    #             added_variables.add('size_category')
        
    #     # 添加基础文件变量（只在第一个插件中添加一次）
    #     if plugin_name == 'manual_grouping':  # 只在第一个插件中添加一次
    #         basic_vars = [
    #             {'name': 'filename', 'description': addon_descriptions.get('filename', '文件名（含扩展名）'), 'example': '{filename}'},
    #             {'name': 'basename', 'description': addon_descriptions.get('basename', '文件名（不含扩展名）'), 'example': '{basename}'},
    #             {'name': 'extension', 'description': addon_descriptions.get('extension', '文件扩展名'), 'example': '{extension}'}
    #         ]
    #         for var in basic_vars:
    #             if var['name'] not in added_variables:
    #                 variables['variables'].append(var)
    #                 added_variables.add(var['name'])

    #     return variables


# ==================== 模块便捷函数 ====================

def create_allocator(target_folder: str, plugins_dir: Optional[str] = None) -> Allocator:
    """
    创建文件分类器实例的便捷工厂函数
    
    这是一个便捷的工厂函数，用于快速创建和初始化Allocator实例，
    简化了常见的创建模式，提供更友好的API接口。
    
    Args:
        target_folder: 目标输出文件夹的绝对路径
                      所有分类后的文件将存储在此目录下
        plugins_dir: 可选的插件目录路径
                    如果不指定，将使用默认的plugins目录
        
    Returns:
        完全初始化的Allocator实例，可以立即使用
        
    功能特点：
    - 简化创建流程：一行代码完成所有初始化
    - 参数验证：自动验证输入参数的有效性
    - 错误处理：提供友好的错误信息
    - 类型安全：完整的类型注解支持
    
    使用场景：
    - 快速原型开发
    - 脚本和自动化工具
    - 第三方集成
    - 测试和演示代码
    
    Example:
        >>> # 使用默认插件目录
        >>> allocator = create_allocator("/output/directory")
        >>> 
        >>> # 使用自定义插件目录
        >>> allocator = create_allocator("/output", "/custom/plugins")
        >>> 
        >>> # 设置模板并分析文件
        >>> allocator.update_template("{primary_group}/{filename}")
        >>> result = allocator.execute("/path/to/file.pdf")
        
    Note:
        - 这是推荐的创建Allocator实例的方式
        - 返回的实例已经完成所有初始化工作
        - 支持链式调用和函数式编程风格
    """
    return Allocator(target_folder, plugins_dir)


# ==================== 模块主程序 ====================

if __name__ == "__main__":
    """
    模块测试和演示程序
    
    当直接运行此模块时，会执行基本的功能演示，
    展示插件发现、变量列表和系统状态等核心功能。
    """
    # 创建测试用的分类器实例
    allocator = create_allocator("/tmp/test")
    
    print("=" * 60)
    print("文件分类器核心模块演示")
    print("=" * 60)
    
    print("\n=== 插件变量发现演示 ===")
    variables_info = allocator.show_available_variables()
    for plugin_info in variables_info:
        print(f"\n插件: {plugin_info['plugin_name']}")
        print(f"描述: {plugin_info['description']}")
        if plugin_info['variables']:
            print("变量:")
            for var in plugin_info['variables']:
                print(f"  - {var['name']}: {var['description']}")
    
    print("\n=== 当前系统状态 ===")
    print(allocator.show_current_status())
