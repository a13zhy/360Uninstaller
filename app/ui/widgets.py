"""界面组件：线性图标、导航项、模式卡、应用行、技术面板、推广位、解决方案

所有图标都用 QPainter 现画，不依赖 svg 插件，任意 DPI 下都清晰。
"""

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (QCheckBox, QFrame, QHBoxLayout, QLabel,
                               QProgressBar, QPushButton, QVBoxLayout, QWidget)

from .. import constants, icon_provider
from . import theme

GLYPH_NAMES = {
    "clean", "bundle", "info", "radar", "shield", "update", "close", "min",
    "retry", "ai", "bird", "check", "clock", "lock",
}


def paint_glyph(p: QPainter, name: str, rect: QRectF, color: str, w: float = 1.6):
    p.save()
    pen = QPen(QColor(color))
    pen.setWidthF(w)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    x, y, s = rect.x(), rect.y(), min(rect.width(), rect.height())
    u = s / 24.0

    if name == "clean":
        p.drawLine(QPointF(x + 13 * u, y + 4 * u), QPointF(x + 17 * u, y + 8 * u))
        path = QPainterPath()
        path.moveTo(x + 12 * u, y + 9 * u)
        path.lineTo(x + 15 * u, y + 12 * u)
        path.lineTo(x + 8 * u, y + 19 * u)
        path.lineTo(x + 5 * u, y + 16 * u)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(x + 5 * u, y + 20 * u), QPointF(x + 8 * u, y + 17 * u))
    elif name == "bundle":
        for cx, cy in ((6, 18), (12, 12), (18, 6)):
            p.drawEllipse(QPointF(x + cx * u, y + cy * u), 2.2 * u, 2.2 * u)
        p.drawLine(QPointF(x + 7.6 * u, y + 16.4 * u), QPointF(x + 10.4 * u, y + 13.6 * u))
        p.drawLine(QPointF(x + 13.6 * u, y + 10.4 * u), QPointF(x + 16.4 * u, y + 7.6 * u))
    elif name == "info":
        p.drawEllipse(QRectF(x + 3 * u, y + 3 * u, 18 * u, 18 * u))
        p.drawLine(QPointF(x + 12 * u, y + 11 * u), QPointF(x + 12 * u, y + 17 * u))
        p.drawEllipse(QPointF(x + 12 * u, y + 7.6 * u), 0.9 * u, 0.9 * u)
    elif name == "radar":
        p.drawEllipse(QRectF(x + 3 * u, y + 3 * u, 18 * u, 18 * u))
        p.drawEllipse(QRectF(x + 7.6 * u, y + 7.6 * u, 8.8 * u, 8.8 * u))
        p.drawLine(QPointF(x + 12 * u, y + 12 * u), QPointF(x + 18 * u, y + 6 * u))
        p.drawEllipse(QPointF(x + 16.2 * u, y + 7.8 * u), 1.1 * u, 1.1 * u)
    elif name == "shield":
        path = QPainterPath()
        path.moveTo(x + 12 * u, y + 3 * u)
        path.lineTo(x + 19 * u, y + 6 * u)
        path.lineTo(x + 19 * u, y + 12 * u)
        path.cubicTo(x + 19 * u, y + 17 * u, x + 15.5 * u, y + 20 * u,
                     x + 12 * u, y + 21.5 * u)
        path.cubicTo(x + 8.5 * u, y + 20 * u, x + 5 * u, y + 17 * u,
                     x + 5 * u, y + 12 * u)
        path.lineTo(x + 5 * u, y + 6 * u)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(x + 9 * u, y + 12 * u), QPointF(x + 11.4 * u, y + 14.4 * u))
        p.drawLine(QPointF(x + 11.4 * u, y + 14.4 * u), QPointF(x + 15.4 * u, y + 9.6 * u))
    elif name == "update":
        p.drawEllipse(QRectF(x + 4 * u, y + 4 * u, 16 * u, 16 * u))
        p.drawLine(QPointF(x + 12 * u, y + 7.4 * u), QPointF(x + 12 * u, y + 12 * u))
        p.drawLine(QPointF(x + 12 * u, y + 12 * u), QPointF(x + 15.4 * u, y + 14 * u))
    elif name == "clock":
        p.drawEllipse(QRectF(x + 3.4 * u, y + 3.4 * u, 17.2 * u, 17.2 * u))
        p.drawLine(QPointF(x + 12 * u, y + 7.4 * u), QPointF(x + 12 * u, y + 12 * u))
        p.drawLine(QPointF(x + 12 * u, y + 12 * u), QPointF(x + 15 * u, y + 14.2 * u))
    elif name == "retry":
        path = QPainterPath()
        path.arcMoveTo(QRectF(x + 4 * u, y + 4 * u, 16 * u, 16 * u), 40)
        path.arcTo(QRectF(x + 4 * u, y + 4 * u, 16 * u, 16 * u), 40, 280)
        p.drawPath(path)
        p.drawLine(QPointF(x + 14.6 * u, y + 3.4 * u), QPointF(x + 19.4 * u, y + 6.2 * u))
        p.drawLine(QPointF(x + 14.6 * u, y + 3.4 * u), QPointF(x + 13.2 * u, y + 7.4 * u))
    elif name == "ai":
        p.drawRoundedRect(QRectF(x + 4 * u, y + 6 * u, 16 * u, 12 * u), 2.4 * u, 2.4 * u)
        p.drawEllipse(QPointF(x + 9.4 * u, y + 12 * u), 1.1 * u, 1.1 * u)
        p.drawEllipse(QPointF(x + 14.6 * u, y + 12 * u), 1.1 * u, 1.1 * u)
        p.drawLine(QPointF(x + 12 * u, y + 6 * u), QPointF(x + 12 * u, y + 3.4 * u))
        p.drawLine(QPointF(x + 4 * u, y + 16 * u), QPointF(x + 4 * u, y + 18.4 * u))
        p.drawLine(QPointF(x + 20 * u, y + 16 * u), QPointF(x + 20 * u, y + 18.4 * u))
    elif name == "bird":
        path = QPainterPath()
        path.moveTo(x + 4 * u, y + 14 * u)
        path.cubicTo(x + 8 * u, y + 7 * u, x + 14 * u, y + 6 * u, x + 20 * u, y + 9 * u)
        path.cubicTo(x + 17 * u, y + 15 * u, x + 11 * u, y + 18.4 * u, x + 5 * u, y + 16.4 * u)
        p.drawPath(path)
        p.drawEllipse(QPointF(x + 15.4 * u, y + 10 * u), 0.9 * u, 0.9 * u)
    elif name == "check":
        p.drawLine(QPointF(x + 6 * u, y + 12.4 * u), QPointF(x + 10.2 * u, y + 16.8 * u))
        p.drawLine(QPointF(x + 10.2 * u, y + 16.8 * u), QPointF(x + 18 * u, y + 7.6 * u))
    elif name == "close":
        p.drawLine(QPointF(x + 7 * u, y + 7 * u), QPointF(x + 17 * u, y + 17 * u))
        p.drawLine(QPointF(x + 17 * u, y + 7 * u), QPointF(x + 7 * u, y + 17 * u))
    elif name == "min":
        p.drawLine(QPointF(x + 6 * u, y + 12 * u), QPointF(x + 18 * u, y + 12 * u))
    elif name == "lock":
        p.drawRoundedRect(QRectF(x + 6 * u, y + 11 * u, 12 * u, 9 * u), 1.6 * u, 1.6 * u)
        path = QPainterPath()
        path.arcMoveTo(QRectF(x + 8 * u, y + 5 * u, 8 * u, 10 * u), 0)
        path.arcTo(QRectF(x + 8 * u, y + 5 * u, 8 * u, 10 * u), 0, 180)
        p.drawPath(path)
    p.restore()


