"""通用界面组件：应用行、读数、控制台、宣传条

布局常量 COL_* 由主窗口表头复用，保证表头与数据行的列宽严格对齐。
"""

import time

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PySide6.QtWidgets import (QCheckBox, QFrame, QHBoxLayout, QLabel,
                               QPlainTextEdit, QProgressBar, QPushButton,
                               QSizePolicy, QVBoxLayout, QWidget)

from .. import icon_provider
from ..constants import APP_NAME
from . import theme

COL_CHECK = 15
COL_BADGE = 30
COL_STATE = 84
COL_COUNT = 88
COL_SIZE = 88
ROW_MARGIN_H = 12


def _label(text: str, obj: str, parent=None) -> QLabel:
    lb = QLabel(text, parent)
    lb.setObjectName(obj)
    return lb


class AppRow(QFrame):
    """单个 360 应用行：勾选框 + 徽章 + 名称描述 + 状态 + 项目数 + 占用。"""

    toggled = Signal(str, bool)

    def __init__(self, index: int, app: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("AppRow")
        self.app = app
        self.setProperty("checked", "false")
        self.setProperty("installed", "false")
        self.setProperty("dim", "false")
        self.setFixedHeight(46)
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(ROW_MARGIN_H, 2, ROW_MARGIN_H, 2)
        lay.setSpacing(8)

        self.cb = QCheckBox()
        self.cb.setCursor(Qt.PointingHandCursor)
        self.cb.setFixedWidth(COL_CHECK)
        self.cb.toggled.connect(self._on_toggle)
        self.cb.setChecked(False)
        self.cb.setEnabled(False)  # 扫描确认已安装后才可勾选
        lay.addWidget(self.cb)
        self.cb.setToolTip("勾选后可卸载该应用，也可以直接点击整行")

        badge = QLabel()
        badge.setPixmap(icon_provider.badge_icon(index, self._initial(app["name"]), COL_BADGE)
                        .pixmap(COL_BADGE, COL_BADGE))
        badge.setFixedSize(COL_BADGE, COL_BADGE)
        lay.addWidget(badge)

        text_box = QVBoxLayout()
        text_box.setSpacing(0)
        text_box.setContentsMargins(0, 0, 0, 0)
        name = _label(app["name"], "AppName")
        desc = _label(app["desc"], "AppDesc")
        text_box.addWidget(name)
        text_box.addWidget(desc)
        lay.addLayout(text_box, 1)

        self.count_label = _label("", "AppCount")
        self.count_label.setFixedWidth(COL_COUNT)
        self.count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(self.count_label)

        self.state_label = _label("未检测到", "AppState")
        self.state_label.setProperty("state", "clean")
        self.state_label.setFixedWidth(COL_STATE)
        self.state_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lay.addWidget(self.state_label)

        self.size_label = _label("", "AppSize")
        self.size_label.setFixedWidth(COL_SIZE)
        self.size_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(self.size_label)

    @staticmethod
    def _initial(name: str) -> str:
        for ch in name:
            if ch in " \t\u3000":
                continue
            if ch.isdigit():
                continue
            if ch.isascii():
                return ch.upper()
            return ch
        return "3"

    def _on_toggle(self, checked: bool):
        self.setProperty("checked", "true" if checked else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.toggled.emit(self.app["key"], checked)

    def set_state(self, installed: bool, note: str, item_count: int, size_text: str):
        self.setProperty("installed", "true" if installed else "false")
        if installed:
            state = "running" if note == "正在运行" else "installed"
            note = note or "已安装"
            self.state_label.setText(note)
            self.state_label.setToolTip(note)
            self.state_label.setProperty("state", state)
            self.count_label.setText(f"{item_count} 项" if item_count else "—")
            self.size_label.setText(size_text if item_count else "—")
            self.cb.setEnabled(True)
        else:
            self.state_label.setText("未检测到")
            self.state_label.setToolTip("未在注册表或安装目录发现该组件的安装信息")
            self.state_label.setProperty("state", "clean")
            self.count_label.setText("—")
            self.size_label.setText("—")
            self.setProperty("dim", "true")
            self.cb.setEnabled(False)
            self.cb.setChecked(False)
        self.state_label.style().unpolish(self.state_label)
        self.state_label.style().polish(self.state_label)
        self.style().unpolish(self)
        self.style().polish(self)

    def is_checked(self) -> bool:
        return self.cb.isChecked()

    def set_checked(self, value: bool):
        self.cb.setChecked(value)

    def set_interactive(self, on: bool):
        """任务执行期间锁住整行，避免误勾选导致状态与执行不一致。"""
        self.cb.setEnabled(on and self.property("installed") != "false")
        self.setCursor(Qt.PointingHandCursor if on else Qt.ArrowCursor)

    def mousePressEvent(self, event):
        # 整行可点：只点小方框对用户来说太窄，容易点空
        if event.button() == Qt.LeftButton and self.cb.isEnabled():
            self.cb.setChecked(not self.cb.isChecked())
            event.accept()
            return
        super().mousePressEvent(event)


def table_header() -> QWidget:
    """与 AppRow 列宽对齐的表头。"""
    head = QWidget()
    head.setObjectName("TableHead")
    head.setFixedHeight(26)
    lay = QHBoxLayout(head)
    lay.setContentsMargins(ROW_MARGIN_H + 2, 0, ROW_MARGIN_H, 6)
    lay.setSpacing(8)

    spacer = QLabel("")
    spacer.setFixedWidth(COL_CHECK)
    lay.addWidget(spacer)

    spacer2 = QLabel("")
    spacer2.setFixedWidth(COL_BADGE)
    lay.addWidget(spacer2)

    app_head = _label("应用 / 组件", "HeadCell")
    lay.addWidget(app_head, 1)

    count_head = _label("项目", "HeadCell")
    count_head.setFixedWidth(COL_COUNT)
    count_head.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    lay.addWidget(count_head)

    state_head = _label("状态", "HeadCell")
    state_head.setFixedWidth(COL_STATE)
    lay.addWidget(state_head)

    size_head = _label("占用", "HeadCell")
    size_head.setFixedWidth(COL_SIZE)
    size_head.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    lay.addWidget(size_head)
    return head


class StatCard(QFrame):
    """读数：无底色、无圆角，只靠左侧一条竖线与相邻读数分开。"""

    def __init__(self, label: str, value: str = "0", parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setFixedHeight(52)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 4, 8, 4)
        lay.setSpacing(0)
        self.value_label = _label(value, "StatValue")
        self.name_label = _label(label, "StatLabel")
        lay.addWidget(self.value_label)
        lay.addWidget(self.name_label)

    def set_value(self, text: str):
        self.value_label.setText(text)


class ConsoleWidget(QFrame):
    """右侧控制台：日志流 + 进度 + 关键指标。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ConsolePanel")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(9)

        head = QHBoxLayout()
        head.setSpacing(8)
        mark = QLabel("")
        mark.setFixedSize(3, 14)
        mark.setStyleSheet(f"background:{theme.COLORS['accent']};")
        title = _label("CONSOLE", "ConsoleTitle")
        hint = _label("实时日志 / 执行进度", "ConsoleHint")
        hint.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.btn_clear = QPushButton("清屏")
        self.btn_clear.setObjectName("ConsoleGhost")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        head.addWidget(mark)
        head.addWidget(title)
        head.addWidget(hint)
        head.addStretch(1)
        head.addWidget(self.btn_clear)
        lay.addLayout(head)

        self.console = QPlainTextEdit()
        self.console.setObjectName("Console")
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(4000)
        self.console.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.console.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.console.verticalScrollBar().setObjectName("ConsoleScroll")
        mono = QFont("Cascadia Mono")
        mono.setStyleHint(QFont.Monospace)
        mono.setPointSize(8)
        self.console.setFont(mono)
        self.console.setPlaceholderText("READY · 选择左侧操作，或等待扫描结果")
        pal = self.console.palette()
        pal.setColor(pal.ColorRole.PlaceholderText, QColor("#42566B"))
        self.console.setPalette(pal)
        lay.addWidget(self.console, 1)

        self.bar = QProgressBar()
        self.bar.setObjectName("ConsoleBar")
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(3)
        lay.addWidget(self.bar)

        stage_row = QHBoxLayout()
        stage_row.setSpacing(8)
        self.stage = _label("待命", "ConsoleHint")
        self.pct = _label("0%", "ConsoleHint")
        self.pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.pct.setFixedWidth(46)
        stage_row.addWidget(self.stage, 1)
        stage_row.addWidget(self.pct)
        lay.addLayout(stage_row)

        stats = QHBoxLayout()
        stats.setSpacing(0)
        self.stat_ok = self._mini_stat("已清理", "0")
        self.stat_fail = self._mini_stat("失败", "0")
        self.stat_freed = self._mini_stat("释放空间", "0 B")
        stats.addWidget(self.stat_ok[0], 1)
        stats.addWidget(self.stat_fail[0], 1)
        stats.addWidget(self.stat_freed[0], 1)
        lay.addLayout(stats)

        self.btn_clear.clicked.connect(self.console.clear)

    def _mini_stat(self, name: str, value: str):
        card = QFrame()
        card.setObjectName("ConsoleStatCard")
        card.setFixedHeight(52)
        v = QVBoxLayout(card)
        v.setContentsMargins(0, 6, 0, 2)
        v.setSpacing(0)
        val = _label(value, "ConsoleStatValue")
        lab = _label(name, "ConsoleStatLabel")
        v.addWidget(val)
        v.addWidget(lab)
        return card, val

    def log(self, message: str, level: str = "info"):
        color = {"info": "#C4D3E2", "ok": "#55D08C", "warn": "#E9B269",
                 "err": "#F27378", "title": "#E0A03C"}.get(level, "#C4D3E2")
        ts = time.strftime("%H:%M:%S")
        safe = (message.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))
        self.console.appendHtml(
            f'<span style="color:#4E6176">{ts}&nbsp;&nbsp;</span>'
            f'<span style="color:{color}">{safe}</span>'
        )
        sb = self.console.verticalScrollBar()
        sb.setValue(sb.maximum())

    def set_stage(self, text: str):
        self.stage.setText(text)

    def set_progress(self, pct: int, text: str = ""):
        value = max(0, min(100, pct))
        self.bar.setValue(value)
        self.pct.setText(f"{value}%")
        if text:
            self.stage.setText(text)

    def set_stats(self, ok=None, fail=None, freed=None):
        if ok is not None:
            self.stat_ok[1].setText(str(ok))
        if fail is not None:
            self.stat_fail[1].setText(str(fail))
        if freed is not None:
            self.stat_freed[1].setText(freed)


class PromoCard(QFrame):
    """底部宣传条：360 全家桶一键全部移除。"""

    action = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PromoCard")
        self.setMinimumHeight(92)
        self.setMaximumHeight(104)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 10, 18, 10)
        lay.setSpacing(16)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        kicker = _label("360 全家桶 · 彻底清除", "PromoKicker")
        title = _label("360 一键全部移除", "PromoTitle")
        desc = _label("进程 / 服务 / 目录 / 注册表 / 计划任务 / 快捷方式；"
                      "无权访问自动接管所有权并强删", "PromoDesc")
        desc.setWordWrap(True)
        text_box.addWidget(kicker)
        text_box.addWidget(title)
        text_box.addWidget(desc)
        lay.addLayout(text_box, 1)

        self.btn = QPushButton("全部移除")
        self.btn.setObjectName("PromoBtn")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setMinimumWidth(112)
        self.btn.setMinimumHeight(34)
        self.btn.clicked.connect(self.action.emit)
        lay.addWidget(self.btn, 0, Qt.AlignVCenter)

    def set_button_state(self, enabled: bool, text: str = "", tooltip: str = ""):
        self.btn.setEnabled(enabled)
        self.btn.setCursor(Qt.PointingHandCursor if enabled else Qt.ArrowCursor)
        if text:
            self.btn.setText(text)
        if tooltip:
            self.btn.setToolTip(tooltip)


class EmptyState(QWidget):
    def __init__(self, text: str = "暂无数据", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lb = QLabel(text)
        lb.setAlignment(Qt.AlignCenter)
        lb.setStyleSheet(f"color:{theme.COLORS['text_muted']}; font-size:9pt;")
        lay.addWidget(lb)


class BottomFade(QWidget):
    """列表底部渐隐：让被截断的行淡出，而不是硬切一刀。"""

    def __init__(self, target: QWidget, height: int = 26, parent=None):
        super().__init__(parent or target)
        self._target = target
        self._h = height
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        target.installEventFilter(self)
        self._sync()

    def _sync(self):
        self.setGeometry(0, self._target.height() - self._h,
                         self._target.width(), self._h)
        self.raise_()

    def eventFilter(self, obj, event):
        if obj is self._target and event.type() == QEvent.Resize:
            self._sync()
        return False

    def paintEvent(self, _event):
        gradient = QLinearGradient(0, 0, 0, self.height())
        base = QColor(theme.COLORS["bg"])
        top = QColor(base)
        top.setAlpha(0)
        bottom = QColor(base)
        bottom.setAlpha(235)
        gradient.setColorAt(0.0, top)
        gradient.setColorAt(1.0, bottom)
        painter = QPainter(self)
        painter.fillRect(self.rect(), gradient)
