using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using Microsoft.Maui.Controls;
using ResidualCleaner.Maui.Models;

namespace ResidualCleaner.Maui.Services;

public static class IconService
{
    private static readonly Dictionary<string, ImageSource?> Cache = new(StringComparer.OrdinalIgnoreCase);
    private static readonly object Lock = new();

    public static ImageSource? Resolve(AppDefinition app, IReadOnlyList<CleanItem>? items)
    {
        var exe = ResolveExecutable(app, items);
        if (string.IsNullOrEmpty(exe)) return null;
        lock (Lock)
        {
            if (Cache.TryGetValue(exe, out var cached)) return cached;
        }
        var source = Extract(exe);
        lock (Lock) Cache[exe] = source;
        return source;
    }

    public static ImageSource? Resolve(CleanItem item)
    {
        if (!string.IsNullOrEmpty(item.IconHint) && File.Exists(item.IconHint))
            return Extract(item.IconHint);
        if (item.Kind == "shortcut" && File.Exists(item.Target))
        {
            var target = ResolveShortcutTarget(item.Target);
            if (!string.IsNullOrEmpty(target)) return Extract(target);
        }
        return null;
    }

    private static string ResolveExecutable(AppDefinition app, IReadOnlyList<CleanItem>? items)
    {
        var running = RunningExecutable(app, items);
        if (!string.IsNullOrEmpty(running)) return running;

        foreach (var dir in app.Dirs)
        {
            var exe = FindMainExecutable(dir);
            if (!string.IsNullOrEmpty(exe)) return exe;
        }

        try
        {
            var scanner = new Scanner();
            var match = scanner.UninstallEntries().FirstOrDefault(e =>
                app.Keywords.Any(k => e.Name.Contains(k, StringComparison.OrdinalIgnoreCase)) ||
                e.Name.Contains(app.Name.Replace(" ", ""), StringComparison.OrdinalIgnoreCase));
            if (match != null)
            {
                var loc = match.InstallLocation;
                if (!string.IsNullOrEmpty(loc))
                {
                    var exe = FindMainExecutable(loc);
                    if (!string.IsNullOrEmpty(exe)) return exe;
                }
                var quoted = ParseQuotedPath(match.UninstallString);
                if (!string.IsNullOrEmpty(quoted))
                {
                    var exe = FindMainExecutable(Path.GetDirectoryName(quoted) ?? "");
                    if (!string.IsNullOrEmpty(exe)) return exe;
                    if (quoted.EndsWith(".exe", StringComparison.OrdinalIgnoreCase)) return quoted;
                }
            }
        }
        catch { }
        return "";
    }

    private static string RunningExecutable(AppDefinition app, IReadOnlyList<CleanItem>? items)
    {
        var wanted = new HashSet<string>(app.Processes, StringComparer.OrdinalIgnoreCase);
        if (items != null)
            foreach (var it in items.Where(i => i.Kind == "process"))
                wanted.Add(it.Target);
        try
        {
            foreach (var proc in Process.GetProcesses())
            {
                try
                {
                    var file = proc.MainModule?.FileName;
                    if (string.IsNullOrEmpty(file)) continue;
                    if (wanted.Contains(Path.GetFileName(file))) return file;
                }
                catch { }
                finally { proc.Dispose(); }
            }
        }
        catch { }
        return "";
    }

    private static string FindMainExecutable(string dir)
    {
        if (string.IsNullOrWhiteSpace(dir) || !Directory.Exists(dir)) return "";
        string[] exes;
        try { exes = Directory.GetFiles(dir, "*.exe", SearchOption.TopDirectoryOnly); }
        catch { return ""; }
        if (exes.Length == 0)
        {
            try
            {
                var sub = Directory.GetDirectories(dir).Take(5);
                foreach (var s in sub)
                {
                    try { exes = Directory.GetFiles(s, "*.exe", SearchOption.TopDirectoryOnly); }
                    catch { continue; }
                    if (exes.Length > 0) break;
                }
            }
            catch { return ""; }
        }
        if (exes.Length == 0) return "";
        return exes
            .OrderByDescending(e => ScoreExe(e))
            .First();
    }

    private static int ScoreExe(string exe)
    {
        var n = Path.GetFileNameWithoutExtension(exe).ToLowerInvariant();
        if (n.Contains("uninstall") || n.Contains("setup") || n.Contains("update") || n.Contains("upgrade")) return 0;
        if (n.Contains("helper") || n.Contains("tray") || n.Contains("service") || n.Contains("svc")) return 1;
        if (n.Contains("safe") || n.Contains("main") || n.Contains("core") || n.Contains("browser") || n.Contains("host")) return 3;
        return 2;
    }

    private static string ParseQuotedPath(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return "";
        var t = text.Trim();
        if (t.StartsWith("\""))
        {
            var end = t.IndexOf('"', 1);
            return end > 1 ? t[1..end] : "";
        }
        var sp = t.Split(' ', 2);
        return sp[0];
    }

    private static string ResolveShortcutTarget(string lnk)
    {
        try
        {
            var shellType = Type.GetTypeFromProgID("WScript.Shell");
            if (shellType == null) return "";
            dynamic shell = Activator.CreateInstance(shellType)!;
            dynamic sc = shell.CreateShortcut(lnk);
            return (string)sc.TargetPath;
        }
        catch { return ""; }
    }

    private static ImageSource? Extract(string path)
    {
        try
        {
            var hIcon = ExtractIconHandle(path);
            if (hIcon == IntPtr.Zero) return null;
            try
            {
                using var bitmap = System.Drawing.Bitmap.FromHicon(hIcon);
                using var scaled = new System.Drawing.Bitmap(32, 32);
                using (var g = System.Drawing.Graphics.FromImage(scaled))
                {
                    g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
                    g.Clear(System.Drawing.Color.Transparent);
                    g.DrawImage(bitmap, 0, 0, 32, 32);
                }
                var ms = new MemoryStream();
                scaled.Save(ms, System.Drawing.Imaging.ImageFormat.Png);
                ms.Position = 0;
                return ImageSource.FromStream(() => new MemoryStream(ms.ToArray()));
            }
            finally { DestroyIcon(hIcon); }
        }
        catch { return null; }
    }

    private static IntPtr ExtractIconHandle(string path)
    {
        var shfi = new SHFILEINFO();
        const uint SHGFI_ICON = 0x100;
        const uint SHGFI_LARGEICON = 0x0;
        const uint SHGFI_USEFILEATTRIBUTES = 0x10;
        var isDir = Directory.Exists(path) && !File.Exists(path);
        var flags = SHGFI_ICON | SHGFI_LARGEICON;
        if (isDir) flags |= SHGFI_USEFILEATTRIBUTES;
        var attr = isDir ? 0x10u : 0x80u;
        return SHGetFileInfo(path, attr, ref shfi, (uint)Marshal.SizeOf(shfi), flags) != IntPtr.Zero ? shfi.hIcon : IntPtr.Zero;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct SHFILEINFO
    {
        public IntPtr hIcon;
        public int iIcon;
        public uint dwAttributes;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 260)] public string szDisplayName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 80)] public string szTypeName;
    }

    [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
    private static extern IntPtr SHGetFileInfo(string pszPath, uint dwFileAttributes, ref SHFILEINFO psfi, uint cbFileInfo, uint uFlags);

    [DllImport("user32.dll")]
    private static extern bool DestroyIcon(IntPtr hIcon);
}
