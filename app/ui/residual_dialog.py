"""残余项目检查小窗：扫描 → 勾选 → 删除 → 结果"""

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import (QCheckBox, QDialog, QFrame, QHBoxLayout,
                               QLabel, QListWidget, QListWidgetItem,
                               QMessageBox, QProgressBar, QPushButton,
                               QVBoxLayout, QWidget)

from .. import cleanup, icon_provider
from ..scanner import Item
from ..worker import Worker
from . import theme


KIND_COLORS = {
    "process": "#1E63D6", "service": "#0E9384", "dir": "#7C5CFC",
    "file": "#7C5CFC", "registry": "#E8A33D", "task": "#D4587E",
    "shortcut": "#5A7D9A",
}


class ResidualRow(QWidget):
    toggled = Signal()

    def __init__(self, item: Item, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(8)

        self.cb = QCheckBox()
        self.cb.setChecked(True)
        self.cb.toggled.connect(lambda _v: self.toggled.emit())
        lay.addWidget(self.cb)

        kind = QLabel(item.kind_label)
        kind.setAlignment(Qt.AlignCenter)
        kind.setFixedWidth(56)
        color = KIND_COLORS.get(item.kind, "#5A7D9A")
        kind.setStyleSheet(
            f"color:{color}; background:{theme.COLORS['surface']};"
            f"border:1px solid {color}33; border-radius:8px; font-size:8pt; padding:1px 4px;"
        )
        lay.addWidget(kind)

        text = QLabel(item.label)
        text.setToolTip(item.target)
        text.setStyleSheet("font-size:9pt;")
        text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(text, 1)

        size = QLabel(item.size_text)
        size.setFixedWidth(72)
        size.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        size.setStyleSheet(f"color:{theme.COLORS['text_muted']}; font-size:8.5pt;")
        lay.addWidget(size)

    def is_checked(self) -> bool:
        return self.cb.isChecked()

    def set_checked(self, v: bool):
        self.cb.setChecked(v)


class ResidualDialog(QDialog):
    """卸载完成后弹出，检查残余项目并支持勾选删除。"""

    finished_cleanup = Signal(dict)

    def __init__(self, parent=None, deep: bool = True, title: str = "残余项目检查"):
        super().__init__(parent)
        self.setObjectName("ResidualDialog")
        self.setWindowTitle(title)
        self.setWindowIcon(icon_provider.app_icon())
        self.setMinimumSize(780, 600)
        self.resize(820, 650)
        self.setModal(True)

        self.items: list[Item] = []
        self.rows: list[ResidualRow] = []
        self.worker: Worker | None = None
        self.deep = deep
        self.deleted = False
        self.clean_result: dict = {}
        self._deleting = False
        self._emitted = False
        self._count_word = "项残留"

        self._build()

    # ------------------------------------------------------------------ UI
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(12)
        icon = QLabel()
        icon.setPixmap(icon_provider.app_pixmap(44))
        icon.setFixedSize(44, 44)
        head.addWidget(icon)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        self.title = QLabel("正在检查残余项目…")
        self.title.setObjectName("DialogTitle")
        self.sub = QLabel("扫描进程、服务、目录、注册表、计划任务与磁盘残留文件")
        self.sub.setObjectName("DialogSub")
        titles.addWidget(self.title)
        titles.addWidget(self.sub)
        head.addLayout(titles, 1)
        root.addLayout(head)

        # 扫描进度区
        self.scan_box = QFrame()
        self.scan_box.setObjectName("DialogStat")
        sb = QVBoxLayout(self.scan_box)
        sb.setContentsMargins(14, 12, 14, 12)
        sb.setSpacing(8)
        self.scan_text = QLabel("准备扫描…")
        self.scan_text.setStyleSheet("font-size:9pt;")
        sb.addWidget(self.scan_text)
        self.scan_bar = QProgressBar()
        self.scan_bar.setRange(0, 100)
        self.scan_bar.setValue(0)
        self.scan_bar.setFixedHeight(8)
        self.scan_bar.setTextVisible(False)
        sb.addWidget(self.scan_bar)
        root.addWidget(self.scan_box)

        # 统计条
        self.stat_box = QFrame()
        self.stat_box.setObjectName("DialogStat")
        self.stat_box.setVisible(False)
        st = QHBoxLayout(self.stat_box)
        st.setContentsMargins(14, 10, 14, 10)
        st.setSpacing(24)
        self.lb_count = QLabel("0 项残留")
        self.lb_count.setStyleSheet("font-size:11pt; font-weight:700;")
        self.lb_size = QLabel("可释放 0 B")
        self.lb_size.setStyleSheet(f"font-size:9pt; color:{theme.COLORS['text_sub']};")
        self.lb_hint = QLabel("勾选后点击“删除选中项”")
        self.lb_hint.setStyleSheet(f"font-size:8.5pt; color:{theme.COLORS['text_muted']};")
        st.addWidget(self.lb_count)
        st.addWidget(self.lb_size)
        st.addStretch(1)
        st.addWidget(self.lb_hint)
        root.addWidget(self.stat_box)

        # 列表
        self.list = QListWidget()
        self.list.setObjectName("ResidualList")
        self.list.setSelectionMode(QListWidget.NoSelection)
        self.list.setFocusPolicy(Qt.NoFocus)
        self.list.setVisible(False)
        root.addWidget(self.list, 1)

        # 空状态
        self.empty = QLabel("未发现残留项目，系统已清理干净")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setStyleSheet(f"color:{theme.COLORS['text_sub']}; font-size:10pt;")
        self.empty.setVisible(False)
        root.addWidget(self.empty)

        # 底部操作
        btns = QHBoxLayout()
        btns.setSpacing(8)
        self.btn_all = QPushButton("全选")
        self.btn_all.setObjectName("Ghost")
        self.btn_all.clicked.connect(self._toggle_all)
        self.btn_scan_again = QPushButton("重新扫描")
        self.btn_scan_again.setObjectName("Ghost")
        self.btn_scan_again.clicked.connect(lambda: self.start_scan())
        self.btn_close = QPushButton("跳过，稍后处理")
        self.btn_close.clicked.connect(self._close_dialog)
        self.btn_delete = QPushButton("删除选中项")
        self.btn_delete.setObjectName("Primary")
        self.btn_delete.clicked.connect(self._delete_selected)

        btns.addWidget(self.btn_all)
        btns.addWidget(self.btn_scan_again)
        btns.addStretch(1)
        btns.addWidget(self.btn_close)
        btns.addWidget(self.btn_delete)
        root.addLayout(btns)

        self._set_actions(False)

    def _set_actions(self, ready: bool, deleting: bool = False):
        self.btn_all.setEnabled(ready and not deleting)
        self.btn_scan_again.setEnabled(not deleting)
        self.btn_delete.setEnabled(ready and not deleting and self._selected_count() > 0)
        self.btn_close.setEnabled(not deleting)

    def _selected_count(self) -> int:
        return sum(1 for r in self.rows if r.is_checked())

    def _update_selection_stats(self):
        if not self.items:
            return
        n = self._selected_count()
        size = sum(it.size for it, r in zip(self.items, self.rows) if r.is_checked())
        self.lb_count.setText(f"{len(self.items)} {self._count_word} · 已选 {n}")
        self.lb_size.setText(f"预计释放 {cleanup.human_size(size)}")
        self.btn_delete.setEnabled(n > 0 and not self._deleting)
        self.btn_all.setText("全选" if n < len(self.rows) else "全不选")
        if n == 0:
            self.lb_hint.setText("还没勾选任何项目，点“全选”可以一次勾满")
        else:
            self.lb_hint.setText("点击“删除选中项”，逐项执行并回报每一项结果")

    def _emit_cleanup(self):
        """同一窗口只上报一次结果，避免关闭时重复通知主界面。"""
        if self._emitted or not self.clean_result:
            return
        self._emitted = True
        self.finished_cleanup.emit(self.clean_result)

    # ------------------------------------------------------------------ 扫描
    def start_scan(self):
        if self.worker and self.worker.isRunning():
            return
        self.items.clear()
        self.rows.clear()
        self.list.clear()
        self.list.setVisible(False)
        self.list.setEnabled(True)
        self.empty.setVisible(False)
        self.stat_box.setVisible(False)
        self.scan_box.setVisible(True)
        self.scan_bar.setValue(0)
        self.scan_text.setText("正在扫描残余项目…")
        self.title.setText("正在检查残余项目…")
        self.sub.setText("扫描进程、服务、目录、注册表、计划任务与磁盘残留文件")
        self._deleting = False
        self._count_word = "项残留"
        self.btn_close.setText("跳过，稍后处理")
        self._set_actions(False)
        self.btn_delete.setText("删除选中项")
        # 重新扫描后允许再次上报结果，避免上一轮“已上报”标记把新结果吞掉
        self._emitted = False
        self.clean_result = {}

        self.worker = Worker(Worker.MODE_RESIDUAL, {"deep": self.deep}, parent=self)
        self.worker.log.connect(lambda m: self.scan_text.setText(m))
        self.worker.progress.connect(self._on_progress)
        self.worker.result.connect(self._on_scan_done)
        self.worker.start()

    def _populate_demo(self):
        """预览模式：填充示例残留，展示结果态。"""
        demo = [
            Item("dir", r"C:\Program Files (x86)\360\360Safe", r"C:\Program Files (x86)\360\360Safe",
                 "", "残留目录", 268_435_456),
            Item("dir", r"C:\ProgramData\360safe", r"C:\ProgramData\360safe",
                 "", "残留目录", 41_943_040),
            Item("dir", r"C:\Users\Administrator\AppData\Roaming\360safe",
                 r"…\AppData\Roaming\360safe", "", "残留目录", 12_582_912),
            Item("file", r"C:\Users\Administrator\Desktop\360安全卫士.lnk",
                 "360安全卫士.lnk", "", "残留文件", 2048),
            Item("file", r"C:\Users\Administrator\Downloads\360safe_setup.exe",
                 "360safe_setup.exe", "", "深度扫描", 58_720_256),
            Item("service", "360rp", "360rp", "", "360 服务"),
            Item("service", "360SoftMgrSvc", "360SoftMgrSvc", "", "360 服务"),
            Item("task", "360安全卫士-每日体检", "360安全卫士-每日体检", "", "残留任务"),
            Item("registry", r"HKLM\SOFTWARE\WOW6432Node\360Safe",
                 r"HKLM\SOFTWARE\WOW6432Node\360Safe", "", "残留注册表"),
            Item("registry", r"HKCU\Software\360Safe",
                 r"HKCU\Software\360Safe", "", "残留注册表"),
            Item("registry", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run::360Safetray",
                 "360Safetray", "", "开机启动项", extra={"value_name": "360Safetray"}),
            Item("shortcut", r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\360安全卫士.lnk",
                 "360安全卫士.lnk", "", "残留快捷方式"),
        ]
        self.scan_box.setVisible(False)
        self._on_scan_done({
            "items": demo,
            "total_size": sum(i.size for i in demo),
        })
        self.title.setText("残余项目检查结果")
        self.sub.setText("勾选需要删除的项目，逐项执行删除并回报结果")

    def _on_progress(self, pct: int, text: str):
        self.scan_bar.setValue(pct)
        if text:
            self.scan_text.setText(text)

    def _on_scan_done(self, data: dict):
        self.items = data.get("items", [])
        self.scan_box.setVisible(False)
        self.title.setText("残余项目检查结果")
        self.sub.setText("勾选需要删除的项目，逐项执行删除并回报结果")

        if not self.items:
            self.empty.setVisible(True)
            self.btn_close.setText("完成")
            self._set_actions(False)
            return

        self.stat_box.setVisible(True)
        total_size = data.get("total_size", 0)
        self.lb_count.setText(f"{len(self.items)} 项残留")
        self.lb_size.setText(f"可释放 {cleanup.human_size(total_size)}")

        self.list.setVisible(True)
        self.list.setEnabled(True)
        for item in self.items:
            li = QListWidgetItem(self.list)
            li.setSizeHint(QSize(0, 34))
            row = ResidualRow(item)
            row.toggled.connect(self._update_selection_stats)
            self.rows.append(row)
            self.list.setItemWidget(li, row)

        self._count_word = "项残留"
        self._set_actions(True)
        self._update_selection_stats()

    def _toggle_all(self):
        target = not all(r.is_checked() for r in self.rows)
        for r in self.rows:
            r.set_checked(target)
        self.btn_all.setText("全不选" if target else "全选")
        self._update_selection_stats()

    # ------------------------------------------------------------------ 删除
    def _selected(self) -> list[Item]:
        return [it for it, row in zip(self.items, self.rows) if row.is_checked()]

    def _delete_selected(self):
        selected = self._selected()
        if not selected:
            self.lb_hint.setText("请先勾选要删除的项目")
            return
        self._deleting = True
        self.list.setEnabled(False)
        self.btn_delete.setText("删除中…")
        self._set_actions(True, deleting=True)
        self.scan_box.setVisible(True)
        self.scan_bar.setValue(0)
        self.scan_text.setText(f"正在删除 {len(selected)} 个项目…")

        self.worker = Worker(Worker.MODE_CLEAN, {"items": selected}, parent=self)
        self.worker.log.connect(lambda m: self.scan_text.setText("删除进度 · " + m[:100]))
        self.worker.progress.connect(self._on_progress)
        self.worker.result.connect(self._on_clean_done)
        self.worker.start()

    def _on_clean_done(self, data: dict):
        self.clean_result = data
        self.deleted = True
        ok = data.get("ok", 0)
        fail = data.get("fail", 0)
        pending = data.get("pending", 0)
        freed = data.get("freed_text", "0 B")
        self.scan_box.setVisible(False)
        self.title.setText("残余清理完成")
        sub = f"成功 {ok} 项 · 失败 {fail} 项 · 释放 {freed}"
        if pending:
            sub += f" · {pending} 项待重启后删除"
        self.sub.setText(sub)
        self.lb_hint.setText(
            f"{pending} 项已登记重启后删除，重启一次即完成"
            if pending else "建议重启电脑以完成最后的文件释放")

        # 只保留失败项供重试
        failed_targets = {r["target"] for r in data.get("rows", []) if not r["ok"]}
        remaining = [it for it in self.items if it.target in failed_targets]
        self.list.clear()
        self.rows.clear()
        self.items = remaining
        self._deleting = False
        self.list.setEnabled(True)
        for item in remaining:
            li = QListWidgetItem(self.list)
            li.setSizeHint(QSize(0, 34))
            row = ResidualRow(item)
            row.toggled.connect(self._update_selection_stats)
            self.rows.append(row)
            self.list.setItemWidget(li, row)

        self.stat_box.setVisible(bool(remaining))
        if remaining:
            self._count_word = "项未清理"
            self.list.setVisible(True)
            self.btn_delete.setText("重试删除选中项")
            self.btn_close.setText("完成")
            self._set_actions(True)
            self._update_selection_stats()
        else:
            self.list.setVisible(False)
            self.empty.setVisible(True)
            self.empty.setText(
                f"清理完成，释放 {freed}。"
                + (f"另有 {pending} 项安排在重启后删除，重启一次即可清空。" if pending
                   else "建议重启电脑。"))
            self.btn_close.setText("完成")
            self._set_actions(False)

        self._emit_cleanup()

    def _close_dialog(self):
        if self.worker and self.worker.isRunning():
            if not self._confirm_stop():
                return
            self.worker.request_stop()
            self.worker.wait(3000)
        self._emit_cleanup()
        self.accept()

    def _confirm_stop(self) -> bool:
        ret = QMessageBox.question(
            self, "操作仍在进行",
            "扫描或删除还没有结束，现在关闭会中止剩余步骤，"
            "可能留下删了一半的项目。\n\n确定要关闭吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return ret == QMessageBox.Yes

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            if not self._confirm_stop():
                event.ignore()
                return
            self.worker.request_stop()
            self.worker.wait(3000)
        self._emit_cleanup()
        super().closeEvent(event)
