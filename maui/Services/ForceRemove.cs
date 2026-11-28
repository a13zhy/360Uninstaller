using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32;

namespace ResidualCleaner.Maui.Services;

public static class ForceRemove
{
    private const int FileAttributeNormal = 0x80;
    private const int MoveFileDelayUntilReboot = 0x4;
    private const int ErrorFileNotFound = 2;
    private const int ErrorPathNotFound = 3;
    private const int ErrorAccessDenied = 5;
    private const int ErrorSharingViolation = 32;
    private const int ErrorLockViolation = 33;
    private const int ErrorDeletePending = 303;

    private const string PendingRegPath = @"SYSTEM\CurrentControlSet\Control\Session Manager";
    private const string PendingValue = "PendingFileRenameOperations";

    public static bool IsAdmin()
    {
        try { return Shell32IsUserAnAdmin(); }
        catch { return false; }
    }

    public static string NtPath(string path)
    {
        var full = Path.GetFullPath(path);
        if (full.StartsWith("\\\\?\\")) return full;
        if (full.StartsWith("\\\\")) return "\\\\?\\UNC\\" + full.TrimStart('\\');
        return "\\\\?\\" + full;
    }

    public static bool ClearAttributes(string path)
    {
        try { return SetFileAttributesW(NtPath(path), FileAttributeNormal); }
        catch { return false; }
    }

    public static List<(int Pid, string Name)> FindHolders(string path)
    {
        var result = new List<(int, string)>();
        string[] targets;
        if (Directory.Exists(path))
        {
            targets = EnumerateFiles(path, 300).ToArray();
        }
        else if (File.Exists(path))
        {
            targets = new[] { path };
        }
        else return result;
        if (targets.Length == 0) return result;

        uint session = 0;
        var key = new StringBuilder(256);
        try
        {
            if (RmStartSession(out session, 0, key.ToString()) != 0) return result;
            if (RmRegisterResources(session, (uint)targets.Length, targets, 0, IntPtr.Zero, 0, IntPtr.Zero) != 0) return result;

            uint needed = 0, count = 0, reason = 0;
            var rc = RmGetList(session, ref needed, ref count, null, ref reason);
            if (rc != 234 || needed == 0) return result;

            var buffer = new RM_PROCESS_INFO[needed];
            count = needed;
            rc = RmGetList(session, ref needed, ref count, buffer, ref reason);
            if (rc != 0) return result;

            for (var i = 0; i < count; i++)
            {
                var pid = (int)buffer[i].Process.dwProcessId;
                if (pid <= 0) continue;
                var name = string.IsNullOrWhiteSpace(buffer[i].strAppName) ? ProcessImage(pid) : buffer[i].strAppName;
                result.Add((pid, name));
            }
        }
        catch { }
        finally
        {
            if (session != 0) try { RmEndSession(session); } catch { }
        }
        return result;
    }

    public static (List<int> Killed, List<string> Others) ReleaseHolders(string path, Action<string>? log)
    {
        var killed = new List<int>();
        var others = new List<string>();
        foreach (var (pid, name) in FindHolders(path))
        {
            var image = ProcessImage(pid).IfEmpty(name);
            var low = image.ToLowerInvariant();
            var isTarget = low.Contains("360") || low.Contains("qhsafe") || low.Contains("qihu")
                        || low.Contains("2345") || low.Contains("haozip") || low.Contains("pcsafe") || low.Contains("safehelper");
            if (!isTarget)
            {
                others.Add(Path.GetFileName(image) ?? $"PID {pid}");
                continue;
            }
            try
            {
                var handle = OpenProcess(0x0001, false, pid);
                if (handle != IntPtr.Zero)
                {
                    TerminateProcess(handle, 1);
                    CloseHandle(handle);
                }
            }
            catch { }
            ProcessService.Run("taskkill", new[] { "/F", "/PID", pid.ToString(), "/T" }, 20);
            killed.Add(pid);
            log?.Invoke($"  结束占用进程 {Path.GetFileName(image) ?? pid.ToString()}（PID {pid}）");
        }
        return (killed, others);
    }

