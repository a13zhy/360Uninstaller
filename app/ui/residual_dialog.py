"""残余项目小窗：扫描 → 勾选 → 删除 → 结果与解决方案

窗口缩到 640×440，行高 40，一条一行；失败项在底部给出可照做的下一步。
"""

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QFontMetrics, QMovie
from PySide6.QtWidgets import (QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel,
                               QMessageBox, QProgressBar, QPushButton,
                               QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from .. import cleanup, solutions
from ..scanner import Item
from ..worker import Worker
from . import theme
from .widgets import SolutionBox

KIND_TONE = {
    "process": ("进程", "#5B6470"),
    "service": ("服务", "#2B7CF6"),
    "dir": ("目录", "#C26A14"),
    "file": ("文件", "#5B6470"),
    "dll": ("DLL", "#8B5CF6"),
    "registry": ("注册表", "#D54941"),
    "task": ("任务", "#2BA471"),
    "startup": ("启动项", "#2BA471"),
    "shortcut": ("快捷方式", "#8B939E"),
}

TECH_FOR_KIND = {
    "process": "taskkill /T /F",
    "service": "sc stop / delete",
    "task": "schtasks /delete",
    "startup": "启动项直删",
    "shortcut": "快捷方式直删",
    "dir": "接管所有权+删树",
    "file": "接管所有权+删",
    "dll": "RestartManager",
    "registry": "ACL+RegDelete",
}


class _Row(QFrame):

    def __init__(self, item: Item, parent=None):
        super().__init__(parent)
        self.item = item
        self.setObjectName("AppTile")
        self.setFixedHeight(40)
        self.setStyleSheet(
            f"QFrame#AppTile {{ background: #FFFFFF; border: none;"
            f" border-bottom: 1px solid {theme.COLORS['line']}; border-radius: 0; }}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 2, 10, 2)
        row.setSpacing(8)

        self.box = QCheckBox(self)
        self.box.setChecked(True)
        row.addWidget(self.box)

        label, color = KIND_TONE.get(item.kind, (item.kind, "#5B6470"))
        tag = QLabel(label)
        tag.setFixedWidth(48)
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tag.setStyleSheet(
            f"background:#FFFFFF; color:{color}; border:1px solid {theme.COLORS['line']};"
            f" border-radius:2px; font-size:7pt; padding:1px 0px;")
        row.addWidget(tag)

        name = QLabel(item.label or item.target)
        name.setObjectName("TileName")
        name.setFixedWidth(132)
        name.setToolTip(item.label or item.target)
        row.addWidget(name)

        path = QLabel()
        path.setObjectName("Mono")
        path.setToolTip(item.target)
        metrics = QFontMetrics(path.font())
        path.setText(metrics.elidedText(item.target, Qt.TextElideMode.ElideMiddle, 236))
        path.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        row.addWidget(path, 1)

        size = QLabel(item.size_text)
        size.setObjectName("TileSize")
        size.setFixedWidth(54)
        size.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(size)

        tech = QLabel(TECH_FOR_KIND.get(item.kind, "直删"))
        tech.setObjectName("SectionHint")
        tech.setFixedWidth(100)
        row.addWidget(tech)

    def is_checked(self) -> bool:
        return self.box.isChecked()


class ResidualDialog(QDialog):
    def __init__(self, parent=None, deep: bool = True,
                 title: str = "残余项目检查", auto_start: bool = True):
        super().__init__(parent)
        self.setObjectName("ResidualDialog")
        self.deep = deep
        self.title_text = title
        self.auto_start = auto_start
        self.items: list[Item] = []
        self.rows: list[_Row] = []
        self.worker: Worker | None = None
        self.cleanup_data: dict | None = None
        self._scanning = False
        self._deleting = False

        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(640, 440)
        self.setMinimumSize(600, 400)
        self._build()

        if auto_start:
            QTimer.singleShot(120, self.start_scan)

    # ------------------------------------------------------------ 构建
    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        head = QHBoxLayout()
        head.setSpacing(8)
        self.spinner = QLabel()
        self.spinner.setFixedSize(22, 22)
        self.movie = QMovie(theme.asset_path("scan_ring.gif"))
        if self.movie.isValid():
            self.movie.setScaledSize(QSize(22, 22))
            self.spinner.setMovie(self.movie)
        self.spinner.setVisible(False)
        head.addWidget(self.spinner)

        titles = QVBoxLayout()
        titles.setSpacing(1)
        self.lb_title = QLabel(self.title_text)
        self.lb_title.setObjectName("DialogTitle")
        self.lb_sub = QLabel("扫盘 + 注册表复查" if self.deep else "注册表与目录复查")
        self.lb_sub.setObjectName("DialogSub")
        titles.addWidget(self.lb_title)
        titles.addWidget(self.lb_sub)
        head.addLayout(titles, 1)

        self.btn_close_top = QPushButton("关闭")
        self.btn_close_top.setObjectName("Link")
        head.addWidget(self.btn_close_top)
        lay.addLayout(head)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(4)
        self.bar.setValue(0)
        lay.addWidget(self.bar)

        self.lb_status = QLabel("准备扫描…")
        self.lb_status.setObjectName("DialogSub")
        lay.addWidget(self.lb_status)

        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(1, 1, 1, 1)
        cl.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.host = QWidget()
        self.list_box = QVBoxLayout(self.host)
        self.list_box.setContentsMargins(0, 0, 0, 0)
        self.list_box.setSpacing(0)
        self.list_box.addStretch(1)
        scroll.setWidget(self.host)
        cl.addWidget(scroll)
        lay.addWidget(card, 1)

        self.solbox = SolutionBox()
        lay.addWidget(self.solbox)

        foot = QHBoxLayout()
        foot.setSpacing(8)
        self.lb_stat = QLabel("尚未扫描")
        self.lb_stat.setObjectName("StatChip")
        foot.addWidget(self.lb_stat)
        foot.addStretch(1)
        self.btn_all = QPushButton("全选")
        self.btn_all.setObjectName("Link")
        self.btn_clean = QPushButton("清理选中（0）")
        self.btn_clean.setObjectName("Primary")
        self.btn_all.setEnabled(False)
        self.btn_clean.setEnabled(False)
        foot.addWidget(self.btn_all)
        foot.addWidget(self.btn_clean)
        lay.addLayout(foot)

        self.btn_close_top.clicked.connect(self._close_dialog)
        self.btn_all.clicked.connect(self._toggle_all)
        self.btn_clean.clicked.connect(self._delete_selected)

    # ------------------------------------------------------------ 扫描
    def start_scan(self):
        if self._scanning:
            return
        if not self.auto_start:
            self.auto_start = True
            return
        self._scanning = True
        self.solbox.clear()
        self._set_rows([])
        self.lb_status.setText("正在扫描…" if self.deep else "正在复查注册表与目录…")
        self.spinner.setVisible(True)
        if self.movie.isValid():
            self.movie.start()
        self.bar.setValue(0)
        self.btn_all.setEnabled(False)
        self.btn_clean.setEnabled(False)

        self.worker = Worker(Worker.MODE_RESIDUAL, {"deep": bool(self.deep)}, self)
        self.worker.progress.connect(self._on_progress)
        self.worker.result.connect(self._on_scan_done)
        self.worker.start()

    def _on_progress(self, pct: int, text: str):
        self.bar.setValue(max(0, min(100, int(pct))))
        self.lb_status.setText(text)

    def _on_scan_done(self, data: dict):
        self._scanning = False
        self.spinner.setVisible(False)
        if self.movie.isValid():
            self.movie.stop()
        items = data.get("items", [])
        self.items = list(items)
        self._set_rows(self.items)
        self.bar.setValue(100)
        total = data.get("total_size")
        if total is None:
            total = sum(getattr(i, "size", 0) for i in self.items)
        self.lb_status.setText(
            f"扫描完成：{len(self.items)} 项 · {cleanup.human_size(total)}")
        self._update_stats()

    def _set_rows(self, items: list):
        while self.list_box.count():
            entry = self.list_box.takeAt(0)
            if entry.widget():
                entry.widget().setParent(None)
                entry.widget().deleteLater()
        self.rows = []
        if not items:
            hint = QLabel("没有发现残余项目，这块已经干净了。")
            hint.setObjectName("Empty")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint.setMinimumHeight(120)
            self.list_box.addWidget(hint)
            self.list_box.addStretch(1)
            return
        for item in items:
            row = _Row(item)
            row.box.toggled.connect(lambda _c: self._update_stats())
            self.list_box.addWidget(row)
            self.rows.append(row)
        self.list_box.addStretch(1)
        self._update_stats()

    def _update_stats(self):
        picked = [r for r in self.rows if r.is_checked()]
        total = sum(r.item.size for r in picked)
        self.btn_clean.setText(f"清理选中（{len(picked)}）")
        self.btn_clean.setEnabled(bool(picked) and not self._scanning and not self._deleting)
        self.btn_all.setEnabled(bool(self.rows) and not self._deleting)
        self.lb_stat.setText(
            f"{len(self.rows)} 项 · 选中 {len(picked)} · {cleanup.human_size(total)}")

    def _toggle_all(self):
        all_on = all(r.is_checked() for r in self.rows) if self.rows else False
        for row in self.rows:
            row.box.setChecked(not all_on)
        self._update_stats()

    # ------------------------------------------------------------ 删除
    def _delete_selected(self):
        picked = [r for r in self.rows if r.is_checked()]
        if not picked:
            return
        ret = QMessageBox.question(
            self, "确认清理",
            f"将删除 {len(picked)} 项，其中目录会整棵删除。\n"
            "删不掉的会自动用接管所有权与重启删除兜底。继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return

        self._deleting = True
        self.btn_clean.setEnabled(False)
        self.btn_all.setEnabled(False)
        self.bar.setValue(0)
        self.lb_status.setText("正在清理…")
        self.spinner.setVisible(True)
        if self.movie.isValid():
            self.movie.start()

        self.worker = Worker(Worker.MODE_CLEAN,
                             {"items": [r.item for r in picked]}, self)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._on_del_log)
        self.worker.result.connect(self._on_clean_done)
        self.worker.start()

    def _on_del_log(self, message: str):
        if len(message) > 90:
            message = message[:87] + "…"
        self.lb_status.setText(message)

    def _on_clean_done(self, data: dict):
        self._deleting = False
        self.cleanup_data = data
        self.spinner.setVisible(False)
        if self.movie.isValid():
            self.movie.stop()
        ok = int(data.get("ok", 0))
        fail = int(data.get("fail", 0))
        pending = int(data.get("pending", 0))
        self.bar.setValue(100)
        self.lb_status.setText(
            f"清理完成：成功 {ok} · 失败 {fail} · 登记重启删除 {pending}")
        sols = solutions.collect(data.get("rows", []))
        self.solbox.set_solutions([s.to_dict() for s in sols])

        self._set_rows([])
        self.items = []
        self.btn_clean.setText("清理选中（0）")
        self.btn_clean.setEnabled(False)
        self.btn_all.setEnabled(False)
        self.lb_stat.setText(f"成功 {ok} · 失败 {fail} · 重启删除 {pending}")
        self.btn_close_top.setText("完成")
        if fail == 0:
            self.lb_title.setText("清理完成")
        else:
            self.lb_title.setText("部分项目未清理")

    def _close_dialog(self):
        if self._scanning or self._deleting:
            if not self._confirm_stop():
                return
        self.accept()

    def _confirm_stop(self) -> bool:
        ret = QMessageBox.question(
            self, "任务进行中", "扫描或清理还没结束，现在关闭会中断。确定关闭？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return False
        if self.worker and self.worker.isRunning():
            self.worker.request_stop()
            self.worker.wait(1500)
        return True

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning() and not self._confirm_stop():
            event.ignore()
            return
        super().closeEvent(event)

    # ------------------------------------------------------------ 演示
    def _populate_demo(self):
        demo = [
            Item("dir", r"C:\Program Files (x86)\360\360Safe", "360Safe 安装目录", size=162_334_000),
            Item("registry", r"HKLM\SOFTWARE\WOW6432Node\360Safe", "360Safe 主键", size=0),
            Item("dll", r"C:\Windows\System32\drivers\360FsFlt.sys", "360FsFlt 驱动", size=1_204_000),
            Item("task", r"360安全卫士自动升级", "计划任务", size=0),
            Item("startup", r"C:\ProgramData\...\Startup\360Safe.lnk", "开机启动项", size=1_800),
            Item("dir", r"C:\Users\Administrator\AppData\Local\360Chrome\Cache", "浏览器缓存目录",
                 size=418_770_000),
        ]
        self._scanning = False
        self.items = demo
        self._set_rows(demo)
        self.bar.setValue(100)
        self.lb_status.setText("演示状态：扫描完成，6 项 · 592.3 MB")
        self.lb_title.setText(self.title_text)
