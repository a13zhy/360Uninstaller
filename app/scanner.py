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


def merge_items(items: list[Item]) -> list[Item]:
    """按 (类型, 路径) 去重，并丢掉被父目录整体覆盖的子目录项。

    先排目录、再按路径长度排序，父目录一定排在子目录前面，
    这样“删掉整个 360 目录”不会和它里面的子目录重复列出。
    """
    def norm(path: str) -> str:
        return os.path.normcase(str(path).replace("/", "\\"))

    ordered = sorted(items, key=lambda i: (0 if i.kind == "dir" else 1, len(i.target)))
    seen_keys: set[tuple[str, str]] = set()
    kept_dirs: list[str] = []
    result: list[Item] = []

    for item in ordered:
        key = (item.kind, norm(item.target))
        if key in seen_keys:
            continue
        if item.kind == "dir":
            target = norm(item.target).rstrip("\\")
            if any(target.startswith(d + "\\") for d in kept_dirs):
                continue
            kept_dirs.append(target)
        seen_keys.add(key)
        result.append(item)
    return result


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
                for mod in self._modules_in_dir(d):
                    items.append(Item("dll", mod, os.path.basename(mod),
                                      app["key"], app["name"],
                                      self._file_size(mod)))

        for r in app["regs"]:
            if registry_utils.key_exists(r):
                items.append(Item("registry", r, r, app["key"], app["name"]))

        for t in self.tasks:
            if any(k.lower() in t.lower() for k in app["tasks"]):
                items.append(Item("task", t, t, app["key"], app["name"]))

        for sc in self._shortcuts():
            if any(k.lower() in os.path.basename(sc).lower() for k in app["shortcuts"]):
                items.append(Item("shortcut", sc, os.path.basename(sc), app["key"], app["name"]))

        for sc in self._startup_items():
            if any(k.lower() in os.path.basename(sc).lower() for k in app["shortcuts"]) or \
                    _kw_hit(os.path.basename(sc), ["360", "qhsafe"]):
                items.append(Item("startup", sc, os.path.basename(sc),
                                  app["key"], app["name"], self._file_size(sc)))

        return items

    def _file_size(self, path: str) -> int:
        try:
            return os.path.getsize(path)
        except OSError:
            return 0

    def _modules_in_dir(self, folder: str, limit: int = 200) -> list[str]:
        """只扫安装目录顶层，挑出 360 自己的 dll/sys/ocx，不递归也不碰系统目录。"""
        found: list[str] = []
        if not folder or not os.path.isdir(folder):
            return found
        try:
            entries = sorted(os.listdir(folder))
        except OSError:
            return found
        for name in entries:
            low = name.lower()
            if not low.endswith(constants.DLL_EXTS):
                continue
            if _kw_hit(low, constants.DLL_KEYWORDS):
                path = os.path.join(folder, name)
                if os.path.isfile(path):
                    found.append(path)
                    if len(found) >= limit:
                        break
        return found

    def _startup_items(self) -> list[str]:
        """开机启动文件夹里 360 相关的快捷方式 / 脚本。"""
        found: list[str] = []
        for base in constants.STARTUP_DIRS:
            if not base or not os.path.isdir(base):
                continue
            try:
                entries = os.listdir(base)
            except OSError:
                continue
            for name in entries:
                if not name.lower().endswith((".lnk", ".exe", ".bat", ".vbs", ".cmd")):
                    continue
                if _kw_hit(name, ["360", "qhsafe", "qihu"]):
                    found.append(os.path.join(base, name))
        return found

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

        for sc in self._startup_items():
            items.append(Item("startup", sc, os.path.basename(sc),
                              "", "360 开机启动项", self._file_size(sc)))

        for mod in self._driver_modules():
            items.append(Item("dll", mod, os.path.basename(mod),
                              "", "360 驱动残留", self._file_size(mod)))

        return items

    def _driver_modules(self) -> list[str]:
        """系统驱动目录里只挑名字带 360 的 .sys，绝不整目录搬。"""
        found: list[str] = []
        drivers = constants.DRIVER_DIR
        if not drivers or not os.path.isdir(drivers):
            return found
        try:
            entries = os.listdir(drivers)
        except OSError:
            return found
        for name in entries:
            low = name.lower()
            if low.endswith(constants.DLL_EXTS) and _kw_hit(low, constants.DLL_KEYWORDS):
                path = os.path.join(drivers, name)
                if os.path.isfile(path):
                    found.append(path)
        return found

    # ------------------------------------------------------------ 深度扫盘
    def deep_scan(self, keywords: list[str] | None = None,
                  limit: int = 300,
                  progress=None,
                  stop=None) -> list[Item]:
        """受控范围的磁盘扫描：只进入常见安装/数据目录，排除系统关键目录。"""
        keywords = keywords or constants.FILE_KEYWORDS
        excludes = {os.path.normcase(p) for p in constants.SCAN_EXCLUDES if p}
        items: list[Item] = []
        visited = 0
        max_visited = 120000

        roots = [r for r in constants.SCAN_ROOTS if r and os.path.exists(r)]
        # 追加其他盘符根目录下的一级常见目录
        if constants.DRIVER_DIR and os.path.isdir(constants.DRIVER_DIR):
            roots.append(constants.DRIVER_DIR)
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
                if stop and stop():
                    return items
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
                        kind = "dll" if f.lower().endswith(constants.DLL_EXTS) else "file"
                        items.append(Item(kind, full, full, "", "深度扫描", size))
                        if len(items) >= limit:
                            return items

        return items

    # ------------------------------------------------------------ 残留扫描
    def scan_residual(self, deep: bool = True, progress=None, stop=None) -> list[Item]:
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

        for sc in self._startup_items():
            items.append(Item("startup", sc, os.path.basename(sc),
                              "", "残留启动项", self._file_size(sc)))

        for app in constants.APPS:
            for d in app["dirs"]:
                if d and os.path.isdir(d):
                    for mod in self._modules_in_dir(d):
                        items.append(Item("dll", mod, os.path.basename(mod),
                                          app["key"], app["name"], self._file_size(mod)))

        for mod in self._driver_modules():
            items.append(Item("dll", mod, os.path.basename(mod),
                              "", "360 驱动残留", self._file_size(mod)))

        if deep:
            if progress:
                progress("扫描各个 360 目录…", len(items))
            items.extend(self.scan_360_folders(progress=progress, stop=stop))
            if progress:
                progress("深度扫描残留文件…", len(items))
            items.extend(self.deep_scan(progress=progress, stop=stop))

        return merge_items(items)

    # ------------------------------------------------------------ 360 目录清扫
    def folder_roots(self) -> list[str]:
        """收集所有可能是 360 的目录：应用定义目录、公共目录、常见父目录下的 360 子目录、各盘一级 360 目录。"""
        roots: list[str] = []
        seen: set[str] = set()

        def add(path: str) -> None:
            if not path:
                return
            full = os.path.abspath(os.path.expandvars(path))
            low = os.path.normcase(full)
            if low in seen:
                return
            seen.add(low)
            roots.append(full)

        for app in constants.APPS:
            for d in app["dirs"]:
                add(d)
        for d in constants.COMMON_DIRS:
            add(d)

        for parent in constants.SCAN_PARENTS:
            parent = os.path.abspath(os.path.expandvars(parent)) if parent else ""
            if not parent or not os.path.isdir(parent):
                continue
            try:
                entries = os.listdir(parent)
            except OSError:
                continue
            for name in entries:
                full = os.path.join(parent, name)
                if not os.path.isdir(full):
                    continue
                if _kw_hit(name, ["360", "qhsafe", "qihu"]):
                    add(full)

        for drive in constants.SCAN_DRIVES:
            if not os.path.isdir(drive):
                continue
            try:
                entries = os.listdir(drive)
            except OSError:
                continue
            for name in entries:
                full = os.path.join(drive, name)
                if os.path.isdir(full) and _kw_hit(name, ["360", "qhsafe"]):
                    add(full)

        return [p for p in roots if os.path.isdir(p)]

    def scan_360_folders(self, progress=None, stop=None,
                         limit: int = constants.PATROL_MAX_ITEMS) -> list[Item]:
        """把每个 360 目录整体当成一个删除项，删掉目录即清空里面的全部残留。

        progress 回调签名是 (说明, 百分比)，与 scan_patrol 保持一致。
        """
        roots = self.folder_roots()
        total = max(1, len(roots))
        items: list[Item] = []
        for idx, folder in enumerate(roots, start=1):
            if stop and stop():
                break
            if len(items) >= limit:
                break
            if progress:
                progress(f"扫描 360 目录 {idx}/{total}：{os.path.basename(folder)}",
                         min(95, int(idx * 95 / total)))
            size = cleanup.path_size(folder)
            items.append(Item("dir", folder, folder, "", "360 目录", size))
        return items

    def scan_patrol(self, progress=None, stop=None) -> list[Item]:
        """开机巡检：常规残留 + 全部 360 目录 + 受控深度扫盘。

        progress(说明, 百分比 0-100)，供右下角小窗直接画进度条。
        """
        items = self.scan_residual(deep=False, progress=None, stop=stop)
        if progress:
            progress("扫描各个 360 目录…", 30)

        def _folder_progress(msg: str, pct: int) -> None:
            if progress:
                progress(msg, 30 + int(max(0, min(100, pct)) * 0.45))

        items.extend(self.scan_360_folders(progress=_folder_progress, stop=stop))
        if progress:
            progress("深度扫描散落文件…", 80)
        items.extend(self.deep_scan(progress=None, stop=stop))
        result = merge_items(items)
        if progress:
            progress(f"扫描完成，发现 {len(result)} 项", 100)
        return result

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
