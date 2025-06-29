#!/usr/bin/env python3
"""
手动分组插件 - 支持全局分组规则的文件分类插件

支持的功能：
    多种匹配模式：简单字符串、通配符、高级通配符（数字范围）
    规则管理：添加、删除、显示、清空
"""

import os
import re
from typing import List, Set, Dict, Any, Optional

# ==================== 全局分组规则管理 ====================

# 全局分组规则存储
GLOBAL_GROUPING_RULES: Dict[str, List[str]] = {}

# 简化命名的管理函数
def init():
    """插件初始化函数"""

def delete():
    """插件清理函数"""
    global GLOBAL_GROUPING_RULES
    GLOBAL_GROUPING_RULES.clear()

def reload():
    """插件重新加载函数"""
    setup_global_grouping_rules()

# ==================== 规则管理函数 ====================

def setup_global_grouping_rules(rules_dict: Optional[Dict[str, List[str]]] = None) -> Dict[str, List[str]]:
    """
    设置全局分组规则 - 只需要调用一次，应用到所有文件
    
    Args:
        rules_dict: 可选的规则字典，如果提供则直接使用，否则通过交互式输入
        
    Returns:
        设置的规则字典
    """
    global GLOBAL_GROUPING_RULES
    
    if rules_dict is not None:
        GLOBAL_GROUPING_RULES = rules_dict.copy()
        return GLOBAL_GROUPING_RULES
    
    print("=== 设置全局分组规则 ===")
    print("这些规则将应用到所有处理的文件上\n")
    
    try:
        rules_num = int(input("请输入分组规则数量: "))
    except ValueError:
        print("❌ 无效的数字")
        return GLOBAL_GROUPING_RULES
    
    new_rules = {}
    
    for i in range(rules_num):
        print(f"\n--- 规则 {i+1} ---")
        group_name = input("请输入分组名称: ").strip()
        
        if not group_name:
            print("❌ 分组名称不能为空，跳过此规则...")
            continue
        
        print("匹配模式选择:")
        print("1. 简单匹配 (包含指定字符串)")
        print("2. 通配符匹配 (支持 * 和 ?)")
        print("3. 高级通配符 (支持数字范围，如 ABC*EFG,*=1-29,33)")
        
        mode = input("请选择匹配模式 (1-3): ").strip()
        
        if mode == '1':
            # 简单字符串匹配
            pattern = input("请输入匹配字符串: ").strip()
            if pattern:
                pass
            else:
                continue
                
        elif mode == '2':
            # 简单通配符匹配
            pattern = input("请输入通配符模式: ").strip()
            if pattern:
                pass
            else:
                continue
            
        elif mode == '3':
            # 高级通配符匹配（支持数字范围）
            pattern = input("请输入高级通配符模式: ").strip()
            if pattern:
                pass
            else:
                continue
        else:
            continue
        
        # 将规则添加到分组中
        if group_name in new_rules:
            new_rules[group_name].append(pattern)
        else:
            new_rules[group_name] = [pattern]
    
    # 将规则存储到全局变量
    GLOBAL_GROUPING_RULES = new_rules
    
    return new_rules

def add_global_rule(group_name: str, patterns: List[str]) -> None:
    """添加分组规则到全局规则中"""
    global GLOBAL_GROUPING_RULES
    if group_name in GLOBAL_GROUPING_RULES:
        GLOBAL_GROUPING_RULES[group_name].extend(patterns)
    else:
        GLOBAL_GROUPING_RULES[group_name] = patterns.copy()

def show_global_rules() -> Dict[str, List[str]]:
    """显示当前设置的全局规则"""
    global GLOBAL_GROUPING_RULES
    return GLOBAL_GROUPING_RULES.copy()

def clear_global_rules() -> None:
    """清除所有全局规则"""
    global GLOBAL_GROUPING_RULES
    GLOBAL_GROUPING_RULES.clear()

# ==================== 匹配算法 ====================

def parse_number_range(range_str: str) -> Set[str]:
    """
    解析数字范围字符串，支持单个数字、范围和混合格式
    保留原始字符串格式（如前导零）
    
    例如：
    - "1-29,33,999-1024" -> {"1","2",...,"29","33","999",...,"1024"}
    - "001-005,123" -> {"001","002","003","004","005","123"}
    """
    numbers = set()
    parts = range_str.split(',')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        if '-' in part:
            # 处理范围，如 "001-005" 或 "1-29"
            try:
                start_str, end_str = part.split('-', 1)
                start_str = start_str.strip()
                end_str = end_str.strip()
                
                start_num = int(start_str)
                end_num = int(end_str)
                
                if start_num <= end_num:
                    # 检测是否有前导零
                    if len(start_str) > 1 and start_str.startswith('0'):
                        # 有前导零，保持格式
                        width = len(start_str)
                        for num in range(start_num, end_num + 1):
                            numbers.add(str(num).zfill(width))
                    else:
                        # 无前导零，使用普通格式
                        for num in range(start_num, end_num + 1):
                            numbers.add(str(num))
                    
            except ValueError:
                continue
        else:
            # 处理单个数字，如 "33" 或 "001"
            try:
                # 验证是否为有效数字
                int(part)
                numbers.add(part)  # 保持原始格式
            except ValueError:
                continue
    
    return numbers

