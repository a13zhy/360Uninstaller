namespace ResidualCleaner.Maui.Services;

public sealed class Solution
{
    public string Code { get; set; } = "";
    public string Title { get; set; } = "";
    public string Level { get; set; } = "warn";
    public List<string> Steps { get; } = new();

    public Solution() { }

    public Solution(string code, string title, string level, IEnumerable<string> steps)
    {
        Code = code;
        Title = title;
        Level = level;
        Steps.AddRange(steps);
    }
}

public static class Solutions
{
    private static readonly string[] Denied = ["拒绝访问", "access is denied", "access denied", "0x5", "error 5"];
    private static readonly string[] Locked = ["正被使用", "being used", "占用", "另一个程序", "sharing violation", "32"];
    private static readonly string[] Driver = ["驱动", "内核", "driver", "fsflt", "antihijack", "selfprotection"];
    private static readonly string[] RegProtect = ["注册表", "regdelete", "regopen", "自我保护的注册表"];

    private static bool Hit(string? text, IEnumerable<string> words)
    {
        var low = (text ?? "").ToLowerInvariant();
        return words.Any(w => low.Contains(w.ToLowerInvariant()));
    }

    public static Solution? ForFailure(string kind, string detail, int pending = 0)
    {
        if (pending > 0)
        {
            return new Solution("REBOOT_DELETE", "已登记重启删除", "info", new[]
            {
                "文件句柄还被内核占着，删除动作已挂到下次开机执行",
                "重启后系统会在 360 自保护加载之前完成删除",
                "重启后打开本工具点「复查」确认是否清干净",
            });
        }

        if (Hit(detail, Denied) || (Hit(kind, new[] { "registry" }) && Hit(detail, RegProtect)))
        {
            return new Solution("ACL_TAKEOVER", "权限被拒绝", "warn", new[]
            {
                "工具会自动接管所有权并给 Administrators 完全控制，然后重试",
                "仍失败说明 360 自保护在内核层拦写，先在 360 主界面关闭「自我保护」",
                "关不掉就重启进安全模式，在安全模式下再跑一次一条龙",
            });
        }

        if (Hit(detail, Driver))
        {
            return new Solution("KERNEL_PROTECT", "被 360 内核驱动拦截", "danger", new[]
            {
                "ZhuDongFangYu / 360FsFlt / 360AntiHijack 在驱动层拒绝删除",
                "先退出 360 托盘并关闭自我保护，再执行清理",
                "已有残留驱动就进安全模式清理，正常模式下删不掉是预期行为",
            });
        }

        if (Hit(detail, Locked))
        {
            return new Solution("FILE_LOCKED", "文件被占用", "warn", new[]
            {
                "在任务管理器结束对应的 360 进程，或用工具里的「结束占用」",
                "关掉正在占用该目录的程序（解压软件、浏览器、壁纸客户端）",
                "仍占用就点清理，工具会把删除登记到下次重启",
            });
        }

        if (kind is "dir" or "file" or "dll")
        {
            return new Solution("RETRY_ADMIN", "删除未完成", "warn", new[]
            {
                "确认程序是以管理员身份启动（标题栏应有「管理员」标记）",
                "点「重新扫描」定位剩余项后单独重试",
                "反复失败时进安全模式做一次全量清理",
            });
        }

        return new Solution("GENERIC", "这一项没删干净", "warn", new[]
        {
            "右键「以管理员身份运行」后重试一次",
            "在日志里搜索该项路径，确认是否真的还在磁盘上",
            "把日志反馈到仓库 Issue，附上这项的类型和报错",
        });
    }

    public static Solution ForProtected(int count, string pack = "")
    {
        var steps = new List<string>
        {
            string.IsNullOrEmpty(pack)
                ? "工具已把这些键记入安全模式清理清单"
                : $"工具已把这些键导出成安全模式清理脚本：{pack}",
            "重启进安全模式（开机按 F8 或在系统设置里选「高级启动」）",
            "安全模式下运行生成的脚本，或在安全模式里再跑一次一条龙",
        };
        return new Solution("REG_SAFE_PACK", $"{count} 项注册表被自我保护拦截", "danger", steps);
    }

    public static List<Solution> Collect(IEnumerable<EngineRow>? rows)
    {
        var outList = new List<Solution>();
        var seen = new HashSet<string>();
        foreach (var row in rows ?? Enumerable.Empty<EngineRow>())
        {
            if (row.Ok) continue;
            var sol = ForFailure(row.Kind, row.Detail, row.Pending);
            if (sol == null || !seen.Add(sol.Code)) continue;
            outList.Add(sol);
        }
        return outList;
    }
}
