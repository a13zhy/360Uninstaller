using System.Diagnostics;
using System.Runtime.InteropServices;

namespace ResidualCleaner.Maui.Services;

public static class Elevation
{
    [DllImport("shell32.dll")]
    private static extern bool IsUserAnAdmin();

    [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
    private static extern IntPtr ShellExecuteW(IntPtr hwnd, string op, string file, string? args, string? dir, int show);

    public static bool IsAdmin()
    {
        try { return IsUserAnAdmin(); }
        catch { return false; }
    }

    public static bool RelaunchAsAdmin()
    {
        try
        {
            var exe = Environment.ProcessPath ?? "";
            var ptr = ShellExecuteW(IntPtr.Zero, "runas", exe, "", Path.GetDirectoryName(exe), 1);
            return ptr.ToInt64() > 32;
        }
        catch
        {
            return false;
        }
    }

    public static void EnsureAdmin()
    {
        if (IsAdmin()) return;
        if (RelaunchAsAdmin())
        {
            Process.GetCurrentProcess().Kill();
        }
    }
}
