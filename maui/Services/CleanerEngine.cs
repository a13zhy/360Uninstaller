using System.Diagnostics;
using System.IO;
using System.Threading;
using ResidualCleaner.Maui.Models;

namespace ResidualCleaner.Maui.Services;

public sealed class EngineRow
{
    public string Kind { get; set; } = "";
    public string KindLabel { get; set; } = "";
    public string Label { get; set; } = "";
    public string Target { get; set; } = "";
    public long Size { get; set; }
    public bool Ok { get; set; }
    public int Pending { get; set; }
    public string Detail { get; set; } = "";
}

public sealed class EngineResult
{
    public int Ok { get; set; }
    public int Fail { get; set; }
    public int Skipped { get; set; }
    public long Freed { get; set; }
    public int Pending { get; set; }
    public List<EngineRow> Rows { get; } = new();

    public int Total => Ok + Fail;

    public void Add(CleanItem item, bool ok, string detail, int pending = 0)
    {
        if (ok) Ok++; else Fail++;
        Pending += Math.Max(0, pending);
        if (ok && pending == 0) Freed += item.Size;
        Rows.Add(new EngineRow
        {
            Kind = item.Kind,
            KindLabel = item.KindLabel,
            Label = item.Label,
            Target = item.Target,
            Size = item.Size,
            Ok = ok,
            Pending = pending,
            Detail = detail,
        });
    }
}

public sealed class CleanerEngine
{
    private readonly Action<string> _logger;
    private readonly Action<int, string> _progress;
    private readonly Func<bool> _shouldStop;

    public CleanerEngine(Action<string>? logger = null, Action<int, string>? progress = null, Func<bool>? shouldStop = null)
    {
        _logger = logger ?? (_ => { });
        _progress = progress ?? ((pct, msg) => { });
        _shouldStop = shouldStop ?? (() => false);
    }

    public EngineResult CleanItems(IReadOnlyList<CleanItem> items, string stagePrefix = "")
    {
        var result = new EngineResult();
        var total = Math.Max(1, items.Count);
        for (var i = 0; i < items.Count; i++)
        {
            if (_shouldStop())
            {
                result.Skipped += total - i;
                _logger("用户已取消，剩余项目跳过");
                break;
            }
            var item = items[i];
            var pct = (i + 1) * 100 / total;
            _progress(pct, $"{stagePrefix}正在处理 {i + 1}/{total}：{item.Label}");
            var (ok, detail, pending) = RemoveOne(item);
            result.Add(item, ok, detail, pending);
            if (item.Kind is "dir" or "file" && ok && pending == 0)
                _logger($"  释放空间 {AppPaths.HumanSize(item.Size)}");
            Thread.Sleep(50);
        }
        return result;
    }

    public EngineResult UninstallApps(IEnumerable<AppDefinition> apps, Dictionary<string, List<CleanItem>> itemsByApp, List<CleanItem>? extraItems = null)
    {
        var all = new List<CleanItem>();
        foreach (var app in apps)
            if (itemsByApp.TryGetValue(app.Key, out var list)) all.AddRange(list);
        if (extraItems != null) all.AddRange(extraItems);

        var seen = new HashSet<string>();
        var unique = all.Where(i => seen.Add(i.Key)).ToList();

        var order = new Dictionary<string, int>
        {
            ["process"] = 0, ["service"] = 1, ["task"] = 2, ["dir"] = 3,
            ["file"] = 4, ["registry"] = 5, ["shortcut"] = 6,
        };
        unique.Sort((a, b) => order.GetValueOrDefault(a.Kind, 9).CompareTo(order.GetValueOrDefault(b.Kind, 9)));

        var labels = new Dictionary<int, string>
        {
            [0] = "结束进程", [1] = "停止并删除服务", [2] = "清理计划任务",
            [3] = "删除安装目录", [4] = "删除残留文件", [5] = "清理注册表", [6] = "清理快捷方式",
        };

        var result = new EngineResult();
        var total = Math.Max(1, unique.Count);
        for (var i = 0; i < unique.Count; i++)
        {
            if (_shouldStop())
            {
                result.Skipped += total - i;
                _logger("用户已取消");
                break;
            }
            var item = unique[i];
            var stage = labels.GetValueOrDefault(order.GetValueOrDefault(item.Kind, 9), "清理");
            var pct = (i + 1) * 100 / total;
            _progress(pct, $"{stage}：{item.Label} ({i + 1}/{total})");
            var (ok, detail, pending) = RemoveOne(item);
            result.Add(item, ok, detail, pending);
        }
        return result;
    }

