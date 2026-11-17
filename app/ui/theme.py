"""界面主题：跟随 Windows 的深/浅色模式与应用强调色

配色不写死：启动时读注册表拿 AppsUseLightTheme 与 ColorizationColor，
按系统强调色推导 hover/press/soft，浅色模式自动切换文字与底色。
所有对话框文字都用显式颜色指定，避免落到系统灰。
"""

import os
import sys

try:
    import winreg
except Exception:  # 非 Windows（CI 里的渲染检查）
    winreg = None

DEFAULT_ACCENT = "#0F6CBD"
FONT_UI = "Microsoft YaHei UI"
FONT_MONO = "Cascadia Mono, Consolas, Courier New"


def asset_path(name: str) -> str:
    roots = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(os.path.join(meipass, "assets"))
    here = os.path.dirname(os.path.abspath(__file__))
    roots.append(os.path.join(os.path.dirname(os.path.dirname(here)), "assets"))
    for root in roots:
        path = os.path.join(root, name)
        if os.path.exists(path):
            return path.replace("\\", "/")
    return ""


def _rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(c)))) for c in rgb)


def _mix(a: str, b: str, t: float) -> str:
    ra, rb = _rgb(a), _rgb(b)
    return _hex(tuple(ra[i] + (rb[i] - ra[i]) * t for i in range(3)))


def lighten(color: str, t: float) -> str:
    return _mix(color, "#FFFFFF", t)


def darken(color: str, t: float) -> str:
    return _mix(color, "#000000", t)


def alpha(color: str, a: float) -> str:
    r, g, b = _rgb(color)
    return f"rgba({r},{g},{b},{a:.3f})"


def _read_reg(path: str, name: str):
    if winreg is None:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            return winreg.QueryValueEx(key, name)[0]
    except Exception:
        return None


