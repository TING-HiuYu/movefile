"""
极简 Flask Web UI 服务器
打包后体积约 10MB
"""
from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import sys
import webbrowser
import threading
import time
import socket
import random
import signal

from module.config import Config as ConfigManager
from module.file_manager import current_copying_instance
from module.allocator import Allocator

app = Flask(__name__)

# 全局变量存储配置和管理器
config_manager = None
allocator = None
current_port = None  # 存储当前使用的端口



def is_port_available(port):
    """检查端口是否可用"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('127.0.0.1', port))
        sock.listen(1)
        sock.close()
        return True
    except (socket.error, OSError):
        return False

def find_available_port(start_port=8000, end_port=10000):
    """在指定范围内寻找可用端口"""
    # 如果常用端口都不可用，随机选择
    ports = list(range(start_port, end_port + 1))
    random.shuffle(ports)
    
    for port in ports:
        if is_port_available(port):
            return port
    
    # 如果都不可用，返回None
    return None

def format_paths_as_tree(paths):
    """将路径列表格式化为树形结构显示（无emoji，变量用[]包裹）"""
    if not paths:
        return ''
    
    # 构建树形结构
    tree_lines = []
    for i, path in enumerate(paths[:3]):  # 最多显示3个预览
        parts = path.split('/')
        current_path = ''
        
        # 为每一级目录添加缩进和显示
        for j, part in enumerate(parts):
            indent = '  ' * j  # 使用2个空格缩进
            
            # 检测并高亮变量（用[]包裹）
            display_part = part
            # 查找模板变量模式并替换为[]格式
            import re
            variable_pattern = r'\{([^}]+)\}'
            display_part = re.sub(variable_pattern, r'[\1]', display_part)
            
            if j == len(parts) - 1:  # 最后一级（文件）
                if '.' in part:  # 有扩展名，是文件
                    current_path += f"{indent}|- {display_part}"
                else:  # 无扩展名，可能是目录
                    current_path += f"{indent}|- {display_part}/"
            else:  # 中间级别（目录）
                if j == 0:  # 根目录
                    current_path += f"{display_part}/\n"
                else:
                    current_path += f"{indent}|- {display_part}/\n"
        
        tree_lines.append(current_path)
    
    return '\n'.join(tree_lines)

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    """获取当前配置"""
    global config_manager
    try:
        if not config_manager:
            config_manager = ConfigManager()
        
        # 获取主要配置项
        config = {
            'target_folder': config_manager.get_config('target_folder', '/tmp/output'),
            'hash_check_enable': config_manager.get_config('hash_check_enable', 'sha256'),
            'pathTemplate': config_manager.get_config('pathTemplate', ''),
            'external_plugins_dir': config_manager.get_config('external_plugins_dir', '')
        }
        
        print("111", config, "111")
        
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/config', methods=['POST'])
def update_config():
    """更新配置"""
    global config_manager
    try:
        data = request.get_json()
        if not config_manager:
            config_manager = ConfigManager()
        
        # 检查是否是首次配置
        is_initial_setup = data.get('is_initial_setup', False)
        
        # 更新各个配置项
        if 'target_folder' in data:
            config_manager.set_config('target_folder', data['target_folder'])
        if 'hash_check_enable' in data:
            config_manager.set_config('hash_check_enable', data['hash_check_enable'])
        if 'external_plugins_dir' in data:
            config_manager.set_config('external_plugins_dir', data['external_plugins_dir'])
        if 'pathTemplate' in data:
            template = data['pathTemplate']
            
            # 后端兜底：确保模板以文件名变量结尾
            file_variables = ['filename', 'basename']
            ends_with_file_variable = any(template.endswith(f'{{{var}}}') for var in file_variables)
            
            if not ends_with_file_variable and template.strip():
                # 如果模板不为空且不以文件变量结尾，自动添加 /{filename}
                if not template.endswith('/'):
                    template += '/'
                template += '{filename}'
            
            config_manager.set_config('pathTemplate', template)
        
        response_data = {
            'success': True,
            'message': '配置更新成功'
        }
        
        # 如果是首次配置，标记需要重启
        if is_initial_setup:
            response_data['requires_restart'] = True
            response_data['message'] = '配置保存成功，服务器将重启以加载新配置'
        
        return jsonify(response_data)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/restart-server', methods=['POST'])
def restart_server():
    """重启服务器"""
    try:
        data = request.get_json() or {}
        delay = data.get('delay', 0.5)  # 默认2秒后重启
        
        def delayed_restart():
            time.sleep(delay)
            print("\n[INFO] 重启服务器...")
            # 使用退出码1来指示启动器需要重启
            os._exit(1)
        
        # 在后台线程中执行重启
        threading.Thread(target=delayed_restart, daemon=True).start()
        
        return jsonify({
            'success': True,
            'message': f'服务器将在 {delay} 秒后重启'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scan', methods=['POST'])
def scan_directory():
    """扫描目录"""
    try:
        data = request.get_json()
        directory = data.get('directory', '')
        recursive = data.get('recursive', True)
        
        if not os.path.exists(directory):
            return jsonify({
                'success': False,
                'error': '目录不存在'
            }), 400
        
        # 扫描目录中的文件
        files = []
        if recursive:
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    if os.path.isfile(file_path):
                        files.append({
                            'path': file_path,
                            'name': filename,
                            'size': os.path.getsize(file_path)
                        })
        else:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path):
                    files.append({
                        'path': item_path,
                        'name': item,
                        'size': os.path.getsize(item_path)
                    })
        
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/allocate', methods=['POST'])
def allocate_files():
    """分配文件"""
    global allocator, config_manager
    try:
        data = request.get_json()
        files = data.get('files', [])
        
        if not config_manager:
            config_manager = ConfigManager()
        
        target_folder = config_manager.get_config('target_folder', '/tmp/output')
        template = config_manager.get_path_template()
        
        if not allocator:
            allocator = Allocator(target_folder)
        
        # 更新模板
        allocator.update_template(template)
        
        # 批量分析文件并生成目标路径
        allocated_files = []
        for file_info in files:
            file_path = file_info.get('path') if isinstance(file_info, dict) else str(file_info)
            if not file_path:
                continue
                
            try:
                target_path = allocator.execute(file_path)
                allocated_files.append({
                    'source': file_path,
                    'target': target_path,
                    'success': True
                })
            except Exception as e:
                allocated_files.append({
                    'source': file_path,
                    'target': None,
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'allocated_files': allocated_files
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/execute', methods=['POST'])
def execute_move():
    """执行文件移动"""
    try:
        data = request.get_json()
        allocation = data.get('allocation', [])
        
        results = []
        for item in allocation:
            source = item.get('source')
            target = item.get('target')
            
            if not source or not target:
                results.append({
                    'source': source,
                    'target': target,
                    'success': False,
                    'error': 'Missing source or target path'
                })
                continue
            
            try:
                # 使用文件管理器复制文件
                file_copier = current_copying_instance(source)
                
                # 确保目标目录存在
                target_dir = os.path.dirname(target)
                os.makedirs(target_dir, exist_ok=True)
                
                # 复制文件
                success = file_copier.copy_initiator((target,))
                
                results.append({
                    'source': source,
                    'target': target,
                    'success': success
                })
                
                # 释放资源
                file_copier.release()
                
            except Exception as e:
                results.append({
                    'source': source,
                    'target': target,
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'result': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/move', methods=['POST'])
def move_files():
    """执行文件移动"""
    try:
        data = request.get_json()
        files = data.get('files', [])
        enable_hash = data.get('enable_hash', True)
        
        results = []
        for file_info in files:
            source = file_info.get('source')
            target = file_info.get('target')
            
            if not source or not target or not file_info.get('success'):
                results.append({
                    'source': source,
                    'target': target,
                    'success': False,
                    'error': 'Invalid file allocation'
                })
                continue
            
            try:
                # 确保目标目录存在
                target_dir = os.path.dirname(target)
                os.makedirs(target_dir, exist_ok=True)
                
                # 使用文件管理器复制文件
                file_copier = current_copying_instance(source)
                
                # 复制文件
                success = file_copier.copy_initiator((target,))
                
                results.append({
                    'source': source,
                    'target': target,
                    'success': success
                })
                
                # 释放资源
                file_copier.release()
                
            except Exception as e:
                results.append({
                    'source': source,
                    'target': target,
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/variables', methods=['GET'])
def get_variables():
    """获取可用的插件变量"""
    global allocator
    try:
        if not allocator:
            # 创建一个临时的allocator来获取变量信息
            allocator = Allocator('/tmp/temp')
        
        variables = allocator.show_available_variables()
        
        # 清理变量信息，移除不能序列化的GUI函数
        cleaned_variables = []
        for variable_info in variables:
            cleaned_info = {
                'plugin_name': variable_info.get('plugin_name', ''),
                'description': variable_info.get('description', ''),
                'variables': variable_info.get('variables', [])
            }
            
            # 检查是否有 webui 配置
            gui_info = variable_info.get('gui', {})
            if gui_info and 'webui' in gui_info:
                webui_config = gui_info['webui']
                if webui_config.get('enabled', False):
                    cleaned_info['webui'] = {
                        'enabled': True,
                        'path': webui_config.get('path', ''),
                        'title': webui_config.get('title', ''),
                        'width': webui_config.get('width', 800),
                        'height': webui_config.get('height', 600)
                    }
            
            # 移除 GUI 函数对象，只保留基本信息
            cleaned_variables.append(cleaned_info)
        
        return jsonify({
            'success': True,
            'variables': cleaned_variables
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/init-check', methods=['GET'])
def check_init():
    """检查是否需要初始化配置"""
    global config_manager
    try:
        if not config_manager:
            config_manager = ConfigManager()
        
        # 检查关键配置是否存在
        target_folder = config_manager.get_config('target_folder')
        has_valid_config = (
            target_folder and 
            target_folder != '/tmp/output' and 
            os.path.exists(target_folder)
        )
        
        return jsonify({
            'success': True,
            'needs_init': not has_valid_config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'needs_init': True
        })

@app.route('/api/browse', methods=['POST'])
def browse_directory():
    """浏览目录内容"""
    try:
        data = request.get_json()
        path = data.get('path', '/')
        
        # 确保路径存在
        if not os.path.exists(path):
            # 如果路径不存在，返回根目录
            path = '/'
        
        # 如果不是目录，返回其父目录
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        
        contents = []
        try:
            # 获取目录内容
            items = os.listdir(path)
            items.sort()
            
            for item in items:
                item_path = os.path.join(path, item)
                
                # 跳过隐藏文件和无权限文件
                if item.startswith('.'):
                    continue
                
                try:
                    if os.path.isdir(item_path):
                        contents.append({
                            'name': item,
                            'path': item_path,
                            'type': 'directory'
                        })
                    else:
                        contents.append({
                            'name': item,
                            'path': item_path,
                            'type': 'file'
                        })
                except (OSError, PermissionError):
                    # 跳过无权限访问的文件/目录
                    continue
        except (OSError, PermissionError):
            # 无权限访问该目录，返回空内容
            contents = []
        
        return jsonify({
            'success': True,
            'path': path,
            'contents': contents
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/template-preview', methods=['POST'])
def template_preview():
    """生成模板预览"""
    template = ''  # 初始化变量
    try:
        data = request.get_json()
        template = data.get('template', '')
        
        if not template:
            return jsonify({
                'success': True,
                'preview': '',
                'template': template
            })
        
        # 创建一个专门用于预览的allocator，使用空目录作为基础
        preview_allocator = Allocator('')  # 空基础目录
        preview_allocator.update_template(template)
        
        # 使用示例文件生成预览
        sample_files = ['example.pdf', 'document.doc', 'image.jpg']
        preview_paths = []
        
        for sample_file in sample_files:
            try:
                # 直接使用文件名，不需要完整路径
                target_path = preview_allocator.execute(sample_file)
                # 保留完整的路径（包括文件名）
                if target_path and target_path not in preview_paths:
                    # 清理路径，移除不必要的前缀
                    clean_path = target_path.replace('//', '/')  # 秘除双斜杠
                    if clean_path.startswith('/'):
                        clean_path = clean_path[1:]  # 秘除开头的斜杠
                    if clean_path and clean_path not in preview_paths:
                        preview_paths.append(clean_path)
                        
            except Exception as e:
                # 如果某个示例文件失败，忽略它，继续尝试其他文件
                continue
        
        # 如果没有成功的预览路径，使用简单的字符串替换
        if not preview_paths:
            # 手动进行基本的变量替换，但保留模板变量格式用于显示
            basic_preview = template
            # 不进行实际替换，直接显示模板结构
            
            # 清理路径
            if basic_preview.startswith('/'):
                basic_preview = basic_preview[1:]
            preview_paths = [basic_preview] if basic_preview != template else ['示例路径/[filename]']
        
        # 将路径转换为树形结构显示
        tree_preview = format_paths_as_tree(preview_paths)
        
        return jsonify({
            'success': True,
            'preview': tree_preview,
            'template': template
        })
    except Exception as e:
        # 即使预览失败，也要返回成功，提供基本的模板显示
        return jsonify({
            'success': True,
            'preview': template or '预览失败',
            'template': template or ''
        })

@app.route('/api/browse-system', methods=['POST'])
def browse_system():
    """调用系统文件浏览器"""
    try:
        data = request.get_json()
        browse_type = data.get('type', 'directory')
        
        # 使用独立的文件对话框脚本
        import subprocess
        import json
        
        script_path = os.path.join(os.path.dirname(__file__), 'file_dialog.py')
        
        try:
            # 运行独立的文件对话框脚本
            result = subprocess.run(
                [sys.executable, script_path, browse_type],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                try:
                    response_data = json.loads(result.stdout.strip())
                    return jsonify(response_data)
                except json.JSONDecodeError:
                    return jsonify({
                        'success': False,
                        'error': '解析响应失败'
                    }), 500
            else:
                return jsonify({
                    'success': False,
                    'error': f'文件对话框失败: {result.stderr}'
                }), 500
                
        except subprocess.TimeoutExpired:
            return jsonify({
                'success': False,
                'error': '文件对话框超时'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/process-files', methods=['POST'])
def process_files():
    """处理文件并提供实时进度"""
    try:
        data = request.get_json()
        files = data.get('files', [])
        enable_hash = data.get('enable_hash', True)
        
        if not files:
            return jsonify({
                'success': False,
                'error': '没有文件需要处理'
            }), 400
        
        # 先分配所有文件
        global allocator, config_manager
        
        if not config_manager:
            config_manager = ConfigManager()
        
        target_folder = config_manager.get_config('target_folder', '/tmp/output')
        template = config_manager.get_path_template()
        
        if not allocator:
            allocator = Allocator(target_folder)
        
        # 更新模板和目标目录
        allocator.update_template(template)
        
        # 批量分析文件并生成目标路径
        allocated_files = []
        for file_info in files:
            file_path = file_info.get('path') if isinstance(file_info, dict) else str(file_info)
            if not file_path:
                continue
                
            try:
                target_path = allocator.execute(file_path)
                allocated_files.append({
                    'source': file_path,
                    'target': target_path,
                    'success': True
                })
            except Exception as e:
                allocated_files.append({
                    'source': file_path,
                    'target': None,
                    'success': False,
                    'error': str(e)
                })
        
        # 生成处理任务ID
        import uuid
        task_id = str(uuid.uuid4())
        
        # 存储任务状态
        task_status = {
            'task_id': task_id,
            'total_files': len(allocated_files),
            'completed_files': 0,
            'failed_files': 0,
            'current_files': [],
            'results': [],
            'status': 'processing'
        }
        
        # 简化版本：直接处理所有文件
        for i, file_info in enumerate(allocated_files):
            if not file_info.get('success'):
                task_status['failed_files'] += 1
                task_status['results'].append({
                    'source': file_info.get('source'),
                    'target': file_info.get('target'),
                    'success': False,
                    'error': file_info.get('error', 'Allocation failed')
                })
                continue
            
            source = file_info.get('source')
            target = file_info.get('target')
            
            try:
                # 确保目标目录存在
                target_dir = os.path.dirname(target)
                os.makedirs(target_dir, exist_ok=True)
                
                # 使用文件管理器复制文件
                file_copier = current_copying_instance(source)
                success = file_copier.copy_initiator((target,))
                
                task_status['results'].append({
                    'source': source,
                    'target': target,
                    'success': success,
                    'progress': 100
                })
                
                if success:
                    task_status['completed_files'] += 1
                else:
                    task_status['failed_files'] += 1
                
                # 释放资源
                file_copier.release()
                
            except Exception as e:
                task_status['failed_files'] += 1
                task_status['results'].append({
                    'source': source,
                    'target': target,
                    'success': False,
                    'error': str(e),
                    'progress': 0
                })
        
        task_status['status'] = 'completed'
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'results': task_status['results'],
            'total_files': task_status['total_files'],
            'completed_files': task_status['completed_files'],
            'failed_files': task_status['failed_files']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/hash-algorithms', methods=['GET'])
def get_hash_algorithms():
    """获取系统支持的哈希算法"""
    try:
        import hashlib
        
        # 获取所有可用的哈希算法
        all_algorithms = sorted(hashlib.algorithms_available)
        
        # 定义常用算法的显示顺序和友好名称
        common_algorithms = [
            {'value': '', 'name': '禁用校验', 'description': '不进行文件完整性校验'},
            {'value': 'md5', 'name': 'MD5', 'description': '快速但安全性较低'},
            {'value': 'sha1', 'name': 'SHA1', 'description': '较快，安全性一般'},
            {'value': 'sha224', 'name': 'SHA224', 'description': 'SHA-2系列，安全性好'},
            {'value': 'sha256', 'name': 'SHA256', 'description': 'SHA-2系列，推荐使用'},
            {'value': 'sha384', 'name': 'SHA384', 'description': 'SHA-2系列，高安全性'},
            {'value': 'sha512', 'name': 'SHA512', 'description': 'SHA-2系列，最高安全性'},
            {'value': 'sha3_256', 'name': 'SHA3-256', 'description': 'SHA-3系列，现代算法'},
            {'value': 'sha3_512', 'name': 'SHA3-512', 'description': 'SHA-3系列，最高安全性'},
            {'value': 'blake2b', 'name': 'BLAKE2b', 'description': '快速且安全的现代算法'},
            {'value': 'blake2s', 'name': 'BLAKE2s', 'description': '快速且安全的现代算法'},
        ]
        
        # 过滤出系统实际支持的算法
        supported_algorithms = []
        for algo in common_algorithms:
            if algo['value'] == '' or algo['value'] in all_algorithms:
                supported_algorithms.append(algo)
        
        # 添加其他系统支持但不在常用列表中的算法
        for algo_name in all_algorithms:
            if not any(a['value'] == algo_name for a in supported_algorithms):
                # 跳过一些不太实用的算法
                if algo_name in ['md5-sha1', 'shake_128', 'shake_256']:
                    continue
                supported_algorithms.append({
                    'value': algo_name,
                    'name': algo_name.upper(),
                    'description': f'{algo_name.upper()} 算法'
                })
        
        return jsonify({
            'success': True,
            'algorithms': supported_algorithms,
            'default': 'sha256'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/hash-algorithms/current', methods=['GET'])
def get_current_hash_algorithm():
    """获取当前配置的哈希算法"""
    try:
        global config_manager
        if not config_manager:
            config_manager = ConfigManager()
        
        current_algorithm = config_manager.get_config('hash_check_enable', 'sha256')
        
        return jsonify({
            'success': True,
            'current_algorithm': current_algorithm,
            'enabled': bool(current_algorithm and current_algorithm.strip())
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/hash-algorithms/current', methods=['POST'])
def update_current_hash_algorithm():
    """更新当前的哈希算法配置"""
    try:
        global config_manager
        if not config_manager:
            config_manager = ConfigManager()
        
        data = request.get_json()
        algorithm = data.get('algorithm', '')
        
        # 更新配置
        config_manager.set_config('hash_check_enable', algorithm)
        
        return jsonify({
            'success': True,
            'message': '完整性校验算法已更新',
            'current_algorithm': algorithm,
            'enabled': bool(algorithm and algorithm.strip())
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 动态插件配置API
@app.route('/api/plugin/<plugin_name>/config', methods=['GET', 'POST'])
def plugin_config(plugin_name):
    """动态插件配置 API"""
    global allocator
    try:
        if not allocator:
            allocator = Allocator('/tmp/temp')
        
        # 查找插件
        plugin_info = None
        for name, info in allocator.loaded_plugins.items():
            if name == plugin_name:
                plugin_info = info
                break
        
        if not plugin_info:
            return jsonify({
                'success': False,
                'error': f'插件 {plugin_name} 未找到'
            }), 404
        
        plugin_module = plugin_info['module']
        
        if request.method == 'GET':
            # 获取插件配置 - 调用插件的get_config API
            if hasattr(plugin_module, 'get_config'):
                try:
                    config = plugin_module.get_config()
                    return jsonify({
                        'success': True,
                        'config': config
                    })
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'error': f'获取插件配置失败: {str(e)}'
                    }), 500
            else:
                return jsonify({
                    'success': False,
                    'error': f'插件 {plugin_name} 不支持配置获取'
                }), 404
        
        elif request.method == 'POST':
            # 保存插件配置 - 调用插件的set_config API
            data = request.get_json()
            config = data.get('config', {})
            
            if hasattr(plugin_module, 'set_config'):
                try:
                    result = plugin_module.set_config(config)
                    if isinstance(result, dict) and 'success' in result:
                        return jsonify(result)
                    else:
                        return jsonify({
                            'success': True,
                            'message': '配置保存成功',
                            'result': result
                        })
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'error': f'保存插件配置失败: {str(e)}'
                    }), 500
            else:
                return jsonify({
                    'success': False,
                    'error': f'插件 {plugin_name} 不支持配置保存'
                }), 404
                
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/plugin/<plugin_name>/test', methods=['POST'])
def plugin_test(plugin_name):
    """动态插件测试 API"""
    try:
        global allocator
        if not allocator:
            allocator = Allocator('/tmp/temp')
        
        # 查找插件
        plugin_info = None
        for name, info in allocator.loaded_plugins.items():
            if name == plugin_name:
                plugin_info = info
                break
        
        if not plugin_info:
            return jsonify({
                'success': False,
                'error': f'插件 {plugin_name} 未找到'
            }), 404
        
        plugin_module = plugin_info['module']
        data = request.get_json()
        
        # 调用插件的test API
        if hasattr(plugin_module, 'test'):
            try:
                result = plugin_module.test(data)
                if isinstance(result, dict) and 'success' in result:
                    return jsonify(result)
                else:
                    return jsonify({
                        'success': True,
                        'results': result
                    })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'插件测试失败: {str(e)}'
                }), 500
        elif hasattr(plugin_module, 'test_file_matching'):
            # 兼容旧版API
            filename = data.get('filename', '')
            if not filename:
                return jsonify({
                    'success': False,
                    'error': '缺少 filename 参数'
                }), 400
            
            result = plugin_module.test_file_matching(filename)
            return jsonify(result)
        else:
            return jsonify({
                'success': False,
                'error': f'插件 {plugin_name} 不支持测试功能'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/plugin/<plugin_name>/<path:filename>')
def serve_plugin_file(plugin_name, filename):
    """提供插件静态文件服务"""
    # 新架构：插件文件夹/webui/文件
    plugin_webui_path = os.path.join(os.path.dirname(__file__), 'module', 'plugins', plugin_name, 'webui')
    if os.path.exists(plugin_webui_path):
        return send_from_directory(plugin_webui_path, filename)
    
    # 向后兼容：旧的 plugin_name_webui 文件夹
    old_plugin_webui_path = os.path.join(os.path.dirname(__file__), 'module', 'plugins', f'{plugin_name}_webui')
    if os.path.exists(old_plugin_webui_path):
        return send_from_directory(old_plugin_webui_path, filename)
    
    return "Plugin webui not found", 404

@app.route('/api/plugin/<plugin_name>/<api_name>', methods=['GET', 'POST'])
def plugin_api(plugin_name, api_name):
    """插件 API 接口"""
    try:
        print(f"[DEBUG] 插件API调用: {plugin_name}.{api_name}")
        global allocator
        if not allocator:
            allocator = Allocator('/tmp/temp')
        
        # 查找插件
        plugin_info = None
        for name, info in allocator.loaded_plugins.items():
            if name == plugin_name:
                plugin_info = info
                break
        
        if not plugin_info:
            print(f"[ERROR] 插件 {plugin_name} 未找到")
            return jsonify({
                'success': False,
                'error': f'插件 {plugin_name} 未找到'
            }), 404
        
        plugin_module = plugin_info['module']
        print(f"[DEBUG] 找到插件模块: {plugin_module}")
        
        # 获取请求数据
        if request.method == 'POST':
            data = request.get_json() or {}
        else:
            data = request.args.to_dict()
        
        print(f"[DEBUG] 请求数据: {data}")
        print(f"[DEBUG] 查找API函数: {api_name}")
        print(f"[DEBUG] 插件模块属性: {[attr for attr in dir(plugin_module) if not attr.startswith('_')]}")
        
        # 调用插件 API - 通用API调用
        if hasattr(plugin_module, api_name):
            api_func = getattr(plugin_module, api_name)
            if callable(api_func):
                try:
                    # 根据请求方法调用API
                    if request.method == 'POST':
                        if data:
                            # 如果有数据，尝试传递参数
                            import inspect
                            sig = inspect.signature(api_func)
                            if len(sig.parameters) > 0:
                                # 判断是否需要传递整个data对象还是单个参数
                                param_names = list(sig.parameters.keys())
                                if len(param_names) == 1 and len(data) == 1:
                                    # 单个参数，直接传递值
                                    first_key = list(data.keys())[0]
                                    result = api_func(data[first_key])
                                else:
                                    # 多个参数或整个对象，传递字典
                                    result = api_func(data)
                            else:
                                # 无参数函数
                                result = api_func()
                        else:
                            # 无数据，直接调用
                            result = api_func()
                    else:
                        # GET请求，直接调用
                        result = api_func()
                    
                    # 如果结果已经是字典且包含success字段，直接返回
                    if isinstance(result, dict) and 'success' in result:
                        return jsonify(result)
                    else:
                        # 否则包装结果
                        return jsonify({
                            'success': True,
                            'data': result
                        })
                except Exception as e:
                    print(f"[ERROR] API调用异常: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return jsonify({
                        'success': False,
                        'error': f'API调用失败: {str(e)}'
                    }), 500
            else:
                return jsonify({
                    'success': False,
                    'error': f'{api_name} 不是可调用的函数'
                }), 400
        
        # 兼容旧版API
        elif api_name == 'get_groups' and hasattr(plugin_module, 'get_plugin_groups'):
            result = plugin_module.get_plugin_groups()
            return jsonify({
                'success': True,
                'data': result
            })
        
        elif api_name == 'update_groups' and hasattr(plugin_module, 'update_plugin_groups'):
            result = plugin_module.update_plugin_groups(data)
            return jsonify(result)
        
        elif api_name == 'test_matching' and hasattr(plugin_module, 'test_file_matching'):
            filename = data.get('filename', '')
            if not filename:
                return jsonify({
                    'success': False,
                    'error': '缺少 filename 参数'
                }), 400
            
            result = plugin_module.test_file_matching(filename)
            return jsonify(result)
        
        else:
            return jsonify({
                'success': False,
                'error': f'API {api_name} 不存在或未在插件中定义'
            }), 404
            
    except Exception as e:
        print(f"[ERROR] 插件API路由异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/configured', methods=['GET'])
def check_configured():
    """检查是否已完成配置"""
    global config_manager
    try:
        if not config_manager:
            config_manager = ConfigManager()
        
        # 获取所有配置项
        target_folder = config_manager.get_config('target_folder')
        external_plugins_dir = config_manager.get_config('external_plugins_dir')
        
        # 检查必要的配置项是否已设置
        if not target_folder or target_folder == '/tmp/output':
            return jsonify({
                'configured': False,
                'message': '输出目录未配置'
            }), 403
            
        if not external_plugins_dir:
            return jsonify({
                'configured': False,
                'message': '插件目录未配置'
            }), 403
        
        return jsonify({
            'configured': True,
            'message': '配置已完成'
        })
    except Exception as e:
        return jsonify({
            'configured': False,
            'error': str(e)
        }), 403

def restart_app():
    """重启应用程序"""
    global current_port
    print(f"\n[INFO] 重启服务器，保持端口 {current_port}...")
    
    # 保存端口信息到环境变量
    os.environ['WEBUI_RESTART_PORT'] = str(current_port)
    os.environ['WEBUI_NO_BROWSER'] = '1'  # 标记不要打开浏览器
    
    # 重启Python进程
    python = sys.executable
    os.execl(python, python, *sys.argv)

# 全局变量存储活跃连接
active_connections = set()
last_heartbeat = time.time()

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """心跳包API"""
    global last_heartbeat
    try:
        data = request.get_json() or {}
        client_id = data.get('client_id', 'default')
        
        # 更新心跳时间
        last_heartbeat = time.time()
        active_connections.add(client_id)
        
        return jsonify({
            'success': True,
            'server_time': last_heartbeat
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def monitor_heartbeat():
    """监控心跳包，如果超时则退出服务器"""
    global last_heartbeat
    while True:
        time.sleep(1)  # 每秒检查一次
        current_time = time.time()
        
        # 如果超过3秒没有收到心跳包，退出服务器
        if current_time - last_heartbeat > 3:
            print(f"\n[INFO] 心跳包超时，前端可能已关闭，退出服务器...")
            os._exit(0)

if __name__ == '__main__':
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Web UI 服务器')
    parser.add_argument('--port', type=int, help='指定服务器端口')
    args = parser.parse_args()
    
    print("启动 Web UI 服务器...")
    
    # 检查是否是重启模式
    restart_port = os.environ.get('WEBUI_RESTART_PORT')
    no_browser = os.environ.get('WEBUI_NO_BROWSER')
    
    if args.port:
        # 使用命令行指定的端口
        available_port = args.port
        print(f"使用指定端口: {available_port}")
    elif restart_port:
        # 清除重启标志
        del os.environ['WEBUI_RESTART_PORT']
        if no_browser:
            del os.environ['WEBUI_NO_BROWSER']
        available_port = int(restart_port)
        print(f"重启模式：使用原端口 {available_port}")
    else:
        # 自动检测可用端口
        available_port = find_available_port(8000, 10000)
        
        if available_port is None:
            print("错误：无法找到可用端口（8000-10000）")
            sys.exit(1)
    
    # 保存当前端口
    current_port = available_port
    
    server_url = f'http://127.0.0.1:{available_port}'
    print(f"访问地址: {server_url}")
    
    # 浏览器打开由启动脚本负责，这里不再自动打开
    # if not restart_port:
    #     def open_browser():
    #         time.sleep(1.5)
    #         webbrowser.open(server_url)
    #     
    #     threading.Thread(target=open_browser, daemon=True).start()
    
    # 启动心跳监控线程
    heartbeat_thread = threading.Thread(target=monitor_heartbeat, daemon=True)
    heartbeat_thread.start()
    
    # 启动 Flask 服务器
    try:
        app.run(debug=False, host='127.0.0.1', port=available_port)
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"服务器启动失败: {e}")
        sys.exit(1)
