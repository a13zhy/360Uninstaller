using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32;

namespace ResidualCleaner.Maui.Services;

public static class RegistryService
{
    private const int KeyRead = 0x20019;
    private const int KeyWow6464 = 0x0100;
    private const int KeyWow6432 = 0x0200;
    private const int WriteDac = 0x00040000;
    private const int WriteOwner = 0x00080000;
    private const int ReadControl = 0x00020000;
    private const int KeyAllAccess = 0xF003F;
    private const int SeRegistryKey = 4;
    private const int OwnerSecurityInformation = 0x00000001;
    private const int DaclSecurityInformation = 0x00000004;
    private const int TokenAdjustPrivileges = 0x0020;
    private const int TokenQuery = 0x0008;
    private const int SePrivilegeEnabled = 0x0002;
    private const int ErrorSuccess = 0;
    private const int ErrorFileNotFound = 2;
    private const int ErrorAccessDenied = 5;

    private static readonly HashSet<string> ProtectedProcesses = new(StringComparer.OrdinalIgnoreCase)
    {
        "ZhuDongFangYu.exe", "360tray.exe", "360Safe.exe", "QHSafeTray.exe", "360sd.exe",
        "2345Update.exe", "2345Svc.exe",
    };

    private static readonly HashSet<string> ProtectedServices = new(StringComparer.OrdinalIgnoreCase)
    {
        "ZhuDongFangYu", "360SelfProtection", "360AntiHacker", "QHActiveDefense", "360rp", "360rps",
    };

    private static readonly List<string> _protected = new();

    private static readonly Dictionary<string, RegistryKey> Roots = new(StringComparer.OrdinalIgnoreCase)
    {
        ["HKLM"] = Registry.LocalMachine,
        ["HKCU"] = Registry.CurrentUser,
        ["HKCR"] = Registry.ClassesRoot,
        ["HKU"] = Registry.Users,
    };

    private static readonly Dictionary<string, IntPtr> RawRoots = new(StringComparer.OrdinalIgnoreCase)
    {
        ["HKLM"] = unchecked((IntPtr)0x80000002),
        ["HKCU"] = unchecked((IntPtr)0x80000001),
        ["HKCR"] = unchecked((IntPtr)0x80000000),
        ["HKU"] = unchecked((IntPtr)0x80000003),
    };

    private static (RegistryKey Root, string Sub, IntPtr Raw) Split(string path)
    {
        var parts = path.Split('\\', 2);
        var root = parts[0].ToUpperInvariant();
        var sub = parts.Length > 1 ? parts[1] : "";
        return Roots.TryGetValue(root, out var key)
            ? (key, sub, RawRoots[root])
            : (Registry.LocalMachine, sub, RawRoots["HKLM"]);
    }

    private static IEnumerable<RegistryView> Views(string sub)
    {
        if (sub.Contains("wow6432node", StringComparison.OrdinalIgnoreCase))
        {
            yield return RegistryView.Default;
            yield break;
        }
        yield return RegistryView.Registry64;
        yield return RegistryView.Registry32;
    }

    public static bool KeyExists(string path)
    {
        var (root, sub, _) = Split(path);
        foreach (var view in Views(sub))
        {
            try
            {
                using var k = root.OpenSubKey(sub, false);
                if (k != null) return true;
            }
            catch (UnauthorizedAccessException) { return true; }
            catch (System.Security.SecurityException) { return true; }
            catch { }
        }
        return false;
    }

    public static List<string> ListSubkeys(string path)
    {
        var set = new SortedSet<string>(StringComparer.OrdinalIgnoreCase);
        var (root, sub, _) = Split(path);
        foreach (var view in Views(sub))
        {
            try
            {
                using var k = root.OpenSubKey(sub, false);
                if (k == null) continue;
                foreach (var name in k.GetSubKeyNames()) set.Add(name);
            }
            catch { }
        }
        return set.ToList();
    }

    public static Dictionary<string, string> ReadValues(string path)
    {
        var data = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var (root, sub, _) = Split(path);
        foreach (var view in Views(sub))
        {
            try
            {
                using var k = root.OpenSubKey(sub, false);
                if (k == null) continue;
                foreach (var name in k.GetValueNames())
                {
                    var v = k.GetValue(name);
                    if (v != null) data[name] = v.ToString() ?? "";
                }
            }
            catch { }
        }
        return data;
    }

