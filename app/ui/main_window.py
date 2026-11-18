"""主窗口：左侧导航 / 中间清单 / 右侧技术面板

这一版按安全软件的信息密度重排：窗口缩到 940×608，清单只列本机真实装了的，
卸载过程把“正在用什么技术”摆在右边，失败项直接给解决方案。
"""

import os
import time

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QFrame,
                               QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                               QPushButton, QScrollArea, QSizeGrip,
                               QVBoxLayout, QWidget)

from .. import (bootguard, cleanup, elevation, icon_provider, solutions,
                system_actions, updater)
from ..constants import (APP_NAME, APP_VERSION, APPS, BUNDLE_TECH, ENV_PREVIEW,
                         LOG_DIR, LOG_FILE, MODE_BUNDLE, MODE_INFO, MODE_SINGLE,
                         SUPPORT_HINT, env_flag)
from ..detector import Detected, Detector
from ..tray import TrayController
from ..worker import Worker
from .patrol_window import PatrolWindow
from .residual_dialog import ResidualDialog
from .update_dialog import UpdateDialog
from .widgets import (AdSlot, AppTile, EmptyState, ModeCard, NavItem,
                      SolutionBox, TechPanel, glyph_icon)

WIN_W, WIN_H = 940, 608


class _DragBar(QFrame):
    """无边框窗口的拖拽条：交给系统处理移动，缩放靠右下角 SizeGrip。"""

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle:
                handle.startSystemMove()
                return
        super().mousePressEvent(event)


class _DetectWorker(QThread):
    done = Signal(list)

    def run(self):
        try:
            found = Detector().detect(measure=True)
        except Exception:
            found = []
        self.done.emit(found)


def _clear(layout):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()


