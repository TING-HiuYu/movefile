#!/usr/bin/env python3
"""
手动分组插件 - 基于多策略的智能文件分组系统

这是一个功能强大的文件分组插件，支持多种匹配策略和复杂的分组规则。
通过策略组的概念，用户可以定义精确的文件分类逻辑，实现高度定制化的文件管理。

核心特性：
- 多策略支持：包含字符串、通配符、正则表达式三种匹配方式
- 策略组管理：多个策略组合形成复杂的分组逻辑
- 高级通配符：支持约束参数的智能通配符匹配
- 可视化配置：提供GUI界面进行策略可视化配置
- 实时预览：配置过程中实时显示匹配结果

支持的匹配策略：
1. 包含字符串匹配 (contains)：
   - 简单字符串包含检查
   - 大小写敏感匹配
   - 适用于固定文本模式匹配

2. 通配符匹配 (wildcard)：
   - 标准通配符：* 匹配任意字符序列，? 匹配单个字符
   - 高级约束：支持 {范围} 和 {值列表} 约束参数
   - 示例：IMG_{100-200}.{jpg,png} 匹配IMG_150.jpg等

3. 正则表达式匹配 (regex)：
   - 完整的Python正则表达式支持
   - 预编译优化，提高匹配性能
   - 支持复杂的模式匹配和分组捕获

策略组配置格式：
```yaml
pluginConfig:
  manual_grouping:
    groups:
      - name: "照片文件"
        strategies:
          - type: "wildcard"
            pattern: "IMG_*.{jpg,jpeg,png}"
            range_filter: "{1000-9999},{jpg,jpeg,png}"
      - name: "文档文件"  
        strategies:
          - type: "regex"
            pattern: ".*\\.(doc|docx|pdf)$"
```

Author: File Classifier Project
License: MIT
Version: 2.0
"""

import os
import re
import fnmatch
from typing import List, Set, Dict, Any, Optional, NamedTuple, TYPE_CHECKING
from enum import Enum
import importlib.util
from dataclasses import dataclass

# GUI导入处理 - 条件导入避免在CLI环境下的依赖问题
if TYPE_CHECKING:
    # 类型检查时导入，确保类型注解正确
    from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QWidget, 
                                 QPushButton, QLabel, QLineEdit, QComboBox, 
                                 QTextEdit, QScrollArea, QGroupBox, QGridLayout,
                                 QMessageBox, QFrame, QSplitter, QListWidget,
                                 QListWidgetItem, QInputDialog, QTabWidget)
    from PySide6.QtCore import Qt, Signal, QTimer
    from PySide6.QtGui import QFont, QColor

try:
    # 运行时导入，只有在GUI可用时才导入
    from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QWidget, 
                                 QPushButton, QLabel, QLineEdit, QComboBox, 
                                 QTextEdit, QScrollArea, QGroupBox, QGridLayout,
                                 QMessageBox, QFrame, QSplitter, QListWidget,
                                 QListWidgetItem, QInputDialog, QTabWidget)
    from PySide6.QtCore import Qt, Signal, QTimer
    from PySide6.QtGui import QFont, QColor
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# ==================== 策略类型定义 ====================

class StrategyType(Enum):
    """策略类型枚举"""
    CONTAINS = "contains"      # 包含字符串
    WILDCARD = "wildcard"      # 通配符
    REGEX = "regex"           # 正则表达式