def windows_theme() -> tuple[str, bool]:
    """返回 (强调色, 是否深色)。读不到就用默认值，绝不抛异常。"""
    accent = DEFAULT_ACCENT
    raw = _read_reg(r"Software\Microsoft\Windows\DWM", "ColorizationColor")
    if isinstance(raw, int):
        rgb = raw & 0xFFFFFF
        b, g, r = (rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF
        if max(r, g, b) > 40:
            accent = _hex((r, g, b))
    else:
        palette = _read_reg(
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent", "AccentPalette")
        if isinstance(palette, (bytes, bytearray)) and len(palette) >= 24:
            r, g, b = palette[16], palette[17], palette[18]
            if max(r, g, b) > 40:
                accent = _hex((r, g, b))

    light = _read_reg(
        r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        "AppsUseLightTheme")
    dark = True if light is None else (int(light) == 0)
    return accent, dark


def build(accent: str | None = None, dark: bool | None = None) -> dict:
    # 允许用环境变量钉住主题（出预览图、录屏时用固定配色）
    env_accent = os.environ.get("360TOOL_ACCENT", "").strip()
    env_theme = os.environ.get("360TOOL_THEME", "").strip().lower()
    if env_accent:
        accent = env_accent
    if env_theme in ("light", "dark"):
        dark = env_theme == "dark"
    if accent is None or dark is None:
        sys_accent, sys_dark = windows_theme()
        accent = accent or sys_accent
        dark = sys_dark if dark is None else dark

    if dark:
        base = {
            "dark": True,
            "bg": "#0C0F13",
            "surface": "#12171D",
            "surface_alt": "#0E1217",
            "border": "#242B34",
            "border_strong": "#39434F",
            "text": "#EDF2F7",
            "text_sub": "#BCC8D6",
            "text_muted": "#8B9AAB",
            "console_bg": "#080A0E",
            "console_panel": "#0B0F14",
            "console_border": "#1E262F",
            "console_text": "#D2DDE9",
            "console_dim": "#7A8B9E",
            "danger": "#E5484D",
            "success": "#3FCB85",
            "teal": "#2E9C8F",
            "warn": "#E3A33C",
        }
        accent_final = accent
        if sum(_rgb(accent)) < 180:  # 太暗的强调色在深底上压不住
            accent_final = lighten(accent, 0.35)
        title_text = "#F4F8FC"
    else:
        base = {
            "dark": False,
            "bg": "#F3F5F8",
            "surface": "#FFFFFF",
            "surface_alt": "#E9EDF2",
            "border": "#D3D8E0",
            "border_strong": "#B4BCC8",
            "text": "#15191F",
            "text_sub": "#41505F",
            "text_muted": "#5E6C7B",
            "console_bg": "#FFFFFF",
            "console_panel": "#EDF0F4",
            "console_border": "#D3D8E0",
            "console_text": "#1F2933",
            "console_dim": "#63717F",
            "danger": "#C32B30",
            "success": "#1E8E5A",
            "teal": "#12766C",
            "warn": "#8A5A00",
        }
        accent_final = accent
        if sum(_rgb(accent)) > 520:  # 太亮的强调色在白底上不压字
            accent_final = darken(accent, 0.22)
        title_text = "#0E1217"

    c = dict(base)
    c.update({
        "accent": accent_final,
        "accent_hover": lighten(accent_final, 0.14) if dark else darken(accent_final, 0.08),
        "accent_press": darken(accent_final, 0.18) if dark else darken(accent_final, 0.20),
        "accent_soft": _mix(base["surface"], accent_final, 0.16),
        "accent_line": _mix(base["border"], accent_final, 0.42),
        "on_accent": "#0B0E12" if sum(_rgb(accent_final)) > 420 else "#FFFFFF",
        "title": title_text,
        "hover_bg": _mix(base["bg"], base["text"], 0.05) if dark else _mix(base["bg"], "#000000", 0.04),
        "danger_hover": lighten(base["danger"], 0.10) if dark else darken(base["danger"], 0.10),
        "danger_soft": _mix(base["surface"], base["danger"], 0.18),
        "danger_line": _mix(base["border"], base["danger"], 0.55),
        "success_soft": _mix(base["surface"], base["success"], 0.16),
        "row_line": _mix(base["bg"], base["text"], 0.06) if dark else _mix(base["bg"], "#000000", 0.07),
    })
    return c


COLORS = build()
CHECK_URL = ""
CHECK_IMG = "image: none;"


def _refresh_assets():
    global CHECK_URL, CHECK_IMG
    CHECK_URL = asset_path("check.png")
    CHECK_IMG = f'image: url("{CHECK_URL}");' if CHECK_URL else "image: none;"


_refresh_assets()


def qss() -> str:
    c = COLORS
    return f"""
* {{
    font-family: "{FONT_UI}";
    font-size: 10pt;
    color: {c['text']};
    outline: none;
}}
QMainWindow, QWidget#Root, QDialog {{
    background: {c['bg']};
}}
QToolTip {{
    background: {c['surface']};
    color: {c['text']};
    border: 1px solid {c['border_strong']};
    padding: 5px 8px;
}}

QWidget#TopBar {{
    background: {c['surface_alt']};
    border-bottom: 1px solid {c['border']};
}}
QLabel#BrandTitle {{
    font-size: 13pt;
    font-weight: 700;
    color: {c['title']};
}}
QLabel#BrandSub {{
    font-size: 8.5pt;
    color: {c['text_muted']};
}}
QLabel#VersionBadge, QLabel#AdminBadge {{
    background: transparent;
    border: 1px solid {c['border_strong']};
    padding: 3px 9px;
    color: {c['text_sub']};
    font-size: 8.5pt;
}}
QLabel#VersionBadge {{
    font-family: "{FONT_MONO}";
}}
QLabel#AdminBadge[on="true"] {{
    border: 1px solid {c['accent_line']};
    color: {c['accent']};
}}
QLabel#AdminBadge[warn="true"] {{
    border: 1px solid {c['danger_line']};
    color: {c['danger']};
}}

QFrame#LeftPanel {{
    background: {c['bg']};
    border: none;
    border-right: 1px solid {c['border']};
}}
QFrame#ConsolePanel {{
    background: {c['console_panel']};
    border: none;
    border-left: 1px solid {c['border']};
}}
QLabel#SectionTitle {{
    font-size: 12.5pt;
    font-weight: 700;
    color: {c['title']};
}}
QLabel#SectionHint {{
    font-size: 9pt;
    color: {c['text_muted']};
}}
QLabel#HeadCell {{
    font-size: 8.5pt;
    color: {c['text_muted']};
}}
QWidget#TableHead {{
    background: {c['surface_alt']};
    border-top: 1px solid {c['border']};
    border-bottom: 1px solid {c['border']};
}}

QFrame#StatCard {{
    background: {c['surface']};
    border: 1px solid {c['border']};
    border-left: 3px solid {c['accent']};
}}
QLabel#StatValue {{
    font-family: "{FONT_MONO}";
    font-size: 18pt;
    font-weight: 700;
    color: {c['title']};
}}
QLabel#StatLabel {{
    font-size: 8.5pt;
    color: {c['text_muted']};
}}

QScrollArea#AppScroll, QWidget#AppListHost {{
    background: transparent;
    border: none;
}}
QFrame#AppRow {{
    background: transparent;
    border: none;
    border-bottom: 1px solid {c['row_line']};
    border-left: 2px solid transparent;
}}
QFrame#AppRow:hover {{
    background: {c['hover_bg']};
}}
QFrame#AppRow[checked="true"] {{
    background: {c['accent_soft']};
    border-left: 2px solid {c['accent']};
}}
QLabel#AppName {{
    font-size: 10pt;
    font-weight: 600;
    color: {c['text']};
}}
QLabel#AppDesc {{
    font-size: 8.5pt;
    color: {c['text_muted']};
}}
QLabel#AppState {{
    font-size: 8.5pt;
    color: {c['text_muted']};
}}
QLabel#AppState[state="installed"] {{
    color: {c['success']};
}}
QLabel#AppState[state="running"] {{
    color: {c['accent']};
}}
QLabel#AppCount, QLabel#AppSize {{
    font-family: "{FONT_MONO}";
    font-size: 8.5pt;
    color: {c['text_sub']};
}}

QCheckBox {{
    spacing: 8px;
    color: {c['text']};
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {c['border_strong']};
    background: {c['surface']};
}}
QCheckBox::indicator:hover {{
    border-color: {c['accent']};
}}
QCheckBox::indicator:checked {{
    background: {c['accent']};
    border-color: {c['accent']};
    {CHECK_IMG}
}}
QCheckBox::indicator:checked:disabled {{
    background: {c['border']};
    border-color: {c['border']};
    {CHECK_IMG}
}}

QPushButton {{
    background: {c['surface']};
    border: 1px solid {c['border_strong']};
    padding: 8px 16px;
    color: {c['text']};
}}
QPushButton:hover {{
    background: {c['hover_bg']};
    border-color: {c['accent_line']};
}}
QPushButton:pressed {{
    background: {c['surface_alt']};
}}
QPushButton:disabled {{
    color: {c['text_muted']};
    border-color: {c['border']};
    background: transparent;
}}
QPushButton#Primary {{
    background: {c['accent']};
    border: 1px solid {c['accent']};
    color: {c['on_accent']};
    font-weight: 700;
}}
QPushButton#Primary:hover {{
    background: {c['accent_hover']};
    border-color: {c['accent_hover']};
}}
QPushButton#Primary:pressed {{
    background: {c['accent_press']};
    border-color: {c['accent_press']};
}}
QPushButton#Primary:disabled {{
    background: transparent;
    border: 1px solid {c['border_strong']};
    color: {c['text_muted']};
}}
QPushButton#Danger {{
    background: transparent;
    border: 1px solid {c['danger_line']};
    color: {c['danger']};
    font-weight: 600;
}}
QPushButton#Danger:hover {{
    background: {c['danger']};
    border-color: {c['danger']};
    color: {c['on_accent']};
}}
QPushButton#Danger:pressed {{
    background: {c['danger_hover']};
}}
QPushButton#Danger:disabled {{
    background: transparent;
    border-color: {c['border']};
    color: {c['text_muted']};
}}
QPushButton#Ghost {{
    background: transparent;
    border: 1px solid transparent;
    color: {c['text_sub']};
}}
QPushButton#Ghost:hover {{
    background: transparent;
    border: 1px solid {c['border_strong']};
    color: {c['text']};
}}
QPushButton#ConsoleGhost {{
    background: transparent;
    border: 1px solid {c['border']};
    color: {c['text_sub']};
    padding: 4px 10px;
    font-size: 8.5pt;
}}
QPushButton#ConsoleGhost:hover {{
    border-color: {c['accent_line']};
    color: {c['text']};
}}
QPushButton#UpdateHot {{
    background: {c['accent_soft']};
    border: 1px solid {c['accent_line']};
    color: {c['accent']};
    font-weight: 600;
}}
QPushButton#UpdateHot:hover {{
    background: {c['accent']};
    color: {c['on_accent']};
}}

QProgressBar {{
    background: {c['border']};
    border: none;
}}
QProgressBar::chunk {{
    background: {c['accent']};
}}
QProgressBar#ConsoleBar {{
    background: {c['border']};
}}
QProgressBar#ConsoleBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {c['accent_press']}, stop:1 {c['accent_hover']});
}}

QLabel#ConsoleTitle {{
    font-family: "{FONT_MONO}";
    font-size: 9.5pt;
    font-weight: 700;
    color: {c['text']};
}}
QLabel#ConsoleHint {{
    font-family: "{FONT_MONO}";
    font-size: 8pt;
    color: {c['console_dim']};
}}
QLabel#ConsoleStatValue {{
    font-family: "{FONT_MONO}";
    font-size: 13pt;
    font-weight: 700;
    color: {c['text']};
}}
QLabel#ConsoleStatLabel {{
    font-size: 8pt;
    color: {c['console_dim']};
}}
QFrame#ConsoleStatCard {{
    background: transparent;
    border: none;
    border-top: 1px solid {c['console_border']};
}}
QPlainTextEdit#Console {{
    background: {c['console_bg']};
    border: 1px solid {c['console_border']};
    color: {c['console_text']};
    font-family: "{FONT_MONO}";
    font-size: 9pt;
    padding: 8px;
    selection-background-color: {c['accent_soft']};
    selection-color: {c['text']};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 11px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {c['border_strong']};
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c['accent']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background: {c['border_strong']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QFrame#PromoCard {{
    background: {c['surface']};
    border: none;
    border-top: 1px solid {c['border']};
    border-left: 3px solid {c['accent']};
}}
QLabel#PromoKicker {{
    font-family: "{FONT_MONO}";
    font-size: 8pt;
    font-weight: 600;
    color: {c['accent']};
}}
QLabel#PromoTitle {{
    font-size: 12pt;
    font-weight: 700;
    color: {c['title']};
}}
QLabel#PromoDesc {{
    font-size: 8.5pt;
    color: {c['text_sub']};
}}
QPushButton#PromoBtn {{
    background: {c['accent']};
    color: {c['on_accent']};
    border: 1px solid {c['accent']};
    padding: 9px 20px;
    font-weight: 700;
}}
QPushButton#PromoBtn:hover {{
    background: {c['accent_hover']};
    border-color: {c['accent_hover']};
}}
QPushButton#PromoBtn:pressed {{
    background: {c['accent_press']};
}}
QPushButton#PromoBtn:disabled {{
    background: transparent;
    border-color: {c['border_strong']};
    color: {c['text_muted']};
}}

QLabel#FooterText {{
    font-family: "{FONT_MONO}";
    font-size: 8.5pt;
    color: {c['text_sub']};
    background: {c['surface_alt']};
    border-top: 1px solid {c['border']};
    padding: 5px 16px;
}}

QDialog QLabel {{
    color: {c['text']};
}}
QLabel#DialogTitle {{
    font-size: 13.5pt;
    font-weight: 700;
    color: {c['title']};
}}
QLabel#DialogSub {{
    font-size: 9.5pt;
    color: {c['text_sub']};
}}
QListWidget#ResidualList {{
    background: {c['surface']};
    border: 1px solid {c['border_strong']};
    padding: 2px;
    color: {c['text']};
    font-family: "{FONT_MONO}";
    font-size: 9pt;
}}
QListWidget#ResidualList::item {{
    border-bottom: 1px solid {c['row_line']};
    padding: 2px;
}}
QListWidget#ResidualList::item:selected {{
    background: {c['accent_soft']};
    color: {c['text']};
}}
QFrame#DialogStat {{
    background: {c['surface']};
    border: 1px solid {c['border']};
}}
QTextBrowser#UpdateNotes {{
    background: {c['surface']};
    border: 1px solid {c['border_strong']};
    padding: 10px;
    font-size: 10pt;
    color: {c['text']};
}}
QMessageBox {{
    background: {c['surface_alt']};
}}
QMessageBox QLabel {{
    color: {c['text']};
    font-size: 10pt;
    min-width: 320px;
}}
QMessageBox QPushButton {{
    min-width: 84px;
    min-height: 30px;
}}
QMenu#TrayMenu {{
    background: {c['surface']};
    border: 1px solid {c['border_strong']};
    padding: 4px;
}}
QMenu#TrayMenu::item {{
    padding: 8px 18px;
    color: {c['text']};
}}
QMenu#TrayMenu::item:selected {{
    background: {c['accent_soft']};
    color: {c['accent']};
}}
QMenu#TrayMenu::separator {{
    height: 1px;
    background: {c['border']};
    margin: 4px 8px;
}}

QFrame#ScanHud {{
    background: {c['surface']};
    border: 1px solid {c['accent_line']};
    border-left: 3px solid {c['accent']};
}}
QLabel#HudTitle {{
    font-size: 9.5pt;
    font-weight: 700;
    color: {c['title']};
}}
QLabel#HudText {{
    font-size: 8.5pt;
    color: {c['text_sub']};
}}
QLabel#HudPct {{
    font-family: "{FONT_MONO}";
    font-size: 9pt;
    color: {c['accent']};
}}
QPushButton#HudClose {{
    background: transparent;
    border: none;
    color: {c['text_muted']};
    padding: 0px 4px;
    font-size: 11pt;
}}
QPushButton#HudClose:hover {{
    color: {c['danger']};
}}

QFrame#PatrolCard {{
    background: {c['surface']};
    border: 1px solid {c['border_strong']};
    border-left: 3px solid {c['accent']};
}}
QLabel#PatrolTitle {{
    font-size: 10.5pt;
    font-weight: 700;
    color: {c['title']};
}}
QLabel#PatrolChip {{
    font-size: 8pt;
    color: {c['accent']};
    background: {c['accent_soft']};
    border: 1px solid {c['accent_line']};
    padding: 1px 6px;
}}
QLabel#PatrolPct {{
    font-family: "{FONT_MONO}";
    font-size: 9pt;
    color: {c['accent']};
}}
QLabel#PatrolStatus {{
    font-size: 10pt;
    font-weight: 600;
    color: {c['text']};
}}
QLabel#PatrolDetail {{
    font-size: 8.5pt;
    color: {c['text_muted']};
}}
QLabel#PatrolStat {{
    font-size: 9pt;
    color: {c['text_sub']};
}}
QLabel#PatrolStatDim {{
    font-size: 8.5pt;
    color: {c['text_muted']};
}}
QProgressBar#PatrolBar {{
    background: {c['row_line']};
    border: none;
}}
QProgressBar#PatrolBar::chunk {{
    background: {c['accent']};
}}
QCheckBox#PatrolCheck {{
    font-size: 8.5pt;
    color: {c['text_sub']};
    spacing: 6px;
}}
QCheckBox#PatrolCheck::indicator {{
    width: 12px;
    height: 12px;
    border: 1px solid {c['border_strong']};
    background: {c['surface_alt']};
}}
QCheckBox#PatrolCheck::indicator:checked {{
    background: {c['accent']};
    border-color: {c['accent']};
    {CHECK_IMG}
}}
"""


def apply(app):
    global COLORS
    COLORS = build()
    _refresh_assets()
    try:
        from PySide6.QtGui import QColor, QPalette

        pal = app.palette()
        c = COLORS
        for role, color in (
            (QPalette.WindowText, c["text"]),
            (QPalette.Text, c["text"]),
            (QPalette.ButtonText, c["text"]),
            (QPalette.ToolTipText, c["text"]),
            (QPalette.Window, c["bg"]),
            (QPalette.Base, c["surface"]),
            (QPalette.AlternateBase, c["surface_alt"]),
            (QPalette.Button, c["surface"]),
            (QPalette.Highlight, c["accent"]),
            (QPalette.HighlightedText, c["on_accent"]),
        ):
            pal.setColor(role, QColor(color))
        app.setPalette(pal)
    except Exception:
        pass
    app.setStyleSheet(qss())


def color(key: str, default: str = "#EDF2F7") -> str:
    return COLORS.get(key, default)
