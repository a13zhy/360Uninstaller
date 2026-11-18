"""本机安装检测：只把真实装过的 360 系软件摆到界面上

判定依据（命中任意一条即认为已安装）：
    进程正在运行 / 安装目录存在 / 注册表键存在 / 卸载项已登记 / 服务已注册
同时给出证据文本，让用户知道“凭什么说它装了”。
"""

import os
from dataclasses import dataclass, field

from . import cleanup, constants, process_utils, registry_utils


@dataclass
class Detected:
    key: str
    name: str
    desc: str
    app: dict
    evidence: list[str] = field(default_factory=list)
    dirs: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    size: int = 0
    running: bool = False

    @property
    def installed(self) -> bool:
        return bool(self.evidence)

    @property
    def size_text(self) -> str:
        return cleanup.human_size(self.size) if self.size else "待统计"

    def detail_text(self, limit: int = 2) -> str:
        if not self.evidence:
            return "未检测到"
        parts = self.evidence[:limit]
        return " · ".join(parts)


def _norm(text: str) -> str:
    return str(text or "").lower().replace(" ", "").replace("　", "")


class Detector:
    def __init__(self):
        self._procs: dict[str, str] | None = None
        self._services: list[str] | None = None
        self._entries: list[dict] | None = None

    # ------------------------------------------------------------ 系统快照
    @property
    def procs(self) -> dict[str, str]:
        if self._procs is None:
            try:
                self._procs = {n.lower(): p for n, p in process_utils.list_processes()}
            except Exception:
                self._procs = {}
        return self._procs

    @property
    def services(self) -> list[str]:
        if self._services is None:
            try:
                self._services = [s.lower() for s in process_utils.list_services()]
            except Exception:
                self._services = []
        return self._services

    @property
    def entries(self) -> list[dict]:
        if self._entries is None:
            try:
                from .scanner import Scanner
                self._entries = Scanner().uninstall_entries()
            except Exception:
                self._entries = []
        return self._entries

    # ------------------------------------------------------------ 检测
    def _check(self, app: dict) -> Detected:
        found = Detected(key=app["key"], name=app["name"], desc=app["desc"], app=app)

        procs = self.procs
        for name in app["processes"]:
            if name.lower() in procs:
                found.running = True
                found.evidence.append(f"进程 · {name}")
                break

        for d in app["dirs"]:
            if d and os.path.isdir(constants.expand(d)):
                real = constants.expand(d)
                found.dirs.append(real)
                found.evidence.append(f"目录 · {real}")

        for r in app["regs"]:
            if registry_utils.key_exists(r):
                found.evidence.append(f"注册表 · {r}")

        svc_hits = []
        for svc in app["services"]:
            low = svc.lower()
            for real in self.services:
                if real == low or real.startswith(low):
                    svc_hits.append(real)
        if svc_hits:
            found.services = svc_hits
            found.evidence.append(f"服务 · {svc_hits[0]}")

        key_tokens = [t for t in (_norm(app["name"]), _norm(app["key"])) if t]
        for entry in self.entries:
            name = _norm(entry.get("name", ""))
            if not name:
                continue
            if any(t and t in name for t in key_tokens) or (
                    app["key"].replace("360", "") and
                    app["key"].replace("360", "") in name):
                found.evidence.append(f"安装登记 · {entry.get('name', '')}")
                loc = entry.get("install_location") or ""
                if loc and os.path.isdir(loc) and loc not in found.dirs:
                    found.dirs.append(loc)
                break

        return found

    def detect(self, measure: bool = True) -> list[Detected]:
        """返回本机真实安装的 360 系软件，按定义顺序排列。"""
        out: list[Detected] = []
        for app in constants.APPS:
            found = self._check(app)
            if not found.installed:
                continue
            if measure:
                found.size = self.measure(found)
            out.append(found)
        return out

    def measure(self, found: Detected) -> int:
        total = 0
        for d in found.dirs:
            try:
                total += cleanup.path_size(d, limit_files=3000)
            except Exception:
                continue
        return total

    def scan_items(self, found: Detected):
        """把某一款应用的清理项交给扫描器枚举（进程/服务/目录/注册表）。"""
        from .scanner import Scanner
        return Scanner().scan_app(found.app)

    def summary(self, found_list: list[Detected]) -> dict:
        return {
            "apps": len(found_list),
            "size": sum(f.size for f in found_list),
            "running": sum(1 for f in found_list if f.running),
            "services": sum(len(f.services) for f in found_list),
        }
