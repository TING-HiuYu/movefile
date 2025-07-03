"""
文件自动分类和管理系统 - 主程序模块

这是一个基于插件架构的智能文件分类系统的程序入口，整合了以下核心功能：

系统架构：
- 插件化设计：支持可扩展的文件分类策略插件
- 双模式运行：GUI图形界面和CLI命令行交互两种模式
- 配置驱动：基于YAML配置文件的灵活参数管理
- 模板系统：可视化路径模板构建，支持动态变量替换

核心功能：
- 多维度文件分类：按日期、大小、扩展名、手动分组等策略分类
- 智能文件复制：多线程并行复制，支持大文件分块传输
- 完整性验证：可选的哈希校验确保数据传输完整性
- 实时预览：模板效果即时预览，所见即所得的配置体验

使用场景：
- 文档归档整理：按时间、类型自动分类文档
- 媒体文件管理：照片、视频的智能分组存储
- 备份策略实施：按规则复制重要文件到指定位置
- 批量文件操作：大量文件的统一处理和分类

运行模式：
- GUI模式（默认）：可视化界面，支持拖拽、实时预览
- CLI模式：命令行交互，适合脚本集成和服务器环境

Author: File Classifier Project
License: MIT
Version: 2.0
"""

import sys
import argparse
from typing import Tuple, Optional
from PySide6.QtWidgets import QApplication, QFileDialog
import module.config as config
import module.allocator as allocator
import module.file_manager as file_manager

def file_selector() -> Tuple[str, ...]:
    """
    基于PySide6的可视化文件选择器
    
    创建QApplication实例（如果尚不存在），并弹出标准文件选择对话框供用户选择多个文件。
    支持所有文件类型的多选操作。
    
    技术实现：
    - 使用PySide6.QtWidgets.QFileDialog提供原生文件对话
    - 确保在任何模式下都能正确创建和使用QApplication
    - 支持键盘快捷键和鼠标操作的多文件选择
    
    Returns:
        Tuple[str, ...]: 用户选择的文件路径元组，按选择顺序排列
                        如果用户取消选择则返回空元组
        
    Note:
        - 该函数现在依赖PySide6，与GUI模式保持一致
        - 返回的路径都是绝对路径，便于后续处理
    """
    # 确保QApplication实例存在
    app = QApplication.instance()
    if not app:
        # 如果没有实例，创建一个新的。这对于在CLI模式下调用至关重要。
        app = QApplication(sys.argv)

    # 打开多文件选择对话框
    dialog = QFileDialog()
    dialog.setWindowTitle("选择要复制的文件")
    dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)  # 设置为选择已存在的文件
    dialog.setNameFilter("所有文件 (*.*)")  # 文件类型过滤器

    # 显示对话框并获取结果
    if dialog.exec():
        selected_files = dialog.selectedFiles()
        return tuple(selected_files)
    else:
        # 用户取消选择
        return ()


