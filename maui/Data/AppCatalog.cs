using ResidualCleaner.Maui.Models;
using ResidualCleaner.Maui.Services;

namespace ResidualCleaner.Maui.Data;

public static class AppCatalog
{
    public static readonly Dictionary<string, string> KindLabels = new()
    {
        ["process"] = "进程",
        ["service"] = "服务",
        ["dir"] = "目录",
        ["file"] = "文件",
        ["registry"] = "注册表",
        ["task"] = "计划任务",
        ["shortcut"] = "快捷方式",
    };

    public static readonly List<string> KindOrder = new()
    {
        "process", "service", "task", "dir", "file", "registry", "shortcut",
    };

    public static readonly string[] SelfProtectKeywords =
    {
        "360selfprotection", "360antihacker", "360fsflt", "360rp", "360rps",
        "zhudongfangyu", "qhactivedefense", "qhsafemonitor", "360box",
    };

    public static readonly string[] UninstallKeys =
    {
        @"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        @"HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        @"HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall",
    };

    public static readonly string[] RunKeys =
    {
        @"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
        @"HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run",
        @"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
        @"HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce",
    };

    public static readonly string[] CommonRegRoots =
    {
        @"HKLM\SOFTWARE\WOW6432Node",
        @"HKLM\SOFTWARE",
        @"HKCU\Software",
    };

    public static readonly string[] RegKeywords =
    {
        "360safe", "360sd", "360se", "360chrome", "360zip", "360drvmgr",
        "360softmgr", "360yunpan", "360game", "360mobile", "360ys",
        "360wallpaper", "qhsafe", "zhudongfangyu", "奇虎", "360安全",
    };

    public static readonly string[] FileKeywords = { "360", "qhsafe", "qihu" };

    public static List<string> CommonDirs() => new()
    {
        Path.Combine(AppPaths.ProgramFilesX86, "360"),
        Path.Combine(AppPaths.ProgramFiles, "360"),
        Path.Combine(AppPaths.ProgramFilesX86, "360Safe"),
        Path.Combine(AppPaths.ProgramFiles, "360Safe"),
        Path.Combine(AppPaths.ProgramFilesX86, "360sd"),
        Path.Combine(AppPaths.ProgramFiles, "360sd"),
        Path.Combine(AppPaths.ProgramData, "360safe"),
        Path.Combine(AppPaths.ProgramData, "360"),
        Path.Combine(AppPaths.ProgramData, "360sd"),
        Path.Combine(AppPaths.AppData, "360safe"),
        Path.Combine(AppPaths.AppData, "360"),
        Path.Combine(AppPaths.LocalAppData, "360safe"),
        Path.Combine(AppPaths.LocalAppData, "360"),
        Path.Combine(AppPaths.LocalAppData, "360Chrome"),
        Path.Combine(AppPaths.LocalAppData, "360ChromeX"),
        Path.Combine(AppPaths.LocalAppData, "360YunPan"),
        Path.Combine(AppPaths.LocalAppData, "360Wallpaper"),
    };

    public static List<string> ScanExcludes() => new()
    {
        Path.Combine(AppPaths.WindowsDir, "System32"),
        Path.Combine(AppPaths.WindowsDir, "SysWOW64"),
        Path.Combine(AppPaths.WindowsDir, "WinSxS"),
        Path.Combine(AppPaths.WindowsDir, "SystemApps"),
        Path.Combine(AppPaths.ProgramFiles, "WindowsApps"),
        Path.Combine(AppPaths.ProgramFiles, "Windows Defender"),
        Path.Combine(AppPaths.ProgramData, "Microsoft"),
    };

    public static List<string> ScanRoots() => new()
    {
        Path.Combine(AppPaths.ProgramFilesX86, "360"),
        Path.Combine(AppPaths.ProgramFiles, "360"),
        Path.Combine(AppPaths.ProgramData, "360safe"),
        Path.Combine(AppPaths.ProgramData, "360"),
        Path.Combine(AppPaths.AppData, "360safe"),
        Path.Combine(AppPaths.AppData, "360"),
        Path.Combine(AppPaths.LocalAppData, "360safe"),
        Path.Combine(AppPaths.LocalAppData, "360"),
        AppPaths.Desktop,
        Path.Combine(AppPaths.UserProfile, "Downloads"),
        Path.Combine(AppPaths.UserProfile, "Documents"),
    };

