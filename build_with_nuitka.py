#!/usr/bin/env python3
"""
Nuitka打包脚本 - 文件分类器项目

该脚本使用Nuitka将文件分类器的主程序部分编译为独立的可执行文件，
同时保留插件为Python源码(.py)格式，以支持热插拔功能。

特点：
1. 仅编译核心程序，保留插件为源码
2. 自动创建插件目录和配置文件
3. 支持多平台构建(Windows, macOS, Linux)
4. 生成完整的发布包，包含必要的运行环境
5. 支持多线程编译以加快构建速度
6. 支持链接时优化（LTO）以提升运行性能

使用方法：
    python build_with_nuitka.py [选项]

选项：
    --onefile       生成单文件可执行程序（默认为文件夹模式）
    --no-console    隐藏控制台窗口（仅适用于GUI模式）
    --jobs N        指定并行编译的线程数（默认使用所有CPU核心）
    --lto           启用链接时优化（LTO）以提高运行性能
    --fast          使用快速编译模式（减少优化以加快编译速度）

示例：
    # 基本构建
    python build_with_nuitka.py
    
    # 快速构建（开发测试用）
    python build_with_nuitka.py --fast
    
    # 高性能构建（发布用）
    python build_with_nuitka.py --lto
    
    # 单文件构建，使用4个线程
    python build_with_nuitka.py --onefile --jobs 4

Author: File Classifier Project
License: MIT
Version: 1.1.0
"""

import os
import sys
import shutil
import platform
import subprocess
import argparse
from pathlib import Path


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="使用Nuitka打包文件分类器")
    parser.add_argument("--onefile", action="store_true", help="生成单文件可执行程序")
    parser.add_argument("--no-console", action="store_true", help="隐藏控制台窗口")
    parser.add_argument("--jobs", type=int, default=None, help="并行编译的线程数（默认自动检测CPU核心数）")
    parser.add_argument("--lto", action="store_true", help="启用链接时优化（LTO）以提高性能")
    parser.add_argument("--fast", action="store_true", help="使用快速编译模式（减少优化以加快编译速度）")
    parser.add_argument("--output-dir", type=str, default="release", help="指定最终发布包的输出目录")
    return parser.parse_args()


def get_optimization_args(args):
    """获取性能优化相关的Nuitka参数"""
    opt_args = []
    
    # 并行编译设置
    if args.jobs is not None:
        opt_args.append(f"--jobs={args.jobs}")
    else:
        # 自动检测CPU核心数并使用所有核心
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        opt_args.append(f"--jobs={cpu_count}")
        print(f"检测到 {cpu_count} 个CPU核心，将使用全部核心进行并行编译")
    
    # 链接时优化
    if args.lto:
        opt_args.append("--lto=yes")
        print("启用链接时优化（LTO）")
    
    # 快速编译模式
    if args.fast:
        opt_args.extend([
            "--assume-yes-for-downloads",
            "--no-progress-bar"
        ])
        print("启用快速编译模式")
    else:
        # 标准优化模式
        opt_args.extend([
            "--enable-plugin=anti-bloat",
            "--show-progress"
        ])
    
    return opt_args


def get_platform_specific_args():
    """获取特定平台的Nuitka参数"""
    system = platform.system()
    project_dir = "project"  # 定义项目根目录
    if system == "Windows":
        # 检查图标文件是否存在
        icon_path = os.path.join(project_dir, "resources", "icon.ico")
        if os.path.exists(icon_path):
            return [f"--windows-icon-from-ico={icon_path}"]
        else:
            return []
    elif system == "Darwin":  # macOS
        # 检查图标文件是否存在
        icon_path = os.path.join(project_dir, "resources", "icon.icns")
        if os.path.exists(icon_path):
            return [f"--macos-create-app-bundle", f"--macos-app-icon={icon_path}"]
        else:
            return ["--macos-create-app-bundle"]
    else:  # Linux和其他系统
        return []

def ensure_plugins_dir(dist_dir):
    """确保创建插件目录"""
    plugins_dir = os.path.join(dist_dir, "plugins")
    os.makedirs(plugins_dir, exist_ok=True)
    return plugins_dir

def create_run_script(dist_dir):
    """创建启动脚本"""
    system = platform.system()
    
    if system == "Windows":
        # Windows批处理文件
        with open(os.path.join(dist_dir, "run.bat"), "w") as f:
            f.write("@echo off\r\n")
            f.write("start \"\" \"%~dp0main.exe\" %*\r\n")
    else:
        # Unix shell脚本
        script_path = os.path.join(dist_dir, "run.sh")
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\n")
            f.write('DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n')
            if system == "Darwin":  # macOS
                f.write('"$DIR/main.app/Contents/MacOS/main" "$@"\n')
            else:  # Linux
                f.write('"$DIR/main" "$@"\n')
        
        # 设置执行权限
        os.chmod(script_path, 0o755)


