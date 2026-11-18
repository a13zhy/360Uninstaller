"""浅色安全软件风格主题：细边框、紧凑行高、单一品牌蓝

参考国产安全软件那种“信息密度高但安静”的观感：白底面板 + 1px 分隔线 +
4px 圆角，强调色只有一个，危险/警告各留一个色。所有文字都显式给色，
不落到系统默认灰。
"""

import os
import sys

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

COLORS = {
    "bg": "#F2F4F7",
    "panel": "#FFFFFF",
    "panel_alt": "#FAFBFC",
    "sidebar": "#FFFFFF",
    "line": "#E2E6EB",
    "row_line": "#EEF1F4",
    "text": "#1D2129",
    "text_sub": "#5B6470",
    "text_muted": "#8B939E",
    "accent": "#2B7CF6",
    "accent_dark": "#1F6BE0",
    "accent_soft": "#EAF2FF",
    "accent_line": "#B9D3FF",
    "ok": "#2BA471",
    "ok_soft": "#EAF7F1",
    "warn": "#C26A14",
    "warn_soft": "#FDF3E6",
    "danger": "#D54941",
    "danger_soft": "#FBEDEC",
    "hover": "#F5F8FE",
    "selected": "#F0F6FF",
    "code_bg": "#F5F7FA",
    "console_dim": "#6B7280",
    "check": "#FFFFFF",
}

FONT_UI = "Microsoft YaHei UI"
FONT_MONO = "Cascadia Mono, Consolas, Courier New"


def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


def asset_path(name: str) -> str:
    path = os.path.join(_base_dir(), "assets", name)
    if os.path.exists(path):
        return path.replace("\\", "/")
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        alt = os.path.join(meipass, "assets", name)
        if os.path.exists(alt):
            return alt.replace("\\", "/")
    return ""


def color(key: str, default: str = "#1D2129") -> str:
    return COLORS.get(key, default)


def _rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(c)))) for c in rgb)


def mix(a: str, b: str, t: float) -> str:
    ra, rb = _rgb(a), _rgb(b)
    return _hex(tuple(ra[i] + (rb[i] - ra[i]) * t for i in range(3)))


def lighten(value: str, t: float) -> str:
    return mix(value, "#FFFFFF", t)


def darken(value: str, t: float) -> str:
    return mix(value, "#000000", t)


def alpha(value: str, a: float) -> str:
    r, g, b = _rgb(value)
    return f"rgba({r},{g},{b},{a:.3f})"


def windows_accent() -> str:
    """可选同步 Windows 强调色；读不到就退回品牌蓝。"""
    if os.environ.get("360TOOL_SYNC_WINDOWS") != "1":
        return COLORS["accent"]
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\\Microsoft\\Windows\\DWM") as key:
            value, _t = winreg.QueryValueEx(key, "AccentColor")
            bgra = int(value)
            b, g, r = bgra & 0xFF, (bgra >> 8) & 0xFF, (bgra >> 16) & 0xFF
            return "#%02X%02X%02X" % (r, g, b)
    except Exception:
        return COLORS["accent"]


def build() -> dict:
    accent = os.environ.get("360TOOL_ACCENT") or windows_accent()
    if accent and accent.startswith("#") and len(accent) == 7:
        COLORS["accent"] = accent
        COLORS["accent_dark"] = darken(accent, 0.12)
        COLORS["accent_soft"] = mix(accent, "#FFFFFF", 0.92)
        COLORS["accent_line"] = mix(accent, "#FFFFFF", 0.62)
    return COLORS


