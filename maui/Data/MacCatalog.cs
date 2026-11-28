namespace ResidualCleaner.Maui.Data;

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
