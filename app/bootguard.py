"""开机巡检登记（计划任务优先，Run 兜底）

为什么用计划任务：程序带 uac-admin 清单，直接写 HKCU Run 会让每次开机都弹 UAC。
用 `schtasks /rl HIGHEST` 登记一条登录触发的任务，开机就能以管理员身份静默启动，
不会每次都让用户点“是”。计划任务不可用时退回 HKCU Run（此时会弹 UAC，但功能可用）。

只在用户明确点“是”之后写入，随时可撤销，不注册系统服务、不常驻后台进程。
"""

import os
import subprocess
import sys

from . import constants

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
TASK_NAME = constants.BOOT_PATROL_VALUE


def _command() -> str:
    """返回写进启动项的完整命令行（带 --boot-scan）。"""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" {constants.BOOT_PATROL_ARG}'
    script = os.path.abspath(sys.argv[0])
    if not script.lower().endswith(".py"):
        script = os.path.abspath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "main.py"))
    return f'"{sys.executable}" "{script}" {constants.BOOT_PATROL_ARG}'


def _run(cmd: list[str], timeout: int = 25) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout,
                              creationflags=CREATE_NO_WINDOW)
        out = (proc.stdout or b"").decode("gbk", errors="ignore") + (
            proc.stderr or b"").decode("gbk", errors="ignore")
        return proc.returncode, out.strip()
    except Exception as exc:
        return 1, str(exc)


# ---------------------------------------------------------------- 计划任务
def task_exists() -> bool:
    rc, _ = _run(["schtasks", "/query", "/tn", TASK_NAME])
    return rc == 0


def _create_task() -> tuple[bool, str]:
    cmd = _command()
    base = ["schtasks", "/create", "/tn", TASK_NAME, "/tr", cmd,
            "/sc", "onlogon", "/rl", "HIGHEST", "/f"]
    # 延迟 20 秒，避开登录瞬间的磁盘与网络抢跑；不支持延迟时退回不带 /delay
    rc, out = _run(base[:6] + ["/delay", "0000:20"] + base[6:])
    if rc != 0:
        rc, out = _run(base)
    if rc == 0:
        return True, "已登记计划任务：下次登录后自动以管理员身份启动巡检窗口"
    return False, out or f"schtasks 返回 {rc}"


def _delete_task() -> tuple[bool, str]:
    if not task_exists():
        return True, "计划任务本来就不存在"
    rc, out = _run(["schtasks", "/delete", "/tn", TASK_NAME, "/f"])
    return rc == 0, "已删除开机巡检计划任务" if rc == 0 else (out or f"返回 {rc}")


# ---------------------------------------------------------------- HKCU Run
def _split() -> tuple[str, str]:
    path = constants.BOOT_PATROL_KEY
    root, sub = path.split("\\", 1)
    return root, sub


def _hive(name: str):
    import winreg

    return {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}[name]


def _run_value_exists() -> bool:
    try:
        import winreg

        root, sub = _split()
        with winreg.OpenKey(_hive(root), sub, 0, winreg.KEY_READ) as key:
            value, _type = winreg.QueryValueEx(key, constants.BOOT_PATROL_VALUE)
        return bool(str(value).strip())
    except Exception:
        return False


def _write_run(enable: bool) -> tuple[bool, str]:
    try:
        import winreg

        root, sub = _split()
        with winreg.OpenKey(_hive(root), sub, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                winreg.SetValueEx(key, constants.BOOT_PATROL_VALUE, 0,
                                  winreg.REG_SZ, _command())
                return True, "已登记注册表启动项（开机时可能弹一次 UAC）"
            winreg.DeleteValue(key, constants.BOOT_PATROL_VALUE)
            return True, "已移除注册表启动项"
    except FileNotFoundError:
        return True, "注册表启动项本来就不存在"
    except Exception as exc:
        return False, f"注册表启动项写入失败：{exc}"


# ---------------------------------------------------------------- 对外接口
def is_enabled() -> bool:
    return task_exists() or _run_value_exists()


def enable() -> tuple[bool, str]:
    """登记开机巡检。优先计划任务，失败再写 Run。"""
    ok, msg = _create_task()
    if ok:
        return ok, msg
    ok_run, msg_run = _write_run(True)
    if ok_run:
        return True, f"计划任务不可用（{msg}），已改用注册表启动项"
    return False, f"{msg}；{msg_run}"


def disable() -> tuple[bool, str]:
    """撤销开机巡检，两条通道一起清。"""
    notes = []
    ok_task, msg_task = _delete_task()
    notes.append(msg_task)
    ok_run, msg_run = _write_run(False)
    notes.append(msg_run)
    return (ok_task or ok_run), "；".join(notes)


def sync_state(enabled: bool) -> tuple[bool, str]:
    if enabled:
        return enable()
    return disable()


def state_text() -> str:
    return "开机巡检：已开启" if is_enabled() else "开机巡检：未开启"
