"""文件 / 目录删除与强力删除（解锁占用 + 接管所有权 + 重启后兜底）"""

import os
import shutil
import stat
import subprocess

from . import force_remove

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _run(cmd: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout,
                           creationflags=CREATE_NO_WINDOW)
        out = (p.stdout or b"").decode("gbk", errors="ignore") + (
            p.stderr or b"").decode("gbk", errors="ignore")
        return p.returncode, out.strip()
    except Exception as exc:
        return 1, str(exc)


def human_size(num: float) -> str:
    if num < 1024:
        return f"{int(num)} B"
    for unit in ("KB", "MB", "GB", "TB"):
        num /= 1024.0
        if num < 1024:
            return f"{num:.1f} {unit}"
    return f"{num:.1f} PB"


def path_size(path: str, limit_files: int = 20000) -> int:
    """统计目录/文件占用字节数（有上限，避免卡死）。"""
    try:
        if os.path.isfile(path):
            return os.path.getsize(path)
    except OSError:
        return 0
    total = 0
    count = 0
    for root, dirs, files in os.walk(path, topdown=True, onerror=lambda e: None):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
            count += 1
            if count > limit_files:
                return total
    return total


def _on_rm_error(func, path, exc_info):
    """shutil.rmtree 回调：去掉只读属性后重试。"""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def _try_plain_delete(path: str, freed_box: list, failed: list) -> bool:
    """第一轮常规删除（长路径已由 force_remove 统一处理）。"""
    try:
        if os.path.isdir(path) and not os.path.islink(path):
            force_remove.delete_tree(path, failed, freed_box)
        else:
            try:
                os.chmod(path, stat.S_IWRITE)
            except OSError:
                pass
            force_remove.clear_attributes(path)
            os.remove(path)
    except Exception as exc:
        failed.append(path)
        if isinstance(exc, OSError):
            failed.append(force_remove._error_text(exc))
    return not os.path.lexists(path)


def remove_path(path: str, force: bool = True, log=None) -> tuple[bool, str, int, int]:
    """删除文件或目录，返回 (成功, 说明, 释放字节, 已登记重启后删除项数)。

    三轮执行：
      1. 常规删除（先清只读/系统/隐藏属性，长路径自动加 \\\\?\\ 前缀）
      2. 结束 360 占用进程 → icacls 重置/接管所有权 → 再删
      3. 仍被锁住的项逐项登记 PendingFileRenameOperations，下次开机删除
    """
    path = (path or "").strip().strip('"')
    if not path:
        return False, "路径为空", 0, 0
    path = os.path.abspath(os.path.expandvars(path))
    if not os.path.lexists(path):
        return True, "已不存在", 0, 0

    freed_box = [0]
    failed: list[str] = []

    # 第一轮：常规删除
    if _try_plain_delete(path, freed_box, failed):
        return True, "已删除", freed_box[0], 0

    if not force:
        detail = "；".join(x for x in failed if x and x != path)[:120] or "文件正在使用"
        return False, detail, 0, 0

    notes: list[str] = []

    # 第二轮：解除占用 + 接管所有权
    killed, others = force_remove.release_holders(path, log)
    if killed:
        notes.append(f"结束 {len(killed)} 个 360 占用进程")
    if others:
        notes.append("当前被 " + "、".join(sorted(set(others))[:3]) + " 占用")

    if log:
        log("  接管所有权（icacls 重置 + takeown）")
    force_remove.take_ownership(path, log)

    failed.clear()
    if _try_plain_delete(path, freed_box, failed) or not os.path.lexists(path):
        detail = "强力删除完成（已接管所有权）"
        if notes:
            detail += "，" + "，".join(notes)
        return True, detail, freed_box[0], 0

    # 第三轮：剩余项登记重启后删除
    remaining = [p for p in failed if p and os.path.lexists(p)]
    if os.path.lexists(path):
        remaining.append(path)
    pending, scheduled = force_remove.schedule_delete_on_reboot(remaining, log)

    if scheduled:
        detail = f"尚有 {pending} 项被占用，已登记下次开机时删除"
        if notes:
            detail = "，".join(notes) + "，" + detail
        return True, detail, freed_box[0], pending

    # 既没删掉也登记不了：给出可核实的原因
    reason = "文件正在使用或被系统保护"
    for item in failed:
        if os.path.lexists(item):
            try:
                with open(item, "ab"):
                    pass
            except OSError as exc:
                reason = force_remove._error_text(exc)
                break
    detail = "，".join(notes + [reason]) if notes else reason
    if not force_remove.is_admin():
        detail += "（当前不是管理员，接管所有权与重启删除需要管理员权限）"
    return False, detail[:200], freed_box[0], 0


def remove_shortcut(path: str) -> tuple[bool, str, int]:
    res = remove_path(path, force=False)
    return res[0], res[1], res[2]
