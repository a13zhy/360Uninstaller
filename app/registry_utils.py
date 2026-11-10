"""注册表读写、备份与删除（权限接管 / 自我保护识别 / 安全模式清理包）"""

import ctypes
import os
import subprocess
import time
import winreg
from ctypes import wintypes

from . import constants

HK_ROOTS = {
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
    "HKU": winreg.HKEY_USERS,
}

HK_RAW = {
    "HKLM": 0x80000002,
    "HKCU": 0x80000001,
    "HKCR": 0x80000000,
    "HKU": 0x80000003,
}

BACKUP_DIR = os.path.join(constants.LOG_DIR, "reg_backup")
SAFE_MODE_DIR = os.path.join(constants.LOG_DIR, "safe_mode")

ERROR_SUCCESS = 0
ERROR_FILE_NOT_FOUND = 2
ERROR_ACCESS_DENIED = 5

PROTECT_PROCESSES = ("ZhuDongFangYu.exe", "360tray.exe", "360Safe.exe",
                     "QHSafeTray.exe", "360sd.exe")
PROTECT_SERVICES = ("ZhuDongFangYu", "360SelfProtection", "360AntiHacker",
                    "QHActiveDefense", "360rp", "360rps")

_PROTECTED = []


def split_key(path):
    parts = path.split("\\", 1)
    root = parts[0].upper()
    sub = parts[1] if len(parts) > 1 else ""
    return HK_ROOTS.get(root, winreg.HKEY_LOCAL_MACHINE), sub


def _split_raw(path):
    parts = path.split("\\", 1)
    root = parts[0].upper()
    return HK_RAW.get(root, HK_RAW["HKLM"]), (parts[1] if len(parts) > 1 else "")


def _views(sub):
    """路径里已写 WOW6432Node 时不能再叠加 32 位重定向，否则变成双层路径。"""
    if "wow6432node" in sub.lower():
        return (0,)
    return (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY)


def key_exists(path):
    """存在但读不了（拒绝访问）也要算存在，否则会误报已清理而跳过。"""
    hkey, sub = split_key(path)
    for view in _views(sub):
        try:
            with winreg.OpenKey(hkey, sub, 0, winreg.KEY_READ | view):
                return True
        except PermissionError:
            return True
        except OSError as exc:
            if getattr(exc, "winerror", None) == ERROR_ACCESS_DENIED:
                return True
            continue
    return False


def list_subkeys(path):
    hkey, sub = split_key(path)
    out = []
    for view in _views(sub):
        try:
            with winreg.OpenKey(hkey, sub, 0, winreg.KEY_READ | view) as k:
                for i in range(winreg.QueryInfoKey(k)[0]):
                    try:
                        out.append(winreg.EnumKey(k, i))
                    except OSError:
                        break
        except OSError:
            continue
    return sorted(set(out))


def read_values(path):
    hkey, sub = split_key(path)
    data = {}
    for view in _views(sub):
        try:
            with winreg.OpenKey(hkey, sub, 0, winreg.KEY_READ | view) as k:
                for i in range(winreg.QueryInfoKey(k)[1]):
                    try:
                        name, value, _t = winreg.EnumValue(k, i)
                        data[name] = value
                    except OSError:
                        break
        except OSError:
            continue
    return data


def get_value(path, name):
    return read_values(path).get(name)


def backup_key(path):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    safe = path.replace("\\", "_").replace(" ", "_")
    target = os.path.join(BACKUP_DIR, "%s_%s.reg" % (safe, time.strftime("%Y%m%d_%H%M%S")))
    try:
        p = subprocess.run(["reg", "export", path, target, "/y"],
                           capture_output=True, timeout=20,
                           creationflags=0x08000000)
        if p.returncode == 0 and os.path.exists(target):
            return target
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------- 保护识别
def _running_processes(names):
    TH32CS_SNAPPROCESS = 0x00000002

    class PE32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]

    found = []
    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snap == -1:
            return found
        entry = PE32()
        entry.dwSize = ctypes.sizeof(PE32)
        lowered = {n.lower() for n in names}
        ok = k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            if entry.szExeFile.lower() in lowered:
                found.append(entry.szExeFile)
            ok = k32.Process32NextW(snap, ctypes.byref(entry))
        k32.CloseHandle(snap)
    except Exception:
        pass
    return sorted(set(found))


