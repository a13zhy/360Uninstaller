"""界面主题：深色工业风主区 + 同色系终端控制台

设计取向：方角、细线、低饱和、无卡片阴影；强调色只用琥珀一色，
危险动作用红描边；数字与日志走等宽字体，避免"AI 模板感"。
"""

import os
import sys


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


CHECK_URL = asset_path("check.png")
CHECK_IMG = f'image: url("{CHECK_URL}");' if CHECK_URL else "image: none;"

COLORS = {
    "bg": "#0A0C10",
    "surface": "#121820",
    "surface_alt": "#0F141B",
    "border": "#232C38",
    "border_strong": "#33404F",
    "text": "#E9EFF7",
    "text_sub": "#A7B6C7",
    "text_muted": "#6B7C90",
    "accent": "#E0A03C",
    "accent_hover": "#F2B45A",
    "accent_press": "#C4861F",
    "accent_soft": "#2A2114",
    "teal": "#2E9C8F",
    "danger": "#E5484D",
    "danger_hover": "#F26166",
    "danger_soft": "#2A1416",
    "success": "#3DCB85",
    "warn": "#E0A03C",
    "console_bg": "#06080B",
    "console_panel": "#090C11",
    "console_border": "#1B232D",
    "console_text": "#C4D3E2",
    "console_dim": "#5E7186",
}

FONT_UI = "Microsoft YaHei UI"
FONT_MONO = "Cascadia Mono, Consolas, Courier New"

