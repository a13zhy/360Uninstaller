"""系统动作：只封装“用户点了是”之后才会调用的重启安排。

不做自动重启、不做定时循环；延迟只为给用户留出取消的时间窗口。
"""

import os
import subprocess

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def schedule_reboot(delay_seconds: int = 20) -> tuple[bool, str]:
    """安排一次延迟重启，返回 (是否成功, 说明)。"""
    delay = max(5, min(120, int(delay_seconds)))
    try:
        proc = subprocess.run(
            ["shutdown", "/r", "/t", str(delay),
             "/c", "残留清理卫士：清理已完成，系统将在倒计时结束后重启"],
            capture_output=True, timeout=20, creationflags=CREATE_NO_WINDOW,
        )
        if proc.returncode == 0:
            return True, f"已安排在 {delay} 秒后重启"
        text = (proc.stderr or proc.stdout or b"").decode("gbk", errors="ignore").strip()
        return False, text or f"重启命令返回 {proc.returncode}"
    except Exception as exc:
        return False, str(exc)


def cancel_reboot() -> tuple[bool, str]:
    """取消已经安排的倒计时重启。"""
    try:
        proc = subprocess.run(["shutdown", "/a"], capture_output=True, timeout=15,
                              creationflags=CREATE_NO_WINDOW)
        return proc.returncode == 0, "已取消重启" if proc.returncode == 0 else "没有待取消的重启"
    except Exception as exc:
        return False, str(exc)
