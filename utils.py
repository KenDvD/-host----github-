import os
import sys
import socket
import struct
import ctypes
from typing import Optional, Tuple, List

# 资源路径函数，兼容 PyInstaller 与源码运行
BASE_PATH = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

def resource_path(*parts: str) -> str:
    """返回资源绝对路径，兼容 PyInstaller 与源码运行。"""
    return os.path.join(BASE_PATH, *parts)

# Windows 权限相关函数
def is_admin() -> bool:
    """检查当前用户是否拥有管理员权限。"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

# 网络相关工具函数
def get_host_by_name(hostname: str) -> Optional[Tuple[str, ...]]:
    """获取主机的所有 IP 地址。"""
    try:
        return socket.gethostbyname_ex(hostname)[2]
    except socket.error:
        return None

# 文件操作工具函数
def read_file_lines(file_path: str, encoding: str = 'utf-8') -> List[str]:
    """读取文件内容并返回行列表。"""
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.readlines()
    except FileNotFoundError:
        return []
    except Exception:
        return []

def write_file_lines(file_path: str, lines: List[str], encoding: str = 'utf-8') -> bool:
    """将行列表写入文件。"""
    try:
        with open(file_path, 'w', encoding=encoding) as f:
            f.writelines(lines)
        return True
    except Exception:
        return False