def qss() -> str:
    c = COLORS
    check = asset_path("check.png") or "none"
    return f"""
QWidget {{ color: {c['text']}; }}
QMainWindow, QDialog {{ background: {c['bg']}; }}
QFrame#TopBar {{ background: {c['panel']}; border-bottom: 1px solid {c['line']}; }}
QFrame#Sidebar {{ background: {c['sidebar']}; border-right: 1px solid {c['line']}; }}
QFrame#Content {{ background: {c['bg']}; }}
QFrame#Card, QFrame#TechPanel, QFrame#AdSlot, QFrame#SolutionBox,
QFrame#SummaryCard {{ background: {c['panel']}; border: 1px solid {c['line']};
    border-radius: 4px; }}
QFrame#ModeCard {{ background: {c['panel']}; border: 1px solid {c['line']};
    border-radius: 4px; }}
QFrame#ModeCard:hover {{ border-color: {c['accent_line']}; background: {c['panel_alt']}; }}
QFrame#ModeCard[active="true"] {{ border: 1px solid {c['accent']};
    background: {c['accent_soft']}; }}
QFrame#AppTile {{ background: {c['panel']}; border-bottom: 1px solid {c['row_line']}; }}
QFrame#AppTile:hover {{ background: {c['hover']}; }}
QFrame#AppTile[checked="true"] {{ background: {c['selected']}; }}
QFrame#Divider {{ background: {c['line']}; border: none; }}

QPushButton {{ background: {c['panel']}; border: 1px solid #DCE1E7; border-radius: 3px;
    padding: 0 12px; min-height: 26px; color: {c['text']}; }}
QPushButton:hover {{ border-color: {c['accent_line']}; color: {c['accent_dark']};
    background: {c['hover']}; }}
QPushButton:pressed {{ background: {c['accent_soft']}; }}
QPushButton:disabled {{ color: #A6ADB6; background: #F6F7F9; border-color: #E9EDF1; }}
QPushButton#Primary {{ background: {c['accent']}; border: 1px solid {c['accent']};
    color: #FFFFFF; padding: 0 20px; min-height: 32px; font-weight: 600; }}
QPushButton#Primary:hover {{ background: {c['accent_dark']}; border-color: {c['accent_dark']}; }}
QPushButton#Primary:pressed {{ background: {c['accent_dark']}; }}
QPushButton#Primary:disabled {{ background: #B9D3FF; border-color: #B9D3FF; color: #EFF5FF; }}
QPushButton#Danger {{ background: {c['panel']}; border: 1px solid #F0C7C3;
    color: {c['danger']}; }}
QPushButton#Danger:hover {{ background: {c['danger_soft']}; }}
QPushButton#Ghost {{ background: transparent; border: 1px solid #DCE1E7;
    color: {c['text_sub']}; }}
QPushButton#Link {{ border: none; background: transparent; color: {c['accent']};
    padding: 0 2px; min-height: 20px; }}
QPushButton#Link:hover {{ color: {c['accent_dark']}; }}
QPushButton#IconBtn {{ border: none; background: transparent; padding: 0;
    min-height: 24px; min-width: 24px; }}
QPushButton#IconBtn:hover {{ background: {c['accent_soft']}; border-radius: 3px; }}
QPushButton#NavItem {{ text-align: left; border: none; border-left: 2px solid transparent;
    background: transparent; color: {c['text_sub']}; padding-left: 12px;
    min-height: 38px; border-radius: 0; font-size: 9.5pt; }}
QPushButton#NavItem:hover {{ background: {c['hover']}; color: {c['text']}; }}
QPushButton#NavItem:checked {{ background: {c['accent_soft']}; color: {c['accent_dark']};
    border-left: 2px solid {c['accent']}; font-weight: 600; }}

QLabel#SectionTitle {{ font-size: 10.5pt; font-weight: 600; }}
QLabel#SectionHint {{ color: {c['text_muted']}; font-size: 8.5pt; }}
QLabel#TileName {{ font-size: 9.5pt; font-weight: 600; }}
QLabel#TileMeta {{ color: {c['text_muted']}; font-size: 8pt; }}
QLabel#TileSize {{ color: {c['text_sub']}; font-size: 8pt; }}
QLabel#TileTag {{ background: {c['accent_soft']}; color: {c['accent_dark']};
    border: 1px solid {c['accent_line']}; border-radius: 2px; padding: 1px 5px;
    font-size: 7.5pt; }}
QLabel#TechTitle {{ font-size: 8.5pt; color: {c['text_muted']}; }}
QLabel#TechStage {{ font-size: 9pt; font-weight: 600; color: {c['accent_dark']}; }}
QLabel#TechLine {{ color: {c['text_sub']}; font-size: 8pt; }}
QLabel#Mono {{ font-family: "Cascadia Mono", "Consolas", monospace; font-size: 8pt;
    color: {c['text_sub']}; }}
QLabel#DialogTitle {{ font-size: 12pt; font-weight: 600; }}
QLabel#DialogSub {{ color: {c['text_sub']}; font-size: 8.5pt; }}
QLabel#AdTitle {{ font-size: 9.5pt; font-weight: 600; }}
QLabel#AdLine {{ color: {c['text_muted']}; font-size: 8pt; }}
QLabel#AdTag {{ background: {c['warn_soft']}; color: {c['warn']};
    border: 1px solid #F3D9BC; border-radius: 2px; padding: 1px 5px; font-size: 7.5pt; }}
QLabel#AdFooter {{ color: {c['text_muted']}; font-size: 7pt; }}
QLabel#Badge {{ background: {c['ok_soft']}; color: {c['ok']}; border: 1px solid #CBE9DA;
    border-radius: 2px; padding: 1px 6px; font-size: 7.5pt; }}
QLabel#BadgeWarn {{ background: {c['warn_soft']}; color: {c['warn']};
    border: 1px solid #F3D9BC; border-radius: 2px; padding: 1px 6px; font-size: 7.5pt; }}
QLabel#AdminChip {{ color: {c['text_sub']}; font-size: 8pt; }}
QLabel#StatChip {{ color: {c['text_sub']}; font-size: 8pt; }}
QLabel#SolTitle {{ font-size: 9pt; font-weight: 600; color: {c['warn']}; }}
QLabel#SolStep {{ color: {c['text_sub']}; font-size: 8pt; }}
QLabel#Empty {{ color: {c['text_muted']}; font-size: 9.5pt; }}

QCheckBox {{ spacing: 6px; color: {c['text_sub']}; font-size: 8.5pt; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid #C9D0D8;
    border-radius: 2px; background: #FFFFFF; }}
QCheckBox::indicator:hover {{ border-color: {c['accent']}; }}
QCheckBox::indicator:checked {{ background: {c['accent']}; border-color: {c['accent']};
    image: url({check}); }}

QProgressBar {{ background: {c['row_line']}; border: none; border-radius: 2px;
    height: 4px; }}
QProgressBar::chunk {{ background: {c['accent']}; border-radius: 2px; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #D5DAE0; border-radius: 4px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: #B8C0C9; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QMenu {{ background: {c['panel']}; border: 1px solid {c['line']}; padding: 4px; }}
QMenu::item {{ padding: 5px 22px 5px 12px; border-radius: 3px; font-size: 9pt; }}
QMenu::item:selected {{ background: {c['accent_soft']}; color: {c['accent_dark']}; }}
QMenu::separator {{ height: 1px; background: {c['row_line']}; margin: 4px 8px; }}
QToolTip {{ background: {c['panel']}; color: {c['text']}; border: 1px solid {c['line']};
    padding: 4px 6px; font-size: 8.5pt; }}

QTextBrowser#UpdateNotes {{ background: {c['code_bg']}; border: 1px solid {c['line']};
    border-radius: 3px; padding: 8px; font-size: 8.5pt; color: {c['text_sub']}; }}
QLineEdit {{ background: {c['panel']}; border: 1px solid #DCE1E7; border-radius: 3px;
    padding: 4px 8px; min-height: 26px; }}
QLineEdit:focus {{ border-color: {c['accent']}; }}
"""


def apply(app: QApplication):
    build()
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(COLORS["bg"]))
    pal.setColor(QPalette.ColorRole.Base, QColor(COLORS["panel"]))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(COLORS["panel_alt"]))
    pal.setColor(QPalette.ColorRole.Text, QColor(COLORS["text"]))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(COLORS["text"]))
    pal.setColor(QPalette.ColorRole.Button, QColor(COLORS["panel"]))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(COLORS["text"]))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(COLORS["accent_soft"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(COLORS["text"]))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(COLORS["panel"]))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(COLORS["text"]))
    app.setPalette(pal)

    font = QFont(FONT_UI)
    font.setPointSize(9)
    app.setFont(font)
    app.setStyleSheet(qss())
