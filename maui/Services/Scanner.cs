using System.IO;
using ResidualCleaner.Maui.Data;
using ResidualCleaner.Maui.Models;

namespace ResidualCleaner.Maui.Services;

public sealed class AppStatus
{
    public bool Installed { get; set; }
    public string Note { get; set; } = "";
    public string Name { get; set; } = "";
    public string Desc { get; set; } = "";
}

public sealed class Scanner
{
    private readonly SystemSnapshot _snap = new();
    private readonly Dictionary<string, (bool Installed, string Note)> _cache = new(StringComparer.OrdinalIgnoreCase);

    public sealed record UninstallEntry(string Key, string RegPath, string Name, string Version, string Publisher, string InstallLocation, string UninstallString, long SizeKb);

    private static bool Hit(string text, IEnumerable<string> keywords) =>
        keywords.Any(k => text.Contains(k, StringComparison.OrdinalIgnoreCase));

    public List<UninstallEntry> UninstallEntries()
    {
        var entries = new List<UninstallEntry>();
        foreach (var root in AppCatalog.UninstallKeys)
        {
            foreach (var sub in RegistryService.ListSubkeys(root))
            {
                var path = $"{root}\\{sub}";
                var vals = RegistryService.ReadValues(path);
                vals.TryGetValue("DisplayName", out var name);
                if (string.IsNullOrWhiteSpace(name)) continue;
                if (!Hit(name, new[] { "360", "奇虎", "qihu", "qhsafe" })) continue;
                vals.TryGetValue("DisplayVersion", out var version);
                vals.TryGetValue("Publisher", out var publisher);
                vals.TryGetValue("InstallLocation", out var location);
                vals.TryGetValue("UninstallString", out var uninstall);
                long sizeKb = long.TryParse(vals.GetValueOrDefault("EstimatedSize"), out var s) ? s : 0;
                entries.Add(new UninstallEntry(sub, path, name, version ?? "", publisher ?? "", location ?? "", uninstall ?? "", sizeKb));
            }
        }
        return entries;
    }

    public (bool Installed, string Note) AppInstalled(AppDefinition app)
    {
        if (_cache.TryGetValue(app.Key, out var cached)) return cached;

        var procs = _snap.ProcessNames;
        if (app.Processes.Any(p => procs.Contains(p)))
        {
            _cache[app.Key] = (true, "正在运行");
            return _cache[app.Key];
        }
        if (app.Dirs.Any(d => !string.IsNullOrEmpty(d) && Directory.Exists(d)))
        {
            _cache[app.Key] = (true, "安装目录存在");
            return _cache[app.Key];
        }
        if (app.Regs.Any(RegistryService.KeyExists))
        {
            _cache[app.Key] = (true, "注册表项存在");
            return _cache[app.Key];
        }
        var matchKeywords = app.Keywords.Count > 0 ? app.Keywords : new List<string> { app.Name.Replace(" ", ""), app.Key.Replace("360", "") };
        if (UninstallEntries().Any(e => Hit(e.Name, matchKeywords)))
        {
            _cache[app.Key] = (true, "已注册安装信息");
            return _cache[app.Key];
        }
        _cache[app.Key] = (false, "");
        return _cache[app.Key];
    }

    public List<CleanItem> ScanApp(AppDefinition app, bool withSize = true)
    {
        var items = new List<CleanItem>();
        var procs = _snap.ProcessNames;

        foreach (var p in app.Processes.Where(p => procs.Contains(p)))
            items.Add(new CleanItem { Kind = "process", Target = p, Label = p, AppKey = app.Key, AppName = app.Name });

        foreach (var svc in _snap.Services.Where(s => app.Services.Any(x => s.Contains(x, StringComparison.OrdinalIgnoreCase))))
            items.Add(new CleanItem { Kind = "service", Target = svc, Label = svc, AppKey = app.Key, AppName = app.Name });

        foreach (var d in app.Dirs.Where(d => !string.IsNullOrEmpty(d) && Directory.Exists(d)))
            items.Add(new CleanItem { Kind = "dir", Target = d, Label = d, AppKey = app.Key, AppName = app.Name, Size = withSize ? AppPaths.PathSize(d) : 0 });

        foreach (var r in app.Regs.Where(RegistryService.KeyExists))
            items.Add(new CleanItem { Kind = "registry", Target = r, Label = r, AppKey = app.Key, AppName = app.Name });

        foreach (var t in _snap.Tasks.Where(t => app.Tasks.Any(k => t.Contains(k, StringComparison.OrdinalIgnoreCase))))
            items.Add(new CleanItem { Kind = "task", Target = t, Label = t, AppKey = app.Key, AppName = app.Name });

        foreach (var sc in EnumerateShortcuts().Where(sc => app.Shortcuts.Any(k => Path.GetFileName(sc).Contains(k, StringComparison.OrdinalIgnoreCase))))
            items.Add(new CleanItem { Kind = "shortcut", Target = sc, Label = Path.GetFileName(sc), AppKey = app.Key, AppName = app.Name, Size = FileSize(sc) });

        return items;
    }