def _kv_line(key: str, value: str) -> QWidget:
    w = QWidget()
    row = QHBoxLayout(w)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(10)
    k = QLabel(key)
    k.setObjectName("SectionHint")
    k.setFixedWidth(84)
    v = QLabel(value)
    v.setObjectName("TileMeta")
    v.setWordWrap(True)
    v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    row.addWidget(k)
    row.addWidget(v, 1)
    return w


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("MainWindow")
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setWindowIcon(icon_provider.app_icon())
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.resize(WIN_W, WIN_H)
        self.setMinimumSize(880, 556)

        self._busy = False
        self._found: list[Detected] = []
        self._tiles: dict[str, AppTile] = {}
        self._selected: set[str] = set()
        self.mode = MODE_SINGLE
        self._detect: _DetectWorker | None = None
        self._worker: Worker | None = None
        self._upd: updater.CheckWorker | None = None
        self._patrol: PatrolWindow | None = None
        self._tray: TrayController | None = None
        self._release: dict | None = None
        self._pending_bundle = False
        self._ensure_log_dir()

        self._build_ui()
        self._wire()
        self._init_tray()
        self._refresh_boot_labels()

        QTimer.singleShot(60, self._refresh_installed)
        if not env_flag(ENV_PREVIEW):
            QTimer.singleShot(3200, lambda: self._check_updates(silent=True))

    # ------------------------------------------------------------ 基础
    def _ensure_log_dir(self):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
        except Exception:
            pass

    def log(self, message: str, level: str = "info"):
        stamp = time.strftime("%H:%M:%S")
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"{stamp} [{level}] {message}\n")
        except Exception:
            pass

    # ------------------------------------------------------------ 构建
    def _build_ui(self):
        host = QWidget()
        host.setObjectName("Content")
        root = QVBoxLayout(host)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_top())

        body = QWidget()
        row = QHBoxLayout(body)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self._build_side())

        self.stack = QWidget()
        self.stack_lay = QVBoxLayout(self.stack)
        self.stack_lay.setContentsMargins(0, 0, 0, 0)
        self.stack_lay.setSpacing(0)
        self.page_clean = self._build_page_clean()
        self.page_bundle = self._build_page_bundle()
        self.page_about = self._build_page_about()
        for page in (self.page_clean, self.page_bundle, self.page_about):
            self.stack_lay.addWidget(page)
        row.addWidget(self.stack, 1)

        row.addWidget(self._build_rail())
        root.addWidget(body, 1)

        foot = QWidget()
        foot.setFixedHeight(12)
        frow = QHBoxLayout(foot)
        frow.setContentsMargins(0, 0, 2, 2)
        frow.addStretch(1)
        grip = QSizeGrip(foot)
        grip.setFixedSize(12, 12)
        frow.addWidget(grip)
        root.addWidget(foot)

        self.setCentralWidget(host)
        self._switch_page(0)

    def _build_top(self) -> QWidget:
        bar = _DragBar()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(44)
        row = QHBoxLayout(bar)
        row.setContentsMargins(12, 0, 8, 0)
        row.setSpacing(8)

        logo = QLabel()
        logo.setPixmap(icon_provider.app_pixmap(20))
        logo.setFixedSize(20, 20)
        row.addWidget(logo)

        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 11pt; font-weight: 600;")
        row.addWidget(title)

        ver = QLabel(f"v{APP_VERSION}")
        ver.setObjectName("SectionHint")
        row.addWidget(ver)
        row.addStretch(1)

        self.chip_admin = QLabel("管理员")
        self.chip_admin.setObjectName("Badge")
        row.addWidget(self.chip_admin)

        self.btn_update = QPushButton()
        self.btn_update.setObjectName("IconBtn")
        self.btn_update.setIcon(glyph_icon("update", 16, "#5B6470"))
        self.btn_update.setToolTip("检查更新")
        self.btn_update.setFixedSize(26, 26)
        row.addWidget(self.btn_update)

        self.btn_min = QPushButton()
        self.btn_min.setObjectName("IconBtn")
        self.btn_min.setIcon(glyph_icon("min", 16, "#5B6470"))
        self.btn_min.setToolTip("最小化到托盘")
        self.btn_min.setFixedSize(26, 26)
        row.addWidget(self.btn_min)

        self.btn_close = QPushButton()
        self.btn_close.setObjectName("IconBtn")
        self.btn_close.setIcon(glyph_icon("close", 16, "#5B6470"))
        self.btn_close.setToolTip("关闭窗口（程序仍在托盘）")
        self.btn_close.setFixedSize(26, 26)
        row.addWidget(self.btn_close)
        return bar

    def _build_side(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(168)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(0, 12, 0, 10)
        lay.setSpacing(0)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_clean = NavItem("软件清理", "clean")
        self.nav_bundle = NavItem("一条龙", "bundle")
        self.nav_about = NavItem("关于与更新", "info")
        for i, item in enumerate((self.nav_clean, self.nav_bundle, self.nav_about)):
            self.nav_group.addButton(item, i)
            lay.addWidget(item)

        lay.addStretch(1)

        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 8, 10, 8)
        cl.setSpacing(4)
        self.lb_patrol = QLabel("开机巡检：未开启")
        self.lb_patrol.setObjectName("SectionHint")
        self.lb_patrol.setWordWrap(True)
        cl.addWidget(self.lb_patrol)
        self.lb_support = QLabel(SUPPORT_HINT)
        self.lb_support.setObjectName("AdFooter")
        self.lb_support.setWordWrap(True)
        cl.addWidget(self.lb_support)
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(10, 0, 10, 10)
        wl.addWidget(card)
        lay.addWidget(wrap)
        return side

    def _build_page_clean(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(14, 12, 14, 10)
        lay.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(8)
        title = QLabel("选择要卸载的软件")
        title.setObjectName("SectionTitle")
        head.addWidget(title)
        self.lb_count = QLabel("正在检测本机…")
        self.lb_count.setObjectName("SectionHint")
        head.addWidget(self.lb_count)
        head.addStretch(1)
        self.btn_refresh = QPushButton("重新检测")
        self.btn_refresh.setObjectName("Ghost")
        self.btn_all = QPushButton("全选")
        self.btn_all.setObjectName("Link")
        head.addWidget(self.btn_refresh)
        head.addWidget(self.btn_all)
        lay.addLayout(head)

        modes = QHBoxLayout()
        modes.setSpacing(10)
        self.card_single = ModeCard(MODE_SINGLE, MODE_INFO[MODE_SINGLE]["title"],
                                    MODE_INFO[MODE_SINGLE]["line"], parent=page)
        self.card_bundle = ModeCard(MODE_BUNDLE, MODE_INFO[MODE_BUNDLE]["title"],
                                    MODE_INFO[MODE_BUNDLE]["line"], "含扫盘", page)
        modes.addWidget(self.card_single, 1)
        modes.addWidget(self.card_bundle, 1)
        lay.addLayout(modes)

        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(1, 1, 1, 1)
        cl.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tile_host = QWidget()
        self.tile_box = QVBoxLayout(self.tile_host)
        self.tile_box.setContentsMargins(0, 0, 0, 0)
        self.tile_box.setSpacing(0)
        self.tile_box.addStretch(1)
        scroll.setWidget(self.tile_host)
        cl.addWidget(scroll)
        lay.addWidget(card, 1)

        foot = QHBoxLayout()
        foot.setSpacing(8)
        self.lb_stat = QLabel("尚未检测")
        self.lb_stat.setObjectName("StatChip")
        foot.addWidget(self.lb_stat)
        foot.addStretch(1)
        self.btn_clear = QPushButton("取消选择")
        self.btn_clear.setObjectName("Ghost")
        self.btn_primary = QPushButton("卸载选中（0）")
        self.btn_primary.setObjectName("Primary")
        foot.addWidget(self.btn_clear)
        foot.addWidget(self.btn_primary)
        lay.addLayout(foot)

        self.card_single.set_active(True)
        return page

    def _build_page_bundle(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(14, 12, 14, 10)
        lay.setSpacing(10)

        title = QLabel("一条龙 · 全家桶清除")
        title.setObjectName("SectionTitle")
        lay.addWidget(title)

        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(6)
        sub = QLabel("四个步骤按顺序跑，中间不自动重启，每一步都要你确认。")
        sub.setObjectName("SectionHint")
        sub.setWordWrap(True)
        cl.addWidget(sub)
        for i, (step, note) in enumerate((
                ("全量拆解", "本机检测到的全部 360 系软件，进程→服务→目录→注册表逐层清"),
                ("深度扫盘", "扫描各盘一级 360 目录、两处 Temp、桌面与下载目录"),
                ("残余复核", "残留项列进小窗，逐项勾选后再删，失败项给解决方案"),
                ("开机巡检", "可选登记：下次登录在右下角复查一次，结果仍需你确认")), 1):
            row = QHBoxLayout()
            row.setSpacing(8)
            num = QLabel(str(i))
            num.setObjectName("Mono")
            num.setFixedWidth(14)
            row.addWidget(num)
            name = QLabel(step)
            name.setObjectName("TileName")
            name.setFixedWidth(62)
            row.addWidget(name)
            desc = QLabel(note)
            desc.setObjectName("TileMeta")
            desc.setWordWrap(True)
            row.addWidget(desc, 1)
            cl.addLayout(row)
        lay.addWidget(card)

        patrol = QFrame()
        patrol.setObjectName("Card")
        pl = QVBoxLayout(patrol)
        pl.setContentsMargins(12, 10, 12, 10)
        pl.setSpacing(6)
        prow = QHBoxLayout()
        self.cb_boot = QCheckBox("登记开机巡检（右下角小窗）")
        self.cb_boot.toggled.connect(self._toggle_boot)
        prow.addWidget(self.cb_boot)
        prow.addStretch(1)
        self.btn_patrol_now = QPushButton("立即巡检")
        self.btn_patrol_now.setObjectName("Ghost")
        prow.addWidget(self.btn_patrol_now)
        pl.addLayout(prow)
        self.lb_boot = QLabel(bootguard.state_text())
        self.lb_boot.setObjectName("SectionHint")
        self.lb_boot.setWordWrap(True)
        pl.addWidget(self.lb_boot)
        lay.addWidget(patrol)

        tech = QFrame()
        tech.setObjectName("Card")
        tl = QVBoxLayout(tech)
        tl.setContentsMargins(12, 10, 12, 10)
        tl.setSpacing(5)
        cap = QLabel("会用到哪些技术")
        cap.setObjectName("TechTitle")
        tl.addWidget(cap)
        for name, note in BUNDLE_TECH:
            row = QHBoxLayout()
            row.setSpacing(8)
            lb = QLabel(name)
            lb.setObjectName("TileName")
            lb.setFixedWidth(76)
            row.addWidget(lb)
            desc = QLabel(note)
            desc.setObjectName("TileMeta")
            desc.setWordWrap(True)
            row.addWidget(desc, 1)
            tl.addLayout(row)
        lay.addWidget(tech)
        lay.addStretch(1)

        foot = QHBoxLayout()
        self.lb_bundle_hint = QLabel("清完会问你要不要重启，20 秒内可撤销")
        self.lb_bundle_hint.setObjectName("SectionHint")
        foot.addWidget(self.lb_bundle_hint)
        foot.addStretch(1)
        self.btn_bundle = QPushButton("开始一条龙清除")
        self.btn_bundle.setObjectName("Primary")
        foot.addWidget(self.btn_bundle)
        lay.addLayout(foot)
        return page

    def _build_page_about(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(14, 12, 14, 10)
        lay.setSpacing(10)

        title = QLabel("关于与更新")
        title.setObjectName("SectionTitle")
        lay.addWidget(title)

        info = QFrame()
        info.setObjectName("Card")
        il = QVBoxLayout(info)
        il.setContentsMargins(12, 10, 12, 10)
        il.setSpacing(5)
        il.addWidget(_kv_line("当前版本", f"v{APP_VERSION}"))
        il.addWidget(_kv_line("界面版本", "1.3 紧凑布局 · 浅色安全软件风格"))
        il.addWidget(_kv_line("支持范围",
                              f"{len(APPS) - 1} 款 360 系软件 + 小鸟壁纸（共 {len(APPS)} 款）"))
        il.addWidget(_kv_line("管理员", "已获得管理员权限" if elevation.is_admin()
                              else "未获得，请右键以管理员身份运行"))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_check = QPushButton("检查更新")
        self.btn_check.setObjectName("Ghost")
        self.btn_repo = QPushButton("打开发布页")
        self.btn_repo.setObjectName("Link")
        self.btn_log = QPushButton("打开日志目录")
        self.btn_log.setObjectName("Link")
        row.addWidget(self.btn_check)
        row.addWidget(self.btn_repo)
        row.addWidget(self.btn_log)
        row.addStretch(1)
        il.addLayout(row)
        lay.addWidget(info)

        apps_card = QFrame()
        apps_card.setObjectName("Card")
        al = QVBoxLayout(apps_card)
        al.setContentsMargins(12, 10, 12, 10)
        al.setSpacing(4)
        cap = QLabel("支持清单")
        cap.setObjectName("TechTitle")
        al.addWidget(cap)
        names = [a["name"] for a in APPS]
        for i in range(0, len(names), 3):
            row = QHBoxLayout()
            row.setSpacing(6)
            for name in names[i:i + 3]:
                lb = QLabel(name)
                lb.setObjectName("TileMeta")
                row.addWidget(lb, 1)
            if len(names[i:i + 3]) < 3:
                row.addStretch(1)
            al.addLayout(row)
        lay.addWidget(apps_card)

        safe = QFrame()
        safe.setObjectName("Card")
        sl = QVBoxLayout(safe)
        sl.setContentsMargins(12, 10, 12, 10)
        sl.setSpacing(3)
        cap = QLabel("安全边界")
        cap.setObjectName("TechTitle")
        sl.addWidget(cap)
        for line in ("不做后台静默批量删除，巡检结果必须你确认",
                     "不自动重启、不做重启循环、不注册后台服务",
                     "只清理 360 系与小鸟壁纸相关目录，不碰其他软件"):
            lb = QLabel("· " + line)
            lb.setObjectName("TileMeta")
            lb.setWordWrap(True)
            sl.addWidget(lb)
        lay.addWidget(safe)
        lay.addStretch(1)
        return page

    def _build_rail(self) -> QWidget:
        rail = QWidget()
        rail.setFixedWidth(264)
        lay = QVBoxLayout(rail)
        lay.setContentsMargins(10, 12, 12, 12)
        lay.setSpacing(10)
        self.panel_tech = TechPanel()
        self.solbox = SolutionBox()
        self.ad = AdSlot()
        lay.addWidget(self.panel_tech)
        lay.addWidget(self.solbox)
        lay.addWidget(self.ad)
        lay.addStretch(1)
        self.lb_tip = QLabel("日志：%s" % LOG_DIR)
        self.lb_tip.setObjectName("AdFooter")
        self.lb_tip.setWordWrap(True)
        lay.addWidget(self.lb_tip)
        return rail

    # ------------------------------------------------------------ 连接
    def _wire(self):
        self.nav_group.idClicked.connect(self._switch_page)
        self.btn_refresh.clicked.connect(self._refresh_installed)
        self.btn_all.clicked.connect(self._toggle_all)
        self.btn_clear.clicked.connect(self._clear_selection)
        self.btn_primary.clicked.connect(self._on_primary)
        self.btn_bundle.clicked.connect(self._start_bundle)
        self.btn_patrol_now.clicked.connect(self._start_patrol)
        self.btn_check.clicked.connect(lambda: self._check_updates(False))
        self.btn_repo.clicked.connect(updater.open_release_page)
        self.btn_log.clicked.connect(self._open_log_dir)
        self.btn_update.clicked.connect(lambda: self._check_updates(False))
        self.btn_min.clicked.connect(self._minimize_to_tray)
        self.btn_close.clicked.connect(self.close)
        self.card_single.clicked.connect(self._set_mode)
        self.card_bundle.clicked.connect(self._set_mode)
        self.ad.clicked.connect(self._on_ad_clicked)

    def _switch_page(self, index: int):
        for i, page in enumerate((self.page_clean, self.page_bundle,
                                  self.page_about)):
            page.setVisible(i == index)
        for i, nav in enumerate((self.nav_clean, self.nav_bundle, self.nav_about)):
            nav.setChecked(i == index)

    def _set_mode(self, mode: str):
        if self._busy or mode not in MODE_INFO:
            return
        self.mode = mode
        self.card_single.set_active(mode == MODE_SINGLE)
        self.card_bundle.set_active(mode == MODE_BUNDLE)
        single = mode == MODE_SINGLE
        for tile in self._tiles.values():
            tile.box.setEnabled(single)
            if not single:
                tile.set_checked(False)
        self._switch_page(1 if mode == MODE_BUNDLE else 0)
        self._update_action_state()

    def _on_ad_clicked(self, key: str):
        tile = self._tiles.get(key)
        if tile is None:
            QMessageBox.information(
                self, "本机未安装",
                "这款软件没有在本机检测到，所以列表里没有它。\n"
                "推广位只做公告，不会凭空列出未安装的软件。")
            return
        self.panel_tech.push(f"推广位：已在列表里勾选 {key}")
        tile.set_checked(True)
        self._switch_page(0)

    # ------------------------------------------------------------ 检测
    def _refresh_installed(self):
        if self._busy:
            return
        if env_flag(ENV_PREVIEW):
            if os.environ.get("PREVIEW_EMPTY") == "1":
                self._on_detected([])
            else:
                self._populate_demo()
            return
        if self._detect and self._detect.isRunning():
            return
        self.lb_count.setText("正在检测本机…")
        self._detect = _DetectWorker(self)
        self._detect.done.connect(self._on_detected)
        self._detect.start()

    def _on_detected(self, found: list):
        _clear(self.tile_box)
        self._tiles.clear()
        self._selected.clear()
        self._found = list(found)

        if not found:
            self.tile_box.addWidget(EmptyState(
                "本机没有检测到 360 系软件或小鸟壁纸",
                "支持清单里的其余产品不会显示；装过但目录已清空的，也不再列出"))
            self.lb_count.setText("检测到 0 款")
            self.lb_stat.setText("没有可清理对象")
            self._update_action_state()
            return

        for item in found:
            tile = AppTile(item)
            tile.toggled.connect(self._on_tile_toggled)
            self.tile_box.addWidget(tile)
            self._tiles[item.key] = tile
        self.tile_box.addStretch(1)

        total = sum(f.size for f in found)
        self.lb_count.setText(f"检测到 {len(found)} 款")
        self.lb_stat.setText(
            f"{len(found)} 款 · {cleanup.human_size(total)} · "
            f"{sum(1 for f in found if f.running)} 款正在运行")
        self._set_mode(self.mode)
        self._update_action_state()
        self.log(f"检测到 {len(found)} 款：" +
                 "、".join(f.key for f in found))

    def _on_tile_toggled(self, key: str, checked: bool):
        if checked:
            self._selected.add(key)
        else:
            self._selected.discard(key)
        self._update_action_state()

    def _toggle_all(self):
        if self.mode != MODE_SINGLE:
            return
        all_on = all(t.is_checked() for t in self._tiles.values()) if self._tiles else False
        for tile in self._tiles.values():
            tile.set_checked(not all_on)

    def _clear_selection(self):
        for tile in self._tiles.values():
            tile.set_checked(False)

    def _update_action_state(self):
        n = len(self._tiles)
        if self.mode == MODE_BUNDLE:
            self.btn_primary.setText("开始一条龙清除")
            self.btn_primary.setEnabled(n > 0 and not self._busy)
            self.btn_bundle.setEnabled(n > 0 and not self._busy)
        else:
            self.btn_primary.setText(f"卸载选中（{len(self._selected)}）")
            self.btn_primary.setEnabled(bool(self._selected) and not self._busy)
            self.btn_bundle.setEnabled(n > 0 and not self._busy)
        self.btn_refresh.setEnabled(not self._busy)
        self.btn_all.setEnabled(not self._busy and self.mode == MODE_SINGLE)

    # ------------------------------------------------------------ 卸载
    def _on_primary(self):
        if self.mode == MODE_BUNDLE:
            self._start_bundle()
            return
        apps = [f.app for f in self._found if f.key in self._selected]
        if not apps:
            QMessageBox.information(self, "先选一下", "请先勾选要卸载的软件。")
            return
        names = "\n".join("· " + a["name"] for a in apps)
        ret = QMessageBox.question(
            self, "确认单项卸载",
            f"即将卸载：\n{names}\n\n"
            "不会调用官方卸载程序，直接结束进程、删服务、删目录、清注册表。\n"
            "单项模式不扫盘、不登记开机巡检。继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            self._start_uninstall(apps, bundle=False)

    def _start_bundle(self):
        if self._busy:
            return
        if not self._found:
            self._refresh_installed()
            QMessageBox.information(self, "还没有可清理对象", "先重新检测一次。")
            return
        total = sum(f.size for f in self._found)
        ret = QMessageBox.question(
            self, "确认一条龙清除",
            f"将清理本机检测到的 {len(self._found)} 款，共 {cleanup.human_size(total)}。\n\n"
            "流程：全量拆解 → 深度扫盘 → 残余复核 → 可选开机巡检。\n"
            "自保护开启时部分项目会被内核拦下，会给出解决方案，不会假装删成功。\n"
            "清完会问你要不要重启，不自动重启。继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            self._start_uninstall([f.app for f in self._found], bundle=True)

    def _start_uninstall(self, apps: list, bundle: bool):
        if self._busy:
            return
        self._busy = True
        self._pending_bundle = bundle
        self.panel_tech.reset("开始拆解…")
        self.panel_tech.set_badge("执行中", "warn")
        self.solbox.clear()
        self._switch_page(0)
        self._update_action_state()

        self._worker = Worker(Worker.MODE_UNINSTALL,
                              {"apps": apps, "with_common": bundle}, self)
        self._worker.log.connect(self._on_log)
        self._worker.progress.connect(self._on_progress)
        self._worker.tech.connect(self._on_tech)
        self._worker.result.connect(self._on_uninstall_result)
        self._worker.start()

    def _on_log(self, message: str):
        self.log(message)
        if len(message) > 96:
            message = message[:93] + "…"
        self.panel_tech.push(message)

    def _on_progress(self, pct: int, text: str):
        self.panel_tech.set_progress(pct)
        self.panel_tech.set_stage(text)

    def _on_tech(self, text: str):
        self.panel_tech.set_tech("技术：" + text)
        self.log("技术：" + text)

    def _on_uninstall_result(self, data: dict):
        self._busy = False
        self._update_action_state()
        ok = int(data.get("ok", 0))
        fail = int(data.get("fail", 0))
        pending = int(data.get("pending", 0))
        freed = data.get("freed_text", "")
        self.panel_tech.set_progress(100)
        self.panel_tech.set_stage(
            f"拆解结束：成功 {ok} · 失败 {fail} · 登记重启删除 {pending}")
        self.panel_tech.set_badge("完成" if fail == 0 else "有失败项",
                                  "ok" if fail == 0 else "warn")
        if freed:
            self.panel_tech.push(f"释放空间 {freed}")

        sols = solutions.collect(data.get("rows", []))
        if data.get("protected"):
            sols.append(solutions.for_protected(int(data["protected"]),
                                                data.get("safe_pack", "")))
        self.solbox.set_solutions([s.to_dict() for s in sols])

        deep = bool(self._pending_bundle)
        dlg = ResidualDialog(self, deep=deep,
                             title="残余项目检查" + ("（含扫盘）" if deep else ""))
        dlg.exec()
        self._after_cleanup(data, dlg)

    def _after_cleanup(self, data: dict, dlg: ResidualDialog):
        rows = list(data.get("rows", []))
        extra = dlg.cleanup_data or {}
        rows.extend(extra.get("rows", []))
        sols = solutions.collect(rows)
        if sols:
            self.solbox.set_solutions([s.to_dict() for s in sols])

        pending = int(data.get("pending", 0)) + int(extra.get("pending", 0))
        self._ask_reboot(pending)
        if self._pending_bundle:
            self._offer_boot_patrol()
        self._refresh_installed()

    def _ask_reboot(self, pending: int):
        msg = "清扫已结束。"
        if pending:
            msg += f"\n其中 {pending} 项登记为重启后删除。"
        msg += "\n\n现在重启吗？选“是”会在 20 秒后重启，期间可在命令提示符执行"
        msg += "\nshutdown /a 撤销。"
        ret = QMessageBox.question(
            self, "是否重启",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        ok, text = system_actions.schedule_reboot(20)
        if ok:
            QMessageBox.information(
                self, "已安排重启",
                f"{text}。\n要撤销：Win+R 输入 cmd，执行 shutdown /a。")
        else:
            QMessageBox.warning(self, "无法安排重启", text)

    def _offer_boot_patrol(self):
        if bootguard.is_enabled():
            return
        ret = QMessageBox.question(
            self, "登记开机巡检",
            "下次登录时在右下角弹出巡检小窗，复查残留。\n"
            "小窗可随时关闭，结果必须你确认才清理，不会自动重启。\n"
            "要现在登记吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        ok, text = bootguard.enable()
        self._refresh_boot_labels()
        if ok:
            QMessageBox.information(self, "已登记开机巡检", text)
        else:
            QMessageBox.warning(self, "登记失败", text)

    # ------------------------------------------------------------ 巡检
    def _toggle_boot(self, checked: bool):
        if self._busy:
            return
        if checked:
            ret = QMessageBox.question(
                self, "开启开机巡检",
                "登录后会在右下角出现巡检小窗，344×176，带扫描动图。\n"
                "小窗有关闭按钮，删除项需要你确认，不会自动重启。继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes)
            if ret != QMessageBox.StandardButton.Yes:
                self.cb_boot.blockSignals(True)
                self.cb_boot.setChecked(False)
                self.cb_boot.blockSignals(False)
                return
            ok, text = bootguard.enable()
        else:
            ok, text = bootguard.disable()
        self._refresh_boot_labels()
        if not ok:
            QMessageBox.warning(self, "设置未生效", text)
        else:
            self.panel_tech.push(text)

    def _refresh_boot_labels(self):
        try:
            enabled = bootguard.is_enabled()
        except Exception:
            enabled = False
        self.cb_boot.blockSignals(True)
        self.cb_boot.setChecked(enabled)
        self.cb_boot.blockSignals(False)
        text = "开机巡检：已开启" if enabled else "开机巡检：未开启"
        self.lb_patrol.setText(text)
        self.lb_boot.setText(bootguard.state_text() +
                             "（计划任务优先，失败退回注册表启动项）")
        if self._tray:
            self._tray.set_boot_state(enabled)

    def _start_patrol(self):
        if self._patrol is not None:
            self._patrol.close()
        self._patrol = PatrolWindow(self, auto_start=True)
        self._patrol.destroyed.connect(lambda _=None: self._refresh_installed())
        self._patrol.show_at_corner()

    # ------------------------------------------------------------ 托盘与更新
    def _init_tray(self):
        try:
            self._tray = TrayController(self)
        except Exception:
            self._tray = None
            return
        self._tray.show_requested.connect(self._restore_window)
        self._tray.scan_requested.connect(self._refresh_installed)
        self._tray.patrol_requested.connect(self._start_patrol)
        self._tray.boot_toggle_requested.connect(self._toggle_boot)
        self._tray.update_requested.connect(lambda: self._check_updates(False))
        self._tray.quit_requested.connect(self.quit_app)
        try:
            if self._tray.available():
                self._tray.start()
        except Exception:
            pass

    def _restore_window(self):
        self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    def _minimize_to_tray(self):
        if self._tray and self._tray.available():
            self.hide()
            self._tray.notify_minimized()
        else:
            self.showMinimized()

    def _check_updates(self, silent: bool = False):
        if self._upd and self._upd.isRunning():
            return
        self._upd = updater.CheckWorker(self)
        self._upd.done.connect(lambda data: self._on_update_checked(data, silent))
        self._upd.start()
        if not silent:
            self.panel_tech.push("正在检查更新…")

    def _on_update_checked(self, data: dict, silent: bool):
        if data.get("error"):
            if not silent:
                QMessageBox.warning(self, "检查更新失败", data["error"])
            return
        release = data.get("release") or {}
        if not data.get("has_update"):
            if not silent:
                QMessageBox.information(self, "已是最新版本",
                                       f"当前 v{APP_VERSION} 就是最新版。")
            return
        self._release = release
        dlg = UpdateDialog(release, self)
        dlg.install_requested.connect(self.quit_app)
        dlg.exec()

    def _open_log_dir(self):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            if os.name == "nt":
                os.startfile(LOG_DIR)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", LOG_DIR])
        except Exception as exc:
            QMessageBox.warning(self, "打不开日志目录", str(exc))

    def quit_app(self):
        for worker in (self._worker, self._detect, self._upd):
            try:
                if worker and worker.isRunning():
                    if hasattr(worker, "request_stop"):
                        worker.request_stop()
                    worker.wait(2500)
            except Exception:
                pass
        if self._tray:
            self._tray.icon.hide()
        QApplication.quit()

    # ------------------------------------------------------------ 演示
    def _populate_demo(self):
        demo = [
            ("360safe", ["进程 · 360tray.exe", "目录 · C:\\Program Files (x86)\\360\\360Safe",
                         "服务 · 360rp"], 1_612_345_678, True, "360 安全卫士"),
            ("360se", ["目录 · C:\\Program Files (x86)\\360\\360se6",
                       "注册表 · HKCU\\Software\\360se6"], 486_221_000, True, "360 安全浏览器"),
            ("360zip", ["目录 · C:\\Program Files (x86)\\360\\360zip"], 132_908_000,
             False, "360 压缩"),
            ("360aioffice", ["目录 · C:\\Program Files (x86)\\360\\360AIOffice",
                             "服务 · 360aioffice"], 318_774_000, False, "360 AI 办公"),
            ("xiaoniao", ["目录 · C:\\Users\\Administrator\\AppData\\Local\\XiaoNiao",
                          "进程 · xiaoniao.exe"], 742_113_000, True, "小鸟壁纸"),
        ]
        apps = {a["key"]: a for a in APPS}
        found = []
        for key, evidence, size, running, _name in demo:
            app = apps.get(key)
            if not app:
                continue
            dirs = [e.split(" · ", 1)[1] for e in evidence if e.startswith("目录")]
            found.append(Detected(key=key, name=app["name"], desc=app["desc"],
                                  app=app, evidence=list(evidence), dirs=dirs,
                                  size=size, running=running))
        self._on_detected(found)
        self.panel_tech.set_stage("演示状态：等待开始")
        self.panel_tech.set_tech("技术：进程树终止 · taskkill /T /F")
        self.solbox.set_solutions([{
            "title": "被 360 内核驱动拦截",
            "steps": ["先退出 360 托盘并关闭自我保护，再执行清理",
                      "已有残留驱动就进安全模式清理，正常模式下删不掉是预期行为"],
        }])
        self.lb_stat.setText("5 款 · 3.2 GB · 3 款正在运行")

    # ------------------------------------------------------------ 收尾
    def closeEvent(self, event: QCloseEvent):
        if self._tray and self._tray.available():
            event.ignore()
            self.hide()
            self._tray.notify_minimized()
            return
        if self._worker and self._worker.isRunning():
            ret = QMessageBox.question(
                self, "仍在清理", "后台还在清理，现在退出会中断。确定退出？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if ret != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        super().closeEvent(event)