QSS = f"""
* {{
    font-family: "{FONT_UI}";
    font-size: 9.5pt;
    color: {COLORS['text']};
}}
QMainWindow, QWidget#Root {{
    background: {COLORS['bg']};
}}

/* ---------------------------------------------------------------- 顶栏 */
QWidget#TopBar {{
    background: {COLORS['surface_alt']};
    border-bottom: 1px solid {COLORS['border']};
}}
QLabel#BrandTitle {{
    font-size: 13.5pt;
    font-weight: 700;
    color: {COLORS['text']};
}}
QLabel#BrandSub {{
    font-size: 8pt;
    color: {COLORS['text_muted']};
}}
QLabel#VersionBadge {{
    background: transparent;
    border: 1px solid {COLORS['border']};
    padding: 2px 8px;
    color: {COLORS['text_sub']};
    font-family: "{FONT_MONO}";
    font-size: 8pt;
}}
QLabel#AdminBadge {{
    background: transparent;
    border: 1px solid {COLORS['border_strong']};
    padding: 2px 8px;
    color: {COLORS['text_sub']};
    font-size: 8pt;
}}
QLabel#AdminBadge[on="true"] {{
    border: 1px solid #4A3A1B;
    color: {COLORS['accent']};
}}
QLabel#AdminBadge[warn="true"] {{
    border: 1px solid #53312F;
    color: #F28B8E;
}}

/* ---------------------------------------------------------------- 面板 */
QFrame#LeftPanel {{
    background: {COLORS['bg']};
    border: none;
    border-right: 1px solid {COLORS['border']};
}}
QFrame#ConsolePanel {{
    background: {COLORS['console_panel']};
    border: none;
    border-left: 1px solid {COLORS['border']};
}}
QLabel#SectionTitle {{
    font-size: 12pt;
    font-weight: 700;
    color: {COLORS['text']};
}}
QLabel#SectionHint {{
    font-size: 8.5pt;
    color: {COLORS['text_muted']};
}}
QLabel#RuleLine {{
    background: {COLORS['border']};
    max-height: 1px;
    min-height: 1px;
}}
QWidget#TableHead {{
    background: transparent;
}}
QLabel#HeadCell {{
    font-size: 8pt;
    color: {COLORS['text_muted']};
}}
QLabel#HeadCellRight {{
    font-size: 8pt;
    color: {COLORS['text_muted']};
}}

/* ---------------------------------------------------------------- 读数 */
QFrame#StatCard {{
    background: transparent;
    border: none;
    border-left: 1px solid {COLORS['border']};
}}
QLabel#StatValue {{
    font-family: "{FONT_MONO}";
    font-size: 17pt;
    font-weight: 700;
    color: {COLORS['text']};
}}
QLabel#StatLabel {{
    font-size: 8pt;
    color: {COLORS['text_muted']};
}}

/* ---------------------------------------------------------------- 应用列表 */
QScrollArea#AppScroll {{
    background: transparent;
    border: none;
}}
QWidget#AppListHost {{
    background: transparent;
}}
QFrame#AppRow {{
    background: transparent;
    border: none;
    border-bottom: 1px solid #161D26;
    border-left: 2px solid transparent;
}}
QFrame#AppRow:hover {{
    background: #121A23;
}}
QFrame#AppRow[checked="true"] {{
    background: #151D27;
    border-left: 2px solid {COLORS['accent']};
}}
QFrame#AppRow[dim="true"] {{
    background: transparent;
}}
QLabel#AppName {{
    font-size: 9.5pt;
    font-weight: 600;
    color: {COLORS['text']};
}}
QLabel#AppDesc {{
    font-size: 8pt;
    color: {COLORS['text_muted']};
}}
QLabel#AppState {{
    font-size: 8pt;
    color: {COLORS['text_muted']};
}}
QLabel#AppState[state="installed"] {{
    color: #55D08C;
}}
QLabel#AppState[state="running"] {{
    color: {COLORS['accent']};
}}
QLabel#AppState[state="clean"] {{
    color: #53657A;
}}
QLabel#AppCount {{
    font-family: "{FONT_MONO}";
    font-size: 8pt;
    color: {COLORS['text_sub']};
}}
QLabel#AppSize {{
    font-family: "{FONT_MONO}";
    font-size: 8pt;
    color: {COLORS['text_muted']};
}}

/* ---------------------------------------------------------------- 勾选框 */
QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid #44546A;
    background: #0D1218;
}}
QCheckBox::indicator:hover {{
    border-color: {COLORS['accent']};
}}
QCheckBox::indicator:checked {{
    background: {COLORS['accent']};
    border-color: {COLORS['accent']};
    {CHECK_IMG}
}}
QCheckBox::indicator:checked:disabled {{
    background: #4A3A1B;
    border-color: #4A3A1B;
    {CHECK_IMG}
}}

/* ---------------------------------------------------------------- 按钮 */
QPushButton {{
    background: #131A23;
    border: 1px solid {COLORS['border_strong']};
    padding: 7px 16px;
    color: {COLORS['text']};
}}
QPushButton:hover {{
    background: #1A232E;
    border-color: #46586C;
}}
QPushButton:pressed {{
    background: #0D131A;
}}
QPushButton:disabled {{
    color: #566577;
    border-color: #232C38;
    background: #0E131A;
}}
QPushButton#Primary {{
    background: {COLORS['accent']};
    border: 1px solid {COLORS['accent']};
    color: #0B0E12;
    font-weight: 700;
}}
QPushButton#Primary:hover {{
    background: {COLORS['accent_hover']};
    border-color: {COLORS['accent_hover']};
}}
QPushButton#Primary:pressed {{
    background: {COLORS['accent_press']};
    border-color: {COLORS['accent_press']};
}}
QPushButton#Primary:disabled {{
    background: transparent;
    border: 1px solid #3B3222;
    color: #7A6437;
}}
QPushButton#Danger {{
    background: transparent;
    border: 1px solid #6B3033;
    color: #F27378;
    font-weight: 600;
}}
QPushButton#Danger:hover {{
    background: {COLORS['danger']};
    border-color: {COLORS['danger']};
    color: #0B0E12;
}}
QPushButton#Danger:pressed {{
    background: #C23B40;
    border-color: #C23B40;
    color: #0B0E12;
}}
QPushButton#Danger:disabled {{
    background: transparent;
    border-color: #3A2224;
    color: #7A4C4F;
}}
QPushButton#Ghost {{
    background: transparent;
    border: 1px solid transparent;
    color: {COLORS['text_sub']};
}}
QPushButton#Ghost:hover {{
    background: transparent;
    border: 1px solid {COLORS['border']};
    color: {COLORS['text']};
}}
QPushButton#ConsoleGhost {{
    background: transparent;
    border: 1px solid {COLORS['console_border']};
    color: #8FA3B8;
    padding: 3px 10px;
    font-size: 8pt;
}}
QPushButton#ConsoleGhost:hover {{
    border-color: #33455A;
    color: #D8E4F0;
}}
QPushButton#UpdateHot {{
    background: {COLORS['accent_soft']};
    border: 1px solid #4A3A1B;
    color: {COLORS['accent']};
    font-weight: 600;
}}
QPushButton#UpdateHot:hover {{
    background: {COLORS['accent']};
    border-color: {COLORS['accent']};
    color: #0B0E12;
}}

/* ---------------------------------------------------------------- 进度条 */
QProgressBar {{
    background: #151C25;
    border: none;
    text-align: center;
}}
QProgressBar::chunk {{
    background: {COLORS['accent']};
}}
QProgressBar#ConsoleBar {{
    background: #141B24;
    border: none;
}}
QProgressBar#ConsoleBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #B87B1E, stop:0.6 #E0A03C, stop:1 #F2B45A);
}}

/* ---------------------------------------------------------------- 控制台 */
QLabel#ConsoleTitle {{
    font-family: "{FONT_MONO}";
    font-size: 9pt;
    font-weight: 700;
    color: #D6E3F0;
}}
QLabel#ConsoleHint {{
    font-family: "{FONT_MONO}";
    font-size: 7.5pt;
    color: {COLORS['console_dim']};
}}
QLabel#ConsoleStatValue {{
    font-family: "{FONT_MONO}";
    font-size: 12pt;
    font-weight: 700;
    color: #E9EFF7;
}}
QLabel#ConsoleStatLabel {{
    font-size: 7.5pt;
    color: {COLORS['console_dim']};
}}
QFrame#ConsoleStatCard {{
    background: transparent;
    border: none;
    border-top: 1px solid {COLORS['console_border']};
}}
QPlainTextEdit#Console {{
    background: {COLORS['console_bg']};
    border: 1px solid {COLORS['console_border']};
    color: {COLORS['console_text']};
    font-family: "{FONT_MONO}";
    font-size: 8.5pt;
    padding: 8px;
    selection-background-color: #3A2E18;
    selection-color: #F7EBD8;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: #2B3644;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #3C4C5E;
}}
QScrollBar#ConsoleScroll:vertical {{
    background: transparent;
    width: 10px;
}}
QScrollBar#ConsoleScroll::handle:vertical {{
    background: #26313D;
    min-height: 30px;
}}
QScrollBar#ConsoleScroll::handle:vertical:hover {{
    background: #3A4C60;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
}}
QScrollBar::handle:horizontal {{
    background: #2B3644;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ---------------------------------------------------------------- 宣传条 */
QFrame#PromoCard {{
    background: #101720;
    border: none;
    border-top: 1px solid {COLORS['border']};
    border-left: 3px solid {COLORS['accent']};
}}
QLabel#PromoKicker {{
    font-family: "{FONT_MONO}";
    font-size: 7.5pt;
    font-weight: 600;
    color: {COLORS['accent']};
}}
QLabel#PromoTitle {{
    font-size: 11.5pt;
    font-weight: 700;
    color: {COLORS['text']};
}}
QLabel#PromoDesc {{
    font-size: 8pt;
    color: {COLORS['text_sub']};
}}
QPushButton#PromoBtn {{
    background: {COLORS['accent']};
    color: #0B0E12;
    border: 1px solid {COLORS['accent']};
    padding: 8px 18px;
    font-weight: 700;
}}
QPushButton#PromoBtn:hover {{
    background: {COLORS['accent_hover']};
    border-color: {COLORS['accent_hover']};
}}
QPushButton#PromoBtn:pressed {{
    background: {COLORS['accent_press']};
}}
QPushButton#PromoBtn:disabled {{
    background: transparent;
    border-color: #3B3222;
    color: #7A6437;
}}

/* ---------------------------------------------------------------- 底栏 */
QLabel#FooterText {{
    font-family: "{FONT_MONO}";
    font-size: 8pt;
    color: {COLORS['text_muted']};
    background: #07090C;
    border-top: 1px solid {COLORS['border']};
    padding: 4px 16px;
}}

/* ---------------------------------------------------------------- 对话框 */
QDialog#ResidualDialog {{
    background: {COLORS['surface_alt']};
}}
QLabel#DialogTitle {{
    font-size: 13pt;
    font-weight: 700;
}}
QLabel#DialogSub {{
    font-size: 9pt;
    color: {COLORS['text_muted']};
}}
QListWidget#ResidualList {{
    background: {COLORS['console_bg']};
    border: 1px solid {COLORS['border']};
    padding: 2px;
    font-family: "{FONT_MONO}";
    font-size: 8.5pt;
}}
QListWidget#ResidualList::item {{
    border-bottom: 1px solid #141B24;
    padding: 3px;
}}
QListWidget#ResidualList::item:selected {{
    background: #241D10;
    color: {COLORS['text']};
}}
QFrame#DialogStat {{
    background: transparent;
    border: none;
    border-top: 1px solid {COLORS['border']};
}}
QDialog#UpdateDialog {{
    background: {COLORS['surface_alt']};
}}
QTextBrowser#UpdateNotes {{
    background: {COLORS['console_bg']};
    border: 1px solid {COLORS['border']};
    padding: 8px;
    font-size: 9pt;
    color: {COLORS['text_sub']};
}}
QMenu#TrayMenu {{
    background: {COLORS['surface_alt']};
    border: 1px solid {COLORS['border']};
    padding: 4px;
}}
QMenu#TrayMenu::item {{
    padding: 7px 18px;
    color: {COLORS['text']};
}}
QMenu#TrayMenu::item:selected {{
    background: #241D10;
    color: {COLORS['accent']};
}}
QMenu#TrayMenu::separator {{
    height: 1px;
    background: {COLORS['border']};
    margin: 4px 8px;
}}
QToolTip {{
    background: {COLORS['console_panel']};
    color: {COLORS['console_text']};
    border: 1px solid {COLORS['console_border']};
    padding: 4px 8px;
}}
"""


def apply(app):
    app.setStyleSheet(QSS)
