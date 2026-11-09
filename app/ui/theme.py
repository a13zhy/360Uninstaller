"""界面主题：现代浅色主区 + 深色控制台"""

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
    "bg": "#F2F4F7",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FAFC",
    "border": "#E2E7EE",
    "border_strong": "#CBD5E1",
    "text": "#101828",
    "text_sub": "#475467",
    "text_muted": "#98A2B3",
    "accent": "#1E63D6",
    "accent_hover": "#1852B8",
    "accent_press": "#12408F",
    "accent_soft": "#EAF1FD",
    "teal": "#0E9384",
    "danger": "#D92D20",
    "danger_hover": "#B42318",
    "danger_soft": "#FEF3F2",
    "success": "#12B76A",
    "warn": "#F79009",
    "console_bg": "#0F141A",
    "console_panel": "#141B23",
    "console_border": "#232D3A",
    "console_text": "#C9D6E3",
    "console_dim": "#7C8DA0",
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
QWidget#TopBar {{
    background: {COLORS['surface']};
    border-bottom: 1px solid {COLORS['border']};
}}
QLabel#BrandTitle {{
    font-size: 15pt;
    font-weight: 700;
    color: {COLORS['text']};
}}
QLabel#BrandSub {{
    font-size: 9pt;
    color: {COLORS['text_muted']};
}}
QLabel#VersionBadge {{
    background: {COLORS['surface_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    padding: 2px 9px;
    color: {COLORS['text_sub']};
    font-size: 8pt;
}}
QLabel#AdminBadge {{
    background: #ECFDF3;
    border: 1px solid #ABEFC6;
    border-radius: 10px;
    padding: 2px 9px;
    color: #067647;
    font-size: 8pt;
    font-weight: 600;
}}
QLabel#AdminBadge[warn="true"] {{
    background: #FFFAEB;
    border: 1px solid #FEDF89;
    color: #B54708;
}}
QFrame#LeftPanel {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
}}
QFrame#ConsolePanel {{
    background: {COLORS['console_panel']};
    border: 1px solid {COLORS['console_border']};
    border-radius: 12px;
}}
QLabel#SectionTitle {{
    font-size: 11pt;
    font-weight: 700;
    color: {COLORS['text']};
}}
QLabel#SectionHint {{
    font-size: 8.5pt;
    color: {COLORS['text_muted']};
}}
QLabel#ConsoleTitle {{
    font-size: 10pt;
    font-weight: 700;
    color: #E8EEF5;
}}
QLabel#ConsoleHint {{
    font-size: 8pt;
    color: {COLORS['console_dim']};
}}
QLabel#StatValue {{
    font-size: 16pt;
    font-weight: 700;
    color: {COLORS['text']};
}}
QLabel#StatLabel {{
    font-size: 8.5pt;
    color: {COLORS['text_muted']};
}}
QLabel#ConsoleStatValue {{
    font-size: 13pt;
    font-weight: 700;
    color: #E8EEF5;
}}
QLabel#ConsoleStatLabel {{
    font-size: 8pt;
    color: {COLORS['console_dim']};
}}
QFrame#StatCard {{
    background: {COLORS['surface_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
}}
QFrame#ConsoleStatCard {{
    background: {COLORS['console_bg']};
    border: 1px solid {COLORS['console_border']};
    border-radius: 10px;
}}

/* 应用列表 */
QScrollArea#AppScroll {{
    background: transparent;
    border: none;
}}
QWidget#AppListHost {{
    background: transparent;
}}
QFrame#AppRow {{
    background: {COLORS['surface_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
}}
QFrame#AppRow:hover {{
    background: {COLORS['accent_soft']};
    border-color: #BFD3F2;
}}
QFrame#AppRow[checked="true"] {{
    background: #F0F6FF;
    border-color: #A6C4F1;
}}
QLabel#AppName {{
    font-size: 10pt;
    font-weight: 600;
}}
QLabel#AppDesc {{
    font-size: 8.5pt;
    color: {COLORS['text_muted']};
}}
QLabel#AppState {{
    font-size: 8pt;
    padding: 1px 8px;
    border-radius: 8px;
}}
QLabel#AppState[state="installed"] {{
    background: #ECFDF3;
    color: #067647;
}}
QLabel#AppState[state="clean"] {{
    background: #F2F4F7;
    color: {COLORS['text_muted']};
}}
QLabel#AppState[state="running"] {{
    background: #EAF1FD;
    color: {COLORS['accent']};
}}

QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1.5px solid {COLORS['border_strong']};
    background: {COLORS['surface']};
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
    background: #A6C4F1;
    border-color: #A6C4F1;
    {CHECK_IMG}
}}