    public static string BackupKey(string path)
    {
        try
        {
            Directory.CreateDirectory(AppPaths.RegBackupDir);
            var safe = path.Replace("\\", "_").Replace(" ", "_");
            var target = Path.Combine(AppPaths.RegBackupDir, $"{safe}_{DateTime.Now:yyyyMMdd_HHmmss}.reg");
            var (code, _) = ProcessService.Run("reg", new[] { "export", path, target, "/y" }, 20);
            return code == 0 && File.Exists(target) ? target : "";
        }
        catch { return ""; }
    }

    public static (bool Ok, string Detail) DeleteKey(string path)
    {
        if (!KeyExists(path)) return (true, "注册表项已不存在（无需清理）");
        var backup = BackupKey(path);
        var note = string.IsNullOrEmpty(backup) ? "" : $"（已备份 {Path.GetFileName(backup)}）";

        var (code, output) = ProcessService.Run("reg", new[] { "delete", path, "/f" }, 20);
        if (code == 0) return (true, "已删除" + note);
        var low = output.ToLowerInvariant();
        if (output.Contains("找不到") || low.Contains("unable to find")) return (true, "注册表项已不存在（无需清理）");

        var (_, sub, raw) = Split(path);
        foreach (var view in Views(sub))
        {
            if (NativeDelete(raw, sub, view)) return (true, "已接管权限后删除" + note);
        }

        if (IsProtectedNow())
        {
            lock (_protected) _protected.Add(path);
            return (false, ProtectedMessage());
        }
        return (false, "权限接管后仍被拒绝（该键可能由系统策略或第三方驱动保护）");
    }

    public static (bool Ok, string Detail) DeleteValue(string path, string name)
    {
        var (root, sub, _) = Split(path);
        foreach (var view in Views(sub))
        {
            try
            {
                using var k = root.OpenSubKey(sub, true);
                if (k == null) continue;
                if (k.GetValue(name) == null) continue;
                k.DeleteValue(name, false);
                return (true, "已删除启动项");
            }
            catch { }
        }
        return (true, "启动项已不存在");
    }

    public static List<string> ConsumeProtected()
    {
        lock (_protected)
        {
            var items = new List<string>(_protected);
            _protected.Clear();
            return items;
        }
    }