def create_readme(dist_dir):
    """创建说明文档"""
    with open(os.path.join(dist_dir, "README.txt"), "w") as f:
        f.write("文件分类器 - 使用说明\n")
        f.write("===================\n\n")
        f.write("1. 运行程序\n")
        if platform.system() == "Windows":
            f.write("   双击运行 run.bat 或直接运行 main.exe\n\n")
        elif platform.system() == "Darwin":  # macOS
            f.write("   双击运行 main.app 或使用 run.sh 脚本\n\n")
        else:  # Linux
            f.write("   执行 ./run.sh 或直接运行 ./main\n\n")
        
        f.write("2. 插件管理\n")
        f.write("   - 所有插件位于 plugins 目录中\n")
        f.write("   - 可以直接添加或删除插件文件来管理功能\n")
        f.write("   - 程序会在启动时自动加载所有可用插件\n\n")
        
        f.write("3. 配置文件\n")
        f.write("   - 首次运行时会自动创建 config.yaml 配置文件\n")
        f.write("   - 可以手动编辑该文件来调整系统设置\n\n")
        
        f.write("4. 注意事项\n")
        f.write("   - 请勿删除或修改程序目录中的其他文件\n")
        f.write("   - 如需重置配置，删除 config.yaml 文件后重启程序\n")


def build_with_nuitka(args):
    """使用Nuitka构建项目"""
    print("开始使用Nuitka构建文件分类器...")
    
    # 定义项目和构建目录
    project_dir = "project"
    build_dir = Path("build")
    
    # 清理旧的构建目录
    if build_dir.exists():
        print(f"清理旧的构建目录: {build_dir}")
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    # 构建基本命令
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        f"--output-dir={build_dir}",
        "--follow-imports",
        "--include-package=project.module",
        "--include-package=PySide6",
        "--include-package=exifread",  # 显式包含插件依赖
        "--include-package=rich",      # 显式包含插件依赖
        "--include-package=yaml",      # 显式包含插件依赖
        "--enable-plugin=pyside6",
    ]
    
    # 添加性能优化参数
    cmd.extend(get_optimization_args(args))
    
    # 添加平台特定参数
    cmd.extend(get_platform_specific_args())
    
    # 添加命令行参数
    if args.onefile:
        cmd.append("--onefile")
    
    if args.no_console:
        cmd.append("--windows-disable-console")
    
    # 添加主程序路径
    cmd.append(os.path.join(project_dir, "main.py"))
    
    # 显示构建信息
    print(f"构建模式: {'单文件' if args.onefile else '文件夹'}")
    if args.lto:
        print("优化: 启用LTO")
    if args.fast:
        print("编译模式: 快速模式")
    else:
        print("编译模式: 标准优化模式")
    
    # 执行Nuitka编译
    print("执行命令:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    
    # 确定Nuitka的实际输出目录
    if args.onefile:
        # 单文件模式下，可执行文件直接在 build_dir 中
        dist_dir = build_dir
    else:
        # 文件夹模式下，内容在 build/main.dist/
        dist_dir = build_dir / "main.dist"
    
    return str(dist_dir)


def create_release_package(dist_dir, release_base_dir):
    """创建完整的发布包"""
    # 使用Path对象处理路径
    dist_path = Path(dist_dir)
    release_base_path = Path(release_base_dir)
    release_base_path.mkdir(exist_ok=True)
    
    system = platform.system()
    arch = platform.machine()
    
    # 创建带版本号的发布目录名
    package_name = f"file_classifier_{system.lower()}_{arch}"
    release_path = release_base_path / package_name
    
    # 如果目录已存在，先删除
    if release_path.exists():
        shutil.rmtree(release_path)
    
    # 直接将构建产物目录重命名/移动为最终的发布包
    print(f"正在将 {dist_path} 移动到 {release_path}")
    shutil.move(str(dist_path), str(release_path))
    
    print(f"已创建发布包: {release_path}")
    return str(release_path)


def main():
    """主函数"""
    args = parse_arguments()
    
    # 定义编译后的插件源目录
    compiled_plugins_src_dir = "build/plugins"

    try:
        # 构建主程序
        dist_dir = build_with_nuitka(args)
        print(f"主程序构建完成: {dist_dir}")
        
        # 创建启动脚本和文档
        create_run_script(dist_dir)
        create_readme(dist_dir)
        
        # 创建发布包
        release_path = create_release_package(dist_dir, args.output_dir)
        
        print("\n构建成功!")
        print(f"发布包路径: {release_path}")
        print("使用方法:")
        if platform.system() == "Windows":
            print("  - 进入发布包目录，双击 run.bat")
        else:
            print("  - 进入发布包目录，执行 ./run.sh")

    except subprocess.CalledProcessError as e:
        print(f"\n构建失败: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n发生未知错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
