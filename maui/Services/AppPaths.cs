using System.IO;

namespace ResidualCleaner.Maui.Services;

public static class AppPaths
{
    public static string AppName { get; } = "残留清理卫士";
    public static string AppNameEn { get; } = "ResidualCleaner";
    public static string AppVersion { get; } = "1.3.1.261127";
    public static string Tagline { get; } = "Windows 深度卸载与残留清理";

    public static string ProgramFiles { get; } = Environment.GetEnvironmentVariable("ProgramFiles") ?? @"C:\Program Files";
    public static string ProgramFilesX86 { get; } = Environment.GetEnvironmentVariable("ProgramFiles(x86)") ?? @"C:\Program Files (x86)";
    public static string ProgramData { get; } = Environment.GetEnvironmentVariable("ProgramData") ?? @"C:\ProgramData";
    public static string AppData { get; } = Environment.GetEnvironmentVariable("APPDATA") ?? "";
    public static string LocalAppData { get; } = Environment.GetEnvironmentVariable("LOCALAPPDATA") ?? "";
    public static string UserProfile { get; } = Environment.GetEnvironmentVariable("USERPROFILE") ?? "";
    public static string WindowsDir { get; } = Environment.GetEnvironmentVariable("SystemRoot") ?? @"C:\Windows";
    public static string Desktop { get; } = string.IsNullOrEmpty(UserProfile) ? "" : Path.Combine(UserProfile, "Desktop");

    public static string LogDir { get; } = Path.Combine(LocalAppData, "ResidualCleaner");
    public static string LogFile { get; } = Path.Combine(LogDir, "cleaner.log");
    public static string RegBackupDir { get; } = Path.Combine(LogDir, "reg_backup");
    public static string SafeModeDir { get; } = Path.Combine(LogDir, "safe_mode");
    public static string UpdateDir { get; } = Path.Combine(LogDir, "update");

    public static string Expand(string path) => Environment.ExpandEnvironmentVariables(path);

    public static string HumanSize(double num)
    {
        if (num < 1024) return $"{(int)num} B";
        string[] units = { "KB", "MB", "GB", "TB" };
        foreach (var unit in units)
        {
            num /= 1024.0;
            if (num < 1024) return $"{num:0.0} {unit}";
        }
        return $"{num:0.0} PB";
    }

    public static long PathSize(string path, int limitFiles = 20000)
    {
        try
        {
            if (File.Exists(path)) return new FileInfo(path).Length;
            if (!Directory.Exists(path)) return 0;

            long total = 0;
            int count = 0;
            var stack = new Stack<string>();
            stack.Push(path);
            while (stack.Count > 0)
            {
                var dir = stack.Pop();
                string[] files;
                string[] subdirs;
                try
                {
                    files = Directory.GetFiles(dir);
                    subdirs = Directory.GetDirectories(dir);
                }
                catch
                {
                    continue;
                }
                foreach (var f in files)
                {
                    try { total += new FileInfo(f).Length; } catch { }
                    if (++count > limitFiles) return total;
                }
                foreach (var d in subdirs) stack.Push(d);
            }
            return total;
        }
        catch
        {
            return 0;
        }
    }
}
