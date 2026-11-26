using System.Runtime.InteropServices;
using System.Text;

namespace ResidualCleaner.Maui.Services;

public sealed class TrayService : IDisposable
{
    private const int NIM_ADD = 0;
    private const int NIM_MODIFY = 1;
    private const int NIM_DELETE = 2;
    private const int NIF_ICON = 0x02;
    private const int NIF_MESSAGE = 0x01;
    private const int NIF_TIP = 0x04;
    private const int NIF_INFO = 0x10;
    private const int WmTray = 0x8000 + 1;
    private const int WmLButtonUp = 0x0202;
    private const int WmRButtonUp = 0x0205;
    private const int MenuShow = 1001;
    private const int MenuScan = 1002;
    private const int MenuUpdate = 1003;
    private const int MenuQuit = 1004;
    private const int MenuPatrol = 1005;
    private const int MenuBoot = 1006;
    private const uint MfChecked = 0x08;
    private const uint MfUnchecked = 0x00;
    private const int TpmReturnCmd = 0x0100;
    private const int HwndMessage = -3;
    private const uint ImageIcon = 1;
    private const uint LoadFromFile = 0x10;

    public event Action? ShowRequested;
    public event Action? ScanRequested;
    public event Action? PatrolRequested;
    public event Action<bool>? BootToggleRequested;
    public event Action? UpdateRequested;
    public event Action? QuitRequested;

    private static TrayService? _instance;
    private IntPtr _hwnd;
    private IntPtr _hIcon;
    private bool _registered;
    private bool _bootChecked;
    private readonly WndProcDelegate _wndProc;
    private readonly string _className = "ResidualCleanerTrayWindow";

    public TrayService()
    {
        _instance = this;
        _wndProc = StaticWndProc;
    }

    public void Start()
    {
        var hInstance = GetModuleHandleW(null);
        var wc = new WNDCLASS
        {
            style = 0,
            lpfnWndProc = Marshal.GetFunctionPointerForDelegate(_wndProc),
            cbClsExtra = 0,
            cbWndExtra = 0,
            hInstance = hInstance,
            hIcon = IntPtr.Zero,
            hCursor = IntPtr.Zero,
            hbrBackground = IntPtr.Zero,
            lpszMenuName = null,
            lpszClassName = _className,
        };
        RegisterClassExW(ref wc);

        _hwnd = CreateWindowExW(0, _className, "ResidualCleanerTray", 0, 0, 0, 0, 0,
            (IntPtr)HwndMessage, IntPtr.Zero, hInstance, IntPtr.Zero);

        var iconPath = Path.Combine(AppContext.BaseDirectory, "Assets", "app_icon.ico");
        if (File.Exists(iconPath))
            _hIcon = LoadImageW(IntPtr.Zero, iconPath, ImageIcon, 0, 0, LoadFromFile);

        var data = new NotifyIconData
        {
            cbSize = (uint)Marshal.SizeOf<NotifyIconData>(),
            hWnd = _hwnd,
            uID = 1,
            uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP,
            uCallbackMessage = WmTray,
            hIcon = _hIcon,
            szTip = $"{AppPaths.AppName} {AppPaths.AppVersion}",
        };
        _registered = ShellNotifyIconW(NIM_ADD, ref data);
    }

    public void Notify(string title, string message)
    {
        if (!_registered) return;
        var data = new NotifyIconData
        {
            cbSize = (uint)Marshal.SizeOf<NotifyIconData>(),
            hWnd = _hwnd,
            uID = 1,
            uFlags = NIF_INFO,
            szInfoTitle = title,
            szInfo = message,
            dwInfoFlags = 0,
        };
        ShellNotifyIconW(NIM_MODIFY, ref data);
    }

