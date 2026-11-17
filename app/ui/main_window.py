"""主窗口：左侧主界面 + 右侧控制台"""

import os
import time

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QMainWindow, QMessageBox, QPushButton,
                               QScrollArea, QSizePolicy, QSystemTrayIcon,
                               QVBoxLayout, QWidget)

from .. import (bootguard, cleanup, elevation, icon_provider, system_actions,
                updater)
from ..constants import (APP_NAME, APP_NAME_EN, APP_TAGLINE, APP_VERSION,
                         APPS, ENV_NO_DISCLAIMER, ENV_PREVIEW, LOG_DIR,
                         LOG_FILE, env_flag)
from ..scanner import Item
from ..tray import TrayController
from ..worker import Worker
from .patrol_window import PatrolWindow
from .residual_dialog import ResidualDialog
from .update_dialog import UpdateDialog
from .widgets import (AppRow, BottomFade, ConsoleWidget, PromoCard, ScanHud,
                      StatCard, table_header)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setWindowIcon(icon_provider.app_icon())
        self.resize(1240, 860)
        self.setMinimumSize(1080, 720)

        self.settings = QSettings("ResidualCleaner", "Cleaner")
        self.rows: dict[str, AppRow] = {}
        self.items: list[Item] = []
        self.items_by_app: dict[str, list[Item]] = {}
        self.status: dict = {}
        self.summary: dict = {}
        self.worker: Worker | None = None
        self.busy = False
        self.force_quit = False
        self.pending_release: dict | None = None
        self.check_worker = None
        self.update_worker = None
        self.tray: TrayController | None = None
        self.hud: ScanHud | None = None
        self.patrol: PatrolWindow | None = None
        self._last_cleanup: dict | None = None
        self.preview_mode = env_flag(ENV_PREVIEW)

        self._ensure_log_dir()
        self._build_ui()
        self._wire()
        self._init_tray()

        QTimer.singleShot(120, self._show_disclaimer_if_needed)
        if self.preview_mode:
            QTimer.singleShot(60, self._populate_demo)
        else:
            QTimer.singleShot(260, self.start_scan)
            QTimer.singleShot(4000, self._auto_check_update)

    # ------------------------------------------------------------ 基础设施
    def _ensure_log_dir(self):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            if not os.path.exists(LOG_FILE):
                with open(LOG_FILE, "w", encoding="utf-8") as f:
                    f.write(f"{APP_NAME} {APP_VERSION} 日志\n")
        except Exception:
            pass

    def log(self, message: str, level: str = "info"):
        self.console.log(message, level)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
        except Exception:
            pass

    # ------------------------------------------------------------ 界面构建
    def _build_ui(self):
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_topbar())

        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)
        body_lay.addWidget(self._build_left_panel(), 66)
        self.console = ConsoleWidget()
        body_lay.addWidget(self.console, 34)
        outer.addWidget(body, 1)

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("FooterText")
        self.status_label.setMinimumHeight(26)
        outer.addWidget(self.status_label)

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(58)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 0, 18, 0)
        lay.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(icon_provider.app_pixmap(30))
        logo.setFixedSize(32, 32)
        lay.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel(APP_NAME)
        title.setObjectName("BrandTitle")
        sub = QLabel(f"{APP_NAME_EN} · {APP_TAGLINE}")
        sub.setObjectName("BrandSub")
        titles.addWidget(title)
        titles.addWidget(sub)
        lay.addLayout(titles)

        lay.addStretch(1)

        self.btn_deepscan = QPushButton("深度扫描")
        self.btn_deepscan.setObjectName("Ghost")
        self.btn_deepscan.setCursor(Qt.PointingHandCursor)
        self.btn_deepscan.setToolTip("在右下角小窗里显示扫盘进度，扫完再进结果窗口")
        lay.addWidget(self.btn_deepscan)

        self.btn_update = QPushButton("检查更新")
        self.btn_update.setObjectName("Ghost")
        self.btn_update.setCursor(Qt.PointingHandCursor)
        self.btn_update.setToolTip("从 GitHub Releases 检查新版本，可下载后自动安装")
        lay.addWidget(self.btn_update)

        self.badge_boot = QLabel("巡检：关")
        self.badge_boot.setObjectName("AdminBadge")
        self.badge_boot.setCursor(Qt.PointingHandCursor)
        self.badge_boot.setToolTip("开机巡检：勾选后下次开机会在右下角弹出巡检小窗，随时可关闭")
        self.badge_boot.mousePressEvent = self._on_boot_badge_clicked  # type: ignore
        lay.addWidget(self.badge_boot)

        self.badge_version = QLabel(f"v{APP_VERSION}")
        self.badge_version.setObjectName("VersionBadge")
        lay.addWidget(self.badge_version)

        is_admin = elevation.is_admin()
        self.badge_admin = QLabel("管理员模式" if is_admin else "受限模式")
        self.badge_admin.setObjectName("AdminBadge")
        self.badge_admin.setProperty("on", "true" if is_admin else "false")
        self.badge_admin.setProperty("warn", "false" if is_admin else "true")
        self.badge_admin.setCursor(Qt.PointingHandCursor)
        self.badge_admin.setToolTip(
            "已获得最高权限，可处理服务与受保护目录" if is_admin
            else "点击以管理员身份重新启动，获得完整清理权限"
        )
        self.badge_admin.mousePressEvent = self._on_admin_badge_clicked  # type: ignore
        lay.addWidget(self.badge_admin)

        self.btn_rescan = QPushButton("重新扫描")
        self.btn_rescan.setObjectName("Primary")
        self.btn_rescan.setCursor(Qt.PointingHandCursor)
        lay.addWidget(self.btn_rescan)
        return bar

    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("LeftPanel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # 标题区
        head_wrap = QWidget()
        head = QHBoxLayout(head_wrap)
        head.setContentsMargins(20, 14, 20, 8)
        head.setSpacing(10)
        title = QLabel("清理工作台")
        title.setObjectName("SectionTitle")
        hint = QLabel("勾选需要卸载的应用")
        hint.setObjectName("SectionHint")
        self.head_hint = hint
        self.btn_select_all = QPushButton("全选")
        self.btn_select_all.setObjectName("Ghost")
        self.btn_select_all.setCursor(Qt.PointingHandCursor)
        head.addWidget(title)
        head.addWidget(hint)
        head.addStretch(1)
        head.addWidget(self.btn_select_all)
        lay.addWidget(head_wrap)

        # 读数条
        stats_wrap = QWidget()
        stats = QHBoxLayout(stats_wrap)
        stats.setContentsMargins(20, 0, 20, 10)
        stats.setSpacing(0)
        self.card_installed = StatCard("检测到应用")
        self.card_items = StatCard("可清理项")
        self.card_size = StatCard("占用空间")
        stats.addWidget(self.card_installed, 1)
        stats.addWidget(self.card_items, 1)
        stats.addWidget(self.card_size, 1)
        lay.addWidget(stats_wrap)

        lay.addWidget(table_header())

        scroll = QScrollArea()
        scroll.setObjectName("AppScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.app_scroll = scroll
        host = QWidget()
        host.setObjectName("AppListHost")
        self.app_list_lay = QVBoxLayout(host)
        self.app_list_lay.setContentsMargins(0, 0, 0, 0)
        self.app_list_lay.setSpacing(0)

        for idx, app in enumerate(APPS):
            row = AppRow(idx, app)
            row.toggled.connect(self._on_row_toggled)
            self.rows[app["key"]] = row
            self.app_list_lay.addWidget(row)
        self.app_list_lay.addStretch(1)
        scroll.setWidget(host)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.list_fade = BottomFade(scroll.viewport(), 30)

        # 列表容器：渐隐层与“还有更多”提示共同解决半截行被硬切的问题
        list_holder = QWidget()
        grid = QGridLayout(list_holder)
        grid.setContentsMargins(20, 0, 20, 0)
        grid.setSpacing(0)
        grid.addWidget(scroll, 0, 0)
        lay.addWidget(list_holder, 1)

        bar = scroll.verticalScrollBar()
        bar.rangeChanged.connect(lambda *_: self._update_more_hint())
        bar.valueChanged.connect(lambda *_: self._update_more_hint())

        self.promo = PromoCard()
        lay.addWidget(self.promo)

        # 操作区
        act_wrap = QWidget()
        actions = QHBoxLayout(act_wrap)
        actions.setContentsMargins(20, 12, 20, 14)
        actions.setSpacing(8)
        self.btn_uninstall = QPushButton("卸载选中应用")
        self.btn_uninstall.setObjectName("Primary")
        self.btn_uninstall.setCursor(Qt.PointingHandCursor)
        self.btn_uninstall.setEnabled(False)
        self.btn_uninstall.setMinimumHeight(38)

        self.btn_oneclick = QPushButton("360 一键清除")
        self.btn_oneclick.setObjectName("Danger")
        self.btn_oneclick.setCursor(Qt.PointingHandCursor)
        self.btn_oneclick.setMinimumHeight(38)

        self.btn_log = QPushButton("打开日志")
        self.btn_log.setObjectName("Ghost")
        self.btn_log.setCursor(Qt.PointingHandCursor)
        self.btn_log.setMinimumHeight(38)

        actions.addWidget(self.btn_uninstall, 1)
        actions.addWidget(self.btn_oneclick, 1)
        actions.addWidget(self.btn_log)
        lay.addWidget(act_wrap)
        return panel

    def _wire(self):
        self.btn_rescan.clicked.connect(self.start_scan)
        self.btn_deepscan.clicked.connect(self._start_deep_scan)
        self.btn_select_all.clicked.connect(self._toggle_select_all)
        self.btn_uninstall.clicked.connect(self._on_uninstall_clicked)
        self.btn_oneclick.clicked.connect(self._on_oneclick_clicked)
        self.btn_update.clicked.connect(self._on_update_clicked)
        self.promo.action.connect(self._on_promo_clicked)
        self.btn_log.clicked.connect(self._open_log)

    # ------------------------------------------------------------ 交互辅助
    def _on_admin_badge_clicked(self, _event):
        if elevation.is_admin():
            QMessageBox.information(self, "权限状态",
                                    "当前已是管理员权限，可执行完整清理。")
            return
        if elevation.relaunch_as_admin():
            self.close()
            QTimer.singleShot(0, lambda: os._exit(0))

    def _on_row_toggled(self, _key: str, _checked: bool):
        self._update_action_state()

    def _selected_apps(self) -> list[dict]:
        return [a for a in APPS if self.rows[a["key"]].is_checked()]

    def _toggle_select_all(self):
        selectable = [r for r in self.rows.values() if r.cb.isEnabled()]
        target = (not all(r.is_checked() for r in selectable)) if selectable else False
        for r in selectable:
            r.set_checked(target)
        self.btn_select_all.setText("全不选" if target else "全选")
        self._update_action_state()

    def _clear_selection(self):
        for r in self.rows.values():
            r.set_checked(False)
        self.btn_select_all.setText("全选")
        self._update_action_state()

    def _installed_apps(self) -> list[dict]:
        return [a for a in APPS if self.status.get(a["key"], {}).get("installed")]

    def _refresh_promo(self):
        installed = len(self._installed_apps())
        if self.busy:
            self.promo.set_button_state(False, "执行中…", "任务执行期间不可再次发起")
        elif not self.status:
            self.promo.set_button_state(False, "扫描后可用", "先完成一次扫描")
        elif installed == 0:
            self.promo.set_button_state(False, "未检测到 360", "当前系统没有可清除的 360 组件")
        else:
            self.promo.set_button_state(True, "彻底清除",
                                        f"一次勾选全部 {installed} 款 360 应用并执行完整拆除")

    def _update_action_state(self):
        count = len(self._selected_apps())
        self.btn_uninstall.setText(f"卸载选中应用（{count}）" if count else "卸载选中应用")
        self.btn_uninstall.setEnabled(count > 0 and not self.busy)
        self.btn_uninstall.setToolTip("" if count else "先勾选需要卸载的应用（也可直接点整行）")
        self.btn_oneclick.setEnabled(not self.busy)
        self.btn_rescan.setEnabled(not self.busy)

    def _update_more_hint(self):
        if self.busy:
            return
        bar = self.app_scroll.verticalScrollBar()
        more = bar.maximum() > 0 and bar.value() < bar.maximum()
        self.head_hint.setText("勾选需要卸载的应用 · 列表可滚动查看全部"
                               if more else "勾选需要卸载的应用")

    def _open_log(self):
        try:
            os.startfile(LOG_FILE)
        except Exception as exc:
            QMessageBox.warning(self, "无法打开日志", str(exc))

    def _busy(self, on: bool, stage: str = ""):
        self.busy = on
        self._update_action_state()
        self.btn_select_all.setEnabled(not on)
        for row in self.rows.values():
            row.set_interactive(not on)
        self.head_hint.setText("正在执行，暂不可调整勾选" if on else "勾选需要卸载的应用")
        self._refresh_promo()
        if stage:
            self.status_label.setText(stage)
            self.console.set_stage(stage)
        if not on:
            if self.hud is not None:
                self.hud.hide()
            # 任务结束后恢复“可滚动”提示与渐隐层正确状态
            QTimer.singleShot(0, self._update_more_hint)

    # ------------------------------------------------------------ 托盘 / 更新
    def _init_tray(self):
        if self.preview_mode:
            return
        try:
            if not QSystemTrayIcon.isSystemTrayAvailable():
                self.log("系统托盘不可用，关闭窗口将直接退出", "warn")
                return
            self.tray = TrayController(self)
            self.tray.show_requested.connect(self._restore_window)
            self.tray.scan_requested.connect(self._tray_scan)
            self.tray.patrol_requested.connect(self._start_patrol)
            self.tray.boot_toggle_requested.connect(self._toggle_boot_patrol)
            self.tray.update_requested.connect(lambda: self._check_updates(False))
            self.tray.quit_requested.connect(self.quit_app)
            self.tray.start()
            self.tray.set_boot_state(bootguard.is_enabled())
            self.log("托盘常驻已启用：关闭窗口会最小化到右下角托盘", "info")
        except Exception as exc:
            self.tray = None
            self.log(f"托盘初始化失败：{exc}", "warn")
        self._refresh_boot_badge()

    def _restore_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _tray_scan(self):
        self._restore_window()
        if self.busy:
            self._notify("任务进行中", "当前还有任务在执行，完成后再扫描。")
            return
        self.start_scan()

    def _notify(self, title: str, message: str):
        if self.tray and self.tray.available():
            self.tray.notify(title, message)

    # ------------------------------------------------------------ 开机巡检
    def _refresh_boot_badge(self):
        on = bootguard.is_enabled()
        self.badge_boot.setText("巡检：开" if on else "巡检：关")
        self.badge_boot.setProperty("on", "true" if on else "false")
        self.badge_boot.setProperty("warn", "false" if on else "true")
        self.badge_boot.style().unpolish(self.badge_boot)
        self.badge_boot.style().polish(self.badge_boot)
        if self.tray:
            self.tray.set_boot_state(on)

    def _on_boot_badge_clicked(self, _event):
        self._toggle_boot_patrol(not bootguard.is_enabled())

    def _toggle_boot_patrol(self, enabled: bool):
        """启动项只由这个开关写入，写之前把边界讲清楚。"""
        if enabled and not bootguard.is_enabled():
            ret = QMessageBox.question(
                self, "开启开机巡检",
                "开启后，下次开机会在右下角自动弹出巡检小窗，扫描全部 360 目录：\n\n"
                "· 窗口一直可见，带 ✕ 关闭，不会藏在后台；\n"
                "· 找到项目后仍要你点“立即清理”并二次确认才会删；\n"
                "· 删除完成后才问你要不要重启，不会自动重启；\n"
                "· 随时可在本界面或托盘菜单里关掉这一项，不留后台服务。\n\n"
                "确定登记到下次开机启动吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                if self.tray:
                    self.tray.set_boot_state(False)
                self._refresh_boot_badge()
                return

        ok, msg = bootguard.sync_state(bool(enabled))
        if not ok:
            QMessageBox.warning(self, "开机巡检设置失败", msg)
            self._refresh_boot_badge()
            return
        self.log(msg, "ok" if enabled else "info")
        self.status_label.setText(msg)
        self._refresh_boot_badge()
        if self.tray and enabled:
            self.tray.notify("开机巡检已开启", "下次开机会在右下角自动巡检 360 残留。")

    def _start_patrol(self):
        """从托盘或界面手动拉起巡检小窗（不写注册表）。"""
        if getattr(self, "patrol", None) is None:
            self.patrol = PatrolWindow(self, auto_start=True)
        self.patrol.show_at_corner()

    def _offer_boot_patrol(self):
        """清理完成后问一次要不要登记开机巡检，拒绝后本轮不再重复问。"""
        if bootguard.is_enabled() or self.settings.value("boot_offer_asked", "false") == "true":
            return
        self.settings.setValue("boot_offer_asked", "true")
        ret = QMessageBox.question(
            self, "下次开机自动复查？",
            "这次清理已经完成。要不要登记一次开机巡检？\n\n"
            "下次开机时右下角会弹出小窗，扫描各个 360 目录和散落残留；\n"
            "窗口可见、可关闭，删除前仍需你确认，也不会自动重启。\n\n"
            "登记后随时可以在顶栏“巡检”或托盘菜单里关掉。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret == QMessageBox.Yes:
            self._toggle_boot_patrol(True)
        else:
            self.log("用户未开启开机巡检", "info")

    def _ask_reboot(self, ok: int, fail: int, pending: int) -> bool:
        """删除后询问是否重启；只有用户点“是”才安排重启。"""
        if ok == 0 and pending == 0:
            return False
        if pending or fail:
            text = (f"清理完成：成功 {ok} 项，失败 {fail} 项，"
                    f"{pending} 项已登记到重启后删除。\n\n"
                    "现在重启电脑完成收尾吗？")
        else:
            text = f"清理完成：成功 {ok} 项。\n\n建议重启一次释放被占用的文件，现在重启吗？"
        ret = QMessageBox.question(
            self, "是否重启电脑",
            text + "\n\n选择“是”后有 20 秒倒计时，期间可执行 shutdown /a 取消。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            self.log("用户选择稍后重启", "info")
            return False
        ok_sched, msg = system_actions.schedule_reboot(20)
        if ok_sched:
            QMessageBox.information(self, "已安排重启",
                                    "系统将在 20 秒后重启。\n取消命令：shutdown /a")
            self.log(msg, "warn")
            return True
        QMessageBox.warning(self, "重启失败", f"无法安排重启：{msg}\n请手动重启电脑。")
        return False

    def _auto_check_update(self):
        try:
            last = float(self.settings.value("last_update_check", 0) or 0)
        except Exception:
            last = 0
        if time.time() - last < 86400:
            return
        self._check_updates(True)

    def _check_updates(self, silent: bool = False):
        if self.check_worker and self.check_worker.isRunning():
            if not silent:
                self.status_label.setText("正在检查更新…")
            return
        self.btn_update.setEnabled(False)
        self.btn_update.setText("检查中…")
        self.status_label.setText("正在检查更新…")
        self.check_worker = updater.CheckWorker(self)
        self.check_worker.done.connect(lambda d: self._on_update_checked(d, silent))
        self.check_worker.start()

    def _on_update_checked(self, data: dict, silent: bool):
        self.btn_update.setEnabled(True)
        self.btn_update.setText("检查更新")
        err = data.get("error")
        if err:
            self.status_label.setText("检查更新失败（可稍后重试）")
            self.log(f"检查更新失败：{err}", "warn")
            if not silent:
                QMessageBox.warning(
                    self, "检查更新失败",
                    f"无法连接 GitHub：{err}\n\n"
                    f"可以稍后重试，或手动访问：\n{updater.RELEASE_PAGE}")
            return

        self.settings.setValue("last_update_check", time.time())
        release = data.get("release") or {}
        tag = release.get("tag", "")
        if not data.get("has_update"):
            self.status_label.setText(f"已是最新版本 v{APP_VERSION}")
            self.log(f"检查更新：当前 v{APP_VERSION} 已是最新", "info")
            if not silent:
                QMessageBox.information(
                    self, "已是最新版本",
                    f"当前版本 v{APP_VERSION} 已是最新，无需更新。")
            return

        self.pending_release = release
        self.btn_update.setText(f"有新版本 {tag}")
        self.btn_update.setObjectName("UpdateHot")
        self.btn_update.style().unpolish(self.btn_update)
        self.btn_update.style().polish(self.btn_update)
        self.log(f"发现新版本 {tag}（当前 v{APP_VERSION}）", "ok")
        self.status_label.setText(f"发现新版本 {tag}，点击“有新版本”查看")
        self._notify("发现新版本", f"{tag} 已发布，点击主界面“有新版本”可下载安装。")
        if not self.busy:
            self._show_update_dialog()

    def _show_update_dialog(self):
        if not self.pending_release:
            return
        dlg = UpdateDialog(self.pending_release, self)
        dlg.install_requested.connect(self._finish_update_install)
        dlg.exec()

    def _finish_update_install(self):
        """更新安装前的收尾：停掉后台任务，隐藏托盘，再退出让脚本替换文件。"""
        self.force_quit = True
        if self.worker and self.worker.isRunning():
            self.worker.request_stop()
            self.worker.wait(3000)
        if self.tray:
            self.tray.icon.hide()
        QTimer.singleShot(0, QApplication.quit)

    def _on_update_clicked(self):
        if self.pending_release:
            self._show_update_dialog()
            return
        self._check_updates(False)

    def quit_app(self):
        self.force_quit = True
        if self.worker and self.worker.isRunning():
            # 从托盘退出时窗口可能是隐藏的，确认框要先有可见窗口
            self._restore_window()
            ret = QMessageBox.question(
                self, "任务仍在进行",
                "扫描或清理还没有结束，现在退出会中止剩余步骤，"
                "可能留下删了一半的项目。\n\n确定要退出吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                self.force_quit = False
                return
            self.worker.request_stop()
            self.worker.wait(2500)
            self.log("用户中止任务并退出程序", "warn")
        if self.tray:
            self.tray.icon.hide()
        QApplication.quit()

    # ------------------------------------------------------------ 扫描
    def start_scan(self):
        if self.busy:
            return
        self._busy(True, "正在扫描…")
        self.console.log("开始扫描 360 系列应用与清理项", "title")
        self.console.set_progress(0, "准备扫描")

        self.worker = Worker(Worker.MODE_SCAN, parent=self)
        self.worker.log.connect(lambda m: self.log(m))
        self.worker.progress.connect(self._on_progress)
        self.worker.result.connect(self._on_scan_result)
        self.worker.start()

    def _on_progress(self, pct: int, text: str):
        self.console.set_progress(pct, text)
        self.status_label.setText(text)

    def _on_scan_result(self, data: dict):
        self.items = data.get("items", [])
        self.status = data.get("status", {})
        self.summary = data.get("summary", {})
        self.items_by_app = {}
        for item in self.items:
            self.items_by_app.setdefault(item.app_key, []).append(item)

        installed_count = 0
        for app in APPS:
            key = app["key"]
            st = self.status.get(key, {})
            installed = bool(st.get("installed"))
            note = st.get("note", "")
            items = self.items_by_app.get(key, [])
            size = sum(i.size for i in items)
            self.rows[key].set_state(installed, note, len(items),
                                     cleanup.human_size(size))
            # 安装目录存在时优先用程序自己的 exe/ico
            self.rows[key].set_real_icon(installed)
            if installed:
                installed_count += 1

        total_size = sum(i.size for i in self.items)
        self.card_installed.set_value(str(installed_count))
        self.card_items.set_value(str(len(self.items)))
        self.card_size.set_value(cleanup.human_size(total_size))
        self._clear_selection()
        self.console.set_stats(ok=0, fail=0, freed="0 B")
        self.console.set_progress(100, "扫描完成")
        self._busy(False, f"扫描完成：{installed_count} 款应用，{len(self.items)} 个可清理项")
        self.log(f"扫描完成：检测到 {installed_count} 款应用，"
                 f"{len(self.items)} 个可清理项，合计 {cleanup.human_size(total_size)}", "ok")
        QTimer.singleShot(0, self._update_more_hint)
        if self.tray:
            self.tray.set_tooltip(
                f"{APP_NAME} {APP_VERSION} · {installed_count} 款 360 应用待处理")
        self._notify("扫描完成",
                     f"检测到 {installed_count} 款 360 应用，{len(self.items)} 个可清理项。")

    def _start_deep_scan(self):
        if self.busy:
            return
        self._busy(True, "深度扫描中…")
        self.console.log("开始深度扫描：进程 / 服务 / 目录 / 注册表 / 启动项 / DLL / 磁盘残留",
                         "title")
        self.console.set_progress(0, "准备深度扫描")
        if self.hud is None:
            self.hud = ScanHud("深度扫描 · 全盘残留", self)
            self.hud.cancel_clicked.connect(self._cancel_deep_scan)
        self.hud.update_state("正在准备扫描…", 0)
        self.hud.show_at_corner()

        self.worker = Worker(Worker.MODE_RESIDUAL, {"deep": True}, parent=self)
        self.worker.log.connect(lambda m: self.log(m))
        self.worker.progress.connect(self._on_deep_progress)
        self.worker.result.connect(self._on_deep_result)
        self.worker.start()

    def _on_deep_progress(self, pct: int, text: str):
        self.console.set_progress(pct, text)
        self.status_label.setText(text)
        if self.hud is not None and self.hud.isVisible():
            self.hud.update_state(text or "扫描中…", pct)

    def _cancel_deep_scan(self):
        if self.worker and self.worker.isRunning():
            self.worker.request_stop()
            if self.hud:
                self.hud.update_state("正在停止…", self.hud.bar.value())

    def _on_deep_result(self, data: dict):
        if self.hud is not None:
            self.hud.hide()
        items = data.get("items", [])
        self._busy(False, f"深度扫描完成：{len(items)} 项待处理")
        self.log(f"深度扫描完成：共 {len(items)} 项残留", "ok")
        dlg = ResidualDialog(self, deep=False, title="深度扫描结果", items=items)
        dlg.finished_cleanup.connect(self._on_residual_cleanup)
        dlg.finished.connect(self._after_residual_dialog)
        dlg.show()

    # ------------------------------------------------------------ 卸载
    def _on_uninstall_clicked(self):
        apps = self._selected_apps()
        if not apps:
            return
        names = "、".join(a["name"] for a in apps)
        total_items = sum(len(self.items_by_app.get(a["key"], [])) for a in apps)
        ret = QMessageBox.question(
            self, "确认卸载",
            f"将卸载 {len(apps)} 款应用：\n{names}\n\n"
            f"共 {total_items} 个清理项（进程、服务、目录、注册表、计划任务、快捷方式）。\n"
            "不调用官方卸载程序，直接逐项拆除。注册表删除前会自动备份。\n\n"
            "确定继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return

        items_by_app = {a["key"]: self.items_by_app.get(a["key"], []) for a in apps}
        self._busy(True, "正在卸载…")
        self.console.log(f"开始卸载 {len(apps)} 款应用（{total_items} 个清理项）", "title")
        self.console.set_progress(0, "准备卸载")

        self.worker = Worker(Worker.MODE_UNINSTALL,
                             {"apps": apps, "items_by_app": items_by_app}, parent=self)
        self.worker.log.connect(self._on_worker_log)
        self.worker.progress.connect(self._on_progress)
        self.worker.result.connect(self._on_uninstall_result)
        self.worker.start()

    def _on_worker_log(self, message: str):
        level = "ok" if message.startswith("✔") else ("err" if message.startswith("✘") else "info")
        self.log(message, level)

    def _on_uninstall_result(self, data: dict):
        ok = data.get("ok", 0)
        fail = data.get("fail", 0)
        freed = data.get("freed_text", "0 B")
        pending = data.get("pending", 0)
        self.console.set_stats(ok=ok, fail=fail, freed=freed)
        self.console.set_progress(100, "卸载流程结束")
        stage = (f"卸载完成：成功 {ok} 项，失败 {fail} 项（失败原因见控制台）"
                 if fail else f"卸载完成：全部 {ok} 项已处理，释放 {freed}")
        if pending:
            stage += f" · {pending} 项已登记重启后删除"
        self._busy(False, stage)
        self._clear_selection()
        self.log(f"卸载完成：成功 {ok} 项，失败 {fail} 项，释放 {freed}"
                 + (f"，{pending} 项待重启后删除" if pending else ""),
                 "warn" if fail else "ok")
        self._notify("卸载完成",
                     f"成功 {ok} 项，失败 {fail} 项，释放 {freed}"
                     + (f"，{pending} 项待重启后删除" if pending else ""))

        # 卸载完成 → 进入残余扫描小窗
        QTimer.singleShot(320, lambda: self._open_residual_dialog(
            "卸载完成 · 残余项目检查"))

    def _open_residual_dialog(self, title: str = "残余项目检查"):
        self._last_cleanup = None
        dlg = ResidualDialog(self, deep=True, title=title)
        dlg.finished_cleanup.connect(self._on_residual_cleanup)
        # 无论“删除”还是“跳过”，关闭后都重扫一次，避免主界面停在旧状态
        dlg.finished.connect(self._after_residual_dialog)
        dlg.show()
        QTimer.singleShot(80, dlg.start_scan)

    def _after_residual_dialog(self, _code: int = 0):
        """残余小窗关闭后再问重启与开机巡检，避免提示被模态窗口盖住。"""
        QTimer.singleShot(0, self.start_scan)
        if not self._last_cleanup:
            return
        QTimer.singleShot(200, self._post_cleanup_flow)

    def _post_cleanup_flow(self):
        result = self._last_cleanup
        self._last_cleanup = None
        if not result:
            return
        rebooted = self._ask_reboot(result.get("ok", 0), result.get("fail", 0),
                                    result.get("pending", 0))
        if not rebooted:
            self._offer_boot_patrol()

    def _on_residual_cleanup(self, data: dict):
        ok = data.get("ok", 0)
        fail = data.get("fail", 0)
        pending = data.get("pending", 0)
        freed = data.get("freed_text", "0 B")
        self.console.set_stats(ok=ok, fail=fail, freed=freed)
        self.log(f"残余清理：成功 {ok} 项，失败 {fail} 项，释放 {freed}"
                 + (f"，{pending} 项待重启后删除" if pending else ""),
                 "warn" if fail else "ok")
        self.status_label.setText(
            f"残余清理完成，释放 {freed}" + (f"，{fail} 项未删掉（见小窗）" if fail else "")
            + (f"，{pending} 项待重启后删除" if pending else "")
            + " · 建议重启电脑")
        self._notify("残余清理完成",
                     f"成功 {ok} 项，失败 {fail} 项，释放 {freed}"
                     + (f"，{pending} 项待重启后删除" if pending else ""))
        if ok or pending:
            self._last_cleanup = {"ok": ok, "fail": fail, "pending": pending}

    # ------------------------------------------------------------ 一键清除
    def _on_promo_clicked(self):
        if self.busy:
            return
        installed = self._installed_apps()
        if not installed:
            if not self.status:
                QMessageBox.information(self, "请稍候",
                                        "正在扫描系统，扫描完成后即可一键清除。")
            else:
                QMessageBox.information(self, "无需清理",
                                        "未检测到 360 系列应用与残留，系统很干净。")
            return
        # 宣传区直接进确认清单，不再让用户多点一次按钮
        for a in installed:
            row = self.rows[a["key"]]
            if row.cb.isEnabled():
                row.set_checked(True)
        self._update_action_state()
        self.log(f"一键清除：已自动勾选 {len(installed)} 款 360 应用", "info")
        self._on_oneclick_clicked()

    def _on_oneclick_clicked(self):
        if self.busy:
            return
        targets = [a for a in APPS if self.status.get(a["key"], {}).get("installed")]
        items_by_app = {a["key"]: self.items_by_app.get(a["key"], []) for a in targets}
        common = [i for i in self.items if not i.app_key]

        total = sum(len(v) for v in items_by_app.values()) + len(common)
        if total == 0:
            QMessageBox.information(self, "无需清理", "未发现可清除的 360 相关项目。")
            return

        kinds: dict[str, int] = {}
        for group in list(items_by_app.values()) + [common]:
            for i in group:
                kinds[i.kind_label] = kinds.get(i.kind_label, 0) + 1
        detail = "，".join(f"{k} {v} 项" for k, v in kinds.items())

        preview = []
        for group in list(items_by_app.values()) + [common]:
            for i in group[:3]:
                preview.append(f"· [{i.kind_label}] {i.label}")
        preview_text = "\n".join(preview[:10])

        ret = QMessageBox.warning(
            self, "360 一键清除 · 确认清单",
            f"即将处理 {len(targets)} 款 360 应用的全部相关项目：\n\n"
            f"共 {total} 项（{detail}）\n\n"
            f"部分项目预览：\n{preview_text}\n"
            + ("……\n" if total > 10 else "")
            + "\n执行方式：结束进程 → 删除服务 → 清理计划任务 → 强力删除目录 → "
              "备份并清理注册表 → 删除快捷方式。\n"
              "无权访问的目录会先结束占用它的 360 进程、重置 ACL 并接管所有权后重删；"
              "仍被系统锁住的会登记到下次开机时由系统删除。\n\n"
              "此操作不可恢复（注册表会自动备份到日志目录）。确定执行吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            self.log("用户取消了一键清除", "warn")
            return

        for a in targets:
            self.rows[a["key"]].set_checked(True)

        self._busy(True, "正在执行 360 一键清除…")
        self.console.log(f"360 一键清除：{len(targets)} 款应用，共 {total} 项", "title")
        self.console.set_progress(0, "准备清除")

        self.worker = Worker(Worker.MODE_UNINSTALL,
                             {"apps": targets, "items_by_app": items_by_app,
                              "extra_items": common}, parent=self)
        self.worker.log.connect(self._on_worker_log)
        self.worker.progress.connect(self._on_progress)
        self.worker.result.connect(self._on_oneclick_result)
        self.worker.start()

    def _on_oneclick_result(self, data: dict):
        ok = data.get("ok", 0)
        fail = data.get("fail", 0)
        freed = data.get("freed_text", "0 B")
        pending = data.get("pending", 0)
        self.console.set_stats(ok=ok, fail=fail, freed=freed)
        self.console.set_progress(100, "一键清除完成")
        stage = (f"一键清除完成：成功 {ok} 项，失败 {fail} 项（失败原因见控制台）"
                 if fail else f"一键清除完成：全部 {ok} 项已处理，释放 {freed}")
        if pending:
            stage += f" · {pending} 项已登记重启后删除"
        self._busy(False, stage)
        self._clear_selection()
        self.log(f"一键清除完成：成功 {ok} 项，失败 {fail} 项，释放 {freed}"
                 + (f"，{pending} 项待重启后删除" if pending else ""),
                 "warn" if fail else "ok")
        self._notify("360 一键清除完成",
                     f"成功 {ok} 项，失败 {fail} 项，释放 {freed}"
                     + (f"，{pending} 项待重启后删除" if pending else ""))
        QTimer.singleShot(320, lambda: self._open_residual_dialog(
            "一键清除完成 · 残余项目检查"))

    # ------------------------------------------------------------ 预览演示
    def _populate_demo(self):
        """预览模式：填充演示数据，不触发真实扫描。"""
        demo = {
            "360safe": (True, "正在运行", 12, 553_648_128),
            "360sd": (True, "已安装", 8, 226_492_416),
            "360se": (True, "已安装", 6, 1_288_490_188),
            "360zip": (True, "已安装", 3, 25_792_512),
            "360drvmgr": (True, "已安装", 4, 92_602_368),
            "360softmgr": (True, "已安装", 3, 164_288_512),
            "360chromex": (True, "已安装", 5, 335_712_256),
            "360yunpan": (True, "已安装", 2, 68_157_440),
        }
        installed = 0
        total_items = 0
        total_size = 0
        for app in APPS:
            key = app["key"]
            if key in demo:
                _inst, note, count, size = demo[key]
                self.rows[key].set_state(True, note, count, cleanup.human_size(size))
                installed += 1
                total_items += count
                total_size += size
            else:
                self.rows[key].set_state(False, "", 0, "0 B")

        self.card_installed.set_value(str(installed))
        self.card_items.set_value(str(total_items))
        self.card_size.set_value(cleanup.human_size(total_size))
        for app in APPS:
            self.rows[app["key"]].set_real_icon(app["key"] in demo)
        self.status = {a["key"]: {"installed": a["key"] in demo} for a in APPS}
        self._refresh_promo()

        self.console.log("开始扫描 360 系列应用与清理项", "title")
        self.console.log("读取卸载注册表：WOW6432Node\\...\\Uninstall")
        self.console.log("注册表卸载项命中 8 个 360 相关条目")
        self.console.log("扫描安装目录：Program Files (x86)\\360")
        self.console.log("进程检测：360tray.exe / 360sd.exe 正在运行", "warn")
        self.console.log("服务检测：360rp、360SoftMgrSvc 待处理")
        self.console.log("计划任务：360SafeUpdate 等 2 项")
        self.console.log("快捷方式：桌面 3 项、开始菜单 5 项")
        self.console.log("保护探测：ZhuDongFangYu 驱动运行中", "warn")
        self.console.log("2 个注册表键转为离线清理包", "warn")
        self.console.log(f"扫描完成：{installed} 款应用，"
                         f"{total_items} 个可清理项，合计 {cleanup.human_size(total_size)}", "ok")
        self.console.set_progress(100, "扫描完成")
        self.console.set_stats(ok=26, fail=1, freed="2.1 GB")
        self.status_label.setText(f"扫描完成：{installed} 款应用，{total_items} 个可清理项")
        QTimer.singleShot(0, self._update_more_hint)

    # ------------------------------------------------------------ 免责
    def _show_disclaimer_if_needed(self):
        if env_flag(ENV_NO_DISCLAIMER):
            return
        if self.settings.value("disclaimer_accepted", "false") == "true":
            return
        text = (
            f"欢迎使用 {APP_NAME}。\n\n"
            "本工具用于卸载 360 系列软件并清理残留，执行前请注意：\n\n"
            "1. 会结束相关进程、停止并删除相关服务；\n"
            "2. 会删除安装目录与残留文件，部分操作需要接管文件所有权"
            "（takeown / icacls）；\n"
            "3. 会备份后删除相关注册表项；\n"
            "4. 删除操作不可恢复，请确认已不再需要这些软件与数据；\n"
            "5. 本工具与奇虎 360 无任何关联，为第三方独立工具。\n\n"
            "所有清理项都会先列清单、经你确认后才执行。"
        )
        box = QMessageBox(self)
        box.setWindowTitle("使用前确认")
        box.setIcon(QMessageBox.Information)
        box.setText(text)
        box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        box.button(QMessageBox.Ok).setText("我已了解，继续")
        box.button(QMessageBox.Cancel).setText("退出")
        if box.exec() != QMessageBox.Ok:
            self.quit_app()
            return
        self.settings.setValue("disclaimer_accepted", "true")

    # ------------------------------------------------------------ 关闭
    def closeEvent(self, event: QCloseEvent):
        # 有托盘时：关闭 = 最小化到托盘，任务继续在后台跑
        if not self.force_quit and self.tray and self.tray.available():
            self.hide()
            if self.worker and self.worker.isRunning():
                self._notify("任务仍在后台执行",
                             "窗口已隐藏，任务会继续完成，结束后托盘会提示结果。")
            else:
                self.tray.notify_minimized()
            event.ignore()
            return

        if self.worker and self.worker.isRunning():
            ret = QMessageBox.question(
                self, "任务仍在进行",
                "扫描或清理还没有结束，现在关闭会中止剩余步骤，"
                "可能留下删了一半的项目。\n\n建议等它跑完再关闭。确定要退出吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                event.ignore()
                return
            self.worker.request_stop()
            self.worker.wait(2500)
            self.log("用户中止任务并退出程序", "warn")
        if self.tray:
            self.tray.icon.hide()
        event.accept()
