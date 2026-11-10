"""后台工作线程：扫描 / 卸载 / 残留扫描 / 清理，统一通过信号回传 UI"""

from PySide6.QtCore import QThread, Signal

from .scanner import Scanner
from .uninstaller import UninstallEngine, EngineResult
from . import registry_utils


def _attach_protected(data: dict, log) -> dict:
    """把被 360 自我保护拦下的注册表项汇总成安全模式清理包。"""
    protected = registry_utils.consume_protected()
    if protected:
        pack = registry_utils.build_safe_mode_pack(protected)
        data["protected"] = len(protected)
        data["safe_pack"] = pack
        log(f"⚠ {len(protected)} 项注册表被 360 自我保护拦截，已生成安全模式清理包：{pack}")
    return data


class Worker(QThread):
    log = Signal(str)
    progress = Signal(int, str)
    result = Signal(dict)

    MODE_SCAN = "scan"
    MODE_UNINSTALL = "uninstall"
    MODE_RESIDUAL = "residual"
    MODE_CLEAN = "clean"

    def __init__(self, mode: str, payload: dict | None = None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.payload = payload or {}
        self._stop = False

    def request_stop(self):
        self._stop = True

    def _should_stop(self) -> bool:
        return self._stop

    def run(self):
        try:
            if self.mode == self.MODE_SCAN:
                self._do_scan()
            elif self.mode == self.MODE_UNINSTALL:
                self._do_uninstall()
            elif self.mode == self.MODE_RESIDUAL:
                self._do_residual()
            elif self.mode == self.MODE_CLEAN:
                self._do_clean()
        except Exception as exc:  # pragma: no cover
            self.log.emit(f"任务异常终止：{exc}")
            self.result.emit({"error": str(exc)})

    # ------------------------------------------------------------------
    def _do_scan(self):
        self.log.emit("开始扫描 360 系列应用…")
        scanner = Scanner()
        self.progress.emit(5, "读取已安装程序列表")
        entries = scanner.uninstall_entries()
        self.log.emit(f"注册表卸载项命中 {len(entries)} 个 360 相关条目")

        self.progress.emit(25, "检测进程与服务")
        items, status = scanner.scan_all_apps(with_size=True)
        self.progress.emit(65, "扫描公共组件与启动项")
        common = scanner.scan_common(with_size=True)

        # 去重
        existing = {(i.kind, i.target) for i in items}
        for c in common:
            if (c.kind, c.target) not in existing:
                items.append(c)
                existing.add((c.kind, c.target))

        self.progress.emit(95, "汇总结果")
        summary = scanner.installed_summary()
        summary["entries"] = len(entries)
        summary["items"] = len(items)
        summary["size"] = sum(i.size for i in items)

        self.log.emit(f"扫描完成：{len(items)} 个可清理项，"
                      f"应用 {summary['apps']} 款")
        self.progress.emit(100, "扫描完成")
        self.result.emit({
            "mode": self.mode,
            "items": items,
            "status": status,
            "summary": summary,
        })

    def _do_uninstall(self):
        apps = self.payload.get("apps", [])
        items_by_app = self.payload.get("items_by_app", {})
        extra_items = self.payload.get("extra_items", [])
        self.log.emit(f"开始卸载 {len(apps)} 款应用（不调用官方卸载器）")
        engine = UninstallEngine(logger=self.log.emit, progress=self.progress.emit,
                                 should_stop=self._should_stop)
        res = engine.uninstall_apps(apps, items_by_app, extra_items=extra_items)
        self.progress.emit(100, "卸载流程结束")
        data = res.to_dict()
        data["mode"] = self.mode
        self.result.emit(_attach_protected(data, self.log.emit))

    def _do_residual(self):
        deep = bool(self.payload.get("deep", True))
        self.log.emit("开始扫描残余项目" + ("（含深度扫盘）" if deep else ""))
        scanner = Scanner()
        items = scanner.scan_residual(
            deep=deep,
            progress=lambda msg, count: self.progress.emit(min(90, 10 + count // 20), msg),
        )
        data = {
            "mode": self.mode,
            "items": items,
            "total_size": sum(i.size for i in items),
        }
        self.progress.emit(100, f"残留扫描完成，共 {len(items)} 项")
        self.log.emit(f"残留扫描完成：{len(items)} 项")
        self.result.emit(data)

    def _do_clean(self):
        items = self.payload.get("items", [])
        self.log.emit(f"开始删除 {len(items)} 个项目")
        engine = UninstallEngine(logger=self.log.emit, progress=self.progress.emit,
                                 should_stop=self._should_stop)
        res: EngineResult = engine.clean_items(items)
        data = res.to_dict()
        data["mode"] = self.mode
        self.progress.emit(100, "删除完成")
        self.result.emit(_attach_protected(data, self.log.emit))