    private IntPtr OnWndProc(IntPtr hwnd, uint msg, IntPtr wParam, IntPtr lParam)
    {
        if (msg != WmTray) return DefWindowProcW(hwnd, msg, wParam, lParam);
        var mouse = lParam.ToInt32() & 0xFFFF;
        if (mouse == WmLButtonUp)
        {
            ShowRequested?.Invoke();
        }
        else if (mouse == WmRButtonUp)
        {
            var menu = CreatePopupMenu();
            AppendMenuW(menu, 0, MenuShow, "显示主窗口");
            AppendMenuW(menu, 0, MenuScan, "重新扫描");
            AppendMenuW(menu, 0, MenuPatrol, "立即巡检残余");
            AppendMenuW(menu, _bootChecked ? MfChecked : MfUnchecked, MenuBoot, "开机自动巡检");
            AppendMenuW(menu, 0x10, 0, "");
            AppendMenuW(menu, 0, MenuUpdate, "检查更新");
            AppendMenuW(menu, 0x10, 0, "");
            AppendMenuW(menu, 0, MenuQuit, "退出");
            GetCursorPos(out var pt);
            var cmd = TrackPopupMenuEx(menu, TpmReturnCmd, pt.X, pt.Y, hwnd, IntPtr.Zero);
            DestroyMenu(menu);
            switch (cmd)
            {
                case MenuShow: ShowRequested?.Invoke(); break;
                case MenuScan: ScanRequested?.Invoke(); break;
                case MenuPatrol: PatrolRequested?.Invoke(); break;
                case MenuBoot:
                    _bootChecked = !_bootChecked;
                    BootToggleRequested?.Invoke(_bootChecked);
                    break;
                case MenuUpdate: UpdateRequested?.Invoke(); break;
                case MenuQuit: QuitRequested?.Invoke(); break;
            }
        }
        return IntPtr.Zero;
    }

    public void SetBootState(bool enabled) => _bootChecked = enabled;

    private static IntPtr StaticWndProc(IntPtr hwnd, uint msg, IntPtr wParam, IntPtr lParam)
        => _instance?.OnWndProc(hwnd, msg, wParam, lParam) ?? DefWindowProcW(hwnd, msg, wParam, lParam);

    public void Dispose()
    {
        if (_registered)
        {
            var data = new NotifyIconData { cbSize = (uint)Marshal.SizeOf<NotifyIconData>(), hWnd = _hwnd, uID = 1 };
            ShellNotifyIconW(NIM_DELETE, ref data);
        }
        if (_hIcon != IntPtr.Zero) DestroyIcon(_hIcon);
        if (_hwnd != IntPtr.Zero) DestroyWindow(_hwnd);
        _registered = false;
    }

    [DllImport("user32")] private static extern IntPtr DefWindowProcW(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);
    [DllImport("user32", CharSet = CharSet.Unicode)] private static extern ushort RegisterClassExW(ref WNDCLASS lpwcx);
    [DllImport("user32", CharSet = CharSet.Unicode)] private static extern IntPtr CreateWindowExW(uint exStyle, string className, string windowName, uint style, int x, int y, int width, int height, IntPtr parent, IntPtr menu, IntPtr instance, IntPtr param);
    [DllImport("user32")] private static extern bool DestroyWindow(IntPtr hWnd);
    [DllImport("user32", CharSet = CharSet.Unicode)] private static extern IntPtr LoadImageW(IntPtr instance, string name, uint type, int cx, int cy, uint load);
    [DllImport("user32")] private static extern bool DestroyIcon(IntPtr hIcon);
    [DllImport("shell32", CharSet = CharSet.Unicode, EntryPoint = "Shell_NotifyIconW")] private static extern bool ShellNotifyIconW(uint dwMessage, ref NotifyIconData data);
    [DllImport("user32")] private static extern IntPtr CreatePopupMenu();
    [DllImport("user32", CharSet = CharSet.Unicode)] private static extern bool AppendMenuW(IntPtr menu, uint flags, uint id, string text);
    [DllImport("user32")] private static extern bool DestroyMenu(IntPtr menu);
    [DllImport("user32")] private static extern bool GetCursorPos(out POINT pt);
    [DllImport("user32")] private static extern int TrackPopupMenuEx(IntPtr menu, uint flags, int x, int y, IntPtr hwnd, IntPtr rect);
    [DllImport("kernel32", CharSet = CharSet.Unicode)] private static extern IntPtr GetModuleHandleW(string? module);

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct WNDCLASS
    {
        public uint style;
        public IntPtr lpfnWndProc;
        public int cbClsExtra;
        public int cbWndExtra;
        public IntPtr hInstance;
        public IntPtr hIcon;
        public IntPtr hCursor;
        public IntPtr hbrBackground;
        public string? lpszMenuName;
        public string lpszClassName;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct POINT { public int X; public int Y; }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct NotifyIconData
    {
        public uint cbSize;
        public IntPtr hWnd;
        public uint uID;
        public uint uFlags;
        public uint uCallbackMessage;
        public IntPtr hIcon;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string szTip;
        public uint dwState;
        public uint dwStateMask;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 256)] public string szInfo;
        public uint uTimeoutOrVersion;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 64)] public string szInfoTitle;
        public uint dwInfoFlags;
        public Guid guidItem;
        public IntPtr hBalloonIcon;
    }

    [UnmanagedFunctionPointer(CallingConvention.Winapi)]
    private delegate IntPtr WndProcDelegate(IntPtr hwnd, uint msg, IntPtr wParam, IntPtr lParam);
}
