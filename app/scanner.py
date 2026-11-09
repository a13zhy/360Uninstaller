"""扫描器：应用检测、清理项枚举、卸载后残留扫描、深度扫描"""

import os
from dataclasses import dataclass, field

from . import cleanup, process_utils, registry_utils
from . import constants


@dataclass
class Item:
    kind: str
    target: str
    label: str
    app_key: str = ""
    app_name: str = ""
    size: int = 0
    extra: dict = field(default_factory=dict)

    @property
    def kind_label(self) -> str:
        return constants.KIND_LABELS.get(self.kind, self.kind)

    @property
    def size_text(self) -> str:
        return cleanup.human_size(self.size) if self.size else "-"

    def to_dict(self) -> dict:
        return {
            "kind": self.kind, "target": self.target, "label": self.label,
            "app_key": self.app_key, "app_name": self.app_name,
            "size": self.size, "size_text": self.size_text,
        }


def _kw_hit(text: str, keywords: list[str]) -> bool:
    low = text.lower()
    return any(k.lower() in low for k in keywords)


class Scanner:
    """一次扫描会话内缓存进程/服务/任务列表，避免重复调用系统命令。"""

    def __init__(self):
        self._procs = None
        self._services = None
        self._tasks = None
        self._installed_cache = {}

    # ------------------------------------------------------------ 系统快照
    @property
    def procs(self) -> list[tuple[str, str]]:
        if self._procs is None:
            self._procs = process_utils.list_processes()
        return self._procs

    @property
    def services(self) -> list[str]:
        if self._services is None:
            self._services = process_utils.list_services()
        return self._services

    @property
    def tasks(self) -> list[str]:
        if self._tasks is None:
            self._tasks = process_utils.list_tasks()
        return self._tasks

    # ------------------------------------------------------------ 安装检测
    def uninstall_entries(self) -> list[dict]:
        """从 Uninstall 注册表键读取已安装程序信息。"""
        entries = []
        for root in constants.UNINSTALL_KEYS:
            for sub in registry_utils.list_subkeys(root):
                path = f"{root}\\{sub}"
                vals = registry_utils.read_values(path)
                name = str(vals.get("DisplayName", "") or "")
                if not name:
                    continue
                if not _kw_hit(name, ["360", "奇虎", "qihu", "qhsafe"]):
                    continue
                entries.append({
                    "key": sub,
                    "reg_path": path,
                    "name": name,
                    "version": str(vals.get("DisplayVersion", "") or ""),
                    "publisher": str(vals.get("Publisher", "") or ""),
                    "install_location": str(vals.get("InstallLocation", "") or ""),
                    "uninstall_string": str(vals.get("UninstallString", "") or ""),
                    "size_kb": vals.get("EstimatedSize", 0) or 0,
                })
        return entries

    def app_installed(self, app: dict) -> tuple[bool, str]:
        """返回 (是否安装, 说明)。"""
        key = app["key"]
        if key in self._installed_cache:
            return self._installed_cache[key]

        procs = {n for n, _ in self.procs}
        if any(p in procs for p in app["processes"]):
            self._installed_cache[key] = (True, "正在运行")
            return self._installed_cache[key]

        for d in app["dirs"]:
            if d and os.path.isdir(d):
                self._installed_cache[key] = (True, "安装目录存在")
                return self._installed_cache[key]

        for r in app["regs"]:
            if registry_utils.key_exists(r):
                self._installed_cache[key] = (True, "注册表项存在")
                return self._installed_cache[key]

        for e in self.uninstall_entries():
            if _kw_hit(e["name"], [app["name"].replace(" ", ""), app["key"].replace("360", "")]):
                self._installed_cache[key] = (True, "已注册安装信息")
                return self._installed_cache[key]

        self._installed_cache[key] = (False, "")
        return self._installed_cache[key]

    # ------------------------------------------------------------ 应用清理项
    def scan_app(self, app: dict, with_size: bool = True) -> list[Item]:
        items: list[Item] = []
        procs = {n for n, _ in self.procs}

        for p in app["processes"]:
            if p in procs:
                items.append(Item("process", p, p, app["key"], app["name"]))

        for svc in self.services:
            low = svc.lower()
            if any(s in low for s in app["services"]):
                items.append(Item("service", svc, svc, app["key"], app["name"]))

        for d in app["dirs"]:
            if d and os.path.isdir(d):
                size = cleanup.path_size(d) if with_size else 0
                items.append(Item("dir", d, d, app["key"], app["name"], size))

        for r in app["regs"]:
            if registry_utils.key_exists(r):
                items.append(Item("registry", r, r, app["key"], app["name"]))

        for t in self.tasks:
            if any(k.lower() in t.lower() for k in app["tasks"]):
                items.append(Item("task", t, t, app["key"], app["name"]))

        for sc in self._shortcuts():
            if any(k.lower() in os.path.basename(sc).lower() for k in app["shortcuts"]):
                items.append(Item("shortcut", sc, os.path.basename(sc), app["key"], app["name"]))

        return items

    def _shortcuts(self) -> list[str]:
        found = []
        dirs = list(constants.START_MENU_DIRS)
        if constants.DESKTOP:
            dirs.append(constants.DESKTOP)
        for base in dirs:
            if not base or not os.path.isdir(base):
                continue
            base_depth = base.rstrip(os.sep).count(os.sep)
            for root, subdirs, files in os.walk(base, onerror=lambda e: None):
                if root.count(os.sep) - base_depth >= 3:
                    subdirs[:] = []
                for f in files:
                    if f.lower().endswith(".lnk") and _kw_hit(f, ["360"]):
                        found.append(os.path.join(root, f))
        return found

    def scan_all_apps(self, with_size: bool = True) -> tuple[list[Item], dict]:
        """扫描所有 360 应用，返回 (清理项, 应用状态表)。"""
        items: list[Item] = []
        status = {}
        for app in constants.APPS:
            installed, note = self.app_installed(app)
            status[app["key"]] = {"installed": installed, "note": note,
                                  "name": app["name"], "desc": app["desc"]}
            if installed:
                items.extend(self.scan_app(app, with_size=with_size))
        return items, status

    # ------------------------------------------------------------ 全库扫描
    def scan_common(self, with_size: bool = True) -> list[Item]:
        """扫描公共 360 目录、Run 启动项、计划任务。"""
        items: list[Item] = []
        seen = set()

        for d in constants.COMMON_DIRS:
            if d and os.path.isdir(d) and d not in seen:
                seen.add(d)
                size = cleanup.path_size(d) if with_size else 0
                items.append(Item("dir", d, d, "", "360 公共组件", size))

        for run_key in constants.RUN_KEYS:
            for name, value in registry_utils.read_values(run_key).items():
                text = f"{name} {value}"
                if _kw_hit(text, ["360", "qhsafe", "qihu"]):
                    items.append(Item("registry", f"{run_key}::{name}",
                                      f"{name}", "", "360 开机启动项",
                                      extra={"value_name": name}))

        for t in self.tasks:
            if _kw_hit(t, ["360", "qhsafe"]):
                items.append(Item("task", t, t, "", "360 计划任务"))

        return items

    # ------------------------------------------------------------ 深度扫盘
    def deep_scan(self, keywords: list[str] | None = None,
                  limit: int = 300,
                  progress=None) -> list[Item]:
        """受控范围的磁盘扫描：只进入常见安装/数据目录，排除系统关键目录。"""
        keywords = keywords or constants.FILE_KEYWORDS
        excludes = {os.path.normcase(p) for p in constants.SCAN_EXCLUDES if p}
        items: list[Item] = []
        visited = 0
        max_visited = 120000

        roots = [r for r in constants.SCAN_ROOTS if r and os.path.exists(r)]
        # 追加其他盘符根目录下的一级常见目录
        for drive in ("D:\\", "E:\\", "F:\\"):
            if os.path.isdir(drive):
                for name in ("360", "Program Files", "Program Files (x86)"):
                    p = os.path.join(drive, name)
                    if os.path.isdir(p):
                        roots.append(p)

        for base in roots:
            if not base or not os.path.isdir(base):
                continue
            for root, dirs, files in os.walk(base, topdown=True, onerror=lambda e: None):
                # 剪枝：跳过系统目录
                dirs[:] = [d for d in dirs
                           if os.path.normcase(os.path.join(root, d)) not in excludes
                           and not d.startswith("$")]
                visited += 1
                if visited > max_visited:
                    break
                if progress and visited % 200 == 0:
                    progress(f"深度扫描中… {len(items)} 项", len(items))

                for d in dirs:
                    full = os.path.join(root, d)
                    if _kw_hit(d, keywords):
                        size = cleanup.path_size(full)
                        items.append(Item("dir", full, full, "", "深度扫描", size))
                        dirs.remove(d)  # 命中目录不再深入，避免重复列举
                        if len(items) >= limit:
                            return items

                for f in files:
                    if _kw_hit(f, keywords):
                        full = os.path.join(root, f)
                        try:
                            size = os.path.getsize(full)
                        except OSError:
                            size = 0
                        items.append(Item("file", full, full, "", "深度扫描", size))
                        if len(items) >= limit:
                            return items

        return items

    # ------------------------------------------------------------ 残留扫描
    def scan_residual(self, deep: bool = True, progress=None) -> list[Item]:
        """卸载后残留扫描：进程/服务/目录/注册表/任务/快捷方式/深度扫盘。"""
        items: list[Item] = []
        procs = {n for n, _ in self.procs}

        for app in constants.APPS:
            for p in app["processes"]:
                if p in procs:
                    items.append(Item("process", p, p, app["key"], app["name"]))

        for svc in self.services:
            if _kw_hit(svc, ["360", "qhsafe", "zhudongfangyu"]):
                items.append(Item("service", svc, svc, "", "360 服务"))

        seen = set()
        for d in constants.COMMON_DIRS:
            if d and os.path.isdir(d) and d not in seen:
                seen.add(d)
                size = cleanup.path_size(d)
                items.append(Item("dir", d, d, "", "残留目录", size))

        for root in constants.COMMON_REG_ROOTS:
            for sub in registry_utils.list_subkeys(root):
                if _kw_hit(sub, constants.REG_KEYWORDS):
                    path = f"{root}\\{sub}"
                    items.append(Item("registry", path, path, "", "残留注册表"))

        for run_key in constants.RUN_KEYS:
            for name, value in registry_utils.read_values(run_key).items():
                if _kw_hit(f"{name} {value}", ["360", "qhsafe", "qihu"]):
                    items.append(Item("registry", f"{run_key}::{name}", name,
                                      "", "开机启动项", extra={"value_name": name}))

        for t in self.tasks:
            if _kw_hit(t, ["360", "qhsafe"]):
                items.append(Item("task", t, t, "", "残留任务"))

        for sc in self._shortcuts():
            items.append(Item("shortcut", sc, os.path.basename(sc), "", "残留快捷方式"))

        if deep:
            if progress:
                progress("深度扫描残留文件…", len(items))
            items.extend(self.deep_scan(progress=progress))

        return items

    def installed_summary(self) -> dict:
        total_dir = 0
        total_reg = 0
        installed = 0
        for app in constants.APPS:
            if self.app_installed(app)[0]:
                installed += 1
            for d in app["dirs"]:
                if d and os.path.isdir(d):
                    total_dir += 1
            for r in app["regs"]:
                if registry_utils.key_exists(r):
                    total_reg += 1
        return {"apps": installed, "total_apps": len(constants.APPS),
                "dirs": total_dir, "regs": total_reg}