def glyph_pixmap(name: str, size: int = 16, color: str = "#5B6470") -> QPixmap:
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    paint_glyph(p, name, QRectF(0, 0, size, size), color, 1.6)
    p.end()
    return pm


def glyph_icon(name: str, size: int = 16, color: str = "#5B6470") -> QIcon:
    return QIcon(glyph_pixmap(name, size, color))


class IconGlyph(QWidget):
    """按名字画一个线性图标，居中。"""

    def __init__(self, name: str, size: int = 16, color: str = "#5B6470", parent=None):
        super().__init__(parent)
        self.name = name
        self.color = color
        self.setFixedSize(size, size)

    def set_color(self, color: str):
        self.color = color
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        paint_glyph(p, self.name, QRectF(0, 0, self.width(), self.height()), self.color, 1.6)
        p.end()


class NavItem(QPushButton):
    def __init__(self, text: str, glyph: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("NavItem")
        self.setCheckable(True)
        self._glyph = glyph
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIcon(glyph_icon(glyph, 16, theme.COLORS["text_sub"]))
        self.setIconSize(QSize(16, 16))
        self.toggled.connect(self._recolor)

    def _recolor(self, checked: bool):
        color = theme.COLORS["accent_dark"] if checked else theme.COLORS["text_sub"]
        self.setIcon(glyph_icon(self._glyph, 16, color))


class ModeCard(QFrame):
    """二选一的模式卡：单选圆点 + 标题 + 一行说明。"""

    clicked = Signal(str)

    def __init__(self, key: str, title: str, line: str, badge: str = "", parent=None):
        super().__init__(parent)
        self.key = key
        self._active = False
        self.setObjectName("ModeCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("active", False)
        self.setMinimumHeight(62)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(10)

        text = QVBoxLayout()
        text.setSpacing(1)
        head = QHBoxLayout()
        head.setSpacing(6)
        self.title = QLabel(title)
        self.title.setObjectName("TileName")
        head.addWidget(self.title)
        if badge:
            tag = QLabel(badge)
            tag.setObjectName("Badge")
            head.addWidget(tag)
        head.addStretch(1)
        self.line = QLabel(line)
        self.line.setObjectName("TileMeta")
        text.addLayout(head)
        text.addWidget(self.line)
        row.addLayout(text, 1)

        self._radio_painted = _RadioDot(self)
        row.addWidget(self._radio_painted)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)

    def set_active(self, on: bool):
        self._active = bool(on)
        self.setProperty("active", bool(on))
        self._radio_painted.set_active(bool(on))
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class _RadioDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._on = False

    def set_active(self, on: bool):
        self._on = bool(on)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(1, 1, 14, 14)
        if self._on:
            p.setPen(QPen(QColor(theme.COLORS["accent"]), 1.2))
            p.setBrush(QColor(theme.COLORS["accent"]))
            p.drawEllipse(rect)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#FFFFFF"))
            p.drawEllipse(QRectF(4.6, 4.6, 6.8, 6.8))
        else:
            p.setPen(QPen(QColor("#C9D0D8"), 1.2))
            p.setBrush(QColor("#FFFFFF"))
            p.drawEllipse(rect)
        p.end()


class AppTile(QFrame):
    """一行应用：勾选 + 图标 + 名称/证据 + 体积。"""

    toggled = Signal(str, bool)

    def __init__(self, found, parent=None):
        super().__init__(parent)
        self.key = found.key
        self.found = found
        self.setObjectName("AppTile")
        self.setProperty("checked", False)
        self.setMinimumHeight(52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 6, 12, 6)
        row.setSpacing(10)

        self.box = QCheckBox(self)
        self.box.setChecked(False)
        self.box.toggled.connect(self._on_box)
        row.addWidget(self.box)

        self.icon = QLabel(self)
        self.icon.setFixedSize(28, 28)
        qicon = icon_provider.installed_icon(found.app)
        if qicon.isNull():
            pm = glyph_pixmap("shield", 22, theme.COLORS["accent"])
        else:
            pm = qicon.pixmap(28, 28)
        self.icon.setPixmap(pm)
        row.addWidget(self.icon)

        text = QVBoxLayout()
        text.setSpacing(1)
        head = QHBoxLayout()
        head.setSpacing(6)
        name = QLabel(found.name)
        name.setObjectName("TileName")
        head.addWidget(name)
        if found.app.get("tag"):
            tag = QLabel(found.app["tag"])
            tag.setObjectName("TileTag")
            head.addWidget(tag)
        if found.running:
            run = QLabel("运行中")
            run.setObjectName("BadgeWarn")
            head.addWidget(run)
        head.addStretch(1)
        text.addLayout(head)

        meta = QLabel(found.detail_text(2))
        meta.setObjectName("TileMeta")
        meta.setToolTip("\n".join(found.evidence))
        text.addWidget(meta)
        row.addLayout(text, 1)

        size = QLabel(found.size_text)
        size.setObjectName("TileSize")
        size.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        size.setFixedWidth(64)
        row.addWidget(size)

    def _on_box(self, checked: bool):
        self.setProperty("checked", bool(checked))
        self.style().unpolish(self)
        self.style().polish(self)
        self.toggled.emit(self.key, bool(checked))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.box.setChecked(not self.box.isChecked())
        super().mousePressEvent(event)

    def is_checked(self) -> bool:
        return self.box.isChecked()

    def set_checked(self, value: bool):
        self.box.setChecked(bool(value))


class TechPanel(QFrame):
    """技术面板：当前正在跑的技术 + 最近几步，替代原来的控制台刷屏。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TechPanel")
        self._lines: list[str] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(5)

        head = QHBoxLayout()
        head.setSpacing(6)
        cap = QLabel("技术面板")
        cap.setObjectName("TechTitle")
        head.addWidget(cap)
        head.addStretch(1)
        self.badge = QLabel("待命")
        self.badge.setObjectName("Badge")
        head.addWidget(self.badge)
        lay.addLayout(head)

        self.stage = QLabel("尚未开始")
        self.stage.setObjectName("TechStage")
        self.stage.setWordWrap(True)
        lay.addWidget(self.stage)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(4)
        lay.addWidget(self.bar)

        self.tech = QLabel("")
        self.tech.setObjectName("Mono")
        self.tech.setWordWrap(True)
        lay.addWidget(self.tech)

        box = QVBoxLayout()
        box.setSpacing(2)
        self.line_labels: list[QLabel] = []
        for _ in range(4):
            lb = QLabel("")
            lb.setObjectName("TechLine")
            lb.setVisible(False)
            box.addWidget(lb)
            self.line_labels.append(lb)
        lay.addLayout(box)
        lay.addStretch(1)

    def reset(self, stage: str = "等待开始"):
        self._lines.clear()
        self.stage.setText(stage)
        self.bar.setValue(0)
        self.tech.setText("")
        for lb in self.line_labels:
            lb.setText("")
            lb.setVisible(False)
        self.set_badge("待命", "ok")

    def set_badge(self, text: str, level: str = "ok"):
        self.badge.setText(text)
        self.badge.setObjectName("BadgeWarn" if level == "warn" else "Badge")
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)

    def set_stage(self, text: str):
        self.stage.setText(text)

    def set_progress(self, pct: int):
        self.bar.setValue(max(0, min(100, int(pct))))

    def set_tech(self, text: str):
        self.tech.setText(text)

    def push(self, text: str, keep: int = 4):
        if not text:
            return
        self._lines.insert(0, text)
        self._lines = self._lines[:keep]
        for i, lb in enumerate(self.line_labels):
            if i < len(self._lines):
                lb.setText("· " + self._lines[i])
                lb.setVisible(True)
            else:
                lb.setVisible(False)


class AdSlot(QFrame):
    """推广位：公告新支持卸载的产品，点一下跳到对应条目。"""

    clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AdSlot")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        head = QHBoxLayout()
        cap = QLabel("推广位")
        cap.setObjectName("TechTitle")
        head.addWidget(cap)
        head.addStretch(1)
        note = QLabel("广告")
        note.setObjectName("AdFooter")
        head.addWidget(note)
        lay.addLayout(head)

        for item in constants.PROMO_ITEMS:
            lay.addWidget(self._item(item))
        foot = QLabel("本位置用于公告新增支持，不接第三方投放")
        foot.setObjectName("AdFooter")
        foot.setWordWrap(True)
        lay.addWidget(foot)

    def _item(self, item: dict) -> QWidget:
        w = QFrame(self)
        w.setCursor(Qt.CursorShape.PointingHandCursor)
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 5, 0, 5)
        row.setSpacing(8)
        row.addWidget(IconGlyph(item.get("glyph", "shield"), 18,
                                theme.COLORS["accent"], w))
        text = QVBoxLayout()
        text.setSpacing(1)
        head = QHBoxLayout()
        head.setSpacing(6)
        name = QLabel(item["name"])
        name.setObjectName("AdTitle")
        head.addWidget(name)
        tag = QLabel(item.get("tag", "新"))
        tag.setObjectName("AdTag")
        head.addWidget(tag)
        head.addStretch(1)
        text.addLayout(head)
        line = QLabel(item["line"])
        line.setObjectName("AdLine")
        text.addWidget(line)
        row.addLayout(text, 1)

        def _click(_e, key=item["key"]):
            self.clicked.emit(key)

        w.mousePressEvent = _click
        return w


class SolutionBox(QFrame):
    """解决方案：失败项的下一步怎么做，最多显示三条。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SolutionBox")
        self.setVisible(False)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)
        head = QHBoxLayout()
        cap = QLabel("解决方案")
        cap.setObjectName("TechTitle")
        head.addWidget(cap)
        head.addStretch(1)
        lay.addLayout(head)
        self.body = QVBoxLayout()
        self.body.setSpacing(6)
        lay.addLayout(self.body)

    def clear(self):
        while self.body.count():
            item = self.body.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.setVisible(False)

    def set_solutions(self, solutions: list):
        self.clear()
        if not solutions:
            return
        for sol in solutions[:3]:
            title = QLabel(sol.get("title", "未清理干净"))
            title.setObjectName("SolTitle")
            self.body.addWidget(title)
            for step in sol.get("steps", [])[:3]:
                lb = QLabel("· " + step)
                lb.setObjectName("SolStep")
                lb.setWordWrap(True)
                self.body.addWidget(lb)
        self.setVisible(True)


class EmptyState(QWidget):
    def __init__(self, title: str, hint: str = "", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 28, 16, 28)
        lay.setSpacing(6)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        g = IconGlyph("shield", 40, theme.COLORS["accent_line"], self)
        lay.addWidget(g, 0, Qt.AlignmentFlag.AlignHCenter)
        lb = QLabel(title)
        lb.setObjectName("Empty")
        lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lb)
        if hint:
            h = QLabel(hint)
            h.setObjectName("SectionHint")
            h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h.setWordWrap(True)
            lay.addWidget(h)