    public static List<string> ProtectionRunning()
    {
        var hits = new SortedSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var p in Process.GetProcesses())
        {
            try
            {
                if (ProtectedProcesses.Contains(p.ProcessName + ".exe")) hits.Add(p.ProcessName + ".exe");
            }
            catch { }
        }
        try
        {
            foreach (var svc in ProtectedServices)
            {
                var (code, output) = ProcessService.Run("sc", new[] { "query", svc });
                if (code == 0 && output.Contains("RUNNING", StringComparison.OrdinalIgnoreCase))
                    hits.Add(svc);
            }
        }
        catch { }
        return hits.ToList();
    }

    public static bool SafeModeActive()
    {
        try { return GetSystemMetrics(67) is 1 or 2; }
        catch { return false; }
    }

    private static bool IsProtectedNow() => ProtectionRunning().Count > 0 && !SafeModeActive();

    private static string ProtectedMessage()
    {
        var comps = ProtectionRunning();
        var detail = comps.Count > 0 ? string.Join("、", comps.Take(4)) : "软件自我保护";
        if (SafeModeActive()) return "仍被拦截（安全模式下异常，请检查驱动是否被残留服务重新加载）";
        return $"被软件自我保护拦截（{detail} 运行中），在线无法删除：请关闭自我保护，或用生成的安全模式清理包删除";
    }

    public static string BuildSafeModePack(IEnumerable<string> paths)
    {
        var unique = paths.Where(p => !string.IsNullOrEmpty(p)).Distinct(StringComparer.OrdinalIgnoreCase).ToList();
        if (unique.Count == 0) return "";
        try
        {
            Directory.CreateDirectory(AppPaths.SafeModeDir);
            var stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            var cmdPath = Path.Combine(AppPaths.SafeModeDir, $"安全模式清理_{stamp}.cmd");
            var txtPath = Path.Combine(AppPaths.SafeModeDir, $"待清理清单_{stamp}.txt");

            var lines = new List<string>
            {
                "@echo off", "chcp 65001 >nul", "title 残留清理卫士 - 安全模式清理",
                "echo 正在删除残留注册表项（仅删除下列清单中的项目）...", "echo.",
            };
            foreach (var path in unique)
            {
                lines.Add($"reg delete \"{path}\" /f >nul 2>&1");
                lines.Add($"echo   已处理 {path}");
            }
            lines.AddRange(new[] { "echo.", "echo 清理完成。按任意键退出。", "pause >nul", "" });
            File.WriteAllLines(cmdPath, lines, new UTF8Encoding(true));

            var txt = new List<string> { "以下注册表项因软件自我保护在线无法删除，需在安全模式清理：", "" };
            txt.AddRange(unique);
            txt.Add("");
            txt.Add("使用方法：重启 → 开机时按住 Shift 或 msconfig 选择安全模式 → 以管理员身份运行同目录下的 .cmd 文件。");
            File.WriteAllLines(txtPath, txt);
            return cmdPath;
        }
        catch { return ""; }
    }

    private static bool NativeDelete(IntPtr hkey, string sub, RegistryView view)
    {
        EnablePrivileges("SeTakeOwnershipPrivilege", "SeRestorePrivilege", "SeBackupPrivilege", "SeSecurityPrivilege");
        HardenKey(hkey, sub, view, 0);
        var viewFlag = view == RegistryView.Registry32 ? KeyWow6432 : KeyWow6464;
        var rc = RegDeleteTreeW(hkey, sub);
        if (rc is not (ErrorSuccess or ErrorFileNotFound)) return false;
        rc = RegDeleteKeyExW(hkey, sub, viewFlag, 0);
        return rc is ErrorSuccess or ErrorFileNotFound;
    }

    private static void HardenKey(IntPtr hkey, string sub, RegistryView view, int depth)
    {
        if (depth > 8) return;
        var viewFlag = view == RegistryView.Registry32 ? KeyWow6432 : KeyWow6464;

        var h = OpenRaw(hkey, sub, WriteOwner | ReadControl, viewFlag);
        if (h != IntPtr.Zero)
        {
            try { SetSecurityInfo(h, SeRegistryKey, OwnerSecurityInformation, AdminSid(), IntPtr.Zero, IntPtr.Zero, IntPtr.Zero); }
            finally { RegCloseKey(h); }
        }

        h = OpenRaw(hkey, sub, WriteDac | ReadControl, viewFlag);
        bool granted = false;
        if (h != IntPtr.Zero)
        {
            try { granted = GrantAdminDacl(h, AdminSid()); }
            finally { RegCloseKey(h); }
        }
        if (!granted) return;

        foreach (var child in EnumChildren(hkey, sub, viewFlag))
            HardenKey(hkey, sub + "\\" + child, view, depth + 1);
    }

    private static IntPtr OpenRaw(IntPtr hkey, string sub, int access, int view)
    {
        var handle = IntPtr.Zero;
        var rc = RegOpenKeyExW(hkey, sub, 0, access | view, ref handle);
        return rc == ErrorSuccess ? handle : IntPtr.Zero;
    }

    private static List<string> EnumChildren(IntPtr hkey, string sub, int view)
    {
        var result = new List<string>();
        var h = OpenRaw(hkey, sub, KeyRead, view);
        if (h == IntPtr.Zero) return result;
        try
        {
            var i = 0;
            var buffer = new char[512];
            while (true)
            {
                var size = (uint)buffer.Length;
                var rc = RegEnumKeyExW(h, i, buffer, ref size, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero);
                if (rc != ErrorSuccess) break;
                result.Add(new string(buffer, 0, (int)size));
                i++;
            }
        }
        finally { RegCloseKey(h); }
        return result;
    }

    private static IntPtr AdminSid()
    {
        ConvertStringSidToSidW("S-1-5-32-544", out var sid);
        return sid;
    }

    private static bool GrantAdminDacl(IntPtr handle, IntPtr sid)
    {
        var acl = new byte[1024];
        if (!InitializeAcl(acl, (uint)acl.Length, 2)) return false;
        if (!AddAccessAllowedAce(acl, 2, KeyAllAccess, sid)) return false;
        var pinned = GCHandle.Alloc(acl, GCHandleType.Pinned);
        try
        {
            return SetSecurityInfo(handle, SeRegistryKey, DaclSecurityInformation, IntPtr.Zero, IntPtr.Zero, pinned.AddrOfPinnedObject(), IntPtr.Zero) == ErrorSuccess;
        }
        finally { pinned.Free(); }
    }

    private static void EnablePrivileges(params string[] names)
    {
        try
        {
            var token = IntPtr.Zero;
            if (!OpenProcessToken(GetCurrentProcess(), TokenAdjustPrivileges | TokenQuery, ref token)) return;
            foreach (var name in names)
            {
                var luid = new LUID();
                if (!LookupPrivilegeValueW(IntPtr.Zero, name, ref luid)) continue;
                var privs = new TOKEN_PRIVILEGES
                {
                    PrivilegeCount = 1,
                    Privileges = new LUID_AND_ATTRIBUTES[1],
                };
                privs.Privileges[0].Luid = luid;
                privs.Privileges[0].Attributes = SePrivilegeEnabled;
                AdjustTokenPrivileges(token, false, ref privs, 0, IntPtr.Zero, IntPtr.Zero);
            }
            CloseHandle(token);
        }
        catch { }
    }

    [DllImport("advapi32", CharSet = CharSet.Unicode)]
    private static extern int RegOpenKeyExW(IntPtr hKey, string subKey, uint options, int access, ref IntPtr result);
    [DllImport("advapi32")] private static extern int RegCloseKey(IntPtr hKey);
    [DllImport("advapi32", CharSet = CharSet.Unicode)]
    private static extern int RegEnumKeyExW(IntPtr hKey, int index, char[] name, ref uint size, IntPtr reserved, IntPtr cls, IntPtr clsSize, IntPtr lastWrite);
    [DllImport("advapi32", CharSet = CharSet.Unicode)] private static extern int RegDeleteTreeW(IntPtr hKey, string subKey);
    [DllImport("advapi32", CharSet = CharSet.Unicode)] private static extern int RegDeleteKeyExW(IntPtr hKey, string subKey, int view, int reserved);
    [DllImport("advapi32")] private static extern bool OpenProcessToken(IntPtr process, int access, ref IntPtr token);
    [DllImport("advapi32", CharSet = CharSet.Unicode)] private static extern bool LookupPrivilegeValueW(IntPtr system, string name, ref LUID luid);
    [DllImport("advapi32")] private static extern bool AdjustTokenPrivileges(IntPtr token, bool disableAll, ref TOKEN_PRIVILEGES buffer, int length, IntPtr prev, IntPtr returnLen);
    [DllImport("advapi32", CharSet = CharSet.Unicode)] private static extern bool ConvertStringSidToSidW(string sid, out IntPtr sidPtr);
    [DllImport("advapi32")] private static extern int SetSecurityInfo(IntPtr handle, int objectType, int securityInfo, IntPtr owner, IntPtr group, IntPtr dacl, IntPtr sacl);
    [DllImport("advapi32")] private static extern bool InitializeAcl(byte[] acl, uint size, int revision);
    [DllImport("advapi32")] private static extern bool AddAccessAllowedAce(byte[] acl, int revision, int access, IntPtr sid);
    [DllImport("kernel32")] private static extern IntPtr GetCurrentProcess();
    [DllImport("kernel32")] private static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32")] private static extern bool LocalFree(IntPtr mem);
    [DllImport("user32")] private static extern int GetSystemMetrics(int index);

    [StructLayout(LayoutKind.Sequential)]
    private struct LUID { public uint LowPart; public int HighPart; }
    [StructLayout(LayoutKind.Sequential)]
    private struct LUID_AND_ATTRIBUTES { public LUID Luid; public uint Attributes; }
    [StructLayout(LayoutKind.Sequential)]
    private struct TOKEN_PRIVILEGES { public uint PrivilegeCount; [MarshalAs(UnmanagedType.ByValArray, SizeConst = 1)] public LUID_AND_ATTRIBUTES[] Privileges; }
}