    public static void TakeOwnership(string path, Action<string>? log)
    {
        var nt = NtPath(path);
        var steps = new (string[] Cmd, string Label)[]
        {
            (new[] { "icacls", nt, "/reset", "/t", "/c", "/q" }, "重置访问控制列表"),
            (new[] { "icacls", nt, "/inheritance:e", "/t", "/c", "/q" }, "恢复权限继承"),
            (new[] { "icacls", nt, "/setowner", "*S-1-5-32-544", "/t", "/c", "/q" }, "设置所有者为管理员组"),
            (new[] { "takeown", "/f", nt, "/r", "/a", "/d", "y" }, "接管文件所有权"),
            (new[] { "icacls", nt, "/grant", "*S-1-5-32-544:(OI)(CI)F", "/t", "/c", "/q" }, "授予管理员组完全控制"),
        };
        foreach (var (cmd, label) in steps)
        {
            var (code, output) = ProcessService.Run(cmd[0], cmd[1..], 180);
            log?.Invoke($"  {label}：{(code == 0 ? "完成" : "跳过")}");
            if (code != 0 && output.Contains("拒绝") && output.ToLowerInvariant().Contains("denied")) continue;
        }
    }

    public static bool DeleteTree(string root, List<string> failed, List<long> freed)
    {
        Walk(root, failed, freed);
        return !Directory.Exists(root);
    }

    private static void Walk(string dir, List<string> failed, List<long> freed)
    {
        string[] entries;
        try { entries = Directory.GetFileSystemEntries(dir); }
        catch
        {
            if (!Directory.Exists(dir)) return;
            failed.Add(dir);
            return;
        }
        foreach (var entry in entries)
        {
            try
            {
                if (Directory.Exists(entry) && !IsSymlink(entry))
                {
                    Walk(entry, failed, freed);
                    continue;
                }
                long size = 0;
                try { size = new FileInfo(entry).Length; } catch { }
                ClearAttributes(entry);
                File.Delete(entry);
                freed[0] += Math.Max(0, size);
            }
            catch
            {
                try
                {
                    ClearAttributes(entry);
                    Directory.Delete(entry, false);
                }
                catch { failed.Add(entry); }
            }
        }
        try
        {
            ClearAttributes(dir);
            Directory.Delete(dir, false);
        }
        catch
        {
            if (Directory.Exists(dir)) failed.Add(dir);
        }
    }

    public static (int Scheduled, bool AnyOk) ScheduleDeleteOnReboot(List<string> paths, Action<string>? log)
    {
        if (!IsAdmin())
        {
            log?.Invoke("  当前不是管理员，无法登记重启后删除");
            return (0, false);
        }
        var ordered = new List<string>();
        foreach (var p in paths)
        {
            if (Directory.Exists(p) && !IsSymlink(p))
            {
                foreach (var f in EnumerateFiles(p, int.MaxValue)) ordered.Add(f);
                ordered.Add(p);
            }
            else ordered.Add(p);
        }
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var count = 0;
        var anyOk = false;
        foreach (var p in ordered)
        {
            if (!seen.Add(Path.GetFullPath(p).TrimEnd('\\').ToLowerInvariant())) continue;
            var ok = MoveFileExW(NtPath(p), null, MoveFileDelayUntilReboot);
            if (ok) { count++; anyOk = true; }
        }
        if (anyOk) log?.Invoke($"  已登记 {count} 项在下次开机时由系统删除");
        return (count, anyOk);
    }

    public static List<string> PendingDeleteEntries()
    {
        var result = new List<string>();
        try
        {
            using var k = Registry.LocalMachine.OpenSubKey(PendingRegPath);
            var values = k?.GetValue(PendingValue) as string[];
            if (values == null) return result;
            for (var i = 0; i + 1 < values.Length; i += 2)
            {
                if (string.IsNullOrEmpty(values[i + 1]))
                    result.Add(values[i].TrimStart('\\', '?'));
            }
        }
        catch { }
        return result;
    }

