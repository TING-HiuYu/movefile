#!/usr/bin/env python3
"""
文件分类器 (Allocator) - 插件化的文件分组与路径生成系统

这个分类器支持：
1. 自动加载插件系统
2. 每个插件可以注册 init、execute、delete 三个函数
3. 全局配置管理
4. 批量文件处理
5. 智能模板解析和路径生成
"""

import os
import sys
import importlib
import importlib.util
import re
from typing import Dict, List, Any, Callable, Optional, Set, Union
from pathlib import Path


class Allocator:
    """
    文件分类器 - 插件化的文件分组与路径生成系统
    
    支持动态插件加载、智能模板解析和高效的文件分析。
    """
    
    def __init__(self, target_folder: str, plugins_dir: Optional[str] = None):
        """
        初始化分类器
        
        Args:
            target_folder: 目标文件夹路径
            plugins_dir: 插件目录路径，默认为 'directory_tools'
        """
        # 插件相关
        self.plugins_dir = plugins_dir or os.path.join(os.path.dirname(__file__), 'directory_tools')
        self.loaded_plugins: Dict[str, Any] = {}  # 改为Any类型以存储模块
        
        # 存储插件注册的函数
        self.init_functions: Dict[str, Callable] = {}
        self.execute_functions: Dict[str, Callable] = {}
        self.delete_functions: Dict[str, Callable] = {}
        self.reload_functions: Dict[str, Callable] = {}  # 新增reload函数管理
        
        # 文件分析结果存储
        self.file_data: Dict[str, Dict[str, Any]] = {}
        
        # 插件变量管理
        self.available_variables: Dict[str, Dict[str, Any]] = {}  # 所有可用变量
        self.active_variables: Set[str] = set()  # 当前激活的变量
        self.current_template: str = ""  # 当前模板
        self.__dest_dir: str = target_folder
        
        # 注册基础变量
        self._register_base_variables()
        
        # 扫描所有可用的插件变量
        self._discover_plugin_variables()
        
        # 加载所有插件
        self._load_plugins()
        
        # 执行所有插件的初始化函数
        self._execute_init_functions()

    def _load_plugins(self):
        """加载插件目录下的所有插件"""
        if not os.path.exists(self.plugins_dir):
            return
        
        # 将插件目录添加到Python路径
        if self.plugins_dir not in sys.path:
            sys.path.insert(0, os.path.dirname(self.plugins_dir))
        
        plugin_files = [f for f in os.listdir(self.plugins_dir) 
                       if f.endswith('.py') and not f.startswith('__')]
        
        for plugin_file in plugin_files:
            plugin_name = plugin_file[:-3]  # 移除 .py 扩展名
            try:
                self._load_single_plugin(plugin_name)
            except Exception:
                pass  # 静默处理插件加载失败
    
    def _load_single_plugin(self, plugin_name: str):
        """加载单个插件"""
        # 尝试不同的导入路径，优先使用已导入的模块
        possible_paths = [
            f"module.directory_tools.{plugin_name}",
            f"directory_tools.{plugin_name}"
        ]
        
        plugin_module = None
        for module_path in possible_paths:
            try:
                # 检查模块是否已经在 sys.modules 中
                if module_path in sys.modules:
                    plugin_module = sys.modules[module_path]
                    break
                else:
                    # 尝试导入模块
                    plugin_module = importlib.import_module(module_path)
                    break
            except ImportError:
                continue
        
        if plugin_module is None:
            raise ImportError(f"无法导入插件 {plugin_name}")
        
        try:
            plugin_info = {
                'module': plugin_module,
                'init': None,
                'execute': None,
                'delete': None
            }
            
            # 查找插件的注册函数
            self._register_plugin_functions(plugin_name, plugin_module, plugin_info)
            
            if plugin_info['execute']:
                self.loaded_plugins[plugin_name] = plugin_info
                
        except Exception:
            pass  # 静默处理插件处理错误
    
    def _register_plugin_functions(self, plugin_name: str, plugin_module, plugin_info: Dict):
        """注册插件的函数"""
        
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
                for var_name, var_func in addon_vars.items():
                    if callable(var_func) and not plugin_info['execute']:
                        plugin_info['execute'] = var_func
                        self.execute_functions[plugin_name] = var_func
                        break
            elif isinstance(addon_vars, str) and hasattr(plugin_module, addon_vars):
                func = getattr(plugin_module, addon_vars)
                if callable(func) and not plugin_info['execute']:
                    plugin_info['execute'] = func
                    self.execute_functions[plugin_name] = func
    
    def _register_base_variables(self):
        """注册基础变量（在类初始化时自动调用）"""
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

    def _execute_init_functions(self):
        """执行所有插件的初始化函数"""
        for plugin_name, init_func in self.init_functions.items():
            try:
                init_func()
            except Exception:
                pass  # 静默处理初始化失败

    def _discover_plugin_variables(self):
        """扫描插件目录，发现所有可用的变量"""
        if not os.path.exists(self.plugins_dir):
            return
        
        plugin_files = [f for f in os.listdir(self.plugins_dir) 
                       if f.endswith('.py') and not f.startswith('__')]
        
        for plugin_file in plugin_files:
            plugin_name = plugin_file[:-3]
            try:
                self._discover_single_plugin_variables(plugin_name)
            except Exception:
                pass  # 静默处理发现失败

    def _discover_single_plugin_variables(self, plugin_name: str):
        """发现单个插件提供的变量"""
        # 尝试不同的导入路径
        possible_paths = [
            f"module.directory_tools.{plugin_name}",
            f"directory_tools.{plugin_name}"
        ]
        
        plugin_module = None
        for module_path in possible_paths:
            try:
                if module_path in sys.modules:
                    plugin_module = sys.modules[module_path]
                    break
                else:
                    plugin_module = importlib.import_module(module_path)
                    break
            except ImportError:
                continue
        
        if plugin_module is None:
            # 尝试直接加载文件
            try:
                plugin_path = os.path.join(self.plugins_dir, f"{plugin_name}.py")
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                if spec and spec.loader:
                    plugin_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(plugin_module)
                else:
                    return
            except Exception:
                return
        
        # 分析插件提供的变量
        variables = self._analyze_plugin_variables(plugin_name, plugin_module)
        if variables:
            # 添加插件路径信息
            variables['path'] = os.path.join(self.plugins_dir, f"{plugin_name}.py")
            self.available_variables[plugin_name] = variables

    def _analyze_plugin_variables(self, plugin_name: str, plugin_module) -> Dict[str, Any]:
        """分析插件提供的变量"""
        variables = {
            'plugin_name': plugin_name,
            'description': getattr(plugin_module, '__doc__', '').strip().split('\n')[0] if getattr(plugin_module, '__doc__', '') else f"{plugin_name} 插件",
            'variables': [],
            'functions': []
        }
        
        # 用集合来避免重复变量
        added_variables = set()
        
        # 查找主执行函数
        main_func_name = plugin_name
        if hasattr(plugin_module, main_func_name) and callable(getattr(plugin_module, main_func_name)):
            func = getattr(plugin_module, main_func_name)
            variables['functions'].append({
                'name': main_func_name,
                'type': 'execute',
                'doc': getattr(func, '__doc__', '').strip() if getattr(func, '__doc__', '') else ''
            })
        
        # 查找通过 addon_variables 注册的变量
        if hasattr(plugin_module, 'addon_variables') or hasattr(plugin_module, 'addon_variabls'):
            addon_vars = getattr(plugin_module, 'addon_variables', None) or getattr(plugin_module, 'addon_variabls', None)
            
            # 获取变量描述字典
            addon_descriptions = getattr(plugin_module, 'addon_variables_description', {})
            
            if isinstance(addon_vars, str):
                # 单个变量名
                if addon_vars not in added_variables:
                    # 使用自定义描述或默认描述
                    custom_description = addon_descriptions.get(addon_vars, f"{addon_vars} (来自 {plugin_name})")
                    variables['variables'].append({
                        'name': addon_vars,
                        'description': custom_description,
                        'example': f"{{{addon_vars}}}"
                    })
                    added_variables.add(addon_vars)
            elif isinstance(addon_vars, dict):
                # 多个变量
                for var_name in addon_vars.keys():
                    if var_name not in added_variables:
                        # 使用自定义描述或默认描述
                        custom_description = addon_descriptions.get(var_name, f"{var_name} (来自 {plugin_name})")
                        variables['variables'].append({
                            'name': var_name,
                            'description': custom_description,
                            'example': f"{{{var_name}}}"
                        })
                        added_variables.add(var_name)
        
        # 处理特殊的插件变量和描述
        # self._add_special_plugin_variables(plugin_name, plugin_module, variables, added_variables)
        
        return variables

    def show_available_variables(self) -> List[Dict[str, Any]]:
        """显示所有可用变量的友好信息"""
        if not self.available_variables:
            return []
        
        out: List[Dict[str, Any]] = []

        for plugin_name, plugin_info in self.available_variables.items():
            this_plugin = {
                "plugin_name": plugin_name,
                "description": plugin_info.get('description', plugin_name),
                "variables": [],
            }

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
        """解析模板中使用的变量"""
        # 匹配 {变量名} 或 {变量名[索引]} 格式
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, template)
        
        variables = set()
        for match in matches:
            # 处理数组访问格式，如 manual_grouping[0]
            var_name = match.split('[')[0]
            variables.add(var_name)
        
        return variables

    def update_template(self, template: str):
        """更新模板并动态调整插件加载"""
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
                plugin_variables = [var['name'] for var in plugin_info.get('variables', [])]
                if variable in plugin_variables:
                    plugins_to_load.add(plugin_name)
        
        # 加载插件
        for plugin_name in plugins_to_load:
            if plugin_name not in self.loaded_plugins:
                try:
                    self._load_single_plugin(plugin_name)
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
        """交互式设置模板"""
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
        分析单个文件，执行所有插件的 execute 函数
        
        Args:
            filepath: 文件路径
            
        Returns:
            分析结果字典
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
    
    def cleanup(self):
        """清理资源，执行所有插件的 delete 函数"""
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
        智能解析模板变量，支持数组下标、默认值等高级功能
        
        Args:
            template: 路径模板
            variables: 可用变量字典
            
        Returns:
            解析后的路径
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
                return str(variables[var_name])
            else:
                return f"{{{var_name}}}"  # 保留未找到的变量
        
        result = normal_pattern.sub(replace_normal_variable, result)
        
        # 添加目标文件夹前缀生成完整路径
        if not result.startswith(self.__dest_dir):
            result = os.path.join(self.__dest_dir, result)
        
        return result

    def execute(self, filepath: str, target_template: Optional[str] = None) -> str:
        """
        执行文件分析并生成目标路径
        
        Args:
            filepath: 文件路径
            target_template: 目标路径模板，如果为None则使用当前模板
            
        Returns:
            目标文件路径字符串
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
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """
        重新加载指定插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否成功重新加载
        """
        try:
            # 如果插件当前已加载，先卸载
            if plugin_name in self.loaded_plugins:
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
                if plugin_name in self.reload_functions:
                    del self.reload_functions[plugin_name]
            
            # 重新加载插件模块
            if plugin_name in self.available_variables:
                plugin_info = self.available_variables[plugin_name]
                plugin_path = plugin_info.get('path')
                
                if plugin_path and os.path.exists(plugin_path):
                    # 从sys.modules中移除相关模块（如果存在）
                    modules_to_remove = []
                    for module_name in sys.modules:
                        if plugin_name in module_name:
                            modules_to_remove.append(module_name)
                    
                    for module_name in modules_to_remove:
                        del sys.modules[module_name]
                    
                    # 重新加载
                    try:
                        self._load_single_plugin(plugin_name)
                        
                        # 如果有init函数，调用它
                        if plugin_name in self.init_functions:
                            self.init_functions[plugin_name]()
                        
                        # 如果有reload函数，调用它
                        if plugin_name in self.reload_functions:
                            self.reload_functions[plugin_name]()
                        
                        return True
                    except Exception:
                        return False
            
            return False
            
        except Exception:
            return False
    
    def reload_all_plugins(self) -> Dict[str, bool]:
        """
        重新加载所有已加载的插件
        
        Returns:
            每个插件的重新加载结果
        """
        results = {}
        loaded_plugin_names = list(self.loaded_plugins.keys())
        
        for plugin_name in loaded_plugin_names:
            results[plugin_name] = self.reload_plugin(plugin_name)
        
        return results
    
    def reload(self, plugin_name: Optional[str] = None) -> Union[bool, Dict[str, bool]]:
        """
        重新加载插件的便捷接口
        
        Args:
            plugin_name: 插件名称，如果为None则重新加载所有插件
            
        Returns:
            重新加载结果
        """
        if plugin_name is None:
            return self.reload_all_plugins()
        else:
            return self.reload_plugin(plugin_name)
    
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


# 便捷函数
def create_allocator(target_folder: str, plugins_dir: Optional[str] = None) -> Allocator:
    """
    创建文件分类器实例
    
    Args:
        target_folder: 目标文件夹路径
        plugins_dir: 插件目录路径
        
    Returns:
        Allocator 实例
    """
    return Allocator(target_folder, plugins_dir)


if __name__ == "__main__":
    # 基本演示
    allocator = create_allocator("/tmp/test")
    print("=== 插件变量发现演示 ===")
    print(allocator.show_available_variables())
    print("\n=== 当前状态 ===")
    print(allocator.show_current_status())
