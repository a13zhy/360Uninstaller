"""注册表读写、备份与删除"""

import os
import subprocess
import time
import winreg

from . import constants

HK_ROOTS = {
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
    "HKU": winreg.HKEY_USERS,
}

BACKUP_DIR = os.path.join(constants.LOG_DIR, "reg_backup")


def split_key(path: str) -> tuple[int, str]:
    """把 'HKLM\\SOFTWARE\\...' 拆成 (hkey, 子路径)。"""
    parts = path.split("\\", 1)
    root = parts[0].upper()
    sub = parts[1] if len(parts) > 1 else ""
    return HK_ROOTS.get(root, winreg.HKEY_LOCAL_MACHINE), sub


def key_exists(path: str) -> bool:
    hkey, sub = split_key(path)
    try:
        with winreg.OpenKey(hkey, sub, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY):
            return True
    except OSError:
        try:
            with winreg.OpenKey(hkey, sub, 0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY):
                return True
        except OSError:
            return False


def list_subkeys(path: str) -> list[str]:
    hkey, sub = split_key(path)
    out = []
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(hkey, sub, 0, winreg.KEY_READ | view) as k:
                count = winreg.QueryInfoKey(k)[0]
                for i in range(count):
                    try:
                        out.append(winreg.EnumKey(k, i))
                    except OSError:
                        break
        except OSError:
            continue
    return sorted(set(out))


def read_values(path: str) -> dict:
    hkey, sub = split_key(path)
    data = {}
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(hkey, sub, 0, winreg.KEY_READ | view) as k:
                count = winreg.QueryInfoKey(k)[1]
                for i in range(count):
                    try:
                        name, value, _ = winreg.EnumValue(k, i)
                        data[name] = value
                    except OSError:
                        break
        except OSError:
            continue
    return data


def get_value(path: str, name: str):
    return read_values(path).get(name)


def backup_key(path: str) -> str:
    """导出注册表项到 .reg 文件，返回备份文件路径（失败返回空串）。"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    safe = path.replace("\\", "_").replace(" ", "_")
    target = os.path.join(BACKUP_DIR, f"{safe}_{time.strftime('%Y%m%d_%H%M%S')}.reg")
    try:
        p = subprocess.run(
            ["reg", "export", path, target, "/y"],
            capture_output=True,
            timeout=20,
            creationflags=0x08000000,
        )
        if p.returncode == 0 and os.path.exists(target):
            return target
    except Exception:
        pass
    return ""


def delete_key(path: str) -> tuple[bool, str]:
    """备份后删除整棵注册表子树。"""
    if not key_exists(path):
        return True, "注册表项已不存在"
    backup = backup_key(path)
    try:
        p = subprocess.run(
            ["reg", "delete", path, "/f"],
            capture_output=True,
            timeout=20,
            creationflags=0x08000000,
        )
        out = (p.stdout or b"").decode("gbk", errors="ignore") + (
            p.stderr or b""
        ).decode("gbk", errors="ignore")
        if p.returncode == 0:
            note = f"已删除（已备份 {os.path.basename(backup)}）" if backup else "已删除"
            return True, note
        return False, out.strip() or "删除失败"
    except Exception as exc:
        return False, str(exc)


def delete_value(path: str, name: str) -> tuple[bool, str]:
    """删除单个注册表值（用于 Run 启动项）。"""
    hkey, sub = split_key(path)
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(hkey, sub, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE | view) as k:
                try:
                    winreg.QueryValueEx(k, name)
                except OSError:
                    continue
                winreg.DeleteValue(k, name)
                return True, "已删除启动项"
        except OSError:
            continue
    return True, "启动项已不存在"