    public static string ErrorText(Exception? ex)
    {
        var code = ex?.HResult is int h ? h & 0xFFFF : 0;
        return code switch
        {
            ErrorAccessDenied => "拒绝访问（ACL 或系统保护）",
            ErrorSharingViolation or ErrorLockViolation => "文件正在使用",
            ErrorDeletePending => "已标记删除，等待句柄释放",
            13 => "拒绝访问或被程序占用",
            _ => code != 0 ? $"错误码 {code}" : "删除失败",
        };
    }

    private static IEnumerable<string> EnumerateFiles(string root, int limit)
    {
        var stack = new Stack<string>();
        stack.Push(root);
        var n = 0;
        while (stack.Count > 0 && n < limit)
        {
            var dir = stack.Pop();
            string[] files;
            string[] subdirs;
            try
            {
                files = Directory.GetFiles(dir);
                subdirs = Directory.GetDirectories(dir);
            }
            catch { continue; }
            foreach (var f in files) { yield return f; if (++n >= limit) yield break; }
            foreach (var d in subdirs) stack.Push(d);
        }
    }

    private static bool IsSymlink(string path)
    {
        try { return (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0; }
        catch { return false; }
    }

    private static string ProcessImage(int pid)
    {
        try
        {
            var handle = OpenProcess(0x1000, false, pid);
            if (handle == IntPtr.Zero) return "";
            try
            {
                var buffer = new char[1024];
                var size = (uint)buffer.Length;
                return QueryFullProcessImageNameW(handle, 0, buffer, ref size) ? new string(buffer, 0, (int)size) : "";
            }
            finally { CloseHandle(handle); }
        }
        catch { return ""; }
    }

    [DllImport("shell32", EntryPoint = "IsUserAnAdmin")] private static extern bool Shell32IsUserAnAdmin();
    [DllImport("kernel32", CharSet = CharSet.Unicode)] private static extern bool SetFileAttributesW(string path, int attrs);
    [DllImport("kernel32", CharSet = CharSet.Unicode)] private static extern bool MoveFileExW(string existing, string? newPath, int flags);
    [DllImport("kernel32")] private static extern IntPtr OpenProcess(int access, bool inherit, int pid);
    [DllImport("kernel32")] private static extern bool TerminateProcess(IntPtr handle, int exitCode);
    [DllImport("kernel32")] private static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32", CharSet = CharSet.Unicode)] private static extern bool QueryFullProcessImageNameW(IntPtr process, int flags, char[] buffer, ref uint size);

    [DllImport("rstrtmgr")] private static extern int RmStartSession(out uint session, int flags, string key);
    [DllImport("rstrtmgr", CharSet = CharSet.Unicode)]
    private static extern int RmRegisterResources(uint session, uint nFiles, string[] files, uint nAppInfos, IntPtr appInfos, uint nServices, IntPtr services);
    [DllImport("rstrtmgr")] private static extern int RmGetList(uint session, ref uint nProcInfoNeeded, ref uint nProcInfo, [Out] RM_PROCESS_INFO[]? info, ref uint reason);
    [DllImport("rstrtmgr")] private static extern int RmEndSession(uint session);

    [StructLayout(LayoutKind.Sequential)]
    private struct FILETIME
    {
        public uint dwLowDateTime;
        public uint dwHighDateTime;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct RM_UNIQUE_PROCESS
    {
        public uint dwProcessId;
        public FILETIME ProcessStartTime;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct RM_PROCESS_INFO
    {
        public RM_UNIQUE_PROCESS Process;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 256)] public string strAppName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 64)] public string strServiceShortName;
        public int ApplicationType;
        public uint AppStatus;
        public uint bRestartable;
        public uint tail;
    }
}

internal static class StringExtensions
{
    public static string IfEmpty(this string value, string fallback) =>
        string.IsNullOrWhiteSpace(value) ? fallback : value;
}