/* 按钮 */
QPushButton {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border_strong']};
    border-radius: 8px;
    padding: 7px 16px;
    color: {COLORS['text']};
}}
QPushButton:hover {{
    background: {COLORS['surface_alt']};
    border-color: {COLORS['accent']};
}}
QPushButton:pressed {{
    background: {COLORS['accent_soft']};
}}
QPushButton:disabled {{
    color: {COLORS['text_muted']};
    border-color: {COLORS['border']};
    background: {COLORS['surface_alt']};
}}
QPushButton#Primary {{
    background: {COLORS['accent']};
    border: 1px solid {COLORS['accent']};
    color: #FFFFFF;
    font-weight: 600;
}}
QPushButton#Primary:hover {{
    background: {COLORS['accent_hover']};
    border-color: {COLORS['accent_hover']};
}}
QPushButton#Primary:pressed {{
    background: {COLORS['accent_press']};
}}
QPushButton#Primary:disabled {{
    background: #E3EDFB;
    border-color: #C6D9F2;
    color: #7E96B8;
}}
QPushButton#Danger {{
    background: {COLORS['danger']};
    border: 1px solid {COLORS['danger']};
    color: #FFFFFF;
    font-weight: 600;
}}
QPushButton#Danger:hover {{
    background: {COLORS['danger_hover']};
    border-color: {COLORS['danger_hover']};
}}
QPushButton#Danger:disabled {{
    background: #FBE3E1;
    border-color: #F3C6C1;
    color: #BC7B74;
}}
QPushButton#Ghost {{
    background: transparent;
    border: 1px solid transparent;
    color: {COLORS['text_sub']};
}}
QPushButton#Ghost:hover {{
    background: {COLORS['surface_alt']};
    border-color: {COLORS['border']};
}}
QPushButton#ConsoleGhost {{
    background: transparent;
    border: 1px solid {COLORS['console_border']};
    color: #A9BACB;
    padding: 5px 12px;
}}
QPushButton#ConsoleGhost:hover {{
    border-color: #3A4A5E;
    color: #DCE8F4;
}}
QPushButton#UpdateHot {{
    background: #FFFAEB;
    border: 1px solid #FEDF89;
    color: #B54708;
    font-weight: 600;
}}
QPushButton#UpdateHot:hover {{
    background: #FEF0C7;
    border-color: #F79009;
}}

/* 进度条 */
QProgressBar {{
    background: {COLORS['border']};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: {COLORS['accent']};
    border-radius: 4px;
}}
QProgressBar#ConsoleBar {{
    background: {COLORS['console_bg']};
    border: 1px solid {COLORS['console_border']};
}}
QProgressBar#ConsoleBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #12B76A, stop:0.5 #1E63D6, stop:1 #0E9384);
    border-radius: 4px;
}}

/* 控制台 */
QPlainTextEdit#Console {{
    background: {COLORS['console_bg']};
    border: 1px solid {COLORS['console_border']};
    border-radius: 8px;
    color: {COLORS['console_text']};
    font-family: "{FONT_MONO}";
    font-size: 9pt;
    padding: 8px;
    selection-background-color: #1E63D6;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 2px 1px 2px 1px;
}}
QScrollBar::handle:vertical {{
    background: #AEBBC9;
    border-radius: 5px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background: #8C9CAE;
}}
QScrollBar#ConsoleScroll:vertical {{
    background: transparent;
    width: 12px;
}}
QScrollBar#ConsoleScroll::handle:vertical {{
    background: #33455A;
    border-radius: 5px;
    min-height: 32px;
}}
QScrollBar#ConsoleScroll::handle:vertical:hover {{
    background: #46607C;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background: #C7D0DB;
    border-radius: 4px;
}}

/* 宣传区 */
QFrame#PromoCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1E63D6, stop:0.55 #0E9384, stop:1 #0B7285);
    border: none;
    border-radius: 12px;
}}
QLabel#PromoKicker {{
    color: rgba(255,255,255,0.72);
    font-size: 8pt;
    font-weight: 600;
    letter-spacing: 1px;
}}
QLabel#PromoTitle {{
    color: #FFFFFF;
    font-size: 14pt;
    font-weight: 800;
}}
QLabel#PromoDesc {{
    color: rgba(255,255,255,0.88);
    font-size: 9pt;
}}
QLabel#PromoBadge {{
    color: #E9FFFA;
    background: rgba(255,255,255,0.16);
    border: 1px solid rgba(255,255,255,0.30);
    border-radius: 9px;
    padding: 2px 8px;
    font-size: 8pt;
}}
QPushButton#PromoBtn {{
    background: #FFFFFF;
    color: #0B4C8A;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 700;
}}
QPushButton#PromoBtn:hover {{
    background: #EAF4FF;
}}
QPushButton#PromoBtn:pressed {{
    background: #D6E9FF;
}}

/* 对话框 */
QDialog#ResidualDialog {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
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
    background: {COLORS['surface_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 4px;
}}
QListWidget#ResidualList::item {{
    border-bottom: 1px solid #EEF2F6;
    padding: 2px;
}}
QListWidget#ResidualList::item:selected {{
    background: {COLORS['accent_soft']};
    color: {COLORS['text']};
}}
QFrame#DialogStat {{
    background: {COLORS['surface_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
}}
QDialog#UpdateDialog {{
    background: {COLORS['surface']};
}}
QTextBrowser#UpdateNotes {{
    background: {COLORS['surface_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px;
    font-size: 9pt;
    color: {COLORS['text_sub']};
}}
QMenu#TrayMenu {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 4px;
}}
QMenu#TrayMenu::item {{
    padding: 7px 18px;
    border-radius: 6px;
    color: {COLORS['text']};
}}
QMenu#TrayMenu::item:selected {{
    background: {COLORS['accent_soft']};
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