    private (bool Ok, string Detail, int Pending) RemoveOne(CleanItem item)
    {
        bool ok;
        string detail;
        var pending = 0;

        switch (item.Kind)
        {
            case "process":
                (ok, detail) = ProcessService.KillProcess(item.Target);
                break;
            case "service":
                var (ok1, d1) = ProcessService.StopService(item.Target);
                var (ok2, d2) = ProcessService.DeleteService(item.Target);
                ok = ok1 && ok2;
                detail = $"{d1}；{d2}";
                break;
            case "dir":
            case "file":
                (ok, detail, _, pending) = RemovePath(item.Target, force: true);
                break;
            case "registry":
                if (item.Extra.TryGetValue("value_name", out var valueName))
                {
                    var idx = item.Target.IndexOf("::", StringComparison.Ordinal);
                    var key = idx >= 0 ? item.Target[..idx] : item.Target;
                    (ok, detail) = RegistryService.DeleteValue(key, valueName);
                }
                else
                {
                    (ok, detail) = RegistryService.DeleteKey(item.Target);
                }
                break;
            case "task":
                (ok, detail) = ProcessService.DeleteTask(item.Target);
                break;
            case "shortcut":
                (ok, detail, _, pending) = RemovePath(item.Target, force: false);
                break;
            default:
                ok = false;
                detail = $"未知类型：{item.Kind}";
                break;
        }

        _logger((ok ? "✔ " : "✘ ") + $"[{item.KindLabel}] {item.Label} — {detail}");
        return (ok, detail, pending);
    }

    private (bool Ok, string Detail, long Freed, int Pending) RemovePath(string path, bool force)
    {
        path = (path ?? "").Trim().Trim('"');
        if (string.IsNullOrEmpty(path)) return (false, "路径为空", 0, 0);
        path = Path.GetFullPath(Environment.ExpandEnvironmentVariables(path));
        if (!File.Exists(path) && !Directory.Exists(path)) return (true, "已不存在", 0, 0);

        var freed = 0L;
        var failed = new List<string>();

        if (PlainDelete(path, failed, ref freed)) return (true, "已删除", freed, 0);
        var firstFail = string.Join("；", failed.Where(x => x != path).Take(1));
        if (firstFail.Length > 120) firstFail = firstFail.Substring(0, 120);
        if (!force) return (false, firstFail.IfEmpty("文件正在使用"), 0, 0);

        var notes = new List<string>();
        var (killed, others) = ForceRemove.ReleaseHolders(path, _logger);
        if (killed.Count > 0) notes.Add($"结束 {killed.Count} 个 360 占用进程");
        if (others.Count > 0) notes.Add("当前被 " + string.Join("、", others.Distinct().Take(3)) + " 占用");

        _logger("  接管所有权（icacls 重置 + takeown）");
        ForceRemove.TakeOwnership(path, _logger);

        failed.Clear();
        if (PlainDelete(path, failed, ref freed) || !File.Exists(path) && !Directory.Exists(path))
        {
            var detail = "强力删除完成（已接管所有权）";
            if (notes.Count > 0) detail += "，" + string.Join("，", notes);
            return (true, detail, freed, 0);
        }

        var remaining = failed.Where(p => File.Exists(p) || Directory.Exists(p)).ToList();
        if (File.Exists(path) || Directory.Exists(path)) remaining.Add(path);
        var (scheduled, anyOk) = ForceRemove.ScheduleDeleteOnReboot(remaining, _logger);
        if (anyOk)
        {
            var detail = $"尚有 {scheduled} 项被占用，已登记下次开机时删除";
            if (notes.Count > 0) detail = string.Join("，", notes) + "，" + detail;
            return (true, detail, freed, scheduled);
        }

        var reason = "文件正在使用或被系统保护";
        foreach (var item in failed.Where(p => File.Exists(p) || Directory.Exists(p)))
        {
            try { using var fs = File.OpenWrite(item); }
            catch (Exception ex) { reason = ForceRemove.ErrorText(ex); break; }
        }
        var final = notes.Count > 0 ? string.Join("，", notes) + "，" + reason : reason;
        if (!ForceRemove.IsAdmin()) final += "（当前不是管理员，接管所有权与重启删除需要管理员权限）";
        return (false, final[..Math.Min(200, final.Length)], freed, 0);
    }

    private bool PlainDelete(string path, List<string> failed, ref long freed)
    {
        try
        {
            if (Directory.Exists(path) && !IsSymlink(path))
            {
                var freedBox = new List<long> { 0 };
                ForceRemove.DeleteTree(path, failed, freedBox);
                freed += freedBox[0];
            }
            else
            {
                try { File.SetAttributes(path, FileAttributes.Normal); } catch { }
                ForceRemove.ClearAttributes(path);
                var size = 0L;
                try { size = new FileInfo(path).Length; } catch { }
                File.Delete(path);
                freed += size;
            }
        }
        catch (Exception ex)
        {
            failed.Add(path);
            failed.Add(ForceRemove.ErrorText(ex));
        }
        return !File.Exists(path) && !Directory.Exists(path);
    }

    private static bool IsSymlink(string path)
    {
        try { return (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0; }
        catch { return false; }
    }
}
