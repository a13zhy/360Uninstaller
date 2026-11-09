"""管理员权限检测与自动提权重启"""

import ctypes
import os
import sys
import time

from . import constants


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _exe_command() -> tuple[str, str]:
    """返回 (可执行文件, 参数)。兼容 PyInstaller 单文件与源码运行。"""
    if getattr(sys, "frozen", False):
        return sys.executable, ""
    script = os.path.abspath(sys.argv[0])
    return sys.executable, f'"{script}"'


def relaunch_as_admin() -> bool:
    """以管理员身份重新启动自身，成功后由调用方退出当前进程。"""
    exe, params = _exe_command()
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, params, os.path.dirname(exe) or None, 1
        )
        return rc > 32
    except Exception:
        return False


def ensure_admin(logger=None) -> None:
    """非管理员时自动提权重启；调试环境变量可跳过。"""
    if constants.env_flag(constants.ENV_NO_ELEVATE):
        return
    if is_admin():
        return
    ok = relaunch_as_admin()
    if logger:
        logger("已请求管理员权限，正在重启程序…" if ok else "管理员权限请求被拒绝")
    if ok:
        time.sleep(0.2)
        sys.exit(0)
