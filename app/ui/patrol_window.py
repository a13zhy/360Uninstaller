"""开机巡检小窗：固定在右下角，带扫描动图，删除前必须确认

边界没变：不后台静默批删、不自动重启、不做重启循环；窗口始终可关闭。
"""

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QMovie, QPixmap
from PySide6.QtWidgets import (QCheckBox, QFrame, QHBoxLayout, QLabel,
                               QMessageBox, QProgressBar, QPushButton,
                               QVBoxLayout, QWidget)

from .. import bootguard, cleanup, icon_provider, system_actions
from ..scanner import Item
from ..worker import Worker
from . import theme
from .residual_dialog import ResidualDialog
from .widgets import glyph_icon, glyph_pixmap

WIN_W, WIN_H = 344, 176


class PatrolWindow(QFrame):
    closed = Signal()

    def __init__(self, parent=None, auto_start: bool = True):
        super().__init__(parent)
        self.setObjectName("PatrolWindow")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(WIN_W, WIN_H)
        self.setStyleSheet(
            f"QFrame#PatrolWindow {{ background: {theme.COLORS['panel']};"
            f" border: 1px solid {theme.COLORS['line']}; border-radius: 4px; }}")

        self.items: list[Item] = []
        self.worker: Worker | None = None
        self._scanning = False
        self._cleaning = False
        self._auto_start = auto_start
        self._close_timer: QTimer | None = None

        self._build()
        self._refresh_boot()

        if auto_start:
            QTimer.singleShot(120, self.start_scan)

    # ------------------------------------------------------------ 构建
    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 10, 10)
        lay.setSpacing(6)

        head = QHBoxLayout()
        head.setSpacing(6)
        logo = QLabel()
        logo.setPixmap(icon_provider.app_pixmap(16))
        logo.setFixedSize(16, 16)
        head.addWidget(logo)
        title = QLabel("开机残留巡检")
        title.setStyleSheet("font-size: 9.5pt; font-weight: 600;")
        head.addWidget(title)
        self.chip = QLabel("自动运行")
        self.chip.setObjectName("Badge")
        head.addWidget(self.chip)
        head.addStretch(1)
        self.btn_close = QPushButton()
        self.btn_close.setObjectName("IconBtn")
        self.btn_close.setIcon(glyph_icon("close", 14, "#8B939E"))
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setToolTip("关闭小窗")
        head.addWidget(self.btn_close)
        lay.addLayout(head)

        body = QHBoxLayout()
        body.setSpacing(10)
        self.spinner = QLabel()
        self.spinner.setFixedSize(42, 42)
        self.movie = QMovie(theme.asset_path("scan_ring.gif"))
        if self.movie.isValid():
            self.movie.setScaledSize(QSize(42, 42))
            self.spinner.setMovie(self.movie)
        else:
            self.spinner.setPixmap(glyph_pixmap("radar", 38, theme.COLORS["accent"]))
        body.addWidget(self.spinner)

        info = QVBoxLayout()
        info.setSpacing(2)
        self.lb_main = QLabel("正在扫描…")
        self.lb_main.setStyleSheet("font-size: 10.5pt; font-weight: 600;")
        self.lb_main.setWordWrap(True)
        info.addWidget(self.lb_main)
        self.lb_sub = QLabel("0%")
        self.lb_sub.setObjectName("TileMeta")
        info.addWidget(self.lb_sub)
        self.lb_detail = QLabel("")
        self.lb_detail.setObjectName("SectionHint")
        self.lb_detail.setWordWrap(False)
        self.lb_detail.setFixedHeight(18)
        self.lb_detail.setAlignment(Qt.AlignmentFlag.AlignLeft |
                                    Qt.AlignmentFlag.AlignVCenter)
        info.addWidget(self.lb_detail)
        body.addLayout(info, 1)
        lay.addLayout(body)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(3)
        self.bar.setValue(0)
        lay.addWidget(self.bar)
        lay.addStretch(1)

        foot = QHBoxLayout()
        foot.setSpacing(6)
        self.cb_boot = QCheckBox("开机自动巡检")
        foot.addWidget(self.cb_boot)
        foot.addStretch(1)
        self.btn_review = QPushButton("查看清单")
        self.btn_review.setObjectName("Link")
        self.btn_clean = QPushButton("立即清理")
        self.btn_clean.setObjectName("Primary")
        self.btn_clean.setMinimumHeight(26)
        self.btn_clean.setVisible(False)
        foot.addWidget(self.btn_review)
        foot.addWidget(self.btn_clean)
        lay.addLayout(foot)

        self.btn_close.clicked.connect(self._on_close)
        self.cb_boot.toggled.connect(self._on_boot_toggled)
        self.btn_clean.clicked.connect(self._confirm_clean)
        self.btn_review.clicked.connect(self._open_review)

    def _place_bottom_right(self, margin: int = 16):
        screen = self.screen() or (self.parent().screen() if self.parent() else None)
        if screen is None:
            return
        geo = screen.availableGeometry()
        self.move(geo.right() - self.width() - margin,
                  geo.bottom() - self.height() - margin)

    def show_at_corner(self):
        self._place_bottom_right()
        self.show()
        self.raise_()

    # ------------------------------------------------------------ 扫描
    def start_scan(self):
        if self._scanning or self._cleaning:
            return
        self._scanning = True
        self.items = []
        self.lb_main.setText("正在扫描…")
        self.lb_sub.setText("0%")
        self.lb_detail.setText("读取进程、服务、目录与注册表")
        self.bar.setValue(0)
        self.btn_clean.setVisible(False)
        self.btn_review.setText("查看清单")
        self.set_chip("扫描中")
        self.spinner.setVisible(True)
        self._anim(True)

        self.worker = Worker(Worker.MODE_PATROL, parent=self)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._on_log)
        self.worker.result.connect(self._on_scan_done)
        self.worker.start()

    def _anim(self, on: bool):
        if on:
            if self.movie.isValid():
                self.spinner.setMovie(self.movie)
                self.movie.start()
            return
        if self.movie.isValid():
            self.movie.stop()
        self.spinner.setMovie(None)
        name = "check" if not self.items else "radar"
        tone = theme.COLORS["ok"] if not self.items else theme.COLORS["accent"]
        self.spinner.setPixmap(glyph_pixmap(name, 36, tone))

    def _on_log(self, message: str):
        if len(message) > 46:
            message = message[:44] + "…"
        self.lb_detail.setText(message)

    def _on_progress(self, pct: int, text: str):
        self.bar.setValue(max(0, min(100, int(pct))))
        shown = text if len(text) <= 26 else text[:24] + "…"
        self.lb_sub.setText(f"{pct}% · {shown}" if shown else f"{pct}%")

    def _on_scan_done(self, data: dict):
        self._scanning = False
        self.spinner.setVisible(True)
        self.items = list(data.get("items", []))
        total = data.get("total_size")
        if total is None:
            total = sum(getattr(i, "size", 0) for i in self.items)

        if not self.items:
            self.bar.setValue(100)
            self.lb_main.setText("没有发现残留")
            self.lb_sub.setText("这台机器目前是干净的")
            self.lb_detail.setText("小窗会在 8 秒后自动关闭")
            self.set_chip("已通过")
            self.btn_clean.setVisible(False)
            self.btn_review.setText("关闭")
            self._close_timer = QTimer(self)
            self._close_timer.setSingleShot(True)
            self._close_timer.timeout.connect(self.close)
            self._close_timer.start(8000)
            return

        self.bar.setValue(100)
        self.lb_main.setText(f"发现 {len(self.items)} 项残留")
        self.lb_sub.setText(cleanup.human_size(total))
        self.lb_detail.setText(self._preview_text())
        self.set_chip("待确认", "warn")
        self.btn_clean.setVisible(True)
        self.btn_clean.setText(f"立即清理（{len(self.items)}）")
        self.btn_review.setText("查看清单")

    def _preview_text(self) -> str:
        if not self.items:
            return ""
        first = f"{self.items[0].kind_label}·{self.items[0].label}"
        if len(self.items) == 1:
            return first
        return f"{first} 等 {len(self.items)} 项"

    def set_chip(self, text: str, level: str = "ok"):
        self.chip.setText(text)
        self.chip.setObjectName("BadgeWarn" if level == "warn" else "Badge")
        self.chip.style().unpolish(self.chip)
        self.chip.style().polish(self.chip)

    def _refresh_boot(self):
        try:
            enabled = bootguard.is_enabled()
        except Exception:
            enabled = False
        self.cb_boot.blockSignals(True)
        self.cb_boot.setChecked(enabled)
        self.cb_boot.blockSignals(False)

    # ------------------------------------------------------------ 清理
    def _confirm_clean(self):
        if not self.items or self._cleaning:
            return
        lines = []
        for item in self.items[:6]:
            lines.append(f"· [{item.kind_label}] {item.label}")
        if len(self.items) > 6:
            lines.append(f"· 另有 {len(self.items) - 6} 项")
        ret = QMessageBox.question(
            self, "确认清理残留",
            f"将删除以下 {len(self.items)} 项：\n" + "\n".join(lines) +
            "\n\n目录会整棵删除，删不掉的自动接管所有权并登记重启删除。继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            self._run_clean(self.items)

    def _run_clean(self, items: list):
        if self._cleaning or self._scanning:
            return
        self._cleaning = True
        self.lb_main.setText("正在清理…")
        self.btn_clean.setVisible(False)
        self.bar.setValue(0)
        self.spinner.setVisible(True)
        self._anim(True)

        self.worker = Worker(Worker.MODE_CLEAN, {"items": items}, self)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._on_log)
        self.worker.result.connect(self._on_clean_done)
        self.worker.start()

    def _on_clean_done(self, data: dict):
        self._cleaning = False
        self._anim(False)
        ok = int(data.get("ok", 0))
        fail = int(data.get("fail", 0))
        pending = int(data.get("pending", 0))
        self.bar.setValue(100)
        self.lb_main.setText("清理完成" if fail == 0 else "部分项目未清理")
        self.lb_sub.setText(
            f"成功 {ok} · 失败 {fail} · 重启删除 {pending}")
        self.lb_detail.setText("失败项可在主窗口的「解决方案」里查看")
        self.set_chip("已完成")
        self.btn_review.setText("查看清单")
        self._ask_reboot(ok, fail, pending)

    def _ask_reboot(self, ok: int, fail: int, pending: int):
        msg = f"清理结束：成功 {ok} 项，失败 {fail} 项。"
        if pending:
            msg += f"\n其中 {pending} 项已登记重启删除。"
        msg += "\n\n现在重启吗？选“是”会在 20 秒后重启，可执行 shutdown /a 撤销。"
        ret = QMessageBox.question(
            self, "是否重启", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        ok2, text = system_actions.schedule_reboot(20)
        if ok2:
            QMessageBox.information(self, "已安排重启",
                                   f"{text}。撤销：shutdown /a")
        else:
            QMessageBox.warning(self, "无法安排重启", text)

    def _open_review(self):
        if self.items and not self._scanning:
            dlg = ResidualDialog(self, deep=False, title="残留清单复查")
            dlg.exec()
            return
        self.close()

    def _on_boot_toggled(self, checked: bool):
        if checked:
            ok, text = bootguard.enable()
        else:
            ok, text = bootguard.disable()
        self._refresh_boot()
        if not ok:
            QMessageBox.warning(self, "设置未生效", text)

    def _on_close(self):
        if self._scanning or self._cleaning:
            ret = QMessageBox.question(
                self, "任务进行中", "扫描或清理还没结束，关闭会中断当前任务。确定关闭？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if ret != QMessageBox.StandardButton.Yes:
                return
            if self.worker and self.worker.isRunning():
                self.worker.request_stop()
                self.worker.wait(1500)
        self.closed.emit()
        self.close()

    def closeEvent(self, event):
        if self._close_timer:
            self._close_timer.stop()
        self.closed.emit()
        super().closeEvent(event)

    # ------------------------------------------------------------ 演示
    def demo_scanning(self, pct: int = 46):
        self._scanning = True
        self.lb_main.setText("正在扫描…")
        self.lb_sub.setText(f"{pct}% · 扫描 360Chrome\\Cache")
        self.lb_detail.setText("目录 1286/2740 · 命中 3 项候选")
        self.bar.setValue(pct)
        self.set_chip("扫描中", "warn")
        self._anim(True)

    def demo_result(self):
        self.items = [Item("dir", r"C:\Program Files (x86)\360\360Safe", "360Safe 安装目录",
                           size=1_612_345_678),
                      Item("registry", r"HKLM\SOFTWARE\WOW6432Node\360Safe", "360Safe 主键")]
        self._scanning = False
        self.bar.setValue(100)
        self.lb_main.setText("发现 12 项残留")
        self.lb_sub.setText("1.8 GB")
        self.lb_detail.setText("目录·360Safe 安装目录 等 12 项")
        self.set_chip("待确认", "warn")
        self.btn_clean.setVisible(True)
        self.btn_clean.setText("立即清理（12）")
        self._anim(False)
