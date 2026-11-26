using System.Diagnostics;
using System.Text;

namespace ResidualCleaner.Maui.Services;

public static class ProcessService
{
    private const int CreateNoWindow = 0x08000000;

    static ProcessService()
    {
        Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
    }

    public static (int Code, string Output) Run(string file, string[] args, int timeout = 25)
    {
        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = file,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                StandardOutputEncoding = Encoding.GetEncoding(936),
                StandardErrorEncoding = Encoding.GetEncoding(936),
            };
            foreach (var a in args) psi.ArgumentList.Add(a);
            using var p = Process.Start(psi);
            if (p == null) return (1, "进程无法启动");
            var stdout = p.StandardOutput.ReadToEnd();
            var stderr = p.StandardError.ReadToEnd();
            if (!p.WaitForExit(timeout))
            {
                try { p.Kill(); } catch { }
                return (1, "命令执行超时");
            }
            return (p.ExitCode, (stdout + stderr).Trim());
        }
        catch (Exception ex)
        {
            return (1, ex.Message);
        }
    }

    public static List<(string Name, string Pid)> ListProcesses()
    {
        var result = new List<(string, string)>();
        var (code, output) = Run("tasklist", new[] { "/fo", "csv", "/nh" });
        if (code != 0 || string.IsNullOrWhiteSpace(output)) return result;
        foreach (var line in output.SplitLines())
        {
            var parts = CsvSplit(line);
            if (parts.Count < 2) continue;
            result.Add((parts[0].Trim().ToLowerInvariant(), parts[1].Trim()));
        }
        return result;
    }

    public static List<string> ListServices()
    {
        var result = new List<string>();
        var (code, output) = Run("sc", new[] { "query", "type=", "service", "state=", "all" });
        if (code != 0) return result;
        foreach (var line in output.SplitLines())
        {
            var t = line.Trim();
            if (t.StartsWith("SERVICE_NAME:", StringComparison.OrdinalIgnoreCase))
                result.Add(t.Split(':', 2)[1].Trim());
        }
        return result;
    }

    public static List<string> ListTasks()
    {
        var result = new List<string>();
        var (code, output) = Run("schtasks", new[] { "/query", "/fo", "csv", "/nh" });
        if (code != 0 || string.IsNullOrWhiteSpace(output)) return result;
        foreach (var line in output.SplitLines())
        {
            var parts = CsvSplit(line);
            if (parts.Count > 0 && !string.IsNullOrWhiteSpace(parts[0]) && parts[0].Trim() != "TaskName")
                result.Add(parts[0].Trim().TrimStart('\\'));
        }
        return result;
    }

    public static (bool Ok, string Detail) KillProcess(string name)
    {
        var (code, output) = Run("taskkill", new[] { "/F", "/IM", name, "/T" });
        if (code == 0) return (true, $"已结束进程 {name}");
        var low = output.ToLowerInvariant();
        if (low.Contains("not found") || output.Contains("找不到") || output.Contains("没有运行"))
            return (true, $"进程 {name} 未运行");
        return (false, string.IsNullOrWhiteSpace(output) ? $"结束进程 {name} 失败" : output);
    }

    public static (bool Ok, string Detail) StopService(string name)
    {
        var (code, output) = Run("sc", new[] { "stop", name });
        if (code == 0) return (true, $"已停止服务 {name}");
        if (output.Contains("1060") || output.Contains("1062")) return (true, $"服务 {name} 不存在或未运行");
        return (false, string.IsNullOrWhiteSpace(output) ? $"停止服务 {name} 失败" : output);
    }

    public static (bool Ok, string Detail) DeleteService(string name)
    {
        var (code, output) = Run("sc", new[] { "delete", name });
        if (code == 0) return (true, $"已删除服务 {name}");
        if (output.Contains("1060") || output.Contains("1072")) return (true, $"服务 {name} 已不存在");
        return (false, string.IsNullOrWhiteSpace(output) ? $"删除服务 {name} 失败" : output);
    }

    public static (bool Ok, string Detail) DeleteTask(string name)
    {
        var (code, output) = Run("schtasks", new[] { "/delete", "/f", "/tn", name });
        if (code == 0) return (true, $"已删除计划任务 {name}");
        if (output.Contains("找不到") || output.ToLowerInvariant().Contains("cannot find")) return (true, $"计划任务 {name} 不存在");
        return (false, string.IsNullOrWhiteSpace(output) ? $"删除计划任务 {name} 失败" : output);
    }

    private static List<string> CsvSplit(string line)
    {
        var list = new List<string>();
        var sb = new StringBuilder();
        bool inQuote = false;
        foreach (var ch in line)
        {
            if (ch == '"') { inQuote = !inQuote; continue; }
            if (ch == ',' && !inQuote) { list.Add(sb.ToString()); sb.Clear(); continue; }
            sb.Append(ch);
        }
        list.Add(sb.ToString());
        return list;
    }
}

internal static class StringSplitExtensions
{
    public static string[] SplitLines(this string text) =>
        text.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n', StringSplitOptions.RemoveEmptyEntries);
}
