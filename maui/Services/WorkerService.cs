using ResidualCleaner.Maui.Models;

namespace ResidualCleaner.Maui.Services;

public enum WorkerMode { Scan, Uninstall, Residual, Clean }

public sealed class WorkerPayload
{
    public List<AppDefinition> Apps { get; set; } = new();
    public Dictionary<string, List<CleanItem>> ItemsByApp { get; set; } = new();
    public List<CleanItem>? ExtraItems { get; set; }
    public List<CleanItem>? Items { get; set; }
    public bool Deep { get; set; } = true;
}

public sealed class WorkerResult
{
    public WorkerMode Mode { get; set; }
    public List<CleanItem>? Items { get; set; }
    public Dictionary<string, AppStatus>? Status { get; set; }
    public Dictionary<string, object>? Summary { get; set; }
    public EngineResult? Engine { get; set; }
    public string? Error { get; set; }
    public int Protected { get; set; }
    public string? SafePack { get; set; }
}

public sealed class WorkerService
{
    private readonly CancellationTokenSource _cts = new();
    public event Action<string>? OnLog;
    public event Action<int, string>? OnProgress;
    public event Action<WorkerResult>? OnCompleted;

    public void RequestStop() => _cts.Cancel();

    public async Task RunAsync(WorkerMode mode, WorkerPayload? payload = null)
    {
        payload ??= new WorkerPayload();
        try
        {
            WorkerResult result = mode switch
            {
                WorkerMode.Scan => await DoScanAsync(),
                WorkerMode.Uninstall => DoUninstall(payload),
                WorkerMode.Residual => DoResidual(payload),
                WorkerMode.Clean => DoClean(payload),
                _ => new WorkerResult { Mode = mode, Error = "未知模式" },
            };
            result.Mode = mode;
            AttachProtected(result);
            OnCompleted?.Invoke(result);
        }
        catch (Exception ex)
        {
            OnLog?.Invoke($"任务异常终止：{ex.Message}");
            OnCompleted?.Invoke(new WorkerResult { Mode = mode, Error = ex.Message });
        }
    }

    private async Task<WorkerResult> DoScanAsync()
    {
        OnLog?.Invoke("开始扫描目标软件残留…");
        var scanner = new Scanner();
        OnProgress?.Invoke(5, "读取已安装程序列表");
        var entries = scanner.UninstallEntries();
        OnLog?.Invoke($"注册表卸载项命中 {entries.Count} 个目标软件相关条目");

        OnProgress?.Invoke(25, "检测进程与服务");
        var (items, status) = await Task.Run(() => scanner.ScanAllApps(true));
        OnProgress?.Invoke(65, "扫描公共组件与启动项");
        var common = scanner.ScanCommon(true);

        var existing = items.Select(i => i.Key).ToHashSet(StringComparer.OrdinalIgnoreCase);
        foreach (var c in common)
            if (existing.Add(c.Key)) items.Add(c);

        OnProgress?.Invoke(95, "汇总结果");
        var (apps, totalApps, dirs, regs) = scanner.InstalledSummary();
        var summary = new Dictionary<string, object>
        {
            ["entries"] = entries.Count,
            ["items"] = items.Count,
            ["apps"] = apps,
            ["totalApps"] = totalApps,
            ["dirs"] = dirs,
            ["regs"] = regs,
            ["size"] = items.Sum(i => i.Size),
        };
        OnLog?.Invoke($"扫描完成：{items.Count} 个可清理项，应用 {apps} 款");
        OnProgress?.Invoke(100, "扫描完成");
        return new WorkerResult { Items = items, Status = status, Summary = summary };
    }

    private WorkerResult DoUninstall(WorkerPayload payload)
    {
        OnLog?.Invoke($"开始卸载 {payload.Apps.Count} 款应用（不调用官方卸载器）");
        var engine = new CleanerEngine(OnLog, OnProgress, () => _cts.IsCancellationRequested);
        var result = engine.UninstallApps(payload.Apps, payload.ItemsByApp, payload.ExtraItems);
        OnProgress?.Invoke(100, "卸载流程结束");
        return new WorkerResult { Engine = result };
    }

    private WorkerResult DoResidual(WorkerPayload payload)
    {
        OnLog?.Invoke("开始扫描残余项目" + (payload.Deep ? "（含深度扫盘）" : ""));
        var scanner = new Scanner();
        var items = scanner.ScanResidual(payload.Deep, (msg, count) =>
            OnProgress?.Invoke(Math.Min(90, 10 + count / 20), msg));
        OnProgress?.Invoke(100, $"残留扫描完成，共 {items.Count} 项");
        OnLog?.Invoke($"残留扫描完成：{items.Count} 项");
        return new WorkerResult { Items = items, Summary = new Dictionary<string, object> { ["totalSize"] = items.Sum(i => i.Size) } };
    }

    private WorkerResult DoClean(WorkerPayload payload)
    {
        OnLog?.Invoke($"开始删除 {payload.Items?.Count ?? 0} 个项目");
        var engine = new CleanerEngine(OnLog, OnProgress, () => _cts.IsCancellationRequested);
        var result = engine.CleanItems(payload.Items ?? new List<CleanItem>());
        OnProgress?.Invoke(100, "删除完成");
        return new WorkerResult { Engine = result };
    }

    private void AttachProtected(WorkerResult result)
    {
        var protectedItems = RegistryService.ConsumeProtected();
        if (protectedItems.Count == 0) return;
        var pack = RegistryService.BuildSafeModePack(protectedItems);
        result.Protected = protectedItems.Count;
        result.SafePack = pack;
        OnLog?.Invoke($"⚠ {protectedItems.Count} 项注册表被软件自我保护拦截，已生成安全模式清理包：{pack}");
    }
}
