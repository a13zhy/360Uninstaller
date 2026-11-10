"""全局常量与应用定义（残留清理卫士 3.0）"""

import os

APP_NAME = "残留清理卫士"
APP_NAME_EN = "ResidualCleaner"
APP_VERSION = "1.2.6.261110"
APP_TAGLINE = "Windows 深度卸载与残留清理"

LOG_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "ResidualCleaner"
)
LOG_FILE = os.path.join(LOG_DIR, "cleaner.log")

ENV_NO_ELEVATE = "360TOOL_NO_ELEVATE"
ENV_NO_DISCLAIMER = "360TOOL_NO_DISCLAIMER"
ENV_THEME = "360TOOL_THEME"
ENV_ACCENT = "360TOOL_ACCENT"
ENV_PREVIEW = "360TOOL_PREVIEW"


def env_flag(name: str) -> bool:
    return os.environ.get(name, "") == "1"


def env_str(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def expand(path: str) -> str:
    """展开 %ProgramFiles% 等环境变量，返回真实路径。"""
    return os.path.expandvars(path)


def is_wow64() -> bool:
    try:
        return bool(os.environ.get("PROCESSOR_ARCHITEW6432"))
    except Exception:
        return False


PF = os.environ.get("ProgramFiles", r"C:\Program Files")
PF86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
PROGRAMDATA = os.environ.get("ProgramData", r"C:\ProgramData")
APPDATA = os.environ.get("APPDATA", "")
LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")
USERPROFILE = os.environ.get("USERPROFILE", "")
WINDIR = os.environ.get("SystemRoot", r"C:\Windows")
DESKTOP = os.path.join(USERPROFILE, "Desktop") if USERPROFILE else ""

# ---------------------------------------------------------------- 360 应用定义
# 每项字段：
#   key       唯一标识
#   name      展示名称
#   desc      一句话描述
#   processes 进程名（小写）
#   services  服务名关键词（小写）
#   dirs      可能存在的安装目录（绝对路径模板）
#   regs      可能存在的注册表键
#   tasks     计划任务名称关键词
#   shortcuts 快捷方式关键词
#   assist    是否为辅助/伴随组件（UI 显示"组件"）

def _p(*parts) -> str:
    return os.path.join(*parts)


APPS = [
    {
        "key": "360safe",
        "name": "360 安全卫士",
        "desc": "主程序、托盘、主动防御与体检组件",
        "processes": ["360tray.exe", "360safe.exe", "360rp.exe", "360rps.exe",
                      "zhudongfangyu.exe", "qhsafetray.exe", "qhsafe.exe", "360sd.exe"],
        "services": ["360rp", "360rps", "360safe", "zhudongfangyu", "qhsafe",
                     "360selfprotection", "360antihacker", "360fsflt",
                     "qhactivedefense", "qhsafemonitor"],
        "dirs": [_p(PF86, "360", "360Safe"), _p(PF, "360", "360Safe"),
                 _p(PROGRAMDATA, "360safe"), _p(APPDATA, "360safe"),
                 _p(LOCALAPPDATA, "360safe")],
        "regs": [r"HKLM\SOFTWARE\WOW6432Node\360Safe", r"HKLM\SOFTWARE\360Safe",
                 r"HKCU\Software\360Safe"],
        "tasks": ["360安全卫士", "360 safe"],
        "shortcuts": ["360安全卫士", "360安全卫士极速版"],
    },
    {
        "key": "360sd",
        "name": "360 杀毒",
        "desc": "杀毒引擎、实时防护与隔离区",
        "processes": ["360sd.exe", "360rps.exe", "qhactivedefense.exe", "360deepscan.exe"],
        "services": ["360sd", "qhactivedefense"],
        "dirs": [_p(PF86, "360", "360sd"), _p(PF, "360", "360sd"),
                 _p(PROGRAMDATA, "360sd")],
        "regs": [r"HKLM\SOFTWARE\WOW6432Node\360sd", r"HKLM\SOFTWARE\360sd"],
        "tasks": ["360杀毒"],
        "shortcuts": ["360杀毒"],
    },
    {
        "key": "360se",
        "name": "360 安全浏览器",
        "desc": "安全浏览器主程序与用户数据",
        "processes": ["360se.exe", "360se6.exe", "360se6tray.exe"],
        "services": [],
        "dirs": [_p(PF86, "360", "360se6"), _p(PF86, "360se6"),
                 _p(LOCALAPPDATA, "360Chrome"), _p(APPDATA, "360se6")],
        "regs": [r"HKCU\Software\360se6", r"HKLM\SOFTWARE\WOW6432Node\360se6"],
        "tasks": ["360安全浏览器"],
        "shortcuts": ["360安全浏览器"],
    },
    {
        "key": "360chromex",
        "name": "360 极速浏览器",
        "desc": "极速浏览器内核与缓存目录",
        "processes": ["360chrome.exe", "360chromex.exe"],
        "services": [],
        "dirs": [_p(PF86, "360Chrome"), _p(PF86, "360ChromeX"),
                 _p(LOCALAPPDATA, "360ChromeX")],
        "regs": [r"HKCU\Software\360ChromeX", r"HKCU\Software\360Chrome"],
        "tasks": ["360极速浏览器"],
        "shortcuts": ["360极速浏览器"],
    },
    {
        "key": "360zip",
        "name": "360 压缩",
        "desc": "压缩软件本体与右键菜单扩展",
        "processes": ["360zip.exe", "360zipupdate.exe"],
        "services": [],
        "dirs": [_p(PF86, "360", "360zip"), _p(PF, "360", "360zip")],
        "regs": [r"HKLM\SOFTWARE\WOW6432Node\360zip", r"HKCU\Software\360zip"],
        "tasks": [],
        "shortcuts": ["360压缩"],
    },
    {
        "key": "360drvmgr",
        "name": "360 驱动大师",
        "desc": "驱动检测、下载与安装服务",
        "processes": ["360drvmgr.exe", "360drvmgrassist.exe", "drvmgr.exe"],
        "services": ["360drvmgr"],
        "dirs": [_p(PF86, "360", "360DrvMgr"), _p(PF, "360", "360DrvMgr")],
        "regs": [r"HKLM\SOFTWARE\WOW6432Node\360DrvMgr"],
        "tasks": ["360驱动大师"],
        "shortcuts": ["360驱动大师"],
    },
    {
        "key": "360softmgr",
        "name": "360 软件管家",
        "desc": "软件分发与升级服务组件",
        "processes": ["360softmgr.exe", "softmgrlite.exe", "softmgrhelper.exe"],
        "services": ["360softmgr"],
        "dirs": [_p(PF86, "360", "360SoftMgr"), _p(PF86, "360", "SoftMgr")],
        "regs": [r"HKLM\SOFTWARE\WOW6432Node\360SoftMgr"],
        "tasks": ["360软件管家"],
        "shortcuts": ["360软件管家"],
    },
    {
        "key": "360yunpan",
        "name": "360 安全云盘",
        "desc": "同步客户端与本地缓存",
        "processes": ["360yunpan.exe", "360yunpantray.exe"],
        "services": [],
        "dirs": [_p(LOCALAPPDATA, "360YunPan"), _p(PF86, "360", "360YunPan")],
        "regs": [r"HKCU\Software\360YunPan"],
        "tasks": ["360安全云盘"],
        "shortcuts": ["360安全云盘"],
    },
    {
        "key": "360game",
        "name": "360 游戏大厅",
        "desc": "游戏盒子与下载组件",
        "processes": ["360game.exe", "360gamebox.exe"],
        "services": [],
        "dirs": [_p(PF86, "360", "360Game"), _p(PF86, "360", "360GameBox")],
        "regs": [r"HKLM\SOFTWARE\WOW6432Node\360Game"],
        "tasks": [],
        "shortcuts": ["360游戏大厅", "360游戏盒子"],
    },
    {
        "key": "360mobile",
        "name": "360 手机助手",
        "desc": "手机连接、APK 管理与驱动组件",
        "processes": ["360mobilemgr.exe", "360apk.exe", "360mobileassist.exe"],
        "services": ["360mobilemgr"],
        "dirs": [_p(PF86, "360", "360MobileMgr")],
        "regs": [r"HKLM\SOFTWARE\WOW6432Node\360MobileMgr"],
        "tasks": [],
        "shortcuts": ["360手机助手"],
    },
    {
        "key": "360ys",
        "name": "360 影视大全",
        "desc": "影音客户端与缓存",
        "processes": ["360ys.exe"],
        "services": [],
        "dirs": [_p(PF86, "360", "360YS"), _p(LOCALAPPDATA, "360YS")],
        "regs": [r"HKCU\Software\360YS"],
        "tasks": [],
        "shortcuts": ["360影视大全"],
    },
    {
        "key": "360wallpaper",
        "name": "360 壁纸",
        "desc": "壁纸客户端与图库缓存",
        "processes": ["360wallpaper.exe"],
        "services": [],
        "dirs": [_p(PF86, "360", "360Wallpaper"), _p(LOCALAPPDATA, "360Wallpaper")],
        "regs": [r"HKCU\Software\360Wallpaper"],
        "tasks": [],
        "shortcuts": ["360壁纸"],
    },
]

# 360 自我保护相关驱动 / 服务关键词（强力删除前先尝试停止，避免文件被守护）
SELF_PROTECT_KEYWORDS = [
    "360selfprotection", "360antihacker", "360fsflt", "360rp", "360rps",
    "zhudongfangyu", "qhactivedefense", "qhsafemonitor", "360box",
]

# 360 全家桶公共目录（一键清除时优先检查）
COMMON_DIRS = [
    _p(PF86, "360"),
    _p(PF, "360"),
    _p(PF86, "360Safe"),
    _p(PF, "360Safe"),
    _p(PF86, "360sd"),
    _p(PF, "360sd"),
    _p(PROGRAMDATA, "360safe"),
    _p(PROGRAMDATA, "360"),
    _p(PROGRAMDATA, "360sd"),
    _p(APPDATA, "360safe"),
    _p(APPDATA, "360"),
    _p(LOCALAPPDATA, "360safe"),
    _p(LOCALAPPDATA, "360"),
    _p(LOCALAPPDATA, "360Chrome"),
    _p(LOCALAPPDATA, "360ChromeX"),
    _p(LOCALAPPDATA, "360YunPan"),
    _p(LOCALAPPDATA, "360Wallpaper"),
]

# 公共注册表根（扫描时按前缀匹配）
COMMON_REG_ROOTS = [
    r"HKLM\SOFTWARE\WOW6432Node",
    r"HKLM\SOFTWARE",
    r"HKCU\Software",
]

REG_KEYWORDS = ["360safe", "360sd", "360se", "360chrome", "360zip", "360drvmgr",
                "360softmgr", "360yunpan", "360game", "360mobile", "360ys",
                "360wallpaper", "qhsafe", "zhudongfangyu", "奇虎", "360安全"]

UNINSTALL_KEYS = [
    r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    r"HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    r"HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall",
]

RUN_KEYS = [
    r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    r"HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run",
    r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
    r"HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce",
]

TASKS_DIR = _p(WINDIR, "System32", "Tasks")
QUICK_LAUNCH = _p(APPDATA, "Microsoft", "Internet Explorer", "Quick Launch", "User Pinned", "TaskBar")
START_MENU_DIRS = [
    _p(PROGRAMDATA, "Microsoft", "Windows", "Start Menu", "Programs"),
    _p(APPDATA, "Microsoft", "Windows", "Start Menu", "Programs"),
]

# 全盘扫描排除目录（系统关键，绝不进入）
SCAN_EXCLUDES = [
    _p(WINDIR, "System32"),
    _p(WINDIR, "SysWOW64"),
    _p(WINDIR, "WinSxS"),
    _p(WINDIR, "SystemApps"),
    _p(PF, "WindowsApps"),
    _p(PF, "Windows Defender"),
    _p(PROGRAMDATA, "Microsoft"),
]

# 全盘扫描可覆盖的根目录（受控范围，避免无差别遍历整盘）
SCAN_ROOTS = [
    _p(PF86, "360"), _p(PF, "360"),
    _p(PROGRAMDATA, "360safe"), _p(PROGRAMDATA, "360"),
    _p(APPDATA, "360safe"), _p(APPDATA, "360"),
    _p(LOCALAPPDATA, "360safe"), _p(LOCALAPPDATA, "360"),
    DESKTOP,
    _p(USERPROFILE, "Downloads"),
    _p(USERPROFILE, "Documents"),
]

FILE_KEYWORDS = ["360", "qhsafe", "qihu"]

# 卸载后需要复扫的注册表分支
RESIDUAL_REG_PATHS = [
    r"HKLM\SOFTWARE\WOW6432Node\360Safe",
    r"HKLM\SOFTWARE\360Safe",
    r"HKLM\SOFTWARE\WOW6432Node\360sd",
    r"HKCU\Software\360Safe",
    r"HKLM\SOFTWARE\WOW6432Node\360zip",
    r"HKLM\SOFTWARE\WOW6432Node\360DrvMgr",
    r"HKLM\SOFTWARE\WOW6432Node\360SoftMgr",
]

KIND_LABELS = {
    "process": "进程",
    "service": "服务",
    "dir": "目录",
    "file": "文件",
    "registry": "注册表",
    "task": "计划任务",
    "shortcut": "快捷方式",
}

KIND_ORDER = ["process", "service", "task", "dir", "file", "registry", "shortcut"]
