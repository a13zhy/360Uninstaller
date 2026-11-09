"""检查更新与自动安装：GitHub Releases API + 覆盖式自更新"""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

from PySide6.QtCore import QThread, Signal

from . import constants

REPO = "a13zhy/360Uninstaller"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASE_PAGE = f"https://github.com/{REPO}/releases"
USER_AGENT = f"{constants.APP_NAME_EN}/{constants.APP_VERSION}"
TIMEOUT = 12


def normalize_version(text: str) -> tuple:
    nums = re.findall(r"\d+", text or "")
    if not nums:
        return (0,)
    return tuple(int(n) for n in nums[:4])


def is_newer(remote: str, local: str = constants.APP_VERSION) -> bool:
    r = normalize_version(remote)
    l = normalize_version(local)
    width = max(len(r), len(l))
    return r + (0,) * (width - len(r)) > l + (0,) * (width - len(l))


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def fetch_latest(timeout: int = TIMEOUT) -> dict:
    req = urllib.request.Request(
        API_LATEST,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assets = []
    for a in payload.get("assets", []):
        assets.append({
            "name": a.get("name", ""),
            "url": a.get("browser_download_url", ""),
            "size": int(a.get("size", 0) or 0),
        })
    return {
        "tag": payload.get("tag_name", "") or "",
        "name": payload.get("name", "") or "",
        "body": payload.get("body", "") or "",
        "page": payload.get("html_url", "") or RELEASE_PAGE,
        "published_at": payload.get("published_at", "") or "",
        "assets": assets,
    }


def pick_exe_asset(release: dict) -> dict | None:
    for asset in release.get("assets", []):
        name = (asset.get("name") or "").lower()
        if name.endswith(".exe") and "verify" not in name:
            return asset
    return None


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def update_dir() -> str:
    path = os.path.join(constants.LOG_DIR, "update")
    os.makedirs(path, exist_ok=True)
    return path


def download(url: str, dest: str, progress=None) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)


def _ps_quote(path: str) -> str:
    return "'" + path.replace("'", "''") + "'"


def build_install_script(new_exe: str, target_exe: str, pid: int) -> str:
    return "\n".join([
        "$ErrorActionPreference = 'SilentlyContinue'",
        f"$target = {_ps_quote(target_exe)}",
        f"$new = {_ps_quote(new_exe)}",
        f"$procId = {pid}",
        "for ($i = 0; $i -lt 120; $i++) {",
        "    if (-not (Get-Process -Id $procId -ErrorAction SilentlyContinue)) { break }",
        "    Start-Sleep -Milliseconds 500",
        "}",
        "Start-Sleep -Milliseconds 1200",
        "# 文件可能还被残留句柄占着，最多重试 30 秒",
        "$copied = $false",
        "for ($j = 0; $j -lt 60; $j++) {",
        "    try {",
        "        Copy-Item -LiteralPath $new -Destination $target -Force -ErrorAction Stop",
        "        $copied = $true",
        "        break",
        "    } catch {",
        "        Start-Sleep -Milliseconds 500",
        "    }",
        "}",
        "if ($copied) {",
        "    Remove-Item -LiteralPath $new -Force",
        "    Start-Process -FilePath $target",
        "}",
        "Remove-Item -LiteralPath $PSCommandPath -Force",
        "",
    ])


def restart_and_install(new_exe: str) -> tuple:
    if not is_frozen():
        return False, "源码模式无法自动替换程序文件，请到 Releases 页面手动下载安装"
    target = os.path.abspath(sys.executable)
    script = build_install_script(os.path.abspath(new_exe), target, os.getpid())
    path = os.path.join(tempfile.gettempdir(), f"rc_update_{os.getpid()}.ps1")
    # 带 BOM 写入：Windows PowerShell 5.1 才能正确识别中文路径
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(script)
    flags = 0x08000000 | 0x00000200
    subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-WindowStyle", "Hidden", "-File", path],
        creationflags=flags,
        close_fds=True,
    )
    return True, ""


def open_release_page() -> None:
    try:
        os.startfile(RELEASE_PAGE)
    except Exception:
        pass


class CheckWorker(QThread):
    done = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            release = fetch_latest()
            self.done.emit({
                "release": release,
                "has_update": is_newer(release.get("tag", "")),
                "error": "",
            })
        except Exception as exc:
            self.done.emit({"release": None, "has_update": False,
                            "error": str(exc) or exc.__class__.__name__})


class DownloadWorker(QThread):
    progress = Signal(int, str)
    done = Signal(dict)

    def __init__(self, asset: dict, dest: str, parent=None):
        super().__init__(parent)
        self.asset = asset
        self.dest = dest

    def run(self):
        total = int(self.asset.get("size") or 0)

        def cb(done: int, length: int):
            denom = length or total
            pct = int(done * 100 / denom) if denom else 0
            self.progress.emit(min(99, pct), f"正在下载 {done / 1048576:.1f} MB")

        try:
            download(self.asset["url"], self.dest, cb)
            size = os.path.getsize(self.dest)
            if total and size != total:
                raise RuntimeError(f"下载文件大小不一致（{size} 字节，应为 {total} 字节）")
            with open(self.dest, "rb") as f:
                head = f.read(2)
            if head != b"MZ":
                raise RuntimeError("下载到的文件不是有效的 Windows 程序")
            self.progress.emit(100, "下载完成")
            self.done.emit({"ok": True, "path": self.dest,
                            "sha256": sha256_file(self.dest), "size": size, "error": ""})
        except Exception as exc:
            self.done.emit({"ok": False, "path": "", "sha256": "",
                            "size": 0, "error": str(exc) or exc.__class__.__name__})
