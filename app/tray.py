"""系统托盘常驻：右键菜单、气泡提示、关窗最小化"""

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from . import constants, icon_provider


class TrayController(QObject):
    show_requested = Signal()
    scan_requested = Signal()
    patrol_requested = Signal()
    boot_toggle_requested = Signal(bool)
    update_requested = Signal()
    quit_requested = Signal()

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self._hinted = False
        self.icon = QSystemTrayIcon(icon_provider.app_icon(), self)
        self.icon.setToolTip(f"{constants.APP_NAME} {constants.APP_VERSION}")

        menu = QMenu()
        menu.setObjectName("TrayMenu")
        self.act_show = QAction("显示主窗口", menu)
        self.act_scan = QAction("重新扫描", menu)
        self.act_patrol = QAction("立即巡检残余", menu)
        self.act_boot = QAction("开机自动巡检", menu)
        self.act_boot.setCheckable(True)
        self.act_boot.setToolTip("下次开机时在右下角弹出巡检小窗，随时可撤销")
        self.act_update = QAction("检查更新", menu)
        self.act_quit = QAction("退出", menu)
        menu.addAction(self.act_show)
        menu.addAction(self.act_scan)
        menu.addAction(self.act_patrol)
        menu.addAction(self.act_boot)
        menu.addSeparator()
        menu.addAction(self.act_update)
        menu.addSeparator()
        menu.addAction(self.act_quit)
        self.menu = menu
        self.icon.setContextMenu(menu)

        self.act_show.triggered.connect(self.show_requested.emit)
        self.act_scan.triggered.connect(self.scan_requested.emit)
        self.act_patrol.triggered.connect(self.patrol_requested.emit)
        self.act_boot.triggered.connect(
            lambda checked: self.boot_toggle_requested.emit(bool(checked)))
        self.act_update.triggered.connect(self.update_requested.emit)
        self.act_quit.triggered.connect(self.quit_requested.emit)
        self.icon.activated.connect(self._on_activated)

    # ------------------------------------------------------------------
    def available(self) -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable() and self.icon.isVisible()

    def start(self):
        self.icon.show()

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_requested.emit()

    def set_tooltip(self, text: str):
        self.icon.setToolTip(text)

    def set_boot_state(self, enabled: bool):
        """同步“开机自动巡检”勾选状态，避免界面与注册表不一致。"""
        self.act_boot.blockSignals(True)
        self.act_boot.setChecked(bool(enabled))
        self.act_boot.blockSignals(False)

    def notify(self, title: str, message: str, seconds: int = 4):
        try:
            self.icon.showMessage(title, message, icon_provider.app_icon(), seconds)
        except Exception:
            pass

    def notify_minimized(self):
        """第一次最小化时给一次说明，之后不再打扰。"""
        if self._hinted:
            return
        self._hinted = True
        self.notify("已最小化到托盘",
                     "程序仍在托盘运行，右键托盘图标可扫描、检查更新或退出。")