@dataclass
class Strategy:
    """单个策略定义"""
    strategy_type: StrategyType
    pattern: str
    range_filter: str = ""  # 新增：范围过滤器（用于通配符）
    compiled_regex: Optional[re.Pattern] = None  # 预编译的正则表达式
    
    def __post_init__(self):
        """后初始化，预编译正则表达式以提高性能"""
        if self.strategy_type == StrategyType.REGEX:
            try:
                self.compiled_regex = re.compile(self.pattern)
            except re.error as e:
                raise ValueError(f"无效的正则表达式 '{self.pattern}': {e}")
        elif self.strategy_type == StrategyType.WILDCARD:
            # 如果有约束参数，验证参数数量与通配符数量是否匹配
            if self.range_filter.strip():
                constraints = self._parse_constraints(self.range_filter)
                wildcard_count = self.pattern.count('*')
                
                if len(constraints) != wildcard_count:
                    raise ValueError(
                        f"通配符数量({wildcard_count})与参数数量({len(constraints)})不匹配。"
                        f"模式: '{self.pattern}', 参数: '{self.range_filter}'"
                    )
            
            # 将通配符转换为正则表达式并预编译
            try:
                regex_pattern = fnmatch.translate(self.pattern)
                self.compiled_regex = re.compile(regex_pattern)
            except re.error as e:
                raise ValueError(f"无效的通配符模式 '{self.pattern}': {e}")
    
    def _parse_wildcard_with_constraints(self, filename: str) -> bool:
        """
        解析通配符模式并应用约束条件
        
        格式：DSC+{100-111},{jpg,png}
        - 第一个{}对应第一个*的约束
        - 第二个{}对应第二个*的约束
        - 支持范围：{100-111}、精确值：{jpg,png}、数值范围：{100-200}
        """
        if not self.range_filter.strip():
            return True  # 无约束，直接通过
            
        # 1. 解析约束参数
        constraints = self._parse_constraints(self.range_filter)
        
        # 2. 计算通配符数量
        wildcard_count = self.pattern.count('*')
        
        # 3. 严格检查参数数量与通配符数量是否匹配
        if len(constraints) != wildcard_count:
            raise ValueError(
                f"通配符数量({wildcard_count})与参数数量({len(constraints)})不匹配。"
                f"模式: '{self.pattern}', 参数: '{self.range_filter}'"
            )
        
        # 4. 特殊处理连续通配符
        if '**' in self.pattern:
            return self._validate_consecutive_wildcards(filename, self.pattern, constraints)
        
        # 5. 普通通配符处理：构建捕获正则表达式
        capture_pattern = self._build_capture_pattern(self.pattern)
        if not capture_pattern:
            return True  # 无法构建捕获模式，回退到基本匹配
            
        # 6. 执行匹配并验证约束
        import re as regex_module
        match = regex_module.match(capture_pattern, filename)
        if not match:
            return False  # 基本模式不匹配
            
        # 7. 验证每个捕获组是否满足约束
        captured_groups = match.groups()
        return self._validate_constraints(captured_groups, constraints)
    
    def _parse_constraints(self, range_filter: str) -> List[Optional[Dict]]:
        """
        解析约束参数，支持空约束语法
        
        输入格式：
        - ",{ME}" = [None, {"type": "exact_string", "value": "ME"}] (空参数=任意)
        - "{},{ME}" = [{"type": "exact_string", "value": ""}, {"type": "exact_string", "value": "ME"}] ({}=空字符串)
        - "{RE},{ME}" = [{"type": "exact_string", "value": "RE"}, {"type": "exact_string", "value": "ME"}]
        """
        if not range_filter.strip():
            return []
            
        constraints = []
        
        # 使用正则表达式找到所有花括号内容，避免被内部逗号干扰
        import re
        brace_pattern = r'\{[^}]*\}'
        
        # 先替换所有花括号内容为占位符，避免内部逗号干扰分割
        placeholder_map = {}
        placeholder_counter = 0
        
        def replace_braces(match):
            nonlocal placeholder_counter
            placeholder = f"__BRACE_{placeholder_counter}__"
            placeholder_map[placeholder] = match.group(0)
            placeholder_counter += 1
            return placeholder
        
        temp_filter = re.sub(brace_pattern, replace_braces, range_filter)
        
        # 现在按逗号分割，不会被花括号内的逗号干扰
        parts = temp_filter.split(',')
        
        for part in parts:
            part = part.strip()
            
            if not part:
                # 空字符串部分 = 空参数（任意匹配）
                constraints.append(None)
            else:
                # 恢复花括号内容
                for placeholder, original in placeholder_map.items():
                    part = part.replace(placeholder, original)
                
                if part == '{}':
                    # 空花括号 = 必须匹配空字符串
                    constraints.append({"type": "exact_string", "value": ""})
                elif part.startswith('{') and part.endswith('}'):
                    # 有内容的花括号
                    constraint_content = part[1:-1]  # 去掉花括号
                    constraint = self._parse_single_constraint(constraint_content)
                    constraints.append(constraint)
                else:
                    # 没有花括号的部分，当作精确字符串匹配
                    constraints.append({"type": "exact_string", "value": part})
                    
        return constraints
    
    def _parse_single_constraint(self, constraint_str: str) -> Optional[Dict]:
        """解析单个约束条件，支持空字符串约束"""
        # 注意：这里不再strip()，保留空字符串
        
        # 空字符串是有效的精确匹配约束
        if constraint_str == "":
            return {"type": "exact_string", "value": ""}
        
        # 数值范围：100-111
        if '-' in constraint_str and not constraint_str.startswith('-'):
            parts = constraint_str.split('-')
            if len(parts) == 2:
                try:
                    min_val = int(parts[0].strip())
                    max_val = int(parts[1].strip())
                    return {"type": "range", "min": min_val, "max": max_val}
                except ValueError:
                    pass
        
        # 多个值：jpg,png
        if ',' in constraint_str:
            values = [v.strip() for v in constraint_str.split(',')]
            return {"type": "values", "values": values}
        
        # 单个值：尝试作为数字或字符串
        try:
            num_val = int(constraint_str)
            return {"type": "exact_number", "value": num_val}
        except ValueError:
            # 作为字符串（包括空字符串以外的所有字符串）
            return {"type": "exact_string", "value": constraint_str}
        
        return None
    
    def _build_capture_pattern(self, wildcard_pattern: str) -> str:
        """
        将通配符模式转换为带捕获组的正则表达式
        
        输入: "*.*"
        输出: "([^.]*)\\.([^.]*)"
        
        输入: "***.jpg"  
        输出: 使用分割算法优化的捕获模式
        """
        import re as regex_module
        
        # 特殊处理连续通配符的情况
        if '**' in wildcard_pattern:
            return self._build_consecutive_wildcard_pattern(wildcard_pattern)
        
        # 普通情况：转义所有特殊字符
        escaped = regex_module.escape(wildcard_pattern)
        
        # 恢复*为占位符
        escaped = escaped.replace('\\*', '____STAR____')
        
        # 统计*的数量
        star_count = wildcard_pattern.count('*')
        
        # 根据*的数量构建捕获组
        current_star = 0
        result = escaped
        
        while '____STAR____' in result:
            # 根据位置确定捕获模式
            if current_star == star_count - 1:
                # 最后一个*，可以贪婪匹配
                result = result.replace('____STAR____', '([^.]*)', 1)
            else:
                # 不是最后一个*，使用非贪婪匹配
                result = result.replace('____STAR____', '([^.]*?)', 1)
            current_star += 1
        
        return result
    
    def _build_consecutive_wildcard_pattern(self, wildcard_pattern: str) -> str:
        """
        处理连续通配符模式，如 ***.jpg
        使用分割策略避免指数复杂度
        """
        import re as regex_module
        
        # 找到连续*的位置和数量
        consecutive_groups = []
        i = 0
        while i < len(wildcard_pattern):
            if wildcard_pattern[i] == '*':
                # 统计连续*的数量
                star_count = 0
                start_pos = i
                while i < len(wildcard_pattern) and wildcard_pattern[i] == '*':
                    star_count += 1
                    i += 1
                consecutive_groups.append((start_pos, star_count))
            else:
                i += 1
        
        if not consecutive_groups:
            return regex_module.escape(wildcard_pattern)
        
        # 构建优化的正则表达式
        result = ""
        last_end = 0
        
        for group_idx, (start_pos, star_count) in enumerate(consecutive_groups):
            # 添加前面的固定部分
            if start_pos > last_end:
                fixed_part = wildcard_pattern[last_end:start_pos]
                result += regex_module.escape(fixed_part)
            
            # 处理连续的*
            if star_count == 1:
                # 单个*，使用[^.]*?（不匹配点号）
                result += '([^.]*?)'
            else:
                # 多个连续*，允许匹配任意字符（包括点号）
                # 这样可以处理像 photo.project.jpg 这样的复杂文件名
                for i in range(star_count):
                    if i == star_count - 1:
                        # 最后一个*：贪婪匹配剩余内容到文件扩展名之前
                        # 查看后面是否有固定的扩展名部分
                        remaining_pattern = wildcard_pattern[start_pos + star_count:]
                        if remaining_pattern.startswith('.'):
                            # 有扩展名，使用非贪婪匹配到扩展名之前
                            result += '(.*?)'
                        else:
                            # 没有扩展名，可以贪婪匹配
                            result += '(.*)'
                    else:
                        # 前面的*：允许匹配任意字符，但尽量少匹配
                        result += '(.*?)'
            
            last_end = start_pos + star_count
        
        # 添加最后的固定部分
        if last_end < len(wildcard_pattern):
            fixed_part = wildcard_pattern[last_end:]
            result += regex_module.escape(fixed_part)
        
        return result
    
    def _validate_consecutive_wildcards(self, filename: str, pattern: str, constraints: List[Optional[Dict]]) -> bool:
        """
        使用动态规划算法处理连续通配符的验证逻辑
        """
        if not constraints:
            return True
            
        # 统计通配符数量
        wildcard_count = pattern.count('*')
        
        # 获取固定前缀和后缀
        prefix = ""
        suffix = ""
        wildcard_section = pattern
        
        # 找到第一个*之前的前缀
        first_star = pattern.find('*')
        if first_star > 0:
            prefix = pattern[:first_star]
            wildcard_section = pattern[first_star:]
        
        # 找到最后一个*之后的后缀
        last_star = pattern.rfind('*')
        if last_star < len(pattern) - 1:
            suffix = pattern[last_star + 1:]
            wildcard_section = pattern[first_star:last_star + 1]
        
        # 验证前缀和后缀
        if prefix and not filename.startswith(prefix):
            return False
        if suffix and not filename.endswith(suffix):
            return False
            
        # 提取中间需要匹配的部分
        middle_part = filename
        if prefix:
            middle_part = middle_part[len(prefix):]
        if suffix:
            middle_part = middle_part[:-len(suffix)]
            
        # 使用动态规划算法分配捕获组
        captured_groups = self._dp_wildcard_match(middle_part, wildcard_count, constraints)
        
        if captured_groups is None:
            return False
            
        # 验证捕获的内容是否满足约束
        return self._validate_constraints(captured_groups, constraints)
    
    def _dp_wildcard_match(self, text: str, wildcard_count: int, constraints: List[Optional[Dict]]) -> Optional[tuple]:
        """
        使用动态规划算法分配通配符捕获组
        
        正确处理通配符之间的固定字符分隔符
        """
        if wildcard_count == 0:
            return () if len(text) == 0 else None
        if len(text) == 0:
            # 检查是否所有约束都允许空字符串
            for constraint in constraints:
                if constraint and not self._is_valid_capture("", constraint):
                    return None
            return ("",) * wildcard_count
        
        # 解析模式中的固定字符部分，但需要去掉已经处理的前缀和后缀
        # 因为传入的text已经是去掉前后缀的中间部分
        pattern_for_middle = self.pattern
        
        # 找到第一个*之前的前缀
        first_star = pattern_for_middle.find('*')
        if first_star > 0:
            pattern_for_middle = pattern_for_middle[first_star:]
        
        # 找到最后一个*之后的后缀
        last_star = pattern_for_middle.rfind('*')
        if last_star < len(pattern_for_middle) - 1:
            pattern_for_middle = pattern_for_middle[:last_star + 1]
        
        print(f"DEBUG: 调整后的pattern_for_middle: '{pattern_for_middle}'")
        pattern_parts = self._parse_wildcard_pattern(pattern_for_middle)
        
        # 使用动态规划进行匹配
        return self._dp_match_with_separators(text, pattern_parts, constraints)
    
    def _parse_wildcard_pattern(self, pattern: str) -> List[str]:
        """
        解析通配符模式，返回固定字符部分和通配符部分的列表
        例如：**_*.md -> ['*', '*', '_', '*', '.md']
        但由于我们已经去掉了后缀，实际处理的是 **_* -> ['*', '*', '_', '*']
        """
        parts = []
        i = 0
        current_fixed = ""
        
        while i < len(pattern):
            if pattern[i] == '*':
                # 先保存之前的固定字符
                if current_fixed:
                    parts.append(current_fixed)
                    current_fixed = ""
                # 添加通配符
                parts.append('*')
                i += 1
            else:
                # 收集固定字符
                current_fixed += pattern[i]
                i += 1
        
        # 保存最后的固定字符
        if current_fixed:
            parts.append(current_fixed)
            
        return parts
    
    def _dp_match_with_separators(self, text: str, pattern_parts: List[str], constraints: List[Optional[Dict]]) -> Optional[tuple]:
        """
        使用动态规划匹配，考虑固定字符分隔符
        统一的通配符解析算法，不再枚举特殊情况
        """
        print(f"DEBUG: _dp_match_with_separators - text: '{text}', pattern_parts: {pattern_parts}")
        
        # 统一使用通用的DP算法，不再区分特殊情况
        wildcard_count = len([p for p in pattern_parts if p == '*'])
        return self._universal_dp_match(text, pattern_parts, constraints, wildcard_count)
    
    # def _simple_separator_match(self, text: str, separator: str, constraints: List[Optional[Dict]]) -> Optional[tuple]:
    #     """处理 *sep* 格式的简单情况 - 已注释，使用统一算法"""
    #     pass
    
    # def _correct_double_wildcard_separator_match(self, text: str, separator: str, constraints: List[Optional[Dict]]) -> Optional[tuple]:
    #     """正确处理 **sep* 格式的情况 - 已注释，使用统一算法"""
    #     pass
    
    # def _double_wildcard_separator_match(self, text: str, separator: str, constraints: List[Optional[Dict]]) -> Optional[tuple]:
    #     """处理 **sep* 格式的情况 - 已注释，使用统一算法"""
    #     pass
    
    def _universal_dp_match(self, text: str, pattern_parts: List[str], constraints: List[Optional[Dict]], wildcard_count: int) -> Optional[tuple]:
        """
        统一的通配符匹配算法，使用动态规划处理所有情况
        
        算法思路：
        1. 将pattern_parts按顺序处理，通配符和固定字符交替出现
        2. 使用DP状态：dp[i][j] = 是否可以用前i个pattern_parts匹配前j个字符
        3. 同时记录捕获组的分配
        """
        print(f"DEBUG: _universal_dp_match - text: '{text}', pattern_parts: {pattern_parts}")
        print(f"DEBUG: wildcard_count: {wildcard_count}, constraints: {constraints}")
        
        n = len(text)
        m = len(pattern_parts)
        
        if wildcard_count == 0:
            # 没有通配符，直接比较固定字符
            expected_text = ''.join(pattern_parts)
            return () if text == expected_text else None
        
        # 提取通配符位置
        wildcard_positions = [i for i, part in enumerate(pattern_parts) if part == '*']
        print(f"DEBUG: wildcard_positions: {wildcard_positions}")
        
        # 递归回溯匹配
        def backtrack(part_idx: int, text_pos: int, captures: List[str]) -> Optional[List[str]]:
            print(f"DEBUG: backtrack - part_idx: {part_idx}, text_pos: {text_pos}, captures: {captures}")
            
            # 递归终止条件
            if part_idx >= m:
                if text_pos >= n:
                    print(f"DEBUG: 匹配成功，captures: {captures}")
                    return captures if len(captures) == wildcard_count else None
                else:
                    print(f"DEBUG: part_idx达到末尾但text_pos未到末尾，失败")
                    return None
            
            current_part = pattern_parts[part_idx]
            print(f"DEBUG: 处理part[{part_idx}]: '{current_part}'")
            
            if current_part == '*':
                # 当前是通配符，尝试不同的匹配长度
                wildcard_idx = len(captures)  # 当前通配符的索引
                print(f"DEBUG: 通配符 {wildcard_idx}")
                
                # 计算这个通配符可以匹配的最大长度
                max_match_len = n - text_pos
                
                # 如果还有后续部分，需要为它们预留空间
                remaining_fixed_len = 0
                for i in range(part_idx + 1, m):
                    if pattern_parts[i] != '*':
                        remaining_fixed_len += len(pattern_parts[i])
                
                max_match_len = min(max_match_len, n - text_pos - remaining_fixed_len)
                print(f"DEBUG: max_match_len: {max_match_len}, remaining_fixed_len: {remaining_fixed_len}")
                
                # 尝试不同的匹配长度
                for match_len in range(max_match_len + 1):
                    capture_text = text[text_pos:text_pos + match_len]
                    print(f"DEBUG: 尝试匹配长度 {match_len}, capture_text: '{capture_text}'")
                    
                    # 验证约束
                    if wildcard_idx < len(constraints) and constraints[wildcard_idx]:
                        if not self._is_valid_capture(capture_text, constraints[wildcard_idx]):
                            print(f"DEBUG: 约束验证失败")
                            continue
                        else:
                            print(f"DEBUG: 约束验证成功")
                    
                    # 递归匹配后续部分
                    new_captures = captures + [capture_text]
                    result = backtrack(part_idx + 1, text_pos + match_len, new_captures)
                    if result is not None:
                        return result
                
                print(f"DEBUG: 通配符匹配失败")
                return None
            else:
                # 当前是固定字符，必须精确匹配
                fixed_text = current_part
                print(f"DEBUG: 固定字符: '{fixed_text}'")
                if text_pos + len(fixed_text) > n:
                    print(f"DEBUG: 固定字符超出文本长度")
                    return None
                if text[text_pos:text_pos + len(fixed_text)] != fixed_text:
                    print(f"DEBUG: 固定字符不匹配: 期望'{fixed_text}', 实际'{text[text_pos:text_pos + len(fixed_text)]}'")
                    return None
                
                print(f"DEBUG: 固定字符匹配成功")
                # 匹配成功，继续处理下一部分
                return backtrack(part_idx + 1, text_pos + len(fixed_text), captures)
        
        # 开始回溯
        result = backtrack(0, 0, [])
        if result is not None:
            print(f"DEBUG: 找到匹配: {result}")
            return tuple(result)
        else:
            print(f"DEBUG: 没有找到匹配")
            return None
    
    # def _complex_dp_match(self, text: str, wildcard_count: int, constraints: List[Optional[Dict]]) -> Optional[tuple]:
    #     """复杂情况的动态规划匹配（原来的算法）- 已注释，使用统一算法"""
    #     pass
    
    # def _backtrack_assign(self, wildcard_idx: int, min_pos: int, current_assignment: list, 
    #                      possible_matches: list, text_len: int, wildcard_count: int) -> Optional[list]:
    #     """回溯算法分配通配符位置 - 已注释，使用统一算法"""
    #     pass
    
    def _is_valid_capture(self, captured_text: str, constraint: Optional[Dict]) -> bool:
        """
        检查捕获的文本是否满足约束
        在DP过程中进行预验证以剪枝
        """
        if constraint is None:
            return True  # 空约束总是满足
            
        # 对于某些约束类型可以提前验证
        constraint_type = constraint.get("type")
        
        if constraint_type == "exact_string":
            return captured_text == constraint["value"]
        elif constraint_type == "range":
            # 数值范围验证 - 要求整个捕获文本都是数字
            if not captured_text.isdigit():
                return False
            try:
                value = int(captured_text)
                return constraint["min"] <= value <= constraint["max"]
            except ValueError:
                return False
        elif constraint_type == "exact_number":
            # 精确数值匹配 - 要求整个捕获文本都是数字
            if not captured_text.isdigit():
                return False
            try:
                value = int(captured_text)
                return value == constraint["value"]
            except ValueError:
                return False
        elif constraint_type == "values":
            # 多值匹配
            return captured_text in constraint["values"]
            
        return True  # 其他情况暂时认为有效
    
    def _validate_constraints(self, captured_groups: tuple, constraints: List[Optional[Dict]]) -> bool:
        """验证捕获的内容是否满足约束条件"""
        if not constraints:
            return True
            
        # 确保约束和捕获组数量一致
        max_len = max(len(captured_groups), len(constraints))
        
        for i in range(max_len):
            # 获取捕获值和约束
            captured = captured_groups[i] if i < len(captured_groups) else ""
            constraint = constraints[i] if i < len(constraints) else None
            
            # 跳过空约束
            if constraint is None:
                continue
                
            # 验证非空约束
            if not self._validate_single_constraint(captured, constraint):
                return False
        
        return True
    
    def _validate_single_constraint(self, captured_value: str, constraint: Optional[Dict]) -> bool:
        """验证单个捕获值是否满足约束"""
        if constraint is None:
            return True  # 空约束总是通过（任意匹配）
            
        constraint_type = constraint.get("type")
        
        if constraint_type == "range":
            # 数值范围验证：要求整个捕获文本都是数字
            if not captured_value.isdigit():
                return False
            try:
                value = int(captured_value)
                return constraint["min"] <= value <= constraint["max"]
            except ValueError:
                return False
                
        elif constraint_type == "values":
            # 多值匹配
            return captured_value in constraint["values"]
            
        elif constraint_type == "exact_number":
            # 精确数值匹配：要求整个捕获文本都是数字
            if not captured_value.isdigit():
                return False
            try:
                value = int(captured_value)
                return value == constraint["value"]
            except ValueError:
                return False
                
        elif constraint_type == "exact_string":
            # 精确字符串匹配（包括空字符串）
            return captured_value == constraint["value"]
        
        return True
    
    def matches(self, filename: str) -> bool:
        """检查文件名是否匹配当前策略"""
        if self.strategy_type == StrategyType.CONTAINS:
            return self.pattern in filename
        elif self.strategy_type == StrategyType.WILDCARD:
            # 对于通配符，如果有约束条件，使用约束验证
            if self.range_filter.strip():
                return self._parse_wildcard_with_constraints(filename)
            else:
                # 无约束的通配符，使用基本模式匹配
                return bool(self.compiled_regex and self.compiled_regex.match(filename))
        elif self.strategy_type == StrategyType.REGEX:
            # 正则表达式直接匹配
            return bool(self.compiled_regex and self.compiled_regex.match(filename))
        return False

