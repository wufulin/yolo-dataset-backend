"""Utility functions for file operations."""
import hashlib
import os
import shutil
from pathlib import Path
from typing import Optional
import zipfile


def resolve_target_directory(zip_file_path, target_folder_name=None):
    """
    从zip文件路径解析目标目录路径
    
    Args:
        zip_file_path: zip文件完整路径
        target_folder_name: 目标文件夹名称，默认为None（自动从zip文件名推导）
    
    Returns:
        Path: 目标目录路径对象
    """
    zip_path = Path(zip_file_path)
    
    if target_folder_name is None:
        # 自动从zip文件名推导目录名（去掉.zip后缀）
        target_folder_name = zip_path.stem  # 这会返回 'coco8-detect'
    
    # 构建目标目录路径
    target_dir = zip_path.parent / target_folder_name
    
    return target_dir
    
def extract_skip_root_safe(zip_path: str, extract_dir: str, root_folder_name: Optional[str] = None) -> None:
    """
    解压zip文件，跳过指定的根目录
    
    Args:
        zip_path: zip文件路径
        extract_dir: 解压目标目录
        root_folder_name: 要跳过的根目录名，如果为None则自动检测
    """
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # 如果未指定根目录名，自动检测第一个目录
        if root_folder_name is None:
            names = zip_ref.namelist()
            for name in names:
                if '/' in name and not name.startswith('__MACOSX'):
                    root_folder_name = name.split('/')[0]
                    break
        
        # 确保目标目录存在
        os.makedirs(extract_dir, exist_ok=True)
        
        # 提取文件
        for member in zip_ref.namelist():
            # 跳过系统文件（如macOS的__MACOSX目录）
            if member.startswith('__MACOSX/'):
                continue
                
            # 跳过根目录条目
            if member == root_folder_name + '/':
                continue
                
            # 处理文件路径
            if member.startswith(root_folder_name + '/'):
                # 移除根目录部分
                new_member = member[len(root_folder_name + '/'):]
                
                if new_member:  # 确保不是空字符串
                    # 提取文件
                    source = zip_ref.open(member)
                    target_path = os.path.join(extract_dir, new_member)
                    
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    
                    # 写入文件
                    with open(target_path, 'wb') as target:
                        target.write(source.read())

def ensure_directory(path: str) -> None:
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        path: Directory path
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def get_file_hash(file_path: str, chunk_size: int = 8192) -> str:
    """
    Calculate MD5 hash of a file.
    
    Args:
        file_path: Path to file
        chunk_size: Chunk size for reading
        
    Returns:
        str: MD5 hash
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def safe_remove(path: str) -> bool:
    """
    Safely remove file or directory.
    
    Args:
        path: Path to remove
        
    Returns:
        bool: True if successful
    """
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        return True
    except Exception:
        return False


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        int: File size in bytes
    """
    return os.path.getsize(file_path)


def get_extension(filename: str) -> str:
    """
    Get file extension in lowercase.
    
    Args:
        filename: Filename
        
    Returns:
        str: File extension
    """
    return Path(filename).suffix.lower()


def is_valid_filename(filename: str) -> bool:
    """
    Check if filename is valid.
    
    Args:
        filename: Filename to check
        
    Returns:
        bool: True if filename is valid
    """
    if not filename or filename.startswith('.'):
        return False
    
    # Check for invalid characters
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        if char in filename:
            return False
    
    return True