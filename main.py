"""残留清理卫士 启动入口"""

import argparse
import os
import sys
import traceback

from PySide6.QtCore import QLockFile, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from app import bootguard, constants, elevation, icon_provider
from app.ui import theme
from app.ui.main_window import MainWindow
from app.ui.patrol_window import PatrolWindow

_LOCK: QLockFile | None = None


def _write_crash(exc_text: str):
    try:
        os.makedirs(constants.LOG_DIR, exist_ok=True)
        path = os.path.join(constants.LOG_DIR, "crash.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write(exc_text + "\n")
    except Exception:
        pass


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(constants.BOOT_PATROL_ARG, action="store_true",
                        dest="boot_scan",
                        help="开机巡检模式：直接弹出右下角小窗并扫描")
    return parser.parse_known_args(argv[1:])[0]


def _acquire_lock() -> bool:
    """同一时刻只允许一个实例，避免开机巡检和主程序各扫一遍。"""
    global _LOCK
    try:
        os.makedirs(constants.LOG_DIR, exist_ok=True)
    except Exception:
        return True
    _LOCK = QLockFile(os.path.join(constants.LOG_DIR, "instance.lock"))
    _LOCK.setStaleLockTime(15000)
    return bool(_LOCK.tryLock(50))


def main() -> int:
    args = _parse_args(sys.argv)

    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    app = QApplication(sys.argv[:1])
    app.setApplicationName(constants.APP_NAME_EN)
    app.setApplicationDisplayName(constants.APP_NAME)
    app.setOrganizationName(constants.APP_NAME_EN)
    # 托盘常驻：关闭主窗口不等于退出程序，由托盘菜单控制真正退出
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(icon_provider.app_icon())

    font = QFont("Microsoft YaHei UI")
    font.setPointSize(9)
    app.setFont(font)

    theme.apply(app)

    # 用户已经把巡检开关关掉时，开机那条命令即使还在也不打扰
    if args.boot_scan and not bootguard.is_enabled():
        return 0

    if not _acquire_lock():
        if not args.boot_scan:
            QMessageBox.information(None, "已在运行",
                                    f"{constants.APP_NAME} 已经在运行，请从托盘或任务栏切换。")
        return 0

    elevation.ensure_admin()

    if args.boot_scan:
        patrol = PatrolWindow(auto_start=True)
        patrol.show_at_corner()
        app.setQuitOnLastWindowClosed(True)
        return app.exec()

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        _write_crash(traceback.format_exc())
        raise