@dataclass
class StrategyGroup:
    """策略组定义 - 包含多个策略，使用AND逻辑"""
    group_name: str
    strategies: List[Strategy]
    
    def matches(self, filename: str) -> bool:
        """检查文件名是否匹配策略组（所有策略都必须匹配）"""
        if not self.strategies:
            return False
        return all(strategy.matches(filename) for strategy in self.strategies)

# ==================== 全局策略组存储 ====================

GLOBAL_STRATEGY_GROUPS: List[StrategyGroup] = []

# ==================== 辅助函数 ====================

def create_strategy(strategy_type_str: str, pattern: str, range_filter: str = "") -> Strategy:
    """
    创建策略对象
    
    Args:
        strategy_type_str: 策略类型字符串
        pattern: 匹配模式
        range_filter: 范围过滤器（可选，主要用于通配符）
        
    Returns:
        Strategy对象
    """
    try:
        strategy_type = StrategyType(strategy_type_str)
    except ValueError:
        raise ValueError(f"无效的策略类型: {strategy_type_str}")
    
    return Strategy(strategy_type, pattern, range_filter)

def setup_global_strategy_groups(groups_config: Optional[List[Dict[str, Any]]] = None) -> List[StrategyGroup]:
    """
    设置全局策略组 - 支持编程配置和交互式配置
    
    Args:
        groups_config: 可选的策略组配置列表，格式如下：
        [
            {
                "group_name": "图片文件",
                "strategies": [
                    {"type": "wildcard", "pattern": "*.jpg"},
                    {"type": "contains", "pattern": "IMG"}
                ]
            }
        ]
        
    Returns:
        设置的策略组列表
    """
    global GLOBAL_STRATEGY_GROUPS
    
    if groups_config is not None:
        # 使用提供的配置
        GLOBAL_STRATEGY_GROUPS.clear()
        for group_config in groups_config:
            strategies = []
            for strategy_config in group_config.get('strategies', []):
                try:
                    strategy = create_strategy(
                        strategy_config['type'], 
                        strategy_config['pattern'],
                        strategy_config.get('range_filter', '')
                    )
                    strategies.append(strategy)
                except (KeyError, ValueError) as e:
                    print(f"⚠️ 跳过无效策略: {e}")
                    continue
            
            if strategies:  # 只有当策略组有有效策略时才添加
                strategy_group = StrategyGroup(group_config['group_name'], strategies)
                GLOBAL_STRATEGY_GROUPS.append(strategy_group)
        
        return GLOBAL_STRATEGY_GROUPS
    
    # 交互式配置
    print("=== 设置全局策略组 ===")
    print("策略组系统说明：")
    print("- 每个分组可以有一个或多个策略组")
    print("- 策略组内的所有策略都必须匹配才返回分组名（AND逻辑）")
    print("- 分组名可以重复，实现OR逻辑（多个策略组匹配同一分组）")
    print("- 最终返回时会自动去重\n")
    
    GLOBAL_STRATEGY_GROUPS.clear()
    
    while True:
        group_name = input("请输入分组名称（直接回车结束）: ").strip()
        if not group_name:
            break
            
        strategies = []
        print(f"\n为分组 '{group_name}' 添加策略:")
        
        while True:
            print("\n策略类型:")
            print("1. contains - 包含字符串")
            print("2. wildcard - 通配符 (*, ?)")
            print("3. regex - 正则表达式")
            
            strategy_choice = input("选择策略类型 (1-3，直接回车完成当前分组): ").strip()
            if not strategy_choice:
                break
                
            strategy_type_map = {'1': 'contains', '2': 'wildcard', '3': 'regex'}
            if strategy_choice not in strategy_type_map:
                print("❌ 无效选择")
                continue
                
            strategy_type = strategy_type_map[strategy_choice]
            pattern = input(f"请输入 {strategy_type} 模式: ").strip()
            
            if not pattern:
                print("❌ 模式不能为空")
                continue
                
            try:
                strategy = create_strategy(strategy_type, pattern)
                strategies.append(strategy)
                print(f"✅ 已添加策略: {strategy_type} = '{pattern}'")
            except ValueError as e:
                print(f"❌ 策略无效: {e}")
        
        if strategies:
            strategy_group = StrategyGroup(group_name, strategies)
            GLOBAL_STRATEGY_GROUPS.append(strategy_group)
            print(f"✅ 已添加策略组 '{group_name}'，包含 {len(strategies)} 个策略")
        else:
            print(f"⚠️ 策略组 '{group_name}' 没有有效策略，已跳过")
    
    print(f"\n✅ 配置完成！共设置了 {len(GLOBAL_STRATEGY_GROUPS)} 个策略组")
    return GLOBAL_STRATEGY_GROUPS

