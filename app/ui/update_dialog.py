"""检查更新对话框：版本对比 → 下载 → 重启安装"""

import os
import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QMessageBox,
                               QProgressBar, QPushButton, QTextBrowser,
                               QVBoxLayout)

from .. import constants, icon_provider, updater
from . import theme


def _plain_notes(markdown: str) -> str:
    """把 Release 正文压成可读纯文本，避免对话框里出现一堆 ###。"""
    text = markdown or ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"[*_]{2,}", "", text)
    lines = [ln.rstrip() for ln in text.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


class UpdateDialog(QDialog):
    install_requested = Signal()

    def __init__(self, release: dict, parent=None):
        super().__init__(parent)
        self.release = release
        self.worker: updater.DownloadWorker | None = None
        self.asset = updater.pick_exe_asset(release)
        self.downloaded = ""
        self.setObjectName("UpdateDialog")
        self.setWindowTitle("检查更新")
        self.setWindowIcon(icon_provider.app_icon())
        self.setMinimumWidth(560)
        self.setModal(True)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(12)
        icon = QLabel()
        icon.setPixmap(icon_provider.app_pixmap(44))
        icon.setFixedSize(44, 44)
        head.addWidget(icon)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        tag = self.release.get("tag", "")
        self.title = QLabel(f"发现新版本 {tag}")
        self.title.setObjectName("DialogTitle")
        sub = QLabel(f"当前版本 v{constants.APP_VERSION} · 可直接在程序内下载并安装")
        sub.setObjectName("DialogSub")
        titles.addWidget(self.title)
        titles.addWidget(sub)
        head.addLayout(titles, 1)
        root.addLayout(head)

        notes = _plain_notes(self.release.get("body", ""))[:1200]
        self.notes = QTextBrowser()
        self.notes.setObjectName("UpdateNotes")
        self.notes.setPlainText(notes or "本次更新没有提供详细说明，可直接下载安装。")
        self.notes.setMinimumHeight(180)
        self.notes.setMaximumHeight(240)
        root.addWidget(self.notes)

        self.link = QLabel(
            f'<a style="color:{theme.COLORS["accent"]}; text-decoration:none;" '
            f'href="{self.release.get("page", updater.RELEASE_PAGE)}">在浏览器中查看发布页</a>'
        )
        self.link.setOpenExternalLinks(True)
        root.addWidget(self.link)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFixedHeight(8)
        self.bar.setTextVisible(False)
        self.bar.setVisible(False)
        root.addWidget(self.bar)

        self.status = QLabel("")
        self.status.setObjectName("DialogSub")
        self.status.setVisible(False)
        root.addWidget(self.status)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        self.btn_later = QPushButton("稍后提醒")
        self.btn_later.setObjectName("Ghost")
        self.btn_later.clicked.connect(self.reject)
        self.btn_action = QPushButton("下载并安装")
        self.btn_action.setObjectName("Primary")
        self.btn_action.setMinimumHeight(36)
        self.btn_action.clicked.connect(self._start)
        btns.addStretch(1)
        btns.addWidget(self.btn_later)
        btns.addWidget(self.btn_action)
        root.addLayout(btns)

        if not updater.is_frozen():
            self.btn_action.setText("打开下载页")
        elif not self.asset:
            self.btn_action.setText("打开下载页")

    # ------------------------------------------------------------------
    def _start(self):
        if not updater.is_frozen() or not self.asset:
            updater.open_release_page()
            return
        if self.worker and self.worker.isRunning():
            return

        self.btn_action.setEnabled(False)
        self.btn_later.setEnabled(False)
        self.bar.setVisible(True)
        self.status.setVisible(True)
        self.status.setText("准备下载…")

        dest = os.path.join(updater.update_dir(),
                            self.asset["name"] or "ResidualCleaner-update.exe")
        self.worker = updater.DownloadWorker(self.asset, dest, parent=self)
        self.worker.progress.connect(self._on_progress)
        self.worker.done.connect(self._on_done)
        self.worker.start()

    def _on_progress(self, pct: int, text: str):
        self.bar.setValue(pct)
        self.status.setText(text)

    def _on_done(self, data: dict):
        self.btn_action.setEnabled(True)
        self.btn_later.setEnabled(True)
        if not data.get("ok"):
            self.bar.setVisible(False)
            self.status.setVisible(True)
            self.status.setText("下载失败：" + (data.get("error") or "未知错误"))
            self.btn_action.setText("重试下载")
            return

        self.downloaded = data.get("path", "")
        self.bar.setValue(100)
        self.status.setText(
            f"下载完成 · {data.get('size', 0) / 1048576:.1f} MB · "
            f"SHA-256 {data.get('sha256', '')[:16]}…"
        )
        ret = QMessageBox.question(
            self, "安装新版本",
            "新版本已经下载完成并校验通过。\n\n"
            "点击“立即安装”后，程序会自动关闭，替换文件并重新启动，"
            "整个过程约 5–10 秒。是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if ret != QMessageBox.Yes:
            self.status.setText("已下载，可稍后手动安装")
            return

        ok, err = updater.restart_and_install(self.downloaded)
        if not ok:
            QMessageBox.warning(self, "无法自动安装", err)
            return
        QMessageBox.information(
            self, "即将重启安装",
            "程序现在会关闭，等待文件替换完成后自动重新打开。\n"
            "如果没有自动启动，请手动双击程序图标。",
        )
        # 交给主窗口统一收尾：先停掉后台线程，再退出，避免 QThread 未结束就销毁
        self.install_requested.emit()
        self.accept()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            ret = QMessageBox.question(
                self, "正在下载更新",
                "更新还在下载，现在关闭会中止下载。确定关闭吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                event.ignore()
                return
            self.worker.requestInterruption()
            self.worker.wait(2000)
        super().closeEvent(event)