def expand_wildcard_pattern(pattern: str) -> str:
    """
    将带有数字范围的通配符模式转换为正则表达式
    
    例如：
    - "IMG*,*=001-003" -> 匹配 IMG001.jpg, IMG002.jpg, IMG003.jpg
    - "ABC*EFG,*=1-29,33,999-1024" -> 匹配 ABC1EFG, ABC2EFG, ..., ABC29EFG, ABC33EFG, ABC999EFG, ..., ABC1024EFG
    """
    if ',' not in pattern:
        # 如果没有逗号，说明没有数字范围定义，使用普通通配符
        return pattern.replace('*', r'.*').replace('?', r'.')
    
    # 分离模式和数字范围定义
    parts = pattern.split(',')
    pattern_part = parts[0]
    
    # 重新组织数字范围字符串，将所有数字相关的部分合并
    number_parts = []
    wildcard_symbol = None
    
    for part in parts[1:]:
        part = part.strip()
        if '=' in part:
            # 有等号的部分，如 "*=001-005"
            symbol, range_part = part.split('=', 1)
            wildcard_symbol = symbol.strip()
            number_parts.append(range_part.strip())
        else:
            # 没有等号的部分，如 "123"，应该也是数字
            number_parts.append(part)
    
    # 检查是否有星号范围定义
    if wildcard_symbol == '*' and number_parts:
        # 将所有数字部分合并
        combined_range = ','.join(number_parts)
        numbers = parse_number_range(combined_range)
        if numbers:
            # 创建数字选择的正则表达式
            number_list = sorted(numbers, key=lambda x: int(x))
            number_pattern = '|'.join(number_list)
            
            # 找到第一个星号的位置并替换为数字模式
            first_star_pos = pattern_part.find('*')
            if first_star_pos != -1:
                # 替换第一个星号为数字选择模式，并在后面添加通配符匹配其余部分
                before_star = pattern_part[:first_star_pos]
                after_star = pattern_part[first_star_pos + 1:]
                
                # 如果星号后面还有内容，则需要精确匹配；否则添加通用匹配
                if after_star:
                    # 处理星号后面的内容
                    after_star_regex = after_star.replace('*', r'.*').replace('?', r'.')
                    regex_pattern = f'{before_star}({number_pattern}){after_star_regex}'
                else:
                    # 星号在末尾，添加通用匹配来匹配文件扩展名等
                    regex_pattern = f'{before_star}({number_pattern}).*'
                
                return regex_pattern
    
    # 如果没有数字范围定义，使用普通通配符转换
    regex_pattern = pattern_part.replace('*', r'.*').replace('?', r'.')
    return regex_pattern

def filename_matches_pattern(filename: str, pattern: str) -> bool:
    """检查文件名是否匹配指定的模式"""
    try:
        # 将模式转换为正则表达式
        regex_pattern = expand_wildcard_pattern(pattern)
        
        # 确保完全匹配（从开始到结束）
        if not regex_pattern.startswith('^'):
            regex_pattern = '^' + regex_pattern
        if not regex_pattern.endswith('$'):
            regex_pattern = regex_pattern + '$'
        
        # 编译并匹配
        compiled_pattern = re.compile(regex_pattern)
        return bool(compiled_pattern.match(filename))
        
    except re.error:
        return False

def enhanced_filename_matching(filepath: str, pattern: str) -> bool:
    """增强的文件名匹配功能"""
    filename = os.path.basename(filepath)
    return filename_matches_pattern(filename, pattern)

# ==================== 主要插件函数 ====================

def manual_grouping(filepath: str) -> List[str]:
    """
    手动分组主函数 - 这是注册到 allocator 的 execute 函数
    
    使用全局分组规则对文件进行分组
    
    Args:
        filepath: 文件路径
        
    Returns:
        匹配的分组列表
    """
    global GLOBAL_GROUPING_RULES
    
    # 如果没有设置全局规则，返回空列表
    if not GLOBAL_GROUPING_RULES:
        return []
    
    filename = os.path.basename(filepath)
    groups = []
    
    # 应用所有全局规则
    for group_name, patterns in GLOBAL_GROUPING_RULES.items():
        for pattern in patterns:
            matched = False
            
            # 检查是否是高级通配符模式（包含逗号和等号）
            if ',' in pattern and '=' in pattern:
                # 高级通配符匹配（支持数字范围）
                if enhanced_filename_matching(filepath, pattern):
                    groups.append(group_name)
                    matched = True
            elif '*' in pattern or '?' in pattern:
                # 简单通配符匹配
                if enhanced_filename_matching(filepath, pattern):
                    groups.append(group_name)
                    matched = True
            else:
                # 简单字符串匹配
                if pattern in filename:
                    groups.append(group_name)
                    matched = True
            
            # 如果匹配了，就不再检查该分组的其他模式
            if matched:
                break
    
    return groups

# ==================== 测试和工具函数 ====================

def get_available_functions():
    """获取可用的函数列表"""
    return {
        'setup_global_grouping_rules': setup_global_grouping_rules,
    }

# ==================== 插件注册 ====================

# 新版本插件注册 - 提供更多函数访问
addon_variables = {
    'manual_group': manual_grouping,
}

# 插件变量描述字典 - 直接映射变量名到描述
addon_variables_description = {
    'manual_group': '手动分组插件，支持不同分组规则的文件分类',
}
