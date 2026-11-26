namespace ResidualCleaner.Maui.Data;

/// <summary>
/// macOS 平台预留规则。当前工程仅编译 Windows 目标，本文件不参与清理执行，
/// 只作为将来在 Mac 上构建 .NET MAUI (MacCatalyst) 目标时的残留规则底稿。
/// 注意：以下 Bundle ID、应用包名与残留路径均需在真实 Mac 上探查核对，
/// 未经验证，不能直接用于删除。
/// </summary>
public static class MacCatalog
{
    public const string HomeAppSupport = "~/Library/Application Support";
    public const string HomeCaches = "~/Library/Caches";
    public const string HomePreferences = "~/Library/Preferences";
    public const string HomeLogs = "~/Library/Logs";
    public const string SystemLaunchAgents = "/Library/LaunchAgents";
    public const string SystemLaunchDaemons = "/Library/LaunchDaemons";
    public const string ApplicationsDir = "/Applications";

    public static readonly IReadOnlyList<MacAppRule> Rules = new List<MacAppRule>
    {
        new(
            "360 安全卫士 for Mac",
            new[] { "com.qihoo.360safe.mac", "com.qihoo.safe.mac" },
            "360Safe.app",
            new[] { "360Safe", "Qihoo360", "360sd" },
            new[] { "com.qihoo.360safe.plist", "com.qihoo.safe.plist" },
            new[] { "com.qihoo.360safe.agent.plist", "com.qihoo.360safe.daemon.plist" }
        ),
        new(
            "360 Total Security for Mac",
            new[] { "com.qihoo.totalsecurity.mac", "com.360.totalsecurity" },
            "360TotalSecurity.app",
            new[] { "360TotalSecurity", "Qihoo360", "360ts" },
            new[] { "com.qihoo.totalsecurity.plist" },
            new[] { "com.qihoo.totalsecurity.agent.plist" }
        ),
        new(
            "360 安全浏览器 for Mac",
            new[] { "com.qihoo.360se.mac", "com.360.browser" },
            "360Browser.app",
            new[] { "360Browser", "360se", "Qihoo360" },
            new[] { "com.qihoo.360se.plist" },
            Array.Empty<string>()
        ),
        new(
            "360 团队版 / 企业云终端",
            new[] { "com.qihoo.biz.terminal", "com.360.business.client" },
            "360BizClient.app",
            new[] { "360Biz", "Qihoo360Biz", "360cloud" },
            new[] { "com.qihoo.biz.plist" },
            new[] { "com.qihoo.biz.daemon.plist" }
        ),
    };

    public static readonly string[] UserPathKeywords = { "360", "qihoo", "qhsafe", "qihu" };

    public static readonly string[] SystemServiceLabels = { "360", "qihoo", "qhsafe" };
}

public sealed record MacAppRule(
    string DisplayName,
    string[] BundleIds,
    string AppBundleName,
    string[] DataFolderHints,
    string[] PreferencePlists,
    string[] LaunchServiceLabels);