def _service_running(name):
    SERVICE_QUERY_STATUS = 0x0004
    SERVICE_RUNNING = 0x00000004

    class SVC_STATUS(ctypes.Structure):
        _fields_ = [("dwServiceType", wintypes.DWORD), ("dwCurrentState", wintypes.DWORD),
                    ("dwControlsAccepted", wintypes.DWORD), ("dwWin32ExitCode", wintypes.DWORD),
                    ("dwServiceSpecificExitCode", wintypes.DWORD),
                    ("dwCheckPoint", wintypes.DWORD), ("dwWaitHint", wintypes.DWORD)]

    try:
        adv = ctypes.WinDLL("advapi32", use_last_error=True)
        scm = adv.OpenSCManagerW(None, None, 0x0001)
        if not scm:
            return False
        hsvc = adv.OpenServiceW(scm, name, SERVICE_QUERY_STATUS)
        running = False
        if hsvc:
            st = SVC_STATUS()
            if adv.QueryServiceStatus(hsvc, ctypes.byref(st)):
                running = st.dwCurrentState == SERVICE_RUNNING
            adv.CloseServiceHandle(hsvc)
        adv.CloseServiceHandle(scm)
        return running
    except Exception:
        return False


def protection_running():
    hits = list(_running_processes(PROTECT_PROCESSES))
    for svc in PROTECT_SERVICES:
        if _service_running(svc):
            hits.append(svc)
    return sorted(set(hits))


def safe_mode_active():
    """SM_CLEANBOOT：0 正常，1 安全模式，2 带网络安全模式。"""
    try:
        return ctypes.windll.user32.GetSystemMetrics(67) in (1, 2)
    except Exception:
        return False


# ---------------------------------------------------------------- 原生 API
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

KEY_READ = 0x20019
WRITE_DAC = 0x00040000
WRITE_OWNER = 0x00080000
READ_CONTROL = 0x00020000
KEY_ALL_ACCESS = 0xF003F
SE_REGISTRY_KEY = 4
OWNER_SECURITY_INFORMATION = 0x00000001
DACL_SECURITY_INFORMATION = 0x00000004
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x0002


class _LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", ctypes.c_long)]


class _LUID_ATTR(ctypes.Structure):
    _fields_ = [("Luid", _LUID), ("Attributes", wintypes.DWORD)]


class _TOKEN_PRIVS(ctypes.Structure):
    _fields_ = [("PrivilegeCount", wintypes.DWORD),
                ("Privileges", _LUID_ATTR * 1)]


def _enable_privileges(*names):
    """启用取得所有权 / 备份还原 / 安全权限等特权。"""
    try:
        token = wintypes.HANDLE()
        if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(),
                                         TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                         ctypes.byref(token)):
            return
        for name in names:
            luid = _LUID()
            if not advapi32.LookupPrivilegeValueW(None, name, ctypes.byref(luid)):
                continue
            tp = _TOKEN_PRIVS()
            tp.PrivilegeCount = 1
            tp.Privileges[0].Luid = luid
            tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
            advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(tp),
                                           ctypes.sizeof(tp), None, None)
        kernel32.CloseHandle(token)
    except Exception:
        pass


def _open_raw(hkey, sub, access, view):
    handle = wintypes.HKEY()
    rc = advapi32.RegOpenKeyExW(ctypes.c_void_p(hkey), sub, 0,
                                access | view, ctypes.byref(handle))
    return (handle.value or 0) if rc == ERROR_SUCCESS else 0


def _close_raw(handle):
    if handle:
        advapi32.RegCloseKey(ctypes.c_void_p(handle))


