"""通用界面组件：应用行、统计卡、控制台、宣传卡"""

import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QCheckBox, QFrame, QHBoxLayout, QLabel,
                               QPlainTextEdit, QProgressBar, QPushButton,
                               QSizePolicy, QVBoxLayout, QWidget)

from .. import icon_provider
from ..constants import APP_NAME
from . import theme


def _label(text: str, obj: str, parent=None) -> QLabel:
    lb = QLabel(text, parent)
    lb.setObjectName(obj)
    return lb


class AppRow(QFrame):
    """单个 360 应用行：勾选框 + 徽章 + 名称描述 + 状态 + 项目数。"""

    toggled = Signal(str, bool)

    def __init__(self, index: int, app: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("AppRow")
        self.app = app
        self.setProperty("checked", "false")
        self.setProperty("installed", "false")
        self.setFixedHeight(52)
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 3, 10, 3)
        lay.setSpacing(9)

        self.cb = QCheckBox()
        self.cb.setCursor(Qt.PointingHandCursor)
        self.cb.toggled.connect(self._on_toggle)
        self.cb.setChecked(False)
        self.cb.setEnabled(False)  # 扫描确认已安装后才可勾选
        lay.addWidget(self.cb)
        self.cb.setToolTip("勾选后可卸载该应用，也可以直接点击整行")

        badge = QLabel()
        badge.setPixmap(icon_provider.badge_icon(index, self._initial(app["name"]), 36)
                        .pixmap(36, 36))
        badge.setFixedSize(36, 36)
        lay.addWidget(badge)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        name = _label(app["name"], "AppName")
        desc = _label(app["desc"], "AppDesc")
        text_box.addWidget(name)
        text_box.addWidget(desc)
        lay.addLayout(text_box, 1)

        self.count_label = _label("", "AppDesc")
        self.count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.count_label.setMinimumWidth(74)
        lay.addWidget(self.count_label)
        self.state_label = _label("未检测到", "AppState")
        self.state_label.setProperty("state", "clean")
        self.state_label.setAlignment(Qt.AlignCenter)
        self.state_label.setMinimumWidth(66)
        lay.addWidget(self.state_label)

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
            # 徽章按文字长度自适应，避免“已注册安装信息”这类长文案溢出底色
            need_state = self.state_label.fontMetrics().horizontalAdvance(note) + 20
            self.state_label.setMinimumWidth(max(66, need_state))
            if item_count > 0:
                self.count_label.setText(f"{item_count} 项 · {size_text}")
            else:
                self.count_label.setText("暂无可清理项")
            # 右对齐标签被压窄时会裁掉左侧文字，按实际文字宽度留足空间
            need = self.count_label.fontMetrics().horizontalAdvance(
                self.count_label.text()) + 4
            self.count_label.setMinimumWidth(max(74, need))
            self.cb.setEnabled(True)
        else:
            self.state_label.setText("未检测到")
            self.state_label.setToolTip("未在注册表或安装目录发现该组件的安装信息")
            self.state_label.setProperty("state", "clean")
            self.state_label.setMinimumWidth(66)
            self.count_label.setText("—")
            self.count_label.setMinimumWidth(74)
            self.cb.setEnabled(False)
            self.cb.setChecked(False)
        self.state_label.style().unpolish(self.state_label)
        self.state_label.style().polish(self.state_label)

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


class StatCard(QFrame):
    def __init__(self, label: str, value: str = "0", parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setFixedHeight(58)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
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
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(8)
        dot = QLabel("●")
        dot.setStyleSheet("color:#12B76A; font-size:10pt;")
        title = _label("控制台", "ConsoleTitle")
        hint = _label("实时日志 / 执行进度", "ConsoleHint")
        hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        head.addWidget(dot)
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(hint)
        self.btn_clear = QPushButton("清屏")
        self.btn_clear.setObjectName("ConsoleGhost")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
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
        mono.setPointSize(9)
        lay.addWidget(self.console, 1)

        self.bar = QProgressBar()
        self.bar.setObjectName("ConsoleBar")
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        lay.addWidget(self.bar)

        self.stage = _label("待命", "ConsoleHint")
        lay.addWidget(self.stage)

        stats = QHBoxLayout()
        stats.setSpacing(8)
        self.stat_ok = self._mini_stat("已清理", "0")
        self.stat_fail = self._mini_stat("失败", "0")
        self.stat_freed = self._mini_stat("释放空间", "0 B")
        stats.addWidget(self.stat_ok[0])
        stats.addWidget(self.stat_fail[0])
        stats.addWidget(self.stat_freed[0])
        lay.addLayout(stats)

        self.btn_clear.clicked.connect(self.console.clear)

    def _mini_stat(self, name: str, value: str):
        card = QFrame()
        card.setObjectName("ConsoleStatCard")
        card.setFixedHeight(54)
        v = QVBoxLayout(card)
        v.setContentsMargins(10, 4, 10, 4)
        v.setSpacing(0)
        val = _label(value, "ConsoleStatValue")
        lab = _label(name, "ConsoleStatLabel")
        v.addWidget(val)
        v.addWidget(lab)
        return card, val

    def log(self, message: str, level: str = "info"):
        color = {"info": "#C9D6E3", "ok": "#3CCB7F", "warn": "#F7B267",
                 "err": "#F2777A", "title": "#7AA2F7"}.get(level, "#C9D6E3")
        ts = time.strftime("%H:%M:%S")
        safe = (message.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))
        self.console.appendHtml(
            f'<span style="color:#5D7186">{ts}</span> '
            f'<span style="color:{color}">{safe}</span>'
        )
        sb = self.console.verticalScrollBar()
        sb.setValue(sb.maximum())

    def set_stage(self, text: str):
        self.stage.setText(text)

    def set_progress(self, pct: int, text: str = ""):
        self.bar.setValue(max(0, min(100, pct)))
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
    """界面内 360 全家桶一键清除宣传区。"""

    action = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PromoCard")
        self.setMinimumHeight(124)
        self.setMaximumHeight(140)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(2)

        kicker = _label("360 全家桶专项清理", "PromoKicker")
        lay.addWidget(kicker)

        title = _label("360 一键清除", "PromoTitle")
        lay.addWidget(title)

        desc = _label("进程 / 服务 / 目录 / 注册表 / 任务 / 快捷方式；无权访问自动强删", "PromoDesc")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        self.btn = QPushButton("立即清除")
        self.btn.setObjectName("PromoBtn")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.clicked.connect(self.action.emit)
        row = QHBoxLayout()
        row.addWidget(self.btn)
        row.addStretch(1)
        lay.addLayout(row)

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