    public static List<string> StartMenuDirs() => new()
    {
        Path.Combine(AppPaths.ProgramData, "Microsoft", "Windows", "Start Menu", "Programs"),
        Path.Combine(AppPaths.AppData, "Microsoft", "Windows", "Start Menu", "Programs"),
    };

    public static List<AppDefinition> Apps() => new()
    {
        new()
        {
            Key = "360safe", Name = "360 安全卫士", Desc = "主程序、托盘、主动防御与体检组件",
            Processes = { "360tray.exe", "360safe.exe", "360rp.exe", "360rps.exe", "zhudongfangyu.exe", "qhsafetray.exe", "qhsafe.exe", "360sd.exe" },
            Services = { "360rp", "360rps", "360safe", "zhudongfangyu", "qhsafe", "360selfprotection", "360antihacker", "360fsflt", "qhactivedefense", "qhsafemonitor" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360", "360Safe"), Path.Combine(AppPaths.ProgramFiles, "360", "360Safe"), Path.Combine(AppPaths.ProgramData, "360safe"), Path.Combine(AppPaths.AppData, "360safe"), Path.Combine(AppPaths.LocalAppData, "360safe") },
            Regs = { @"HKLM\SOFTWARE\WOW6432Node\360Safe", @"HKLM\SOFTWARE\360Safe", @"HKCU\Software\360Safe" },
            Tasks = { "360安全卫士", "360 safe" },
            Shortcuts = { "360安全卫士", "360安全卫士极速版" },
            Keywords = { "360安全卫士", "360safe" },
        },
        new()
        {
            Key = "360sd", Name = "360 杀毒", Desc = "杀毒引擎、实时防护与隔离区",
            Processes = { "360sd.exe", "360rps.exe", "qhactivedefense.exe", "360deepscan.exe" },
            Services = { "360sd", "qhactivedefense" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360", "360sd"), Path.Combine(AppPaths.ProgramFiles, "360", "360sd"), Path.Combine(AppPaths.ProgramData, "360sd") },
            Regs = { @"HKLM\SOFTWARE\WOW6432Node\360sd", @"HKLM\SOFTWARE\360sd" },
            Tasks = { "360杀毒" },
            Shortcuts = { "360杀毒" },
            Keywords = { "360杀毒", "360sd" },
        },
        new()
        {
            Key = "360se", Name = "360 安全浏览器", Desc = "安全浏览器主程序与用户数据",
            Processes = { "360se.exe", "360se6.exe", "360se6tray.exe" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360", "360se6"), Path.Combine(AppPaths.ProgramFilesX86, "360se6"), Path.Combine(AppPaths.LocalAppData, "360Chrome"), Path.Combine(AppPaths.AppData, "360se6") },
            Regs = { @"HKCU\Software\360se6", @"HKLM\SOFTWARE\WOW6432Node\360se6" },
            Tasks = { "360安全浏览器" },
            Shortcuts = { "360安全浏览器" },
            Keywords = { "360安全浏览器", "360se" },
        },
        new()
        {
            Key = "360chromex", Name = "360 极速浏览器", Desc = "极速浏览器内核与缓存目录",
            Processes = { "360chrome.exe", "360chromex.exe" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360Chrome"), Path.Combine(AppPaths.ProgramFilesX86, "360ChromeX"), Path.Combine(AppPaths.LocalAppData, "360ChromeX") },
            Regs = { @"HKCU\Software\360ChromeX", @"HKCU\Software\360Chrome" },
            Tasks = { "360极速浏览器" },
            Shortcuts = { "360极速浏览器" },
            Keywords = { "360极速浏览器", "360chrome" },
        },
        new()
        {
            Key = "360zip", Name = "360 压缩", Desc = "压缩软件本体与右键菜单扩展",
            Processes = { "360zip.exe", "360zipupdate.exe" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360", "360zip"), Path.Combine(AppPaths.ProgramFiles, "360", "360zip") },
            Regs = { @"HKLM\SOFTWARE\WOW6432Node\360zip", @"HKCU\Software\360zip" },
            Shortcuts = { "360压缩" },
            Keywords = { "360压缩", "360zip" },
        },
        new()
        {
            Key = "360drvmgr", Name = "360 驱动大师", Desc = "驱动检测、下载与安装服务",
            Processes = { "360drvmgr.exe", "360drvmgrassist.exe", "drvmgr.exe" },
            Services = { "360drvmgr" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360", "360DrvMgr"), Path.Combine(AppPaths.ProgramFiles, "360", "360DrvMgr") },
            Regs = { @"HKLM\SOFTWARE\WOW6432Node\360DrvMgr" },
            Tasks = { "360驱动大师" },
            Shortcuts = { "360驱动大师" },
            Keywords = { "360驱动大师", "360drvmgr" },
        },
        new()
        {
            Key = "360softmgr", Name = "360 软件管家", Desc = "软件分发与升级服务组件",
            Processes = { "360softmgr.exe", "softmgrlite.exe", "softmgrhelper.exe" },
            Services = { "360softmgr" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360", "360SoftMgr"), Path.Combine(AppPaths.ProgramFilesX86, "360", "SoftMgr") },
            Regs = { @"HKLM\SOFTWARE\WOW6432Node\360SoftMgr" },
            Tasks = { "360软件管家" },
            Shortcuts = { "360软件管家" },
            Keywords = { "360软件管家", "360softmgr" },
        },
        new()
        {
            Key = "360yunpan", Name = "360 安全云盘", Desc = "同步客户端与本地缓存",
            Processes = { "360yunpan.exe", "360yunpantray.exe" },
            Dirs = { Path.Combine(AppPaths.LocalAppData, "360YunPan"), Path.Combine(AppPaths.ProgramFilesX86, "360", "360YunPan") },
            Regs = { @"HKCU\Software\360YunPan" },
            Tasks = { "360安全云盘" },
            Shortcuts = { "360安全云盘" },
            Keywords = { "360安全云盘", "360yunpan" },
        },
        new()
        {
            Key = "360game", Name = "360 游戏大厅", Desc = "游戏盒子与下载组件",
            Processes = { "360game.exe", "360gamebox.exe" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360", "360Game"), Path.Combine(AppPaths.ProgramFilesX86, "360", "360GameBox") },
            Regs = { @"HKLM\SOFTWARE\WOW6432Node\360Game" },
            Shortcuts = { "360游戏大厅", "360游戏盒子" },
            Keywords = { "360游戏大厅", "360game" },
        },
        new()
        {
            Key = "360mobile", Name = "360 手机助手", Desc = "手机连接、APK 管理与驱动组件",
            Processes = { "360mobilemgr.exe", "360apk.exe", "360mobileassist.exe" },
            Services = { "360mobilemgr" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360", "360MobileMgr") },
            Regs = { @"HKLM\SOFTWARE\WOW6432Node\360MobileMgr" },
            Shortcuts = { "360手机助手" },
            Keywords = { "360手机助手", "360mobile" },
        },
        new()
        {
            Key = "360ys", Name = "360 影视大全", Desc = "影音客户端与缓存",
            Processes = { "360ys.exe" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360", "360YS"), Path.Combine(AppPaths.LocalAppData, "360YS") },
            Regs = { @"HKCU\Software\360YS" },
            Shortcuts = { "360影视大全" },
            Keywords = { "360影视大全", "360ys" },
        },
        new()
        {
            Key = "360wallpaper", Name = "360 壁纸", Desc = "壁纸客户端与图库缓存",
            Processes = { "360wallpaper.exe" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360", "360Wallpaper"), Path.Combine(AppPaths.LocalAppData, "360Wallpaper") },
            Regs = { @"HKCU\Software\360Wallpaper" },
            Shortcuts = { "360壁纸" },
            Keywords = { "360壁纸", "360wallpaper" },
        },
        new()
        {
            Key = "360safelite", Name = "360 安全卫士极速版", Desc = "卫士极速版主程序与托盘",
            Processes = { "360safelite.exe", "360tray.exe" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360", "360SafeLite"), Path.Combine(AppPaths.LocalAppData, "360SafeLite") },
            Regs = { @"HKLM\SOFTWARE\WOW6432Node\360SafeLite", @"HKCU\Software\360SafeLite" },
            Shortcuts = { "360安全卫士极速版" },
            Keywords = { "极速版", "360safelite" },
        },
        new()
        {
            Key = "360aibrowser", Name = "360 AI 浏览器", Desc = "AI 浏览器主程序与用户数据",
            Processes = { "360ai.exe", "360aibrowser.exe" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360", "360AiBrowser"), Path.Combine(AppPaths.LocalAppData, "360AiBrowser") },
            Regs = { @"HKCU\Software\360AiBrowser" },
            Shortcuts = { "360 AI 浏览器" },
            Keywords = { "AI 浏览器", "360ai" },
        },
        new()
        {
            Key = "360kuaijie", Name = "360 快剪辑", Desc = "视频剪辑客户端与工程缓存",
            Processes = { "360kuaijie.exe", "kuaijie.exe" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360", "360KuaiJie"), Path.Combine(AppPaths.LocalAppData, "360KuaiJie") },
            Regs = { @"HKCU\Software\360KuaiJie" },
            Shortcuts = { "快剪辑" },
            Keywords = { "快剪辑", "360kuaijie" },
        },
        new()
        {
            Key = "360deskmgr", Name = "360 桌面整理", Desc = "桌面分类整理与悬浮组件",
            Processes = { "360deskmanager.exe", "360desktop.exe" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360", "360DeskMgr") },
            Regs = { @"HKLM\SOFTWARE\WOW6432Node\360DeskMgr" },
            Shortcuts = { "360桌面整理" },
            Keywords = { "桌面整理", "360desk" },
        },
        new()
        {
            Key = "360chromelite", Name = "360 浏览器极速版", Desc = "浏览器极速版内核与缓存",
            Processes = { "360chromelite.exe", "360chrome.exe" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360ChromeLite"), Path.Combine(AppPaths.LocalAppData, "360ChromeLite") },
            Regs = { @"HKCU\Software\360ChromeLite" },
            Shortcuts = { "浏览器极速版" },
            Keywords = { "浏览器极速版", "360chromelite" },
        },
        new()
        {
            Key = "360wifi", Name = "360 随身 WiFi", Desc = "随身 WiFi 驱动与管理服务",
            Processes = { "360wifimgr.exe", "360wifi.exe" },
            Services = { "360wifi" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360", "360WiFi") },
            Regs = { @"HKLM\SOFTWARE\WOW6432Node\360WiFi" },
            Shortcuts = { "随身 WiFi" },
            Keywords = { "随身 WiFi", "360wifi" },
        },
        new()
        {
            Key = "360qiangpiao", Name = "360 抢票王", Desc = "抢票插件与本地配置",
            Processes = { "360qiangpiao.exe" },
            Dirs = { Path.Combine(AppPaths.LocalAppData, "360QiangPiao") },
            Regs = { @"HKCU\Software\360QiangPiao" },
            Shortcuts = { "抢票王" },
            Keywords = { "抢票王", "360qiangpiao" },
        },
        new()
        {
            Key = "360child", Name = "360 儿童卫士", Desc = "家长管控与儿童防护组件",
            Processes = { "360kidsafe.exe", "360child.exe" },
            Services = { "360child" },
            Dirs = { Path.Combine(AppPaths.ProgramFilesX86, "360", "360Child") },
            Regs = { @"HKLM\SOFTWARE\WOW6432Node\360Child" },
            Shortcuts = { "儿童卫士" },
            Keywords = { "儿童卫士", "360child" },
        },
        new()
        {
            Key = "360aioffice", Name = "360 AI 办公", Desc = "AI 办公客户端与本地缓存",
            Processes = { "360aioffice.exe" },
            Dirs = { Path.Combine(AppPaths.LocalAppData, "360AIOffice") },
            Regs = { @"HKCU\Software\360AIOffice" },
            Shortcuts = { "360 AI 办公" },
            Keywords = { "AI 办公", "360aioffice" },
        },
        new()
        {
            Key = "birdwallpaper", Name = "小鸟壁纸", Desc = "小鸟壁纸客户端与图库缓存",
            Processes = { "niaowallpaper.exe", "birdwallpaper.exe" },
            Dirs = { Path.Combine(AppPaths.LocalAppData, "BirdWallpaper"), Path.Combine(AppPaths.ProgramFilesX86, "BirdWallpaper") },
            Regs = { @"HKCU\Software\BirdWallpaper" },
            Shortcuts = { "小鸟壁纸" },
            Keywords = { "小鸟壁纸", "birdwallpaper" },
        },
    };
}
