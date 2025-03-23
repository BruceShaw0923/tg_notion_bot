"""
Zotero 工具模块 - 提供辅助工具函数
"""

import logging
import os
import tempfile
import shutil
from pathlib import Path

# 配置日志
logger = logging.getLogger(__name__)

def ensure_directory_exists(directory_path):
    """
    确保目录存在，如果不存在则创建
    
    参数：
        directory_path: 目录路径
        
    返回：
        bool: 创建成功返回 True，否则返回 False
    """
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
            logger.info(f"Created directory: {directory_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory_path}: {str(e)}")
        return False

def create_temp_copy(source_path, keep_original_name=True):
    """
    创建文件的临时副本
    
    参数：
        source_path: 源文件路径
        keep_original_name: 是否保留原始文件名
        
    返回：
        str: 临时文件路径，如果失败返回 None
    """
    try:
        if not os.path.exists(source_path):
            logger.error(f"Source file does not exist: {source_path}")
            return None
            
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        
        # 确定目标文件名
        if keep_original_name:
            target_filename = os.path.basename(source_path)
        else:
            # 获取文件扩展名
            file_ext = os.path.splitext(source_path)[1]
            # 创建临时文件名
            fd, temp_path = tempfile.mkstemp(suffix=file_ext)
            os.close(fd)
            target_filename = os.path.basename(temp_path)
            
        # 完整目标路径
        target_path = os.path.join(temp_dir, target_filename)
        
        # 复制文件
        shutil.copy2(source_path, target_path)
        
        logger.info(f"Created temporary copy: {target_path}")
        return target_path
    except Exception as e:
        logger.error(f"Error creating temporary copy: {str(e)}")
        return None

def cleanup_temp_files(file_path):
    """
    清理临时文件和目录
    
    参数：
        file_path: 临时文件路径
        
    返回：
        bool: 清理成功返回 True，否则返回 False
    """
    try:
        if not file_path or not os.path.exists(file_path):
            return True
            
        # 获取包含临时文件的目录
        temp_dir = os.path.dirname(file_path)
        
        # 删除文件
        if os.path.isfile(file_path):
            os.remove(file_path)
            logger.info(f"Removed temporary file: {file_path}")
            
        # 尝试删除目录（如果为空）
        if os.path.isdir(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
            logger.info(f"Removed temporary directory: {temp_dir}")
            
        return True
    except Exception as e:
        logger.error(f"Error cleaning up temporary files: {str(e)}")
        return False
