"""
文件管理模块

提供高效的文件复制、哈希校验和文件管理功能。
支持多线程复制大文件，并提供完整性验证。
"""

from typing import List, Tuple
import os
import hashlib
import rich.progress
import shutil
from module.config import Config
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import filedialog


class current_copying_instance:
    """
    文件复制实例类
    
    负责单个文件的复制操作，包括哈希校验、多线程复制等功能。
    """
    
    def __init__(self, source_file_path: str) -> None:
        """
        初始化文件复制实例
        
        Args:
            source_file_path: 源文件路径
        """
        self.__config = Config()
        self.__file_path__: str = source_file_path
        
        # 获取哈希算法配置
        if (self.__config.get_config("hash_check_enable") and 
            self.__config.get_config("hash_check_enable") in hashlib.algorithms_available):
            self.__hash_func__: str = self.__config.get_config("hash_check_enable")
        else:
            self.__hash_func__ = 'md5'
            
        self.__split_by_suffix: bool = self.__config.get_config("seperate_by_suffix")
        self.__split_by_date: bool = self.__config.get_config("seperate_by_date")

    def get_hash(self, filepath: str) -> str:
        """
        计算文件的哈希值
        
        Args:
            filepath: 文件路径
            
        Returns:
            文件的十六进制哈希字符串
        """
        if not self.__hash_func__:
            return ""
        
        with rich.progress.open(filepath, 'rb') as f:
            hash = hashlib.new(self.__hash_func__)
            for chunk in iter(lambda: f.read(16384), b''):
                hash.update(chunk)
            return hash.hexdigest()
    
    def __fastcopy(self, target_path: str, max_workers: int = 4, chunk_size: int = 1024 * 1024) -> bool:
        """
        使用多线程快速复制文件
        
        Args:
            target_path: 目标路径
            max_workers: 最大线程数
            chunk_size: 每个块的大小（字节）
            
        Returns:
            复制成功返回 True，失败返回 False
        """
        try:
            # 确保目标目录存在
            target_dir = os.path.dirname(target_path)
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)
            
            # 获取文件大小
            file_size = os.path.getsize(self.__file_path__)
            
            # 如果文件较小，使用单线程复制
            if file_size < chunk_size * 2:
                shutil.copy2(self.__file_path__, target_path)
                return True
            
            # 计算多线程复制的块数
            num_chunks = min(max_workers, (file_size + chunk_size - 1) // chunk_size)
            base_chunk_size = file_size // num_chunks
            
            # 结果跟踪
            results = [False] * num_chunks
            
            def copy_chunk(start_pos: int, end_pos: int, chunk_id: int):
                """复制文件的特定块"""
                try:
                    with open(self.__file_path__, 'rb') as source_file:
                        source_file.seek(start_pos)
                        data = source_file.read(end_pos - start_pos)
                        
                        with open(f"{target_path}.part{chunk_id}", 'wb') as chunk_file:
                            chunk_file.write(data)
                    
                    results[chunk_id] = True
                    return True
                except Exception as e:
                    print(f"复制块 {chunk_id} 时出错: {e}")
                    results[chunk_id] = False
                    return False
            
            # 执行多线程复制
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有复制任务并等待完成
                futures = []
                for i in range(num_chunks):
                    start_pos = i * base_chunk_size
                    # 对于最后一块，包含所有剩余字节
                    if i == num_chunks - 1:
                        end_pos = file_size
                    else:
                        end_pos = (i + 1) * base_chunk_size
                    future = executor.submit(copy_chunk, start_pos, end_pos, i)
                    futures.append(future)
                
                # 等待所有任务完成
                for future in futures:
                    future.result()  # 等待任务并抛出任何异常
            
            # 检查是否所有块都复制成功
            if not all(results):
                print(f"某些块复制失败。结果: {results}")
                # 清理部分文件
                for i in range(num_chunks):
                    part_file = f"{target_path}.part{i}"
                    if os.path.exists(part_file):
                        os.remove(part_file)
                return False
            
            print(f"所有 {num_chunks} 个块复制成功，正在合并...")
            
            # 将所有块合并到最终文件
            with open(target_path, 'wb') as target_file:
                for i in range(num_chunks):
                    part_file = f"{target_path}.part{i}"
                    if not os.path.exists(part_file):
                        print(f"部分文件 {part_file} 丢失！")
                        return False
                    with open(part_file, 'rb') as chunk_file:
                        target_file.write(chunk_file.read())
                    os.remove(part_file)
            
            print(f"文件合并完成")
            
            # 复制文件元数据
            shutil.copystat(self.__file_path__, target_path)
            
            # 验证文件大小
            actual_size = os.path.getsize(target_path)
            if actual_size != file_size:
                print(f"文件大小不匹配: 期望 {file_size}，实际 {actual_size}")
                os.remove(target_path)
                return False
            
            print(f"文件大小验证通过: {actual_size} 字节")
            return True
            
        except Exception as e:
            print(f"文件复制过程中出错: {e}")
            # 清理任何部分文件
            for i in range(10):  # 清理可能的部分文件
                part_file = f"{target_path}.part{i}"
                if os.path.exists(part_file):
                    try:
                        os.remove(part_file)
                    except:
                        pass
            if os.path.exists(target_path):
                try:
                    os.remove(target_path)
                except:
                    pass
            return False

    def copy_initiator(self, destinations: Tuple) -> bool:
        """
        启动文件复制过程到多个目标位置
        
        Args:
            destinations: 目标路径元组，文件将被复制到这些位置
            
        Returns:
            所有复制都成功返回 True，否则返回 False
        """
        if not destinations:
            return False
        
        success = True
        for destination in destinations:
            print(f"正在复制 {self.__file_path__} 到 {destination}...")
            
            try:
                source_hash = self.get_hash(self.__file_path__)
                # 确保目标目录存在
                target_dir = os.path.dirname(destination)
                if target_dir:
                    os.makedirs(target_dir, exist_ok=True)
                
                if not self.__fastcopy(destination):
                    print(f"复制文件到 {destination} 失败")
                    success = False
                else:
                    target_hash = self.get_hash(destination)
                    if source_hash != target_hash:
                        print(f"{self.__file_path__} 和 {destination} 的哈希值不匹配")
                        print(f"源文件哈希: {source_hash}")
                        print(f"目标文件哈希: {target_hash}")
                        if os.path.exists(destination):
                            os.remove(destination)
                        success = False
                    else:
                        print(f"文件成功复制到 {destination}")
            except Exception as e:
                print(f"复制过程中出错: {e}")
                success = False

        return success
    
    def release(self) -> None:
        """
        释放文件内存资源
        
        此方法删除 current_file 类的实例。
        """
        del self
    