"""图标与徽章生成"""

import os
import sys

from PySide6.QtCore import QRectF, Qt, QSize
from PySide6.QtGui import (QBrush, QColor, QFont, QIcon, QLinearGradient,
                           QPainter, QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import QFileIconProvider

from .constants import APP_NAME

PALETTE = [
    "#9FB4C9",
    "#D3AC62",
    "#8FBFA6",
    "#C99280",
    "#93AECB",
    "#B79E76",
    "#A6A2C8",
    "#B58A9A",
    "#8EBB8F",
    "#C0A0A0",
    "#9BA9B8",
    "#BFA07C",
]


def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _draw_trash(size: int = 256) -> QPixmap:
    """程序图标：琥珀方板 + 深色垃圾桶，小尺寸下也能看清轮廓。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)

    rect = QRectF(6, 6, size - 12, size - 12)
    path = QPainterPath()
    path.addRoundedRect(rect, size * 0.14, size * 0.14)
    plate = QLinearGradient(rect.topLeft(), rect.bottomRight())
    plate.setColorAt(0.0, QColor("#F5C071"))
    plate.setColorAt(0.55, QColor("#E0A03C"))
    plate.setColorAt(1.0, QColor("#B87B1E"))
    p.fillPath(path, QBrush(plate))
    p.setPen(QPen(QColor("#F7CF92"), max(2, int(size * 0.014)))
    p.drawPath(path)

    ink = QColor("#0E1319")
    p.setBrush(QBrush(ink))
    p.setPen(Qt.NoPen)
    cx = size / 2

    # 桶盖
    lid = QRectF(cx - size * 0.20, size * 0.28, size * 0.40, size * 0.058)
    p.drawRoundedRect(lid, 4, 4)
    handle = QRectF(cx - size * 0.06, size * 0.228, size * 0.12, size * 0.062)
    p.drawRoundedRect(handle, 3, 3)

    # 桶身（梯形）
    body = QPainterPath()
    body.moveTo(cx - size * 0.17, size * 0.37)
    body.lineTo(cx + size * 0.17, size * 0.37)
    body.lineTo(cx + size * 0.13, size * 0.755)
    body.quadTo(cx + size * 0.12, size * 0.80, cx + size * 0.065, size * 0.80)
    body.lineTo(cx - size * 0.065, size * 0.80)
    body.quadTo(cx - size * 0.12, size * 0.80, cx - size * 0.13, size * 0.755)
    body.closeSubpath()
    p.fillPath(body, QBrush(ink))

    # 桶身竖纹（琥珀色镂空）
    p.setBrush(QBrush(QColor("#E0A03C")))
    for i in (-1, 0, 1):
        x = cx + i * size * 0.078 - size * 0.009
        p.drawRoundedRect(QRectF(x, size * 0.46, size * 0.018, size * 0.25), 2, 2)
    p.end()
    return pm


def app_icon() -> QIcon:
    ico = os.path.join(_base_dir(), "assets", "app_icon.ico")
    png = os.path.join(_base_dir(), "assets", "app_icon.png")
    for path in (ico, png):
        if os.path.exists(path):
            icon = QIcon(path)
            if not icon.isNull():
                return icon
    icon = QIcon()
    pm = _draw_trash(256)
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(pm.scaled(s, s, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    return icon


def app_pixmap(size: int = 64) -> QPixmap:
    ico = dir_icon_path()
    if ico:
        pm = QPixmap(ico)
        if not pm.isNull():
            return pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return _draw_trash(size)


def dir_icon_path() -> str:
    base = _base_dir()
    for name in ("app_icon.png", "app_icon.ico"):
        p = os.path.join(base, "assets", name)
        if os.path.exists(p):
            return p
    return ""


def badge_icon(index: int, text: str, size: int = 48) -> QIcon:
    """为应用生成方形暗底字母徽章，颜色只用于字形，避免界面出现彩色方块。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    color = PALETTE[index % len(PALETTE)]
    rect = QRectF(0.5, 0.5, size - 1, size - 1)
    p.setPen(QPen(QColor("#2E3A48"), 1))
    p.setBrush(QBrush(QColor("#161D26")))
    p.drawRect(rect)

    p.setPen(QColor(color))
    font = QFont("Microsoft YaHei UI")
    font.setPixelSize(int(size * 0.46))
    font.setBold(True)
    p.setFont(font)
    p.drawText(rect, Qt.AlignCenter, text)
    p.end()
    return QIcon(pm)


def file_icon(path: str, size: QSize = QSize(24, 24)) -> QIcon:
    try:
        provider = QFileIconProvider()
        icon = provider.icon(path)
        return icon if not icon.isNull() else QIcon()
    except Exception:
        return QIcon()
