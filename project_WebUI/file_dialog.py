#!/usr/bin/env python3
"""
独立的文件对话框脚本
用于解决 macOS 上 Tkinter 必须在主线程运行的问题
"""
import sys
import tkinter as tk
from tkinter import filedialog
import json

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Missing argument"}))
        return
    
    dialog_type = sys.argv[1]
    
    # 创建隐藏的 root 窗口
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    try:
        if dialog_type == 'directory':
            selected_path = filedialog.askdirectory(
                title="选择目录",
                initialdir='~'
            )
            result = {"success": True, "path": selected_path} if selected_path else {"success": False, "error": "User cancelled"}
        elif dialog_type == 'file':
            selected_path = filedialog.askopenfilename(
                title="选择文件",
                initialdir='~'
            )
            result = {"success": True, "path": selected_path} if selected_path else {"success": False, "error": "User cancelled"}
        elif dialog_type == 'files':
            selected_paths = filedialog.askopenfilenames(
                title="选择文件（可多选）",
                initialdir='~'
            )
            result = {"success": True, "paths": list(selected_paths)} if selected_paths else {"success": False, "error": "User cancelled"}
        else:
            result = {"success": False, "error": "Invalid dialog type"}
        
        print(json.dumps(result))
            
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
    finally:
        root.destroy()

if __name__ == '__main__':
    main()
