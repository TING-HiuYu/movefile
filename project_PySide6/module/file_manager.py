"""
文件管理模块

提供高效的文件复制、哈希校验和文件管理功能。
该模块实现了多线程文件复制策略，支持大文件的分块并行处理，
并提供多种哈希算法的文件完整性验证功能。

主要特性：
- 智能复制策略：小文件单线程，大文件多线程分块复制
- 完整性验证：支持MD5、SHA1、SHA256、SHA512等哈希算法
- 进度显示：集成rich库提供美观的进度条显示
- 错误恢复：复制失败时自动清理临时文件
- 元数据保留：复制后保持原文件的时间戳等属性

性能优化：
- 自适应分块大小，根据文件大小调整策略
- 并行读写，充分利用多核CPU和存储带宽
- 内存友好，避免大文件一次性加载到内存

Author: File Classifier Project
License: MIT
"""

from typing import List, Tuple, Optional
import os
import hashlib
import rich.progress
import importlib.util
import shutil
from concurrent.futures import ThreadPoolExecutor
from module import config  # 导入配置管理器


class current_copying_instance:
    """
    文件复制实例管理类
    
    负责单个文件的完整复制流程，包括多线程复制、哈希校验、
    进度监控和错误处理。每个实例绑定一个源文件，支持复制到
    多个目标位置。
    
    工作流程：
    1. 根据配置决定是否启用哈希校验
    2. 计算源文件哈希值（如果启用校验）
    3. 根据文件大小选择复制策略（单线程/多线程）
    4. 执行文件复制操作
    5. 验证目标文件完整性（如果启用校验）
    6. 清理临时文件（如果复制失败）
    
    Attributes:
        __config: 配置管理器实例
        __file_path__: 源文件的绝对路径
        __hash_func__: 使用的哈希算法名称，空字符串表示不校验
    """
    
    def __init__(self, source_file_path: str) -> None:
        """
        初始化文件复制实例
        
        Args:
            source_file_path: 源文件路径，支持相对路径和绝对路径
            
        Note:
            - 会自动从配置文件读取哈希校验设置
            - 只有在hashlib支持且配置启用时才会进行哈希校验
            - 配置中的hash_check_enable为空字符串时表示不启用校验
        """
        self.__config = config.Config()  # 获取配置实例
        self.__file_path__: str = source_file_path
        
        # 根据配置决定哈希校验算法
        hash_config = self.__config.get_config("hash_check_enable")
        if (hash_config and 
            hash_config in hashlib.algorithms_available):
            self.__hash_func__: str = hash_config
        else:
            self.__hash_func__ = ""

    def get_hash(self, filepath: str) -> str:
        """
        计算文件的哈希值
        
        使用配置指定的哈希算法计算文件的哈希值，支持大文件的
        分块读取以避免内存溢出。集成rich进度条提供用户友好的
        进度显示。
        
        Args:
            filepath: 要计算哈希的文件路径
            
        Returns:
            str: 文件的十六进制哈希字符串，如果不启用校验则返回空字符串
            
        Note:
            - 使用16KB分块读取，平衡内存使用和IO效率
            - 集成rich.progress显示计算进度
            - 支持所有hashlib提供的算法
        """
        if self.__hash_func__ == "":
            return ""
        
        print(f"正在计算文件哈希值: {filepath}")
        print(f"使用算法: {self.__hash_func__}")
        
        try:
            with rich.progress.open(filepath, 'rb') as f:
                hash_obj = hashlib.new(self.__hash_func__)
                # 使用16KB分块读取，平衡性能和内存使用
                for chunk in iter(lambda: f.read(16384), b''):
                    hash_obj.update(chunk)
                return hash_obj.hexdigest()
        except Exception as e:
            print(f"计算哈希值时出错: {e}")
            return ""
    
    def __fastcopy(self, target_path: str, max_workers: int = 4, chunk_size: int = 1024 * 1024) -> bool:
        """
        多线程快速文件复制实现
        
        根据文件大小智能选择复制策略：小文件使用单线程直接复制，
        大文件使用多线程分块并行复制。支持自动错误恢复和临时文件清理。
        
        复制策略：
        - 文件 < 2MB: 单线程复制，使用shutil.copy2保留元数据
        - 文件 ≥ 2MB: 多线程分块复制，提高大文件传输效率
        
        Args:
            target_path: 目标文件路径
            max_workers: 最大线程数，默认4个线程
            chunk_size: 每个分块的大小（字节），默认1MB
            
        Returns:
            bool: 复制成功返回True，失败返回False
            
        Note:
            - 自动创建目标目录
            - 保留文件元数据（时间戳、权限等）
            - 复制失败时自动清理临时文件
            - 支持大文件的内存友好处理
            
        Raises:
            无直接异常抛出，所有异常都被捕获并返回False
        """
        try:
            # 确保目标目录存在
            target_dir = os.path.dirname(target_path)
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)
            
            # 获取源文件大小
            file_size = os.path.getsize(self.__file_path__)
            print(f"文件大小: {file_size} 字节 ({file_size / (1024*1024):.2f} MB)")
            
            # 小文件使用单线程复制，避免多线程开销
            if file_size < chunk_size * 2:
                print("文件较小，使用单线程复制")
                shutil.copy2(self.__file_path__, target_path)
                return True
            
            # 大文件使用多线程分块复制
            print(f"文件较大，使用多线程复制 (最大{max_workers}个线程)")
            
            # 计算最优分块数量和大小
            num_chunks = min(max_workers, (file_size + chunk_size - 1) // chunk_size)
            base_chunk_size = file_size // num_chunks
            
            print(f"分块策略: {num_chunks}个分块，每块约{base_chunk_size / (1024*1024):.2f}MB")
            
            # 线程执行结果跟踪
            results = [False] * num_chunks
            
            def copy_chunk(start_pos: int, end_pos: int, chunk_id: int) -> bool:
                """
                复制文件的指定分块
                
                Args:
                    start_pos: 分块在文件中的起始位置
                    end_pos: 分块在文件中的结束位置
                    chunk_id: 分块编号，用于临时文件命名
                    
                Returns:
                    bool: 分块复制成功返回True
                """
                try:
                    # 读取指定范围的文件数据
                    with open(self.__file_path__, 'rb') as source_file:
                        source_file.seek(start_pos)
                        data = source_file.read(end_pos - start_pos)
                        
                        # 写入临时分块文件
                        temp_chunk_path = f"{target_path}.part{chunk_id}"
                        with open(temp_chunk_path, 'wb') as chunk_file:
                            chunk_file.write(data)
                    
                    # 更新结果状态
                    results[chunk_id] = True
                    print(f"分块 {chunk_id + 1}/{num_chunks} 复制完成")
                    return True
                    
                except Exception as e:
                    print(f"复制分块 {chunk_id} 时出错: {e}")
                    results[chunk_id] = False
                    return False
            
            # 使用线程池执行并行复制
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有分块复制任务
                futures = []
                for i in range(num_chunks):
                    start_pos = i * base_chunk_size
                    # 最后一块包含所有剩余字节
                    if i == num_chunks - 1:
                        end_pos = file_size
                    else:
                        end_pos = (i + 1) * base_chunk_size
                        
                    future = executor.submit(copy_chunk, start_pos, end_pos, i)
                    futures.append(future)
                
                # 等待所有任务完成
                for future in futures:
                    future.result()  # 等待任务完成并获取异常
            
            # 检查所有分块是否都复制成功
            if not all(results):
                print(f"部分分块复制失败。结果状态: {results}")
                # 清理失败的分块文件
                self._cleanup_temp_files(target_path, num_chunks)
                return False
            
            print(f"所有 {num_chunks} 个分块复制成功，正在合并...")
            
            # 将所有分块合并到最终文件
            with open(target_path, 'wb') as target_file:
                for i in range(num_chunks):
                    part_file = f"{target_path}.part{i}"
                    if not os.path.exists(part_file):
                        print(f"分块文件 {part_file} 丢失！")
                        return False
                        
                    with open(part_file, 'rb') as chunk_file:
                        target_file.write(chunk_file.read())
                    
                    # 删除临时分块文件
                    os.remove(part_file)
            
            print("文件合并完成")
            
            # 复制文件元数据（时间戳、权限等）
            shutil.copystat(self.__file_path__, target_path)
            
            # 验证文件大小一致性
            actual_size = os.path.getsize(target_path)
            if actual_size != file_size:
                print(f"文件大小验证失败: 期望 {file_size}，实际 {actual_size}")
                os.remove(target_path)
                return False
            
            print(f"文件大小验证通过: {actual_size} 字节")
            return True
            
        except Exception as e:
            print(f"文件复制过程中出现异常: {e}")
            # 清理可能产生的临时文件
            self._cleanup_temp_files(target_path, 10)  # 清理最多10个可能的分块
            # 清理目标文件
            if os.path.exists(target_path):
                try:
                    os.remove(target_path)
                except:
                    pass
            return False
    
    def _cleanup_temp_files(self, target_path: str, max_chunks: int) -> None:
        """
        清理临时分块文件
        
        Args:
            target_path: 目标文件路径
            max_chunks: 最大分块数量
        """
        for i in range(max_chunks):
            part_file = f"{target_path}.part{i}"
            if os.path.exists(part_file):
                try:
                    os.remove(part_file)
                    print(f"已清理临时文件: {part_file}")
                except Exception as e:
                    print(f"清理临时文件 {part_file} 失败: {e}")

    def copy_initiator(self, destinations: Tuple[str, ...]) -> bool:
        """
        启动文件复制流程到多个目标位置
        
        执行完整的文件复制工作流程，包括完整性校验、复制操作和验证。
        支持同时复制到多个目标位置，每个目标都独立进行完整性验证。
        
        工作流程：
        1. 验证输入参数的有效性
        2. 计算源文件哈希值（如果启用校验）
        3. 对每个目标位置执行复制操作
        4. 验证每个目标文件的完整性
        5. 清理复制失败的文件
        
        Args:
            destinations: 目标路径元组，文件将被复制到这些位置
            
        Returns:
            bool: 所有目标都复制成功返回True，否则返回False
            
        Note:
            - 每个目标位置都独立处理，一个失败不影响其他目标
            - 启用哈希校验时，源文件和目标文件哈希值必须完全一致
            - 复制失败的目标文件会被自动删除，避免留下损坏文件
            
        Example:
            >>> copier = current_copying_instance("source.txt")
            >>> success = copier.copy_initiator(("/path/to/dest1.txt", "/path/to/dest2.txt"))
        """
        if not destinations:
            print("错误: 未指定目标路径")
            return False
        
        # 验证源文件存在性
        if not os.path.exists(self.__file_path__):
            print(f"错误: 源文件不存在: {self.__file_path__}")
            return False
        
        print(f"开始复制文件: {self.__file_path__}")
        print(f"目标数量: {len(destinations)}")
        
        # 计算源文件哈希值（如果启用校验）
        source_hash = ""
        if self.__hash_func__:
            print("正在计算源文件哈希值...")
            source_hash = self.get_hash(self.__file_path__)
            if not source_hash:
                print("警告: 无法计算源文件哈希值，跳过完整性校验")
            else:
                print(f"源文件哈希值: {source_hash}")
        
        overall_success = True
        successful_copies = 0
        
        # 逐个处理每个目标位置
        for i, destination in enumerate(destinations, 1):
            print(f"\n--- 处理目标 {i}/{len(destinations)}: {destination} ---")
            
            try:
                # 确保目标目录存在
                target_dir = os.path.dirname(destination)
                if target_dir:
                    os.makedirs(target_dir, exist_ok=True)
                    print(f"目标目录已准备: {target_dir}")
                
                # 执行文件复制
                print("开始复制文件...")
                if not self.__fastcopy(destination):
                    print(f"❌ 复制到 {destination} 失败")
                    overall_success = False
                    continue
                
                # 完整性校验（如果启用）
                if source_hash:
                    print("正在验证文件完整性...")
                    target_hash = self.get_hash(destination)
                    
                    if target_hash != source_hash:
                        print(f"❌ 完整性校验失败:")
                        print(f"   源文件哈希: {source_hash}")
                        print(f"   目标文件哈希: {target_hash}")
                        
                        # 删除校验失败的文件
                        if os.path.exists(destination):
                            try:
                                os.remove(destination)
                                print(f"已删除校验失败的文件: {destination}")
                            except Exception as e:
                                print(f"删除文件失败: {e}")
                        
                        overall_success = False
                        continue
                    else:
                        print("✅ 完整性校验通过")
                
                print(f"✅ 成功复制到: {destination}")
                successful_copies += 1
                
            except Exception as e:
                print(f"❌ 处理目标 {destination} 时出现异常: {e}")
                overall_success = False
                
                # 清理可能的残留文件
                if os.path.exists(destination):
                    try:
                        os.remove(destination)
                        print(f"已清理异常文件: {destination}")
                    except:
                        pass
        
        # 输出总结信息
        print(f"\n=== 复制任务完成 ===")
        print(f"成功复制: {successful_copies}/{len(destinations)}")
        print(f"整体结果: {'成功' if overall_success else '部分失败'}")
        
        return overall_success
    
    def release(self) -> None:
        """
        释放文件复制实例占用的资源
        
        该方法用于显式清理实例资源，虽然Python的垃圾回收机制
        会自动处理对象销毁，但提供此方法以便在需要时手动释放。
        
        Note:
            - 当前实现使用del self，依赖Python垃圾回收
            - 未来可能扩展为清理临时文件、关闭文件句柄等操作
            - 建议在长时间运行的程序中显式调用此方法
        """
        # 清理可能的临时文件
        # 这里暂时没有需要清理的资源，预留接口
        del self

if __name__ == "__main__":
    # 测试代码示例
    source_file = "example.txt"  # 替换为实际的源文件路径
    destinations = ("copy1.txt", "copy2.txt")  # 替换为实际的目标路径
    
    copier = current_copying_instance(source_file)
    success = copier.copy_initiator(destinations)
    
    if success:
        print("所有文件复制成功")
    else:
        print("部分文件复制失败")
    
    copier.release()  # 显式释放资源