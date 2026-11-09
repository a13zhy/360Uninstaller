"""强力删除引擎：解锁占用 → 清理属性 → 接管所有权 → 递归删除 → 重启后兜底

处理“无权访问 / 文件正在使用 / 路径过长 / 系统属性锁死”这几类常规删除搞不定的
目录，全部基于系统自带 API 与命令，不依赖第三方工具：

1. Restart Manager（rstrtmgr.dll）枚举占用句柄的进程，只结束 360 自己的进程，
   其他占用者只报告不杀，避免误伤用户正在用的程序。
2. 属性清理：SetFileAttributesW 把只读/系统/隐藏重置为 NORMAL。
3. 所有权：icacls /reset 去掉拒绝项 → /inheritance:e 恢复继承 →
   takeown /a 交给 Administrators → icacls 授予完全控制。
4. 长路径：超过 240 字符自动加 \\\\?\\ 前缀，绕过 260 限制。
5. 兜底：仍旧被占用的文件用 MoveFileExW(MOVEFILE_DELAY_UNTIL_REBOOT)
   登记到 PendingFileRenameOperations，下次开机由系统删除。
"""

import ctypes
import ctypes.wintypes as wt
import os
import subprocess

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
FILE_ATTRIBUTE_NORMAL = 0x80
MOVEFILE_DELAY_UNTIL_REBOOT = 0x4
ERROR_FILE_NOT_FOUND = 2
ERROR_PATH_NOT_FOUND = 3
ERROR_ACCESS_DENIED = 5
ERROR_SHARING_VIOLATION = 32
ERROR_LOCK_VIOLATION = 33
ERROR_DELETE_PENDING = 303

PENDING_REG_PATH = r"SYSTEM\CurrentControlSet\Control\Session Manager"
PENDING_VALUE = "PendingFileRenameOperations"


# ------------------------------------------------------------------ 基础工具
def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def nt_path(path: str) -> str:
    """返回 \\\\?\\ 前缀的绝对路径，规避 MAX_PATH 限制。"""
    path = os.path.abspath(path)
    if path.startswith("\\\\?\\"):
        return path
    if path.startswith("\\\\"):
        return "\\\\?\\UNC\\" + path.lstrip("\\")
    return "\\\\?\\" + path


def _last_error() -> int:
    return ctypes.get_last_error() if hasattr(ctypes, "get_last_error") else 0


def clear_attributes(path: str) -> bool:
    """把 只读/系统/隐藏/存档 等属性全部清掉。"""
    try:
        ok = ctypes.windll.kernel32.SetFileAttributesW(nt_path(path),
                                                       FILE_ATTRIBUTE_NORMAL)
        return bool(ok)
    except Exception:
        return False


def _run(cmd: list[str], timeout: int = 180) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout,
                           creationflags=CREATE_NO_WINDOW)
        out = (p.stdout or b"").decode("gbk", errors="ignore") + (
            p.stderr or b"").decode("gbk", errors="ignore")
        return p.returncode, out.strip()
    except Exception as exc:
        return 1, str(exc)


# ------------------------------------------------------------------ 占用解锁
class _RM_UNIQUE_PROCESS(ctypes.Structure):
    _fields_ = [("dwProcessId", wt.DWORD),
                ("ProcessStartTime", wt.FILETIME)]


class _RM_PROCESS_INFO(ctypes.Structure):
    # 实测 Windows 上该结构步长为 668 字节，末尾补一个 DWORD 对齐，
    # 否则 RmGetList 写入越界会破坏堆。
    _fields_ = [
        ("Process", _RM_UNIQUE_PROCESS),
        ("strAppName", wt.WCHAR * 256),
        ("strServiceShortName", wt.WCHAR * 64),
        ("ApplicationType", ctypes.c_int),
        ("AppStatus", ctypes.c_ulong),
        ("bRestartable", ctypes.c_ulong),
        ("_tail", ctypes.c_ulong),
    ]


def _holder_targets(path: str, limit: int = 300) -> list[str]:
    """Restart Manager 只认文件，目录要展开成里面的文件再登记。"""
    if not os.path.isdir(path):
        return [path]
    targets: list[str] = []
    for root, _dirs, files in os.walk(path, topdown=True, onerror=lambda e: None):
        for name in files:
            targets.append(os.path.join(root, name))
            if len(targets) >= limit:
                return targets
    return targets


def _process_image(pid: int) -> str:
    """取进程可执行文件路径，失败返回空串。"""
    handle = None
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            return ""
        buf = ctypes.create_unicode_buffer(1024)
        size = wt.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    except Exception:
        return ""
    finally:
        if handle:
            try:
                ctypes.windll.kernel32.CloseHandle(handle)
            except Exception:
                pass


def find_holders(path: str) -> list[tuple[int, str]]:
    """用 Restart Manager 找出正在占用 path 的进程，返回 [(pid, 映像路径)]。"""
    try:
        rstrtmgr = ctypes.WinDLL("rstrtmgr.dll")
    except Exception:
        return []

    RmStartSession = rstrtmgr.RmStartSession
    RmRegisterResources = rstrtmgr.RmRegisterResources
    RmGetList = rstrtmgr.RmGetList
    RmEndSession = rstrtmgr.RmEndSession

    session = ctypes.c_ulong(0)
    key = ctypes.create_unicode_buffer(256)
    handles: list[int] = []
    targets = _holder_targets(path)
    if not targets:
        return []
    try:
        if RmStartSession(ctypes.byref(session), 0, key) != 0:
            return []
        handles.append(session.value)
        files = (wt.LPCWSTR * len(targets))(*targets)
        if RmRegisterResources(session.value, len(targets), files, 0, None, 0, None) != 0:
            return []
        needed = wt.DWORD(0)
        count = wt.DWORD(0)
        reasons = wt.DWORD(0)
        rc = RmGetList(session.value, ctypes.byref(needed),
                       ctypes.byref(count), None, ctypes.byref(reasons))
        if rc != 234 or needed.value == 0:  # ERROR_MORE_DATA
            return []
        buf = (_RM_PROCESS_INFO * needed.value)()
        count.value = needed.value
        rc = RmGetList(session.value, ctypes.byref(needed),
                       ctypes.byref(count), buf, ctypes.byref(reasons))
        if rc != 0:
            return []
        result = []
        for i in range(count.value):
            pid = int(buf[i].Process.dwProcessId)
            if pid <= 0:
                continue
            name = buf[i].strAppName or _process_image(pid)
            result.append((pid, name))
        return result
    except Exception:
        return []
    finally:
        for h in handles:
            try:
                RmEndSession(h)
            except Exception:
                pass


def release_holders(path: str, log=None) -> tuple[list[int], list[str]]:
    """结束占用 path 的 360 进程，返回 (已结束 pid, 其他占用者名称)。"""
    killed: list[int] = []
    others: list[str] = []
    for pid, name in find_holders(path):
        image = _process_image(pid) or name
        low = image.lower()
        is_360 = "360" in low or "qhsafe" in low or "qihu" in low
        if not is_360:
            others.append(os.path.basename(image) or f"PID {pid}")
            continue
        handle = None
        try:
            handle = ctypes.windll.kernel32.OpenProcess(0x0001, False, pid)
            if handle:
                ctypes.windll.kernel32.TerminateProcess(handle, 1)
        except Exception:
            pass
        finally:
            if handle:
                try:
                    ctypes.windll.kernel32.CloseHandle(handle)
                except Exception:
                    pass
        _run(["taskkill", "/F", "/PID", str(pid), "/T"], timeout=20)
        killed.append(pid)
        if log:
            log(f"  结束占用进程 {os.path.basename(image) or pid}（PID {pid}）")
    return killed, others


# ------------------------------------------------------------------ 所有权
def take_ownership(path: str, log=None) -> str:
    """重置并接管 ACL：去拒绝项 → 恢复继承 → 管理员组持所有权与完全控制。"""
    p = nt_path(path)
    steps = [
        (["icacls", p, "/reset", "/t", "/c", "/q"], "重置访问控制列表"),
        (["icacls", p, "/inheritance:e", "/t", "/c", "/q"], "恢复权限继承"),
        (["icacls", p, "/setowner", "*S-1-5-32-544", "/t", "/c", "/q"], "设置所有者为管理员组"),
        (["takeown", "/f", p, "/r", "/a", "/d", "y"], "接管文件所有权"),
        (["icacls", p, "/grant", "*S-1-5-32-544:(OI)(CI)F", "/t", "/c", "/q"],
         "授予管理员组完全控制"),
    ]
    for cmd, label in steps:
        rc, out = _run(cmd)
        if log:
            ok = "完成" if rc == 0 else "跳过"
            log(f"  {label}：{ok}")
        if rc != 0 and "拒绝" in out and "denied" in out.lower():
            # 权限都被拒绝时后续步骤也可能失败，交给下一轮处理
            continue
    return "已接管所有权"


# ------------------------------------------------------------------ 删除执行
def delete_tree(root: str, failed: list[str], freed: list[int]) -> bool:
    """自底向上删除目录树，删不掉的具体路径收进 failed。返回 root 是否已消失。"""

    def _walk(d: str) -> None:
        try:
            entries = list(os.scandir(d))
        except OSError:
            if not os.path.exists(d):
                return
            failed.append(d)
            return
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    _walk(entry.path)
                    continue
                try:
                    size = entry.stat(follow_symlinks=False).st_size
                except OSError:
                    size = 0
                clear_attributes(entry.path)
                os.remove(entry.path)
                freed[0] += max(0, size)
            except OSError:
                # 目录联接（junction）用 remove 会失败，退回 rmdir
                try:
                    clear_attributes(entry.path)
                    os.rmdir(entry.path)
                except OSError:
                    failed.append(entry.path)
        try:
            clear_attributes(d)
            os.rmdir(d)
        except OSError:
            if os.path.exists(d):
                failed.append(d)

    _walk(root)
    return not os.path.exists(root)


def schedule_delete_on_reboot(paths: list[str], log=None) -> tuple[int, bool]:
    """把剩余项登记为下次开机删除，返回 (登记数量, 是否成功)，自底向上登记。"""
    if not is_admin():
        if log:
            log("  当前不是管理员，无法登记重启后删除")
        return 0, False
    ordered: list[str] = []
    for p in paths:
        if os.path.isdir(p) and not os.path.islink(p):
            for root, dirs, files in os.walk(p, topdown=False,
                                            onerror=lambda e: None):
                ordered.extend(os.path.join(root, f) for f in files)
                ordered.append(root)
        else:
            ordered.append(p)
    seen = set()
    count = 0
    any_ok = False
    for p in ordered:
        key = os.path.normcase(p)
        if key in seen:
            continue
        seen.add(key)
        try:
            ok = ctypes.windll.kernel32.MoveFileExW(
                nt_path(p), None, MOVEFILE_DELAY_UNTIL_REBOOT)
        except Exception:
            ok = 0
        if ok:
            count += 1
            any_ok = True
    if any_ok and log:
        log(f"  已登记 {count} 项在下次开机时由系统删除")
    return count, any_ok


def pending_delete_entries() -> list[str]:
    """读取 PendingFileRenameOperations，返回已登记的重启删除路径。"""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, PENDING_REG_PATH) as k:
            values, _typ = winreg.QueryValueEx(k, PENDING_VALUE)
    except Exception:
        return []
    out = []
    if isinstance(values, (list, tuple)):
        seq = list(values)
        for i in range(0, len(seq), 2):
            if i + 1 < len(seq) and not seq[i + 1]:
                out.append(seq[i].lstrip("\\?\\"))
    return out


def _error_text(exc: OSError) -> str:
    code = getattr(exc, "winerror", None) or getattr(exc, "errno", 0)
    if code == ERROR_ACCESS_DENIED:
        return "拒绝访问（ACL 或系统保护）"
    if code in (ERROR_SHARING_VIOLATION, ERROR_LOCK_VIOLATION):
        return "文件正在使用"
    if code == ERROR_DELETE_PENDING:
        return "已标记删除，等待句柄释放"
    if code == 13:
        return "拒绝访问或被程序占用"
    return f"错误码 {code}" if code else "删除失败"