def _admin_sid():
    """Administrators 内置 SID（S-1-5-32-544），不受系统语言影响。"""
    sid = ctypes.c_void_p()
    if not advapi32.ConvertStringSidToSidW("S-1-5-32-544", ctypes.byref(sid)):
        return None
    return sid


def _take_ownership(handle, sid):
    return advapi32.SetSecurityInfo(ctypes.c_void_p(handle), SE_REGISTRY_KEY,
                                    OWNER_SECURITY_INFORMATION, sid, None,
                                    None, None) == ERROR_SUCCESS


def _grant_admin_dacl(handle, sid):
    """整条 DACL 重建为 Administrators 完全控制，连带清掉所有 Deny ACE。

    Deny 优先于 Allow，只加 Allow 不删 Deny 没用，所以直接覆盖。
    """
    size = 1024
    acl = (ctypes.c_ubyte * size)()
    if not advapi32.InitializeAcl(ctypes.byref(acl), size, 2):
        return False
    if not advapi32.AddAccessAllowedAce(ctypes.byref(acl), 2, KEY_ALL_ACCESS, sid):
        return False
    return advapi32.SetSecurityInfo(ctypes.c_void_p(handle), SE_REGISTRY_KEY,
                                    DACL_SECURITY_INFORMATION, None, None,
                                    ctypes.byref(acl), None) == ERROR_SUCCESS


def _enum_children(hkey, sub, view):
    out = []
    h = _open_raw(hkey, sub, KEY_READ, view)
    if not h:
        return out
    try:
        i = 0
        buf = ctypes.create_unicode_buffer(512)
        while True:
            n = wintypes.DWORD(512)
            rc = advapi32.RegEnumKeyExW(ctypes.c_void_p(h), i, buf,
                                        ctypes.byref(n), None, None, None, None)
            if rc != ERROR_SUCCESS:
                break
            out.append(buf.value)
            i += 1
    finally:
        _close_raw(h)
    return out


def _harden_key(hkey, sub, view, depth=0):
    """接管本键（换属主 + 重建 DACL），再递归处理子键。"""
    if depth > 8:
        return True
    h = _open_raw(hkey, sub, WRITE_OWNER | READ_CONTROL, view)
    sid = _admin_sid()
    try:
        if not h:
            return False
        if sid:
            _take_ownership(h, sid)
    finally:
        _close_raw(h)
        if sid:
            kernel32.LocalFree(sid)

    h = _open_raw(hkey, sub, WRITE_DAC | READ_CONTROL, view)
    sid = _admin_sid()
    ok = False
    try:
        if h and sid:
            ok = _grant_admin_dacl(h, sid)
    finally:
        _close_raw(h)
        if sid:
            kernel32.LocalFree(sid)
    if not ok:
        return False

    for child in _enum_children(hkey, sub, view):
        _harden_key(hkey, sub + "\\" + child, view, depth + 1)
    return True


def _native_delete(hkey, sub, view):
    _enable_privileges("SeTakeOwnershipPrivilege", "SeRestorePrivilege",
                       "SeBackupPrivilege", "SeSecurityPrivilege")
    _harden_key(hkey, sub, view)
    rc = advapi32.RegDeleteTreeW(ctypes.c_void_p(hkey), sub)
    if rc not in (ERROR_SUCCESS, ERROR_FILE_NOT_FOUND):
        return False
    rc = advapi32.RegDeleteKeyExW(ctypes.c_void_p(hkey), sub, view, 0)
    return rc in (ERROR_SUCCESS, ERROR_FILE_NOT_FOUND)


# ---------------------------------------------------------------- 对外接口
def _is_protected_now():
    return bool(protection_running()) and not safe_mode_active()


def _protected_message():
    comps = protection_running()
    detail = "、".join(comps[:4]) if comps else "360 自我保护"
    if safe_mode_active():
        return "仍被拦截（安全模式下异常，请检查驱动是否被残留服务重新加载）"
    return ("被 360 自我保护拦截（%s 运行中），在线无法删除："
            "请关闭自我保护，或用生成的安全模式清理包删除" % detail)


