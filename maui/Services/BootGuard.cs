using System.Diagnostics;
using System.Text;
using Microsoft.Win32;

namespace ResidualCleaner.Maui.Services;

public static class BootGuard
{
    private const string TaskName = "ResidualCleanerPatrol";
    private const string RunKeyPath = @"Software\Microsoft\Windows\CurrentVersion\Run";
    private const string RunValue = "ResidualCleanerPatrol";
    public const string BootArg = "--boot-scan";

    private static string CommandLine()
    {
        var exe = Environment.ProcessPath ?? Path.Combine(AppContext.BaseDirectory, "ResidualCleaner.exe");
        return $"\"{exe}\" {BootArg}";
    }

    private static (int Code, string Output) Run(string[] args, int timeout = 25)
    {
        try
        {
            var psi = new ProcessStartInfo("schtasks", string.Join(" ", args.Select(a => Quote(a))))
            {
                CreateNoWindow = true,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                StandardOutputEncoding = Encoding.GetEncoding(936),
                StandardErrorEncoding = Encoding.GetEncoding(936),
            };
            using var proc = Process.Start(psi);
            if (proc == null) return (1, "无法启动 schtasks");
            var output = proc.StandardOutput.ReadToEnd() + proc.StandardError.ReadToEnd();
            if (!proc.WaitForExit(timeout)) proc.Kill();
            return (proc.ExitCode, output.Trim());
        }
        catch (Exception ex)
        {
            return (1, ex.Message);
        }
    }

    private static string Quote(string s) => "\"" + s + "\"";

    private static bool TaskExists() => Run(["/query", "/tn", TaskName]).Code == 0;

    private static bool RunValueExists()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(RunKeyPath, writable: false);
            if (key == null) return false;
            var value = key.GetValue(RunValue) as string;
            return !string.IsNullOrWhiteSpace(value);
        }
        catch { return false; }
    }

    public static bool IsEnabled() => TaskExists() || RunValueExists();

    private static (bool Ok, string Detail) CreateTask()
    {
        var cmd = CommandLine();
        var baseArgs = new[] { "/create", "/tn", TaskName, "/tr", cmd, "/sc", "onlogon", "/rl", "HIGHEST", "/f" };
        var withDelay = new List<string> { "/create", "/tn", TaskName, "/tr", cmd, "/sc", "onlogon", "/delay", "0000:20", "/rl", "HIGHEST", "/f" };
        var r = Run(withDelay.ToArray());
        if (r.Code == 0) return (true, "已登记计划任务：下次登录后自动以管理员身份启动巡检窗口");
        r = Run(baseArgs);
        return r.Code == 0
            ? (true, "已登记计划任务：下次登录后自动启动巡检窗口")
            : (false, r.Output);
    }

    private static (bool Ok, string Detail) DeleteTask()
    {
        if (!TaskExists()) return (true, "计划任务本来就不存在");
        var r = Run(["/delete", "/tn", TaskName, "/f"]);
        return r.Code == 0 ? (true, "已删除开机巡检计划任务") : (false, r.Output);
    }

    private static (bool Ok, string Detail) WriteRun(bool enable)
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(RunKeyPath, writable: true);
            if (key == null) return (false, "注册表启动项路径不存在");
            if (enable)
            {
                key.SetValue(RunValue, CommandLine());
                return (true, "已登记注册表启动项（开机时可能弹一次 UAC）");
            }
            if (key.GetValue(RunValue) != null) key.DeleteValue(RunValue);
            return (true, "已移除注册表启动项");
        }
        catch (Exception ex)
        {
            return (false, $"注册表启动项写入失败：{ex.Message}");
        }
    }

    public static (bool Ok, string Detail) Enable()
    {
        var (ok, msg) = CreateTask();
        if (ok) return (ok, msg);
        var (okRun, msgRun) = WriteRun(true);
        return okRun ? (true, $"计划任务不可用（{msg}），已改用注册表启动项") : (false, $"{msg}；{msgRun}");
    }

    public static (bool Ok, string Detail) Disable()
    {
        var (okTask, msgTask) = DeleteTask();
        var (okRun, msgRun) = WriteRun(false);
        return (okTask || okRun, $"{msgTask}；{msgRun}");
    }

    public static (bool Ok, string Detail) SyncState(bool enabled) => enabled ? Enable() : Disable();

    public static string StateText() => IsEnabled() ? "开机巡检：已开启" : "开机巡检：未开启";
}
