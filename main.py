"""残留清理卫士 启动入口"""

import os
import sys
import traceback

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app import constants, elevation
from app.ui import theme
from app.ui.main_window import MainWindow


def _write_crash(exc_text: str):
    try:
        os.makedirs(constants.LOG_DIR, exist_ok=True)
        path = os.path.join(constants.LOG_DIR, "crash.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write(exc_text + "\n")
    except Exception:
        pass


def main() -> int:
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName(constants.APP_NAME_EN)
    app.setApplicationDisplayName(constants.APP_NAME)
    app.setOrganizationName(constants.APP_NAME_EN)
    # 托盘常驻：关闭主窗口不等于退出程序，由托盘菜单控制真正退出
    app.setQuitOnLastWindowClosed(False)

    font = QFont("Microsoft YaHei UI")
    font.setPointSize(9)
    app.setFont(font)

    theme.apply(app)
    elevation.ensure_admin()

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
