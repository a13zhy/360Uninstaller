"""界面渲染预览：生成主界面截图（不触发真实扫描、不弹出可见窗口）

用法: python preview.py [宽] [高] [输出文件名]
"""

import os
import sys

os.environ.setdefault("360TOOL_NO_DISCLAIMER", "1")
os.environ.setdefault("360TOOL_NO_ELEVATE", "1")
os.environ.setdefault("360TOOL_PREVIEW", "1")

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.ui import theme  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402
from app.ui.residual_dialog import ResidualDialog  # noqa: E402


def main():
    width = int(sys.argv[1]) if len(sys.argv) > 1 else 1180
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 800
    out = sys.argv[3] if len(sys.argv) > 3 else "ui_preview.png"

    app = QApplication(sys.argv[:1])
    font = QFont("Microsoft YaHei UI")
    font.setPointSize(9)
    app.setFont(font)
    theme.apply(app)

    win = MainWindow()
    win.resize(width, height)
    # 关键：用真实 Windows 字体引擎渲染，但不显示在屏幕上
    win.setAttribute(Qt.WA_DontShowOnScreen, True)
    win.show()

    def capture():
        pm = win.grab()
        pm.save(out)
        print(f"SAVED {os.path.abspath(out)} {pm.width()}x{pm.height()}")

        if os.environ.get("PREVIEW_DIALOG") == "1":
            dlg = ResidualDialog(win, deep=False, title="卸载完成 · 残余项目检查")
            dlg.setAttribute(Qt.WA_DontShowOnScreen, True)
            dlg.resize(800, 580)
            dlg.show()
            dlg._populate_demo()

            def snap_dialog():
                dpm = dlg.grab()
                dpm.save("ui_preview_dialog.png")
                print(f"SAVED ui_preview_dialog.png {dpm.width()}x{dpm.height()}")
                dlg.close()
                app.quit()

            QTimer.singleShot(140, snap_dialog)
        else:
            app.quit()

    QTimer.singleShot(260, capture)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