# ==================== 主要分组函数 ====================

def manual_grouping(filepath: str) -> List[str]:
    """
    手动分组插件的核心文件分组函数
    
    基于预配置的策略组对输入文件进行智能分组，支持多种匹配策略的灵活组合。
    该函数是插件的主要入口点，被文件分类器系统调用以确定文件应归属的分组。
    
    匹配策略：
    1. 包含字符串匹配：检查文件名是否包含指定文本
    2. 通配符匹配：使用 * 和 ? 进行模式匹配，支持高级约束参数
    3. 正则表达式匹配：使用完整的Python正则表达式语法
    
    策略组逻辑：
    - 组内策略：使用AND逻辑，所有策略都必须匹配才能归属该组
    - 组间策略：使用OR逻辑，文件可以同时属于多个分组
    - 优先级：无固定优先级，支持多重分组归属
    
    性能优化：
    - 预编译正则表达式，避免重复编译开销
    - 使用set自动去重，提高大批量文件处理效率
    - 仅对文件名进行匹配，忽略路径信息
    
    Args:
        filepath: 文件的完整路径，函数将自动提取文件名进行匹配
        
    Returns:
        List[str]: 匹配的分组名称列表，可能为空列表或包含多个分组名
                  结果已自动去重，无重复分组名
                  
    Example:
        >>> manual_grouping("/path/to/IMG_1234.jpg")
        ["照片文件", "大尺寸图片"]
        
        >>> manual_grouping("/path/to/document.pdf") 
        ["文档文件"]
        
        >>> manual_grouping("/path/to/unknown.xyz")
        []
        
    Note:
        - 如果未配置任何策略组，返回空列表
        - 文件名大小写敏感，具体取决于各策略的实现
        - 策略组配置通过GUI界面或配置文件管理
    """
    if not GLOBAL_STRATEGY_GROUPS:
        return []
    
    # 只对文件名进行匹配，不考虑路径
    filename = os.path.basename(filepath)
    
    matched_groups = set()  # 使用set自动去重
    
    for strategy_group in GLOBAL_STRATEGY_GROUPS:
        if strategy_group.matches(filename):
            matched_groups.add(strategy_group.group_name)
    
    return list(matched_groups)

