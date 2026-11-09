"""卸载引擎：不调用官方卸载器，直接按清理项逐级拆除"""

import time

from . import cleanup, process_utils, registry_utils
from .constants import KIND_LABELS


class EngineResult:
    def __init__(self):
        self.ok = 0
        self.fail = 0
        self.skipped = 0
        self.freed = 0
        self.pending = 0
        self.rows: list[dict] = []

    def add(self, item, ok: bool, detail: str, pending: int = 0):
        if ok:
            self.ok += 1
        else:
            self.fail += 1
        self.pending += max(0, pending)
        if item is not None:
            self.freed += getattr(item, "size", 0) if ok and not pending else 0
            self.rows.append({
                "kind": item.kind,
                "kind_label": item.kind_label,
                "label": item.label,
                "target": item.target,
                "ok": ok,
                "pending": pending,
                "detail": detail,
            })

    @property
    def total(self) -> int:
        return self.ok + self.fail

    def to_dict(self) -> dict:
        return {
            "total": self.total, "ok": self.ok, "fail": self.fail,
            "freed": self.freed, "freed_text": cleanup.human_size(self.freed),
            "pending": self.pending, "rows": self.rows,
        }


def remove_one(item, logger=None) -> tuple[bool, str, int]:
    """按项目类型执行单项删除，返回 (成功, 说明, 登记重启删除项数)。"""
    kind = item.kind
    target = item.target
    pending = 0

    if kind == "process":
        ok, detail = process_utils.kill_process(target)
    elif kind == "service":
        ok1, d1 = process_utils.stop_service(target)
        ok2, d2 = process_utils.delete_service(target)
        ok, detail = (ok1 and ok2), f"{d1}；{d2}"
    elif kind in ("dir", "file"):
        ok, detail, _freed, pending = cleanup.remove_path(
            target, force=True,
            log=(lambda m: logger(m)) if logger else None)
    elif kind == "registry":
        value_name = item.extra.get("value_name")
        if value_name:
            key, name = target.split("::", 1)
            ok, detail = registry_utils.delete_value(key, name)
        else:
            ok, detail = registry_utils.delete_key(target)
    elif kind == "task":
        ok, detail = process_utils.delete_task(target)
    elif kind == "shortcut":
        ok, detail, _ = cleanup.remove_shortcut(target)
    else:
        ok, detail = False, f"未知类型：{kind}"

    if logger:
        logger(("✔ " if ok else "✘ ") + f"[{KIND_LABELS.get(kind, kind)}] {item.label} — {detail}")
    return ok, detail, pending


class UninstallEngine:
    """对勾选的清理项执行拆除，过程实时回调进度与日志。"""

    def __init__(self, logger=None, progress=None, should_stop=None):
        self.logger = logger or (lambda _msg: None)
        self.progress = progress or (lambda _msg, _pct: None)
        self.should_stop = should_stop or (lambda: False)

    def clean_items(self, items, stage_prefix: str = "") -> EngineResult:
        result = EngineResult()
        total = max(1, len(items))
        for idx, item in enumerate(items, start=1):
            if self.should_stop():
                self.logger("用户已取消，剩余项目跳过")
                result.skipped += total - idx + 1
                break
            pct = int(idx * 100 / total)
            self.progress(f"{stage_prefix}正在处理 {idx}/{total}：{item.label}", pct)
            ok, detail, pending = remove_one(item, self.logger)
            result.add(item, ok, detail, pending)
            if item.kind in ("dir", "file") and ok and not pending:
                self.logger(f"  释放空间 {cleanup.human_size(item.size)}")
            time.sleep(0.05)
        return result

    def uninstall_apps(self, apps: list[dict], items_by_app: dict,
                       extra_items=None) -> EngineResult:
        """完整卸载流程：进程 → 服务 → 计划任务 → 目录 → 注册表 → 快捷方式。"""
        all_items = []
        for app in apps:
            all_items.extend(items_by_app.get(app["key"], []))
        if extra_items:
            all_items.extend(list(extra_items))

        # 去重（同类型同目标只处理一次）
        seen = set()
        unique = []
        for it in all_items:
            key = (it.kind, it.target)
            if key in seen:
                continue
            seen.add(key)
            unique.append(it)
        all_items = unique

        order = {"process": 0, "service": 1, "task": 2, "dir": 3,
                 "file": 4, "registry": 5, "shortcut": 6}
        all_items.sort(key=lambda i: order.get(i.kind, 9))

        labels = {0: "结束进程", 1: "停止并删除服务", 2: "清理计划任务",
                  3: "删除安装目录", 4: "删除残留文件", 5: "清理注册表", 6: "清理快捷方式"}
        result = EngineResult()
        total = max(1, len(all_items))
        for idx, item in enumerate(all_items, start=1):
            if self.should_stop():
                result.skipped += total - idx + 1
                self.logger("用户已取消")
                break
            stage = labels.get(order.get(item.kind, 9), "清理")
            pct = int(idx * 100 / total)
            self.progress(f"{stage}：{item.label} ({idx}/{total})", pct)
            ok, detail, pending = remove_one(item, self.logger)
            result.add(item, ok, detail, pending)
        return result
