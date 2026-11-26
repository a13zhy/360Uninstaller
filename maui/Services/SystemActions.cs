using System.Diagnostics;
using System.Text;

namespace ResidualCleaner.Maui.Services;

/// <summary>
/// 系统动作：只在用户确认后安排延迟重启，不自动重启、不做定时循环；
/// 延迟窗口内可用 shutdown /a 撤销。
/// </summary>
public static class SystemActions
{
    public static (bool Ok, string Detail) ScheduleReboot(int delaySeconds = 20)
    {
        var delay = Math.Clamp(delaySeconds, 5, 120);
        try
        {
            var psi = new ProcessStartInfo("shutdown", $"/r /t {delay} /c \"残留清理卫士：清理已完成，系统将在倒计时结束后重启\"")
            {
                CreateNoWindow = true,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                StandardOutputEncoding = Encoding.GetEncoding(936),
                StandardErrorEncoding = Encoding.GetEncoding(936),
            };
            using var proc = Process.Start(psi);
            if (proc == null) return (false, "无法启动 shutdown");
            var text = proc.StandardOutput.ReadToEnd() + proc.StandardError.ReadToEnd();
            if (!proc.WaitForExit(20000)) proc.Kill();
            return proc.ExitCode == 0
                ? (true, $"已安排在 {delay} 秒后重启")
                : (false, text.Trim() ?? $"重启命令返回 {proc.ExitCode}");
        }
        catch (Exception ex)
        {
            return (false, ex.Message);
        }
    }

    public static (bool Ok, string Detail) CancelReboot()
    {
        try
        {
            var psi = new ProcessStartInfo("shutdown", "/a")
            {
                CreateNoWindow = true,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
            };
            using var proc = Process.Start(psi);
            if (proc == null) return (false, "无法启动 shutdown");
            proc.StandardOutput.ReadToEnd();
            proc.StandardError.ReadToEnd();
            if (!proc.WaitForExit(15000)) proc.Kill();
            return proc.ExitCode == 0 ? (true, "已取消重启") : (false, "没有待取消的重启");
        }
        catch (Exception ex)
        {
            return (false, ex.Message);
        }
    }
}