# ==================== 测试和验证函数 ====================

def test_manual_grouping(test_files: List[str]) -> Dict[str, List[str]]:
    """
    测试手动分组功能
    
    Args:
        test_files: 测试文件名列表
        
    Returns:
        文件名到匹配分组的映射
    """
    results = {}
    for filename in test_files:
        groups = manual_grouping(filename)
        results[filename] = groups
    return results

def validate_strategy_pattern(strategy_type_str: str, pattern: str) -> bool:
    """
    验证策略模式是否有效
    
    Args:
        strategy_type_str: 策略类型字符串
        pattern: 模式字符串
        
    Returns:
        是否有效
    """
    try:
        create_strategy(strategy_type_str, pattern)
        return True
    except ValueError:
        return False

# ==================== GUI 类定义 ====================

if GUI_AVAILABLE:
    class StrategyConfigWidget(QWidget):
        """单个策略配置控件 - 简洁实用设计"""
        
        def __init__(self, strategy: Strategy, strategy_index: int, on_delete=None):
            super().__init__()
            self.strategy = strategy
            self.strategy_index = strategy_index
            self.on_delete = on_delete
            self.init_ui()
            
        def init_ui(self):
            """初始化简洁UI"""
            layout = QVBoxLayout()
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(5)
            
            # 第一行：策略编号、类型、删除按钮
            first_row = QHBoxLayout()
            first_row.setSpacing(10)
            
            # 策略编号
            index_label = QLabel(f"策略{self.strategy_index + 1}:")
            index_label.setMinimumWidth(60)
            first_row.addWidget(index_label)
            
            # 策略类型下拉框
            self.strategy_type_combo = QComboBox()
            self.strategy_type_combo.addItems(['包含字符', '通配符', '正则表达式'])
            self.strategy_type_combo.setMinimumWidth(80)
            
            # 映射显示名称到内部值
            self.type_mapping = {
                '包含字符': 'contains',
                '通配符': 'wildcard', 
                '正则表达式': 'regex'
            }
            self.reverse_mapping = {v: k for k, v in self.type_mapping.items()}
            
            current_type = self.reverse_mapping.get(self.strategy.strategy_type.value, '包含字符')
            self.strategy_type_combo.setCurrentText(current_type)
            self.strategy_type_combo.currentTextChanged.connect(self.on_strategy_type_changed)
            first_row.addWidget(self.strategy_type_combo)
            
            first_row.addStretch()
            
            # 删除按钮
            if self.on_delete:
                delete_btn = QPushButton("删除")
                delete_btn.setMaximumWidth(60)
                delete_btn.clicked.connect(self.on_delete_clicked)
                first_row.addWidget(delete_btn)
            
            layout.addLayout(first_row)
            
            # 第二行：匹配内容输入框
            second_row = QHBoxLayout()
            second_row.setSpacing(10)
            
            pattern_label = QLabel("匹配内容:")
            pattern_label.setMinimumWidth(60)
            second_row.addWidget(pattern_label)
            
            self.pattern_input = QLineEdit()
            self.pattern_input.setText(self.strategy.pattern)
            self.update_placeholder()
            second_row.addWidget(self.pattern_input, 1)
            
            layout.addLayout(second_row)
            
            # 第三行：范围过滤器（仅通配符显示）
            self.range_row = QHBoxLayout()
            self.range_row.setSpacing(10)
            
            self.range_label = QLabel("数值范围:")
            self.range_label.setMinimumWidth(60)
            self.range_row.addWidget(self.range_label)
            
            self.range_input = QLineEdit()
            self.range_input.setText(self.strategy.range_filter)
            self.range_input.setPlaceholderText("如: {100-111},{jpg,png} 或 {1920},{4096}")
            self.range_row.addWidget(self.range_input, 1)
            
            layout.addLayout(self.range_row)
            
            # 根据当前类型显示/隐藏范围输入
            self.update_range_visibility()
            
            self.setLayout(layout)
            
        def update_range_visibility(self):
            """根据策略类型显示/隐藏范围输入框"""
            strategy_type = self.type_mapping.get(self.strategy_type_combo.currentText(), 'contains')
            is_wildcard = strategy_type == 'wildcard'
            
            # 显示或隐藏范围相关控件
            self.range_label.setVisible(is_wildcard)
            self.range_input.setVisible(is_wildcard)
            
        def update_placeholder(self):
            """更新输入框提示文本"""
            strategy_type = self.type_mapping.get(self.strategy_type_combo.currentText(), 'contains')
            if strategy_type == 'contains':
                self.pattern_input.setPlaceholderText("输入要包含的字符串，如: IMG_")
            elif strategy_type == 'wildcard':
                self.pattern_input.setPlaceholderText("使用通配符，如: *.jpg, *_1920*")
            elif strategy_type == 'regex':
                self.pattern_input.setPlaceholderText("输入正则表达式，如: ^IMG_\\d+\\.jpg$")
            
        def on_strategy_type_changed(self, text):
            """策略类型变更事件"""
            try:
                strategy_type_value = self.type_mapping.get(text, 'contains')
                self.strategy.strategy_type = StrategyType(strategy_type_value)
                self.update_placeholder()
                self.update_range_visibility()
                # 重新编译正则表达式
                self.strategy.__post_init__()
            except (ValueError, re.error):
                pass
                
        def on_delete_clicked(self):
            """删除按钮点击事件"""
            if self.on_delete:
                reply = QMessageBox.question(self, '确认删除', '确定要删除此策略吗？',
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                             QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    self.on_delete()
                    
        def get_strategy(self) -> Strategy:
            """获取当前策略配置"""
            strategy_type_value = self.type_mapping.get(self.strategy_type_combo.currentText(), 'contains')
            pattern = self.pattern_input.text()
            range_filter = self.range_input.text() if hasattr(self, 'range_input') else ""
            strategy = Strategy(StrategyType(strategy_type_value), pattern, range_filter)
            return strategy

    class StrategyGroupConfigWidget(QWidget):
        """策略组配置控件 - 简洁实用设计"""
        
        def __init__(self, group: StrategyGroup, group_index: int):
            super().__init__()
            self.group = group
            self.group_index = group_index
            self.strategy_widgets = []
            self.init_ui()
            
        def init_ui(self):
            """初始化简洁UI"""
            # 主布局
            main_layout = QVBoxLayout()
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(10)
            
            # 分组头部
            header_layout = QHBoxLayout()
            header_layout.setSpacing(10)
            
            # 分组标题
            group_title = QLabel(f"分组 {self.group_index + 1}")
            group_title.setStyleSheet("font-weight: bold; font-size: 14px;")
            header_layout.addWidget(group_title)
            
            # 分组名称输入
            name_label = QLabel("名称:")
            header_layout.addWidget(name_label)
            
            self.group_name_input = QLineEdit()
            self.group_name_input.setText(self.group.group_name)
            self.group_name_input.setPlaceholderText("输入分组名称")
            header_layout.addWidget(self.group_name_input, 1)
            
            # 添加策略按钮
            add_strategy_btn = QPushButton("添加策略")
            add_strategy_btn.clicked.connect(self.add_strategy)
            header_layout.addWidget(add_strategy_btn)
            
            main_layout.addLayout(header_layout)
            
            # 策略区域标题
            strategies_title = QLabel("策略列表:")
            strategies_title.setStyleSheet("font-weight: bold; margin-top: 5px;")
            main_layout.addWidget(strategies_title)
            
            # 策略列表容器 - 动态扩展，不使用滚动条
            self.strategies_widget = QWidget()
            self.strategies_layout = QVBoxLayout(self.strategies_widget)
            self.strategies_layout.setContentsMargins(0, 0, 0, 0)
            self.strategies_layout.setSpacing(5)
            
            main_layout.addWidget(self.strategies_widget)
            
            # 加载现有策略
            for strategy in self.group.strategies:
                self.add_strategy_widget(strategy)
                
            # 添加分隔线
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setFrameShadow(QFrame.Shadow.Sunken)
            main_layout.addWidget(separator)
            
            self.setLayout(main_layout)
        def add_strategy(self):
            """添加新策略"""
            strategy = Strategy(StrategyType.CONTAINS, "")
            self.add_strategy_widget(strategy)
            
        def add_strategy_widget(self, strategy: Strategy):
            """添加策略控件"""
            def delete_strategy():
                self.strategy_widgets.remove(widget)
                self.strategies_layout.removeWidget(widget)
                widget.deleteLater()
                # 更新所有策略的索引显示
                self.update_strategy_indices()
                
            strategy_index = len(self.strategy_widgets)
            widget = StrategyConfigWidget(strategy, strategy_index, on_delete=delete_strategy)
            self.strategy_widgets.append(widget)
            self.strategies_layout.addWidget(widget)
            
        def update_strategy_indices(self):
            """更新所有策略的索引显示"""
            for i, widget in enumerate(self.strategy_widgets):
                widget.strategy_index = i
                # 查找并更新策略标签
                for child in widget.findChildren(QLabel):
                    if "策略" in child.text():
                        child.setText(f"策略{i + 1}:")
                        break
            
        def get_strategy_group(self) -> StrategyGroup:
            """获取当前策略组配置"""
            strategies = []
            for widget in self.strategy_widgets:
                strategy = widget.get_strategy()
                if strategy.pattern:  # 只添加非空模式的策略
                    strategies.append(strategy)
            
            return StrategyGroup(
                group_name=self.group_name_input.text(),
                strategies=strategies
            )

    class StrategyGroupConfigDialog(QDialog):
        """策略组配置对话框 - 简洁实用设计"""
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("手动分组配置")
            self.setModal(True)
            self.resize(900, 600)
            self.group_widgets = []
            self.init_ui()
            self.load_current_config()
            
        def init_ui(self):
            """初始化简洁UI"""
            # 主布局
            layout = QVBoxLayout()
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(10)
            
            # 顶部操作栏
            header_layout = QHBoxLayout()
            header_layout.setSpacing(10)
            
            title = QLabel("手动分组配置")
            title.setStyleSheet("font-weight: bold; font-size: 16px;")
            header_layout.addWidget(title)
            header_layout.addStretch()
            
            # 操作按钮
            add_group_btn = QPushButton("新建分组")
            add_group_btn.clicked.connect(self.add_group)
            header_layout.addWidget(add_group_btn)
            
            test_btn = QPushButton("测试配置")
            test_btn.clicked.connect(self.test_config)
            header_layout.addWidget(test_btn)
            
            clear_btn = QPushButton("清空全部")
            clear_btn.clicked.connect(self.clear_all_groups)
            header_layout.addWidget(clear_btn)
            
            layout.addLayout(header_layout)
            
            # 说明文本
            info_text = QLabel(
                "说明：每个分组内的策略使用AND逻辑（全部匹配），多个分组间使用OR逻辑（任一匹配）"
            )
            info_text.setStyleSheet("color: #666; margin: 5px 0;")
            layout.addWidget(info_text)
            
            # 分组列表滚动区域 - 这是唯一的滚动条
            self.groups_scroll = QScrollArea()
            self.groups_scroll.setWidgetResizable(True)
            self.groups_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            
            self.groups_widget = QWidget()
            self.groups_layout = QVBoxLayout(self.groups_widget)
            self.groups_layout.setContentsMargins(5, 5, 5, 5)
            self.groups_layout.setSpacing(10)
            self.groups_layout.addStretch()  # 底部弹性空间
            
            self.groups_scroll.setWidget(self.groups_widget)
            layout.addWidget(self.groups_scroll, 1)  # 占用剩余空间
            
            # 底部按钮
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
            save_btn = QPushButton("保存")
            save_btn.setDefault(True)
            save_btn.clicked.connect(self.save_config)
            button_layout.addWidget(save_btn)
            
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(self.reject)
            button_layout.addWidget(cancel_btn)
            
            layout.addLayout(button_layout)
            self.setLayout(layout)
            
        def load_current_config(self):
            """加载当前配置"""
            for group in GLOBAL_STRATEGY_GROUPS:
                self.add_group_widget(group)
                
        def add_group(self):
            """添加新策略组"""
            group = StrategyGroup("新分组", [])
            self.add_group_widget(group)
            
        def add_group_widget(self, group: StrategyGroup):
            """添加策略组控件"""
            # 创建策略组容器
            group_container = QWidget()
            container_layout = QVBoxLayout(group_container)
            container_layout.setContentsMargins(5, 5, 5, 5)
            container_layout.setSpacing(5)
            
            # 策略组头部（删除按钮）
            header_layout = QHBoxLayout()
            header_layout.addStretch()
            
            delete_btn = QPushButton("删除分组")
            delete_btn.clicked.connect(lambda: self.delete_group(group_container, widget))
            header_layout.addWidget(delete_btn)
            
            container_layout.addLayout(header_layout)
            
            # 策略组配置控件
            group_index = len(self.group_widgets)
            widget = StrategyGroupConfigWidget(group, group_index)
            container_layout.addWidget(widget)
            
            self.group_widgets.append(widget)
            
            # 在弹性空间之前插入
            insert_index = self.groups_layout.count() - 1
            self.groups_layout.insertWidget(insert_index, group_container)
            
        def delete_group(self, group_container, widget):
            """删除策略组"""
            reply = QMessageBox.question(
                self, '确认删除', 
                f'确定要删除分组 "{widget.group_name_input.text()}" 吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.group_widgets.remove(widget)
                self.groups_layout.removeWidget(group_container)
                group_container.deleteLater()
                # 更新所有分组的索引显示
                self.update_group_indices()
                
        def update_group_indices(self):
            """更新所有分组的索引显示"""
            for i, widget in enumerate(self.group_widgets):
                widget.group_index = i
                # 查找并更新分组标题
                for child in widget.findChildren(QLabel):
                    if "分组" in child.text():
                        child.setText(f"分组 {i + 1}")
                        break
            
        def clear_all_groups(self):
            """清空所有分组"""
            if not self.group_widgets:
                if GUI_AVAILABLE:
                    QMessageBox.information(self, '提示', '当前没有分组可清空')
                return
                
            if GUI_AVAILABLE:
                reply = QMessageBox.question(
                    self, '确认清空', 
                    f'确定要清空所有 {len(self.group_widgets)} 个分组吗？\n此操作不可撤销！',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                    QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # 收集所有需要删除的容器
            containers_to_remove = []
            for i in range(self.groups_layout.count()):
                item = self.groups_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    # 检查这个widget是否包含我们的分组控件
                    for group_widget in self.group_widgets:
                        if widget.findChild(type(group_widget)) == group_widget:
                            containers_to_remove.append(widget)
                            break
            
            # 清空widget列表
            self.group_widgets.clear()
            
            # 删除所有容器
            for container in containers_to_remove:
                self.groups_layout.removeWidget(container)
                container.deleteLater()
                        
            if GUI_AVAILABLE:
                QMessageBox.information(self, '清空完成', '所有分组已清空！')
                
        def test_config(self):
            """测试当前配置"""
            # 获取测试文件名
            test_files, ok = QInputDialog.getMultiLineText(
                self, '🧪 测试配置', 
                '请输入测试文件名（每行一个）:\n\n示例文件:\nIMG_001.jpg\ndocument.pdf\nvideo.mp4\nmusic.mp3\nphoto.png\nreport.docx'
            )
            
            if not ok or not test_files.strip():
                return
                
            # 临时应用配置
            temp_groups = []
            for widget in self.group_widgets:
                group = widget.get_strategy_group()
                if group.strategies:  # 只添加有策略的组
                    temp_groups.append(group)
            
            if not temp_groups:
                QMessageBox.warning(self, '配置为空', '❌ 当前没有有效的分组配置可供测试！')
                return
            
            # 保存原配置并临时设置
            global GLOBAL_STRATEGY_GROUPS
            original_groups = GLOBAL_STRATEGY_GROUPS.copy()
            GLOBAL_STRATEGY_GROUPS = temp_groups
            
            # 执行测试
            test_file_list = [line.strip() for line in test_files.split('\n') if line.strip()]
            results = []
            matched_count = 0
            
            for filename in test_file_list:
                groups = manual_grouping(filename)
                if groups:
                    results.append(f"✅ {filename} → {', '.join(groups)}")
                    matched_count += 1
                else:
                    results.append(f"❌ {filename} → (未匹配)")
            
            # 恢复原配置
            GLOBAL_STRATEGY_GROUPS = original_groups
            
            # 显示结果
            result_text = '\n'.join(results)
            summary = f"测试完成！匹配率: {matched_count}/{len(test_file_list)} ({matched_count/len(test_file_list)*100:.1f}%)"
            
            QMessageBox.information(self, '🧪 测试结果', f'{summary}\n\n详细结果:\n{result_text}')
            
        def save_config(self):
            """保存配置"""
            try:
                # 收集所有策略组
                groups = []
                for widget in self.group_widgets:
                    group = widget.get_strategy_group()
                    if group.strategies:  # 只保存有策略的组
                        groups.append(group)
                
                # 应用配置
                global GLOBAL_STRATEGY_GROUPS
                GLOBAL_STRATEGY_GROUPS = groups
                
                # 保存到配置文件
                if save_plugin_config():
                    config_saved_msg = "✅ 配置已保存到文件"
                else:
                    config_saved_msg = "⚠️ 配置文件保存失败，但内存配置已更新"
                
                QMessageBox.information(
                    self, '保存成功', 
                    f'✅ 配置保存成功！\n\n已保存 {len(groups)} 个分组\n总计 {sum(len(g.strategies) for g in groups)} 个策略\n\n{config_saved_msg}'
                )
                self.accept()
                
            except Exception as e:
                QMessageBox.critical(self, '保存失败', f'❌ 保存配置时出错:\n{str(e)}')

        def load_config_data(self, config_data):
            """加载外部配置数据"""
            try:
                if not config_data or 'groups' not in config_data:
                    return
                
                # 简单清空现有分组
                for widget in self.group_widgets:
                    widget.deleteLater()
                self.group_widgets.clear()
                
                # 加载新配置
                for group_data in config_data['groups']:
                    group_name = group_data.get('name', 'New Group')
                    strategies = []
                    
                    for strategy_data in group_data.get('strategies', []):
                        strategy_type = StrategyType(strategy_data.get('type', 'contains'))
                        pattern = strategy_data.get('pattern', '')
                        strategies.append(Strategy(strategy_type, pattern))
                    
                    if strategies:  # 只添加有策略的组
                        strategy_group = StrategyGroup(group_name, strategies)
                        widget = StrategyGroupConfigWidget(strategy_group, len(self.group_widgets))
                        self.group_widgets.append(widget)
                        self.groups_layout.addWidget(widget)
                
                self.update_group_indices()
                
            except Exception as e:
                print(f"加载配置数据时出错: {e}")
        
        def get_config(self):
            """获取当前配置"""
            try:
                groups = []
                for widget in self.group_widgets:
                    group = widget.get_strategy_group()
                    if group.strategies:  # 只返回有策略的组
                        group_data = {
                            'name': group.name,
                            'strategies': [
                                {
                                    'type': strategy.strategy_type.value,
                                    'pattern': strategy.pattern
                                }
                                for strategy in group.strategies
                            ]
                        }
                        groups.append(group_data)
                
                return {'groups': groups}
                
            except Exception as e:
                print(f"获取配置时出错: {e}")
                return None

def show_strategy_config(initial_config=None, parent=None):
    """显示策略配置对话框"""
    if not GUI_AVAILABLE:
        raise RuntimeError("GUI 组件不可用，请安装 PySide6")
    
    dialog = StrategyGroupConfigDialog(parent)
    if initial_config:
        dialog.load_config_data(initial_config)
    
    if dialog.exec():
        return dialog.get_config()
    return None

# ==================== 插件配置持久化功能 ====================

# 尝试导入插件配置模块
spec = importlib.util.spec_from_file_location("__pluginConfig", os.path.join(os.path.dirname(__file__),"__pluginConfig.py"))

if spec is not None and spec.loader is not None:
	__pluginConfig = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(__pluginConfig)

def save_plugin_config():
    """保存当前策略组配置到配置文件"""
    try:
        # 将当前策略组转换为配置数据
        config_data = {
            'groups': []
        }
        
        for group in GLOBAL_STRATEGY_GROUPS:
            group_data = {
                'name': group.group_name,
                'strategies': []
            }
            
            for strategy in group.strategies:
                strategy_data = {
                    'type': strategy.strategy_type.value,
                    'pattern': strategy.pattern,
                    'range_filter': strategy.range_filter
                }
                group_data['strategies'].append(strategy_data)
            
            config_data['groups'].append(group_data)
        
        # 保存到插件配置
        config_data = __pluginConfig.save_config(config_data)
        return True
        
    except Exception as e:
        print(f"保存插件配置时出错: {e}")
        return False

def load_plugin_config():
    """从配置文件加载策略组配置"""
    try:
        # 从插件配置中加载
        config_data = __pluginConfig.load_config()
        
        if not config_data or 'groups' not in config_data:
            print("未找到 manual_grouping 插件配置，使用默认配置")
            return False
        
        # 清空当前策略组
        global GLOBAL_STRATEGY_GROUPS
        GLOBAL_STRATEGY_GROUPS = []
        
        # 加载策略组
        for group_data in config_data['groups']:
            group_name = group_data.get('name', '未命名分组')
            strategies = []
            
            for strategy_data in group_data.get('strategies', []):
                try:
                    strategy_type = StrategyType(strategy_data.get('type', 'contains'))
                    pattern = strategy_data.get('pattern', '')
                    range_filter = strategy_data.get('range_filter', '')
                    
                    if pattern:  # 只添加有效的策略
                        strategy = Strategy(strategy_type, pattern, range_filter)
                        strategies.append(strategy)
                        
                except Exception as e:
                    print(f"加载策略时出错: {e}")
                    continue
            
            if strategies:  # 只添加有策略的组
                strategy_group = StrategyGroup(group_name, strategies)
                GLOBAL_STRATEGY_GROUPS.append(strategy_group)
        
        print(f"成功加载 {len(GLOBAL_STRATEGY_GROUPS)} 个策略组")
        return True
        
    except Exception as e:
        print(f"加载插件配置时出错: {e}")
        return False

def clear_plugin_config() -> bool:
    """
    清空插件配置数据
    
    该函数用于重置插件的所有配置，包括配置文件中的持久化数据
    和内存中的运行时数据。通常用于插件重新配置或故障恢复。
    
    操作内容：
    - 从配置文件中移除插件的所有配置项
    - 清空内存中的全局策略组列表
    - 重置插件到初始状态
    
    Returns:
        bool: 清空成功返回True，失败返回False
        
    Note:
        该操作不可逆，执行后需要重新配置插件策略
    """
    try:
        # 从插件配置中清除配置
        config_data = __pluginConfig.save_config('manual_grouping',{})
        
        # 同时清空内存中的配置
        global GLOBAL_STRATEGY_GROUPS
        GLOBAL_STRATEGY_GROUPS = []
        
        return True
        
    except Exception as e:
        print(f"清空插件配置时出错: {e}")
        return False

def manual_grouping_init() -> None:
    """
    插件初始化函数 - 系统启动时自动调用
    
    该函数负责在插件模块加载时进行必要的初始化操作，
    主要包括从配置文件加载已保存的策略组配置。
    
    初始化流程：
    1. 尝试从config.yaml中的pluginConfig加载策略组配置
    2. 如果配置加载成功，将策略组加载到内存中
    3. 如果配置不存在或加载失败，使用默认空配置
    4. 输出初始化状态信息供调试使用
    
    错误处理：
    - 配置文件格式错误：使用默认配置继续运行
    - 策略解析失败：跳过有问题的策略，加载其他有效策略
    - 严重错误：输出错误信息但不影响插件加载
    
    Note:
        - 该函数在模块导入时自动执行，无需手动调用
        - 初始化失败不会阻止插件加载，确保系统稳定性
        - 配置变更后需要重新加载模块或重启程序
    """
    try:
        # 尝试从配置文件加载策略组
        if load_plugin_config():
            print("manual_grouping 插件配置已从文件加载")
        else:
            print("manual_grouping 插件使用默认配置")
            save_plugin_config()
            
    except Exception as e:
        print(f"manual_grouping 插件初始化时出错: {e}")

# 模块加载时自动初始化
manual_grouping_init()

# 插件变量声明 - 向文件分类器系统注册插件信息
addon_variables = [
    {
        "name": "manual_grouping",
        "description": "基于策略组的手动分组插件，支持包含字符串、通配符和正则表达式匹配",
        "method": manual_grouping,
        "gui": {
            "setting": show_strategy_config if GUI_AVAILABLE else None,
        }
    },
]
