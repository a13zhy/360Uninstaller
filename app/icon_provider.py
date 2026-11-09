"""图标与徽章生成"""

import os
import sys

from PySide6.QtCore import QRectF, Qt, QSize
from PySide6.QtGui import (QBrush, QColor, QFont, QIcon, QLinearGradient,
                           QPainter, QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import QFileIconProvider

from .constants import APP_NAME

PALETTE = [
    ("#0EA5C6", "#0B7C93"),
    ("#2E7CF6", "#1B4FA8"),
    ("#7C5CFC", "#4B32A8"),
    ("#F25F5C", "#B43330"),
    ("#25B09B", "#12806F"),
    ("#E8A33D", "#A66E14"),
    ("#4FA8D8", "#2B6F96"),
    ("#9B6BD6", "#67409B"),
    ("#46A758", "#2A6E38"),
    ("#D4587E", "#94324F"),
    ("#5A7D9A", "#365068"),
    ("#B07A45", "#78502A"),
]


def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _draw_trash(size: int = 256) -> QPixmap:
    """程序图标：蓝绿渐变圆角方块 + 白色垃圾桶。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)

    rect = QRectF(6, 6, size - 12, size - 12)
    path = QPainterPath()
    path.addRoundedRect(rect, size * 0.18, size * 0.18)
    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grad.setColorAt(0.0, QColor("#31C48D"))
    grad.setColorAt(0.55, QColor("#12A8C6"))
    grad.setColorAt(1.0, QColor("#1E63D6"))
    p.fillPath(path, QBrush(grad))
    p.setPen(QPen(QColor(255, 255, 255, 40), 2))
    p.drawPath(path)

    white = QColor("#FFFFFF")
    p.setBrush(QBrush(white))
    p.setPen(Qt.NoPen)
    cx = size / 2

    # 桶盖
    lid = QRectF(cx - size * 0.19, size * 0.30, size * 0.38, size * 0.055)
    p.drawRoundedRect(lid, 6, 6)
    handle = QRectF(cx - size * 0.055, size * 0.255, size * 0.11, size * 0.06)
    p.drawRoundedRect(handle, 5, 5)

    # 桶身（梯形）
    body = QPainterPath()
    body.moveTo(cx - size * 0.16, size * 0.38)
    body.lineTo(cx + size * 0.16, size * 0.38)
    body.lineTo(cx + size * 0.12, size * 0.73)
    body.quadTo(cx + size * 0.11, size * 0.775, cx + size * 0.06, size * 0.775)
    body.lineTo(cx - size * 0.06, size * 0.775)
    body.quadTo(cx - size * 0.11, size * 0.775, cx - size * 0.12, size * 0.73)
    body.closeSubpath()
    p.fillPath(body, QBrush(white))

    # 桶身竖纹
    p.setBrush(QBrush(QColor(18, 130, 180, 120)))
    for i in (-1, 0, 1):
        x = cx + i * size * 0.075 - size * 0.008
        p.drawRoundedRect(QRectF(x, size * 0.45, size * 0.016, size * 0.24), 3, 3)
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
    """为应用生成渐变圆角字母徽章。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    c1, c2 = PALETTE[index % len(PALETTE)]
    rect = QRectF(1, 1, size - 2, size - 2)
    path = QPainterPath()
    path.addRoundedRect(rect, size * 0.22, size * 0.22)
    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grad.setColorAt(0, QColor(c1))
    grad.setColorAt(1, QColor(c2))
    p.fillPath(path, QBrush(grad))
    p.setPen(QPen(QColor(255, 255, 255, 50), 1))
    p.drawPath(path)

    p.setPen(QColor("#FFFFFF"))
    font = QFont("Microsoft YaHei UI")
    font.setPixelSize(int(size * 0.52))
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