    public (List<CleanItem> Items, Dictionary<string, AppStatus> Status) ScanAllApps(bool withSize = true)
    {
        var items = new List<CleanItem>();
        var status = new Dictionary<string, AppStatus>();
        foreach (var app in AppCatalog.Apps())
        {
            var (installed, note) = AppInstalled(app);
            status[app.Key] = new AppStatus { Installed = installed, Note = note, Name = app.Name, Desc = app.Desc };
            if (installed) items.AddRange(ScanApp(app, withSize));
        }
        return (items, status);
    }

    public List<CleanItem> ScanCommon(bool withSize = true)
    {
        var items = new List<CleanItem>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var d in AppCatalog.CommonDirs().Where(d => !string.IsNullOrEmpty(d) && Directory.Exists(d) && seen.Add(d)))
            items.Add(new CleanItem { Kind = "dir", Target = d, Label = d, AppName = "360 公共组件", Size = withSize ? AppPaths.PathSize(d) : 0 });

        foreach (var runKey in AppCatalog.RunKeys)
        {
            foreach (var (name, value) in RegistryService.ReadValues(runKey))
            {
                if (!Hit($"{name} {value}", new[] { "360", "qhsafe", "qihu" })) continue;
                items.Add(new CleanItem
                {
                    Kind = "registry", Target = $"{runKey}::{name}", Label = name, AppName = "360 开机启动项",
                    Extra = { ["value_name"] = name },
                });
            }
        }

        foreach (var t in _snap.Tasks.Where(t => Hit(t, new[] { "360", "qhsafe" })))
            items.Add(new CleanItem { Kind = "task", Target = t, Label = t, AppName = "360 计划任务" });