def _mark_protected(path):
    if path not in _PROTECTED:
        _PROTECTED.append(path)


def consume_protected():
    global _PROTECTED
    items = list(_PROTECTED)
    _PROTECTED = []
    return items


def pending_protected():
    return list(_PROTECTED)


def delete_key(path):
    """备份后删除整棵子树；无权限时先接管所有权再删。"""
    if not key_exists(path):
        return True, "注册表项已不存在（无需清理）"

    backup = backup_key(path)
    note = "（已备份 %s）" % os.path.basename(backup) if backup else ""

    try:
        p = subprocess.run(["reg", "delete", path, "/f"], capture_output=True,
                           timeout=20, creationflags=0x08000000)
        if p.returncode == 0:
            return True, "已删除" + note
        out = ((p.stdout or b"") + (p.stderr or b"")).decode("gbk", errors="ignore")
        if "找不到" in out or "unable to find" in out.lower():
            return True, "注册表项已不存在（无需清理）"
    except Exception as exc:
        return False, str(exc)

    hkey, sub = _split_raw(path)
    for view in _views(sub):
        if _native_delete(hkey, sub, view):
            return True, "已接管权限后删除" + note

    if _is_protected_now():
        _mark_protected(path)
        return False, _protected_message()
    return False, "权限接管后仍被拒绝（该键可能由系统策略或第三方驱动保护）"


def delete_value(path, name):
    hkey, sub = split_key(path)
    for view in _views(sub):
        try:
            with winreg.OpenKey(hkey, sub, 0,
                                winreg.KEY_READ | winreg.KEY_SET_VALUE | view) as k:
                try:
                    winreg.QueryValueEx(k, name)
                except OSError:
                    continue
                winreg.DeleteValue(k, name)
                return True, "已删除启动项"
        except OSError:
            continue

    raw_hkey, raw_sub = _split_raw(path)
    _enable_privileges("SeTakeOwnershipPrivilege", "SeRestorePrivilege")
    for view in _views(raw_sub):
        if not _open_raw(raw_hkey, raw_sub, KEY_READ, view):
            continue
        _harden_key(raw_hkey, raw_sub, view)
        try:
            with winreg.OpenKey(hkey, sub, 0,
                                winreg.KEY_READ | winreg.KEY_SET_VALUE | view) as k:
                winreg.DeleteValue(k, name)
                return True, "已接管权限后删除启动项"
        except OSError:
            continue
    return True, "启动项已不存在"


def build_safe_mode_pack(paths):
    """生成安全模式清理脚本，返回 .cmd 路径。安全模式不加载 360 自保护驱动。"""
    paths = [p for p in dict.fromkeys(paths) if p]
    if not paths:
        return ""
    os.makedirs(SAFE_MODE_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    cmd_path = os.path.join(SAFE_MODE_DIR, "安全模式清理_%s.cmd" % stamp)
    txt_path = os.path.join(SAFE_MODE_DIR, "待清理清单_%s.txt" % stamp)

    lines = ["@echo off", "chcp 65001 >nul",
             "title 残留清理卫士 - 安全模式清理",
             "echo 正在删除 360 残留注册表项（仅删除下列清单中的项目）...", "echo."]
    for path in paths:
        lines.append('reg delete "%s" /f >nul 2>&1' % path)
        lines.append("echo   已处理 %s" % path)
    lines += ["echo.", "echo 清理完成。按任意键退出。", "pause >nul", ""]

    with open(cmd_path, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write("\r\n".join(lines))
    with open(txt_path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("以下注册表项因 360 自我保护在线无法删除，需在安全模式清理：\r\n\r\n")
        for path in paths:
            f.write(path + "\r\n")
        f.write("\r\n使用方法：重启 → 开机时按住 Shift 或 msconfig 选择安全模式 → ")
        f.write("以管理员身份运行同目录下的 .cmd 文件。\r\n")
    return cmd_path
