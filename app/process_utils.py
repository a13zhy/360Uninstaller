"""进程 / 服务 / 计划任务操作（全部基于系统命令，无第三方依赖）"""

import csv
import io
import os
import subprocess

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _run(cmd: list[str], timeout: int = 25) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
        out = (p.stdout or b"").decode("gbk", errors="ignore")
        err = (p.stderr or b"").decode("gbk", errors="ignore")
        return p.returncode, (out + err).strip()
    except subprocess.TimeoutExpired:
        return 1, "命令执行超时"
    except Exception as exc:  # pragma: no cover
        return 1, str(exc)


def list_processes() -> list[tuple[str, str]]:
    """返回 [(进程名小写, PID)]。"""
    rc, out = _run(["tasklist", "/fo", "csv", "/nh"])
    if rc != 0 or not out:
        return []
    rows = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parts = next(csv.reader(io.StringIO(line)))
        except Exception:
            continue
        if len(parts) < 2:
            continue
        rows.append((parts[0].strip().lower(), parts[1].strip()))
    return rows


def kill_process(name: str) -> tuple[bool, str]:
    rc, out = _run(["taskkill", "/F", "/IM", name, "/T"])
    if rc == 0:
        return True, f"已结束进程 {name}"
    if "not found" in out.lower() or "找不到" in out or "没有运行" in out:
        return True, f"进程 {name} 未运行"
    return False, out or f"结束进程 {name} 失败"


def kill_pid(pid: str) -> tuple[bool, str]:
    rc, out = _run(["taskkill", "/F", "/PID", str(pid), "/T"])
    return rc == 0, out or (f"已结束 PID {pid}" if rc == 0 else "结束失败")


def list_services() -> list[str]:
    rc, out = _run(["sc", "query", "type=", "service", "state=", "all"])
    if rc != 0:
        return []
    names = []
    for line in out.splitlines():
        line = line.strip()
        if line.upper().startswith("SERVICE_NAME:"):
            names.append(line.split(":", 1)[1].strip())
    return names


def stop_service(name: str) -> tuple[bool, str]:
    rc, out = _run(["sc", "stop", name])
    if rc == 0:
        return True, f"已停止服务 {name}"
    if "1060" in out or "1062" in out:
        return True, f"服务 {name} 不存在或未运行"
    return False, out or f"停止服务 {name} 失败"


def delete_service(name: str) -> tuple[bool, str]:
    rc, out = _run(["sc", "delete", name])
    if rc == 0:
        return True, f"已删除服务 {name}"
    if "1060" in out or "1072" in out:
        return True, f"服务 {name} 已不存在"
    return False, out or f"删除服务 {name} 失败"


def list_tasks() -> list[str]:
    rc, out = _run(["schtasks", "/query", "/fo", "csv", "/nh"])
    if rc != 0 or not out:
        return []
    tasks = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parts = next(csv.reader(io.StringIO(line)))
        except Exception:
            continue
        if parts and parts[0].strip() and parts[0].strip() != "TaskName":
            tasks.append(parts[0].strip().lstrip("\\"))
    return tasks


def delete_task(name: str) -> tuple[bool, str]:
    rc, out = _run(["schtasks", "/delete", "/f", "/tn", name])
    if rc == 0:
        return True, f"已删除计划任务 {name}"
    if "找不到" in out or "cannot find" in out.lower():
        return True, f"计划任务 {name} 不存在"
    return False, out or f"删除计划任务 {name} 失败"
