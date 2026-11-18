"""界面渲染预览：生成主界面 / 残余小窗 / 巡检小窗截图

用法: python preview.py [宽] [高] [输出文件名]
环境变量：
  PREVIEW_DIALOG=1   追加残余小窗截图
  PREVIEW_PATROL=1   追加巡检小窗（扫描态 + 结果态）
  PREVIEW_PAGE=1|2   截一条龙 / 关于页
  PREVIEW_EMPTY=1    截空状态
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
from app.ui.patrol_window import PatrolWindow  # noqa: E402
from app.ui.residual_dialog import ResidualDialog  # noqa: E402


def main():
    width = int(sys.argv[1]) if len(sys.argv) > 1 else 940
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 608
    out = sys.argv[3] if len(sys.argv) > 3 else "ui_preview.png"

    app = QApplication(sys.argv[:1])
    font = QFont("Microsoft YaHei UI")
    font.setPointSize(9)
    app.setFont(font)
    theme.apply(app)

    win = MainWindow()
    win.resize(width, height)
    win.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    win.show()

    page = os.environ.get("PREVIEW_PAGE")
    if page in ("1", "2"):
        QTimer.singleShot(200, lambda: win._switch_page(int(page)))

    def capture():
        pm = win.grab()
        pm.save(out)
        print(f"SAVED {os.path.abspath(out)} {pm.width()}x{pm.height()}")

        if os.environ.get("PREVIEW_DIALOG") == "1":
            dlg = ResidualDialog(win, deep=False, title="残余项目检查", auto_start=False)
            dlg.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
            dlg.show()
            dlg._populate_demo()

            def snap_dialog():
                dpm = dlg.grab()
                dpm.save("ui_preview_dialog.png")
                print(f"SAVED ui_preview_dialog.png {dpm.width()}x{dpm.height()}")
                dlg.close()
                finish()

            QTimer.singleShot(140, snap_dialog)
        elif os.environ.get("PREVIEW_PATROL") == "1":
            patrol = PatrolWindow(None, auto_start=False)
            patrol.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
            patrol.show()
            patrol.demo_scanning(46)

            def snap_scan():
                patrol.grab().save("ui_preview_patrol_scan.png")
                print("SAVED ui_preview_patrol_scan.png")
                patrol.demo_result()

                def snap_result():
                    patrol.grab().save("ui_preview_patrol.png")
                    print("SAVED ui_preview_patrol.png")
                    patrol.close()
                    finish()

                QTimer.singleShot(120, snap_result)

            QTimer.singleShot(120, snap_scan)
        else:
            finish()

    captured = {"done": False}

    def finish():
        if captured["done"]:
            return
        captured["done"] = True
        app.quit()

    QTimer.singleShot(320, capture)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