        return items;
    }

    public List<CleanItem> DeepScan(string[]? keywords = null, int limit = 300, Action<string, int>? progress = null)
    {
        keywords ??= AppCatalog.FileKeywords;
        var excludes = AppCatalog.ScanExcludes().Select(p => Path.GetFullPath(p).TrimEnd('\\').ToLowerInvariant()).ToHashSet();
        var items = new List<CleanItem>();
        var visited = 0;
        const int maxVisited = 120000;

        var roots = AppCatalog.ScanRoots().Where(Directory.Exists).ToList();
        foreach (var drive in new[] { "D:\\", "E:\\", "F:\\" })
        {
            if (!Directory.Exists(drive)) continue;
            foreach (var name in new[] { "360", "Program Files", "Program Files (x86)" })
            {
                var p = Path.Combine(drive, name);
                if (Directory.Exists(p)) roots.Add(p);
            }
        }

        foreach (var baseDir in roots)
        {
            if (!Directory.Exists(baseDir)) continue;
            var stack = new Stack<string>();
            stack.Push(baseDir);
            while (stack.Count > 0)
            {
                var dir = stack.Pop();
                string[] subdirs;
                string[] files;
                try
                {
                    subdirs = Directory.GetDirectories(dir);
                    files = Directory.GetFiles(dir);
                }
                catch { continue; }

                visited++;
                if (visited > maxVisited) return items;
                if (progress != null && visited % 200 == 0) progress($"深度扫描中… {items.Count} 项", items.Count);

                foreach (var sub in subdirs)
                {
                    var full = sub;
                    if (excludes.Contains(Path.GetFullPath(full).TrimEnd('\\').ToLowerInvariant())) continue;
                    if (Path.GetFileName(full).StartsWith("$")) continue;
                    if (Hit(Path.GetFileName(full), keywords))
                    {
                        items.Add(new CleanItem { Kind = "dir", Target = full, Label = full, AppName = "深度扫描", Size = AppPaths.PathSize(full) });
                        if (items.Count >= limit) return items;
                        continue;
                    }
                    stack.Push(full);
                }

                foreach (var f in files)
                {
                    if (!Hit(Path.GetFileName(f), keywords)) continue;
                    long size = 0;
                    try { size = new FileInfo(f).Length; } catch { }
                    items.Add(new CleanItem { Kind = "file", Target = f, Label = f, AppName = "深度扫描", Size = size });
                    if (items.Count >= limit) return items;
                }
            }
        }
        return items;
    }

    public List<CleanItem> ScanResidual(bool deep = true, Action<string, int>? progress = null)
    {
        var items = new List<CleanItem>();
        var procs = _snap.ProcessNames;

        foreach (var app in AppCatalog.Apps())
            foreach (var p in app.Processes.Where(p => procs.Contains(p)))
                items.Add(new CleanItem { Kind = "process", Target = p, Label = p, AppKey = app.Key, AppName = app.Name });

        foreach (var svc in _snap.Services.Where(s => Hit(s, new[] { "360", "qhsafe", "zhudongfangyu" })))
            items.Add(new CleanItem { Kind = "service", Target = svc, Label = svc, AppName = "360 服务" });

        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var d in AppCatalog.CommonDirs().Where(d => !string.IsNullOrEmpty(d) && Directory.Exists(d) && seen.Add(d)))
            items.Add(new CleanItem { Kind = "dir", Target = d, Label = d, AppName = "残留目录", Size = AppPaths.PathSize(d) });

        foreach (var root in AppCatalog.CommonRegRoots)
            foreach (var sub in RegistryService.ListSubkeys(root).Where(s => Hit(s, AppCatalog.RegKeywords)))
                items.Add(new CleanItem { Kind = "registry", Target = $"{root}\\{sub}", Label = $"{root}\\{sub}", AppName = "残留注册表" });

        foreach (var runKey in AppCatalog.RunKeys)
            foreach (var (name, value) in RegistryService.ReadValues(runKey))
            {
                if (!Hit($"{name} {value}", new[] { "360", "qhsafe", "qihu" })) continue;
                items.Add(new CleanItem
                {
                    Kind = "registry", Target = $"{runKey}::{name}", Label = name, AppName = "开机启动项",
                    Extra = { ["value_name"] = name },
                });
            }

        foreach (var t in _snap.Tasks.Where(t => Hit(t, new[] { "360", "qhsafe" })))
            items.Add(new CleanItem { Kind = "task", Target = t, Label = t, AppName = "残留任务" });

        foreach (var sc in EnumerateShortcuts())
            items.Add(new CleanItem { Kind = "shortcut", Target = sc, Label = Path.GetFileName(sc), AppName = "残留快捷方式", Size = FileSize(sc) });

        if (deep)
        {
            progress?.Invoke("深度扫描残留文件…", items.Count);
            items.AddRange(DeepScan(progress: progress));
        }
        return items;
    }

    public (int Apps, int TotalApps, int Dirs, int Regs) InstalledSummary()
    {
        var installed = 0;
        var dirs = 0;
        var regs = 0;
        var apps = AppCatalog.Apps();
        foreach (var app in apps)
        {
            if (AppInstalled(app).Installed) installed++;
            dirs += app.Dirs.Count(d => !string.IsNullOrEmpty(d) && Directory.Exists(d));
            regs += app.Regs.Count(RegistryService.KeyExists);
        }
        return (installed, apps.Count, dirs, regs);
    }

    private static long FileSize(string path)
    {
        try { return new FileInfo(path).Length; } catch { return 0; }
    }

    private List<string> EnumerateShortcuts()
    {
        var found = new List<string>();
        var dirs = AppCatalog.StartMenuDirs();
        if (!string.IsNullOrEmpty(AppPaths.Desktop)) dirs.Add(AppPaths.Desktop);
        foreach (var baseDir in dirs.Where(Directory.Exists))
        {
            var baseDepth = baseDir.TrimEnd('\\').Count(c => c == '\\');
            var stack = new Stack<string>();
            stack.Push(baseDir);
            while (stack.Count > 0)
            {
                var dir = stack.Pop();
                string[] subdirs;
                string[] files;
                try { subdirs = Directory.GetDirectories(dir); files = Directory.GetFiles(dir); }
                catch { continue; }
                if (dir.Count(c => c == '\\') - baseDepth >= 3) continue;
                foreach (var f in files)
                {
                    if (f.EndsWith(".lnk", StringComparison.OrdinalIgnoreCase) && Hit(Path.GetFileName(f), new[] { "360" }))
                        found.Add(f);
                }
                foreach (var d in subdirs) stack.Push(d);
            }
        }
        return found;
    }
}
