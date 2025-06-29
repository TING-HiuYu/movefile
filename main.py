"""
文件自动分类和管理系统

这是一个基于插件架构的文件分类系统，支持：
- 多种文件分类策略（日期、大小、手动分组等）
- 灵活的路径模板配置
- 自动文件复制和完整性验证
- 可扩展的插件系统
"""

import select
import module.config as config
import module.allocator as allocator
import module.file_manager as file_manager
import tkinter as tk
import os
from tkinter import filedialog


def file_selector() -> tuple[str, ...]:
    """
    基于配置选择要复制的文件
    
    Returns:
        所选文件的路径元组
    """
    # 创建根窗口（但隐藏它）
    root = tk.Tk()
    root.withdraw()

    # 打开文件对话框选择多个文件
    selected_files = filedialog.askopenfilenames(
        title="选择要复制的文件",
        filetypes=[("所有文件", "*.*")]
    )
    
    # 如果用户取消对话框，返回空元组
    if not selected_files:
        return ()
    
    return selected_files


if __name__ == "__main__":
    # 初始化文件分类器
    # 传入目标文件夹，基础变量将自动注册
    allo = allocator.Allocator(config.Config().get_config("target_folder"))

    # 交互式设置路径模板
    # 用户只需输入target_folder后的路径部分
    template = allo.interactive_template_setup()
    
    if template:
        print(f"\n✅ 模板设置完成！")
        print(f"完整路径模板: {config.Config().get_config('target_folder')}/{template}")
        
        # 文件选择和处理
        for file in file_selector():
            destination_path = allo.execute(file)
            print(f"源文件: {file}")
            print(f"目标路径: {destination_path}")
            copying = file_manager.current_copying_instance(file)
            copying.copy_initiator((destination_path,))
    else:
        print("未设置模板，程序退出。")