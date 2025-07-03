#!/usr/bin/env python3
"""
带自动重启功能的Web UI启动脚本
"""

import os
import sys
import subprocess
import time
import webbrowser
import socket

# 全局变量存储端口号
detected_port = None

def parse_port_from_output(output_line):
    """从Flask输出中解析端口号"""
    import re
    # 匹配类似 "* Running on http://127.0.0.1:8000" 的输出
    match = re.search(r'Running on http://127\.0\.0\.1:(\d+)', output_line)
    if match:
        return int(match.group(1))
    
    # 匹配类似 "访问地址: http://127.0.0.1:8000" 的输出
    match = re.search(r'访问地址: http://127\.0\.0\.1:(\d+)', output_line)
    if match:
        return int(match.group(1))
    
    return None

def wait_for_server_and_open_browser(port=None):
    """等待服务器启动后打开浏览器"""
    max_attempts = 30  # 最多等待30秒
    attempts = 0
    
    def detect_port():
        """检测Flask服务器端口"""
        # 扫描8000-9999范围内的端口
        for test_port in range(8000, 10000):
            if is_port_in_use(test_port):
                return test_port
        return None
    
    def is_port_in_use(port):
        """检查端口是否被占用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)  # 设置超时避免阻塞
                result = s.connect_ex(('127.0.0.1', port))
                return result == 0
        except:
            return False
    
    print(f"[INFO] 等待Flask服务器启动...")
    
    while attempts < max_attempts:
        try:
            # 如果没有指定端口，尝试检测
            if port is None:
                port = detect_port()
            
            if port and is_port_in_use(port):
                url = f"http://127.0.0.1:{port}"
                print(f"[INFO] 服务器已启动在端口 {port}，正在打开浏览器: {url}")
                webbrowser.open(url)
                return True
        except Exception as e:
            print(f"[DEBUG] 检查服务器状态失败: {e}")
        
        attempts += 1
        time.sleep(1)
    
    print(f"[WARNING] 等待服务器启动超时，请手动访问 http://127.0.0.1:8000")
    return False

def main():
    """主函数：支持自动重启的启动器"""
    global detected_port
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_script = os.path.join(script_dir, 'app.py')
    
    if not os.path.exists(app_script):
        print("错误：找不到 app.py 文件")
        sys.exit(1)
    
    restart_count = 0
    max_restarts = 10  # 最大重启次数防止无限循环
    process = None
    
    while restart_count < max_restarts:
        try:
            print(f"\n{'='*50}")
            if restart_count == 0:
                print("启动文件分类器 Web UI...")
            else:
                print(f"重启文件分类器 Web UI (第 {restart_count} 次)...")
            print(f"{'='*50}")
            
            # 准备启动参数
            start_args = [sys.executable, app_script]
            
            # 如果已经检测到端口，在重启时传递端口参数
            if detected_port and restart_count > 0:
                start_args.extend(['--port', str(detected_port)])
                print(f"[INFO] 使用指定端口: {detected_port}")
            
            # 启动子进程
            process = subprocess.Popen(
                start_args,
                cwd=script_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            browser_opened = False  # 标记是否已经打开浏览器
            
            # 实时输出日志并检测端口
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    print(line.rstrip())
                    
                    # 首次启动时，从输出中解析端口号并打开浏览器
                    if restart_count == 0 and not browser_opened:
                        current_port = parse_port_from_output(line)
                        if current_port:
                            detected_port = current_port  # 保存端口号到全局变量
                            url = f"http://127.0.0.1:{detected_port}"
                            print(f"[INFO] 检测到服务器端口 {detected_port}，正在打开浏览器: {url}")
                            try:
                                webbrowser.open(url)
                                browser_opened = True
                            except Exception as e:
                                print(f"[WARNING] 打开浏览器失败: {e}")
            
            # 等待进程结束
            exit_code = process.wait()
            
            if exit_code == 0:
                print("\n[INFO] 服务器正常退出")
                break
            elif exit_code == 1:
                print("\n[INFO] 服务器请求重启")
                restart_count += 1
                
                if restart_count < max_restarts:
                    print(f"[INFO] 2秒后重启...")
                    time.sleep(2)
                else:
                    print(f"[ERROR] 已达到最大重启次数 ({max_restarts})，停止重启")
                    break
            else:
                print(f"\n[WARNING] 服务器异常退出，退出码: {exit_code}")
                restart_count += 1
                
                if restart_count < max_restarts:
                    print(f"[INFO] 2秒后重启...")
                    time.sleep(2)
                else:
                    print(f"[ERROR] 已达到最大重启次数 ({max_restarts})，停止重启")
                    break
        
        except KeyboardInterrupt:
            print("\n[INFO] 用户中断，退出...")
            if process:
                process.terminate()
            break
        except Exception as e:
            print(f"\n[ERROR] 启动失败: {e}")
            restart_count += 1
            if restart_count < max_restarts:
                time.sleep(2)
            else:
                break
    
    print("\n[INFO] 启动器退出")

if __name__ == '__main__':
    main()
