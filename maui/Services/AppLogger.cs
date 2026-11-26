using System.IO;

namespace ResidualCleaner.Maui.Services;

public sealed class AppLogger
{
    public event Action<string>? OnLog;

    public void Log(string message)
    {
        var line = $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] {message}";
        OnLog?.Invoke(line);
        try
        {
            Directory.CreateDirectory(AppPaths.LogDir);
            File.AppendAllText(AppPaths.LogFile, line + Environment.NewLine);
        }
        catch { }
    }
}