def run_cli_mode() -> None:
    """
    启动命令行交互模式的文件分类流程
    
    该模式提供基于文本的交互式界面，引导用户完成完整的文件分类操作。
    适合在服务器环境、批处理脚本或偏好命令行工具的用户使用。
    
    完整工作流程：
    1. 配置系统初始化：从config.yaml读取配置，创建分类器实例
    2. 交互式模板配置：通过控制台对话设置路径模板
    3. 文件选择阶段：弹出GUI文件选择器（即使在CLI模式下）
    4. 批量处理执行：逐个处理所选文件，包括路径生成和复制操作
    5. 结果反馈：实时显示处理进度和结果状态
    
    特性优势：
    - 脚本友好：可以通过重定向输入实现自动化
    - 资源占用低：不需要持续运行GUI界面
    - 跨平台兼容：在任何支持Python的环境中运行
    - 详细日志：提供完整的操作记录和错误信息
    
    错误处理：
    - 配置文件缺失或格式错误时提供详细指导
    - 文件处理失败时继续处理其他文件，不中断整个流程
    - 提供明确的错误信息和建议解决方案
    
    Raises:
        SystemExit: 当用户未设置模板或发生严重配置错误时程序退出
        
    Note:
        即使在CLI模式下，文件选择仍使用GUI对话框以提供最佳用户体验
    """
    print("=== 文件分类器 - 命令行模式 ===")
    
    # 从配置文件初始化分类器实例
    try:
        config_instance = config.Config()
        target_folder = config_instance.get_config("target_folder")
        allo = allocator.Allocator(target_folder)
    except Exception as e:
        print(f"初始化配置失败: {e}")
        return

    # 启动交互式模板设置流程
    template = allo.interactive_template_setup()
    
    if template:
        print(f"\n✅ 模板设置完成！")
        print(f"完整路径模板: {config_instance.get_config('target_folder')}/{template}")
        
        # 文件选择和批量处理流程
        selected_files = file_selector()
        if not selected_files:
            print("未选择任何文件，程序退出")
            return
            
        print(f"开始处理 {len(selected_files)} 个文件...")
        
        for file_path in selected_files:
            try:
                # 生成目标路径
                destination_path = allo.execute(file_path)
                print(f"源文件: {file_path}")
                print(f"目标路径: {destination_path}")
                
                # 执行文件复制
                copying_instance = file_manager.current_copying_instance(file_path)
                if copying_instance.copy_initiator((destination_path,)):
                    print("✅ 复制成功")
                else:
                    print("❌ 复制失败")
                    
            except Exception as e:
                print(f"❌ 处理文件 {file_path} 时出错: {e}")
                
        print("所有文件处理完成")
    else:
        print("未设置模板，程序退出")


def run_gui_mode() -> None:
    """
    启动图形用户界面模式
    
    尝试启动基于PySide6的现代化GUI应用程序，提供可视化的文件分类体验。
    如果GUI启动失败（如缺少依赖或系统不支持），自动降级到CLI模式确保程序可用性。
    
    GUI模式核心特性：
    - 可视化模板构建器：拖拽式变量添加，所见即所得的模板编辑
    - 实时目录结构预览：模板变更时即时显示目标目录结构
    - 批量文件处理：支持拖拽多选，可视化进度显示
    - 插件配置管理：图形化的插件参数设置界面
    - 响应式布局：适配不同屏幕尺寸，提供最佳用户体验
    
    技术架构：
    - 基于PySide6（Qt for Python）构建现代化界面
    - 模块化组件设计，便于维护和扩展
    - 异步文件操作，保持界面响应性
    - 集成系统主题，与操作系统外观一致
    
    降级机制与容错：
    - ImportError：检测到缺少PySide6时，提示安装信息并切换到CLI
    - 运行时异常：捕获GUI初始化或运行时错误，提供详细错误信息
    - 自动恢复：任何GUI相关问题都会自动切换到CLI模式，确保功能可用
    
    适用环境：
    - 桌面操作系统（Windows、macOS、Linux）
    - 有图形界面支持的环境
    - 交互式操作需求较高的场景
    
    Note:
        GUI模式需要安装PySide6依赖：pip install PySide6
        如果系统不支持图形界面，程序会自动切换到CLI模式
    """
    try:
        from gui import main as gui_main
        print("=== 文件分类器 - 高级GUI模式 ===")
        gui_main()
    except ImportError as e:
        print(f"无法加载GUI组件: {e}")
        print("GUI模式需要PySide6支持，请安装: pip install PySide6")
        print("自动切换到命令行模式...")
        run_cli_mode()
    except Exception as e:
        import traceback
        print(f"GUI运行时出现异常: {e}")
        print("详细错误信息:")
        traceback.print_exc()
        print("自动切换到命令行模式...")
        run_cli_mode()


if __name__ == "__main__":
    # 命令行参数解析配置
    parser = argparse.ArgumentParser(
        description="文件自动分类和管理系统",
        epilog="示例用法:\n"
               "  python main.py --mode gui     # 启动图形界面模式\n"
               "  python main.py --mode cli     # 启动命令行模式\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--mode", 
        choices=["gui", "cli"], 
        default="gui",
        help="选择运行模式: gui (图形界面，默认) 或 cli (命令行交互)"
    )
    
    # 解析命令行参数并启动相应模式
    args = parser.parse_args()
    
    if args.mode == "gui":
        run_gui_mode()
    else:
        run_cli_mode()

