"""开机巡检小窗：常驻右下角、带扫描动画、删除后询问是否重启。

设计边界（与 README 里的安全说明一致）：
  1. 只在用户显式同意后登记开机启动，勾选框随时可撤销；
  2. 窗口始终可见、可关闭，扫描与删除都在这里显示进度；
  3. 删除前给出数量与目录清单并要求再确认一次；
  4. 重启只发生在用户点“现在重启”之后，并留 20 秒取消窗口。
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QHBoxLayout,
                               QLabel, QMessageBox, QProgressBar, QPushButton,
                               QVBoxLayout, QWidget)

from .. import bootguard, cleanup, icon_provider, system_actions
from ..scanner import Item
from ..worker import Worker
from . import theme
from .residual_dialog import ResidualDialog


class ScanOrbit(QWidget):
    """扫描动画：一圈扫过的光弧 + 中心呼吸点，纯 QPainter 绘制。"""

    def __init__(self, diameter: int = 54, parent=None):
        super().__init__(parent)
        self.setFixedSize(diameter, diameter)
        self._angle = 0.0
        self._pulse = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(45)
        self._timer.timeout.connect(self._tick)
        self._active = False

    def start(self):
        self._active = True
        self._timer.start()

    def stop(self):
        self._active = False
        self._timer.stop()
        self.update()

    def is_running(self) -> bool:
        return self._timer.isActive()

    def _tick(self):
        self._angle = (self._angle + 7.5) % 360
        self._pulse = (self._pulse + 0.16) % 6.283
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        side = min(self.width(), self.height())
        box = QRectF(1, 1, side - 2, side - 2)

        ring = QPen(QColor(theme.COLORS["row_line"]))
        ring.setWidthF(1.0)
        painter.setPen(ring)
        painter.drawEllipse(box)

        arc = QPen(QColor(theme.COLORS["accent"]))
        arc.setWidthF(2.4)
        painter.setPen(arc)
        painter.drawArc(box, int((-self._angle) * 16), int(100 * 16))

        tail = QPen(QColor(theme.COLORS["accent_soft"]))
        tail.setWidthF(2.0)
        painter.setPen(tail)
        painter.drawArc(box, int((-self._angle - 70) * 16), int(26 * 16))

        breath = 2.4 + 1.2 * (0.5 + 0.5 * math.sin(self._pulse))
        dot = QColor(theme.COLORS["accent"])
        dot.setAlpha(215)
        painter.setPen(Qt.NoPen)
        painter.setBrush(dot)
        painter.drawEllipse(QPointF(side / 2, side / 2), breath, breath)


class PatrolWindow(QFrame):
    """开机巡检主窗口（右下角小窗）。"""

    closed = Signal()

    def __init__(self, parent=None, auto_start: bool = True):
        super().__init__(None)
        self._parent_window = parent
        self.setObjectName("PatrolCard")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedWidth(430)
        self.setMinimumHeight(238)

        self.items: list[Item] = []
        self.worker: Worker | None = None
        self._scanning = False
        self._cleaning = False
        self._result: dict = {}

        self._build()
        self._place_bottom_right()
        if auto_start:
            QTimer.singleShot(600, self.start_scan)

    # ------------------------------------------------------------------ 构建
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 13, 16, 13)
        root.setSpacing(9)

        head = QHBoxLayout()
        head.setSpacing(8)
        logo = QLabel()
        logo.setPixmap(icon_provider.app_pixmap(20))
        logo.setFixedSize(20, 20)
        head.addWidget(logo)

        title = QLabel("开机残留巡检")
        title.setObjectName("PatrolTitle")
        head.addWidget(title)

        self.lb_mode = QLabel("自动运行")
        self.lb_mode.setObjectName("PatrolChip")
        head.addWidget(self.lb_mode)
        head.addStretch(1)

        self.lb_pct = QLabel("0%")
        self.lb_pct.setObjectName("PatrolPct")
        head.addWidget(self.lb_pct)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("HudClose")
        self.btn_close.setFixedSize(18, 18)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setToolTip("关闭巡检窗口")
        self.btn_close.clicked.connect(self._on_close)
        head.addWidget(self.btn_close)
        root.addLayout(head)

        body = QHBoxLayout()
        body.setSpacing(12)
        self.orbit = ScanOrbit(54)
        body.addWidget(self.orbit, 0, Qt.AlignVCenter)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        self.lb_status = QLabel("正在检查 360 残留…")
        self.lb_status.setObjectName("PatrolStatus")
        self.lb_detail = QLabel("准备扫描全部 360 目录")
        self.lb_detail.setObjectName("PatrolDetail")
        self.lb_detail.setWordWrap(False)
        texts.addWidget(self.lb_status)
        texts.addWidget(self.lb_detail)
        body.addLayout(texts, 1)
        root.addLayout(body)

        self.bar = QProgressBar()
        self.bar.setObjectName("PatrolBar")
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFixedHeight(4)
        self.bar.setTextVisible(False)
        root.addWidget(self.bar)

        stats = QHBoxLayout()
        stats.setSpacing(10)
        self.lb_count = QLabel("发现 0 项")
        self.lb_count.setObjectName("PatrolStat")
        self.lb_size = QLabel("占用 0 B")
        self.lb_size.setObjectName("PatrolStatDim")
        stats.addWidget(self.lb_count)
        stats.addWidget(self.lb_size)
        stats.addStretch(1)
        self.lb_scope = QLabel("扫描范围：全部 360 目录")
        self.lb_scope.setObjectName("PatrolStatDim")
        stats.addWidget(self.lb_scope)
        root.addLayout(stats)

        acts = QHBoxLayout()
        acts.setSpacing(8)
        self.cb_boot = QCheckBox("下次开机继续巡检")
        self.cb_boot.setObjectName("PatrolCheck")
        self.cb_boot.setChecked(bootguard.is_enabled())
        self.cb_boot.toggled.connect(self._on_boot_toggled)
        self.cb_boot.setToolTip("勾选后在下次开机时自动弹出本窗口；取消勾选即撤销，不留后台服务")
        acts.addWidget(self.cb_boot)
        acts.addStretch(1)

        self.btn_review = QPushButton("查看清单")
        self.btn_review.setObjectName("Ghost")
        self.btn_review.setCursor(Qt.PointingHandCursor)
        self.btn_review.setEnabled(False)
        self.btn_review.clicked.connect(self._open_review)

        self.btn_clean = QPushButton("立即清理")
        self.btn_clean.setObjectName("Primary")
        self.btn_clean.setCursor(Qt.PointingHandCursor)
        self.btn_clean.setEnabled(False)
        self.btn_clean.setMinimumHeight(30)
        self.btn_clean.clicked.connect(self._confirm_clean)
        acts.addWidget(self.btn_review)
        acts.addWidget(self.btn_clean)
        root.addLayout(acts)

    def _place_bottom_right(self, margin: int = 18):
        screen = None
        if self._parent_window is not None:
            screen = self._parent_window.screen()
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        self.adjustSize()
        self.move(geo.right() - self.width() - margin,
                  geo.bottom() - self.height() - margin)

    def show_at_corner(self):
        self._place_bottom_right()
        self.show()
        self.raise_()

    # ------------------------------------------------------------------ 扫描
    def start_scan(self):
        if self._scanning or self._cleaning:
            return
        self._scanning = True
        self.items = []
        self._result = {}
        self.lb_status.setText("正在检查 360 残留…")
        self.lb_detail.setText("准备扫描全部 360 目录")
        self.lb_count.setText("发现 0 项")
        self.lb_size.setText("占用 0 B")
        self.lb_pct.setText("0%")
        self.bar.setValue(0)
        self.btn_clean.setEnabled(False)
        self.btn_review.setEnabled(False)
        self.orbit.start()

        self.worker = Worker(Worker.MODE_PATROL, parent=self)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._on_log)
        self.worker.result.connect(self._on_scan_done)
        self.worker.start()

    def _on_log(self, message: str):
        if message.strip():
            self.lb_detail.setText(self._elide(message))

    def _on_progress(self, pct: int, text: str):
        pct = max(0, min(100, int(pct)))
        self.bar.setValue(pct)
        self.lb_pct.setText(f"{pct}%")
        if text:
            self.lb_status.setText(self._elide(text, 26))
            self.lb_detail.setText(self._elide(text, 44))

    def _on_scan_done(self, data: dict):
        self._scanning = False
        self.orbit.stop()
        self.bar.setValue(100)
        self.lb_pct.setText("100%")
        self.items = data.get("items", [])

        if not self.items:
            self.lb_status.setText("未发现 360 残留")
            self.lb_detail.setText("系统很干净，窗口将在 8 秒后自动关闭")
            self.lb_count.setText("发现 0 项")
            self.lb_size.setText("无需清理")
            QTimer.singleShot(8000, self._on_close)
            return

        total = sum(i.size for i in self.items)
        dirs = sum(1 for i in self.items if i.kind == "dir")
        self.lb_status.setText(f"发现 {len(self.items)} 项 360 残留")
        self.lb_detail.setText(f"其中 {dirs} 个 360 目录，可整体删除清空")
        self.lb_count.setText(f"发现 {len(self.items)} 项")
        self.lb_size.setText(f"占用 {cleanup.human_size(total)}")
        self.btn_clean.setEnabled(True)
        self.btn_review.setEnabled(True)
        self.btn_clean.setText(f"立即清理（{len(self.items)}）")

    def _elide(self, text: str, width_budget: int = 44) -> str:
        text = str(text).replace("\n", " ")
        return text if len(text) <= width_budget else text[: width_budget - 1] + "…"

    # ------------------------------------------------------------------ 清理
    def _confirm_clean(self):
        if self._cleaning or not self.items:
            return
        total = sum(i.size for i in self.items)
        preview = "\n".join(f"· [{i.kind_label}] {i.label}" for i in self.items[:6])
        more = f"\n…… 另有 {len(self.items) - 6} 项" if len(self.items) > 6 else ""
        ret = QMessageBox.question(
            self, "确认清理 360 残留",
            f"即将删除 {len(self.items)} 项（约 {cleanup.human_size(total)}）：\n\n"
            f"{preview}{more}\n\n"
            "删除顺序：结束占用进程 → 接管所有权强力删除 → 注册表备份后清理。\n"
            "仍被系统锁住的会登记到下次开机时删除。删除不可恢复，确定继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            self.lb_detail.setText("已取消清理，残留保持原样")
            return
        self._run_clean(self.items)

    def _run_clean(self, items: list[Item]):
        self._cleaning = True
        self.orbit.start()
        self.btn_clean.setEnabled(False)
        self.btn_review.setEnabled(False)
        self.cb_boot.setEnabled(False)
        self.bar.setValue(0)
        self.lb_status.setText("正在清理…")
        self.lb_detail.setText(f"共 {len(items)} 项")

        self.worker = Worker(Worker.MODE_CLEAN, {"items": items}, parent=self)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(lambda m: self.lb_detail.setText(self._elide(m, 46)))
        self.worker.result.connect(self._on_clean_done)
        self.worker.start()

    def _on_clean_done(self, data: dict):
        self._cleaning = False
        self.orbit.stop()
        self._result = data
        self.cb_boot.setEnabled(True)
        ok = data.get("ok", 0)
        fail = data.get("fail", 0)
        pending = data.get("pending", 0)
        freed = data.get("freed_text", "0 B")
        self.items = []
        self.btn_clean.setEnabled(False)
        self.btn_review.setEnabled(False)
        self.btn_clean.setText("立即清理")
        self.bar.setValue(100)
        self.lb_pct.setText("100%")
        self.lb_status.setText(f"清理完成：成功 {ok} 项，释放 {freed}")
        detail = []
        if pending:
            detail.append(f"{pending} 项已登记重启后删除")
        if fail:
            detail.append(f"{fail} 项未能删除")
        self.lb_detail.setText("，".join(detail) if detail else "全部项目已处理完毕")
        self.lb_count.setText(f"成功 {ok} 项")
        self.lb_size.setText(f"释放 {freed}")
        self._ask_reboot(ok, fail, pending)

    # ------------------------------------------------------------------ 重启
    def _ask_reboot(self, ok: int, fail: int, pending: int):
        if ok == 0 and pending == 0:
            return
        if pending or fail:
            text = (f"清理完成：成功 {ok} 项，{pending} 项要在重启后才会真正消失"
                    f"（失败 {fail} 项）。\n\n现在就重启电脑完成收尾吗？")
        else:
            text = f"清理完成：成功 {ok} 项。\n\n建议重启一次让系统彻底释放被占用的文件。现在重启吗？"
        ret = QMessageBox.question(
            self, "是否重启电脑",
            text + "\n\n选择“是”后会有 20 秒倒计时，期间可在命令行执行 shutdown /a 取消。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            self.lb_detail.setText("已选择稍后重启，残留文件将在下次开机时处理")
            return

        ok_sched, msg = system_actions.schedule_reboot(20)
        if ok_sched:
            QMessageBox.information(
                self, "已安排重启",
                "系统将在 20 秒后重启。\n若要取消，请在命令行执行：shutdown /a")
            QTimer.singleShot(0, QApplication.quit)
        else:
            QMessageBox.warning(self, "重启失败", f"无法安排重启：{msg}\n请手动重启电脑。")

    # ------------------------------------------------------------------ 清单
    def _open_review(self):
        if not self.items:
            return
        dlg = ResidualDialog(self, deep=False, title="巡检结果 · 残余清单",
                             items=self.items)
        dlg.finished_cleanup.connect(self._on_review_cleanup)
        dlg.exec()

    def _on_review_cleanup(self, data: dict):
        ok = data.get("ok", 0)
        fail = data.get("fail", 0)
        pending = data.get("pending", 0)
        self.lb_status.setText(f"清单清理完成：成功 {ok} 项")
        self.lb_detail.setText(f"失败 {fail} 项，{pending} 项待重启后删除")
        self._ask_reboot(ok, fail, pending)

    # ------------------------------------------------------------------ 开关
    def _on_boot_toggled(self, checked: bool):
        ok, msg = bootguard.sync_state(bool(checked))
        self.lb_detail.setText(msg)
        if not ok:
            self.cb_boot.blockSignals(True)
            self.cb_boot.setChecked(not checked)
            self.cb_boot.blockSignals(False)
            QMessageBox.warning(self, "开机巡检登记失败", msg)

    # ------------------------------------------------------------------ 预览
    def demo_scanning(self, pct: int = 46):
        """预览用：模拟扫描中的状态（不启动线程）。"""
        self.orbit.start()
        self.bar.setValue(pct)
        self.lb_pct.setText(f"{pct}%")
        self.lb_status.setText("正在检查 360 残留…")
        self.lb_detail.setText("扫描 360 目录 11/26：360Safe")
        self.lb_count.setText("已扫 11 个目录")
        self.lb_size.setText("扫描范围：全部 360 目录")

    def demo_result(self):
        """预览用：填充示例扫描结果。"""
        demo = [
            Item("dir", r"C:\Program Files (x86)\360\360Safe", r"C:\Program Files (x86)\360\360Safe", "", "360 目录", 553_648_128),
            Item("dir", r"C:\Program Files (x86)\360\360sd", r"C:\Program Files (x86)\360\360sd", "", "360 目录", 226_492_416),
            Item("dir", r"C:\ProgramData\360safe", r"C:\ProgramData\360safe", "", "360 目录", 41_943_040),
            Item("dir", r"C:\Users\Administrator\AppData\Roaming\360safe", r"…\Roaming\360safe", "", "360 目录", 12_582_912),
            Item("dir", r"D:\360Downloads", r"D:\360Downloads", "", "360 目录", 1_073_741_824),
            Item("service", "360rp", "360rp", "", "360 服务"),
            Item("task", "360安全卫士-每日体检", "360安全卫士-每日体检", "", "残留任务"),
            Item("registry", r"HKLM\SOFTWARE\WOW6432Node\360Safe", r"HKLM\SOFTWARE\WOW6432Node\360Safe", "", "残留注册表"),
            Item("registry", r"HKCU\Software\360Safe", r"HKCU\Software\360Safe", "", "残留注册表"),
            Item("dll", r"C:\Windows\System32\360FsFlt.sys", "360FsFlt.sys", "", "驱动残留", 286_720),
            Item("file", r"C:\Users\Administrator\Downloads\360safe_setup.exe", "360safe_setup.exe", "", "深度扫描", 58_720_256),
            Item("startup", r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup\360Safe.lnk", "360Safe.lnk", "", "开机启动项", 1024),
        ]
        self._on_scan_done({"items": demo, "total_size": sum(i.size for i in demo)})

    def _on_close(self):
        if self._scanning or self._cleaning:
            ret = QMessageBox.question(
                self, "任务仍在进行",
                "扫描或清理还没有结束，现在关闭会中止剩余步骤。确定关闭吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return
            if self.worker and self.worker.isRunning():
                self.worker.request_stop()
                self.worker.wait(2500)
        self.closed.emit()
        self.close()
        QApplication.quit()
