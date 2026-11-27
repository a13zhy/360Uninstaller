using System.Collections.ObjectModel;
using System.IO;
using Microsoft.Maui.Controls;
using Microsoft.Maui.Dispatching;
using Microsoft.Maui.Graphics;
using ResidualCleaner.Maui.Data;
using ResidualCleaner.Maui.Models;
using ResidualCleaner.Maui.Services;
using ResidualCleaner.Maui.ViewModels;

namespace ResidualCleaner.Maui;

public partial class MainPage : ContentPage
{
    private readonly ObservableCollection<AppRowViewModel> _rows = new();
    private readonly ObservableCollection<ResidualRowViewModel> _residualRows = new();
    private readonly Dictionary<string, List<CleanItem>> _itemsByApp = new(StringComparer.OrdinalIgnoreCase);
    private readonly List<CleanItem> _commonItems = new();
    private readonly AppLogger _logger = new();
    private WorkerService? _worker;
    private WorkerResult? _lastResult;
    private bool _bootSyncing;
    private bool _bundleMode;
    private bool _scanned;
    private IDispatcherTimer? _rebootTimer;
    private int _rebootLeft;

    public MainPage()
    {
        InitializeComponent();
        AppList.ItemsSource = _rows;
        ResidualList.ItemsSource = _residualRows;
        ApplyNavState(NavClean, true);
        ApplyNavState(NavBundle, false);
        ApplyNavState(NavAbout, false);

        _logger.OnLog += AppendLog;
        _logger.Log("残留清理卫士已启动，正在请求管理员权限…");

        VersionText.Text = $"v{AppPaths.AppVersion}";
        AboutVersion.Text = $"版本 {AppPaths.AppVersion}";
        AboutLogDir.Text = $"日志目录：{AppPaths.LogDir}";
        FooterLog.Text = $"日志：{AppPaths.LogFile}";

        RefreshBootState();
        UpdateSelectedCount();
        ApplyModeState();
    }

    protected override async void OnAppearing()
    {
        base.OnAppearing();
        if (_scanned) return;
        _scanned = true;
        await StartScanAsync();
    }

    private void OnNavClick(object? sender, EventArgs e)
    {
        var tag = (sender as Button)?.CommandParameter?.ToString() ?? "Clean";
        CleanPanel.IsVisible = tag == "Clean";
        BundlePanel.IsVisible = tag == "Bundle";
        AboutPanel.IsVisible = tag == "About";

        ApplyNavState(NavClean, tag == "Clean");
        ApplyNavState(NavBundle, tag == "Bundle");
        ApplyNavState(NavAbout, tag == "About");
    }

    private static Brush B(string key) => (Brush)Application.Current!.Resources[key];
    private static Color C(string key) => (Color)Application.Current!.Resources[key];

    private void ApplyNavState(Button btn, bool active)
    {
        btn.BackgroundColor = active ? C("AppCardColor") : C("AppBackgroundColor");
        btn.TextColor = active ? C("AppAccentColor") : C("AppTextSubColor");
    }

    private void RefreshBootState()
    {
        _bootSyncing = true;
        var enabled = BootGuard.IsEnabled();
        BootRegister.IsChecked = enabled;
        BootStateText.Text = enabled ? "计划任务优先，失败退回注册表启动项" : "未开启（计划任务优先，失败退回注册表启动项）";
        BootCardTitle.Text = BootGuard.StateText();
        _bootSyncing = false;
    }

    private void OnBootToggle(object? sender, CheckedChangedEventArgs e)
    {
        if (_bootSyncing) return;
        var enable = BootRegister.IsChecked;
        var (ok, detail) = BootGuard.SyncState(enable);
        BootStateText.Text = detail;
        BootCardTitle.Text = BootGuard.StateText();
        if (!ok)
        {
            _bootSyncing = true;
            BootRegister.IsChecked = BootGuard.IsEnabled();
            _bootSyncing = false;
        }
    }

    private void OnPatrolClick(object? sender, EventArgs e) => _ = StartResidualAsync();

    private void OnRescanClick(object? sender, EventArgs e) => _ = StartScanAsync();

    private async Task StartScanAsync()
    {
        _worker = new WorkerService();
        Wire(_worker);
        TechBadgeText.Text = "运行中";
        TechState.Text = "正在扫描本机…";
        StatusText.Text = "正在扫描本机…";
        await _worker.RunAsync(WorkerMode.Scan);
    }

    private async Task StartResidualAsync()
    {
        _worker = new WorkerService();
        Wire(_worker);
        TechBadgeText.Text = "运行中";
        StatusText.Text = "正在巡检本机残留…";
        await _worker.RunAsync(WorkerMode.Residual, new WorkerPayload { Deep = true });
    }

    private void Wire(WorkerService worker)
    {
        worker.OnLog += msg => Dispatcher.Dispatch(() => AppendLog(msg));
        worker.OnProgress += (_, msg) => Dispatcher.Dispatch(() =>
        {
            TechState.Text = msg;
            StatusText.Text = msg;
        });
        worker.OnCompleted += result => Dispatcher.Dispatch(() => OnCompleted(result));
    }

    private void OnCompleted(WorkerResult result)
    {
        _lastResult = result;
        TechBadgeText.Text = "待命";
        if (result.Mode == WorkerMode.Scan)
            OnScanCompleted(result);
        else if (result.Mode == WorkerMode.Residual)
        {
            StatusText.Text = result.Items == null ? "巡检失败：" + result.Error : $"巡检完成：{result.Items.Count} 个残留项。";
            RenderSolutions(result);
        }
        else if (result.Mode == WorkerMode.Clean)
        {
            ApplyResidualResult(result);
            RenderSolutions(result);
        }
        else
            RenderSolutions(result);
    }

    private void OnScanCompleted(WorkerResult result)
    {
        if (!string.IsNullOrEmpty(result.Error))
        {
            TechState.Text = "扫描失败";
            StatusText.Text = "扫描失败：" + result.Error;
            return;
        }

        _rows.Clear();
        _itemsByApp.Clear();
        _commonItems.Clear();

        if (result.Items != null)
        {
            foreach (var item in result.Items)
            {
                if (string.IsNullOrEmpty(item.AppKey))
                {
                    _commonItems.Add(item);
                }
                else if (!_itemsByApp.TryGetValue(item.AppKey, out var list))
                {
                    _itemsByApp[item.AppKey] = new List<CleanItem> { item };
                }
                else
                {
                    list.Add(item);
                }
            }
        }

        var running = 0;
        if (result.Status != null)
        {
            foreach (var (key, status) in result.Status)
            {
                if (!status.Installed) continue;
                var app = AppCatalog.Apps().FirstOrDefault(a => a.Key == key);
                if (app == null) continue;
                _itemsByApp.TryGetValue(key, out var items);
                var row = new AppRowViewModel(app)
                {
                    Note = status.Note,
                    Detail = BuildDetail(items ?? new List<CleanItem>()),
                };
                if (row.Running) running++;
                _rows.Add(row);
            }
        }

        long size = 0;
        if (result.Summary != null && result.Summary.TryGetValue("size", out var s) && s is long l) size = l;

        DetectCount.Text = $"检测到 {_rows.Count} 款";
        CleanStats.Text = $"{_rows.Count} 款 · {AppPaths.HumanSize(size)} · {running} 款正在运行";
        TechState.Text = "演示状态：等待开始";
        StatusText.Text = $"扫描完成：{_rows.Count} 款已安装，{result.Items?.Count ?? 0} 个可清理项。";
        UpdateSelectedCount();
        RenderSolutions(result);
    }

    private static string BuildDetail(List<CleanItem> items)
    {
        var parts = items.Take(4).Select(i => $"{i.KindLabel} · {Shorten(i.Target)}");
        return string.Join("  ", parts);
    }

    private static string Shorten(string text) => text.Length <= 44 ? text : text[..41] + "…";

    private void OnSelectAll(object? sender, EventArgs e)
    {
        foreach (var row in _rows) row.IsChecked = true;
        UpdateSelectedCount();
    }

    private void OnClearAll(object? sender, EventArgs e)
    {
        foreach (var row in _rows) row.IsChecked = false;
        UpdateSelectedCount();
    }

    private List<AppRowViewModel> SelectedRows() => _rows.Where(r => r.IsChecked).ToList();

    private void UpdateSelectedCount()
    {
        ActionButton.Text = $"卸载选中（{SelectedRows().Count}）";
    }

    private void OnModeSelect(object? sender, EventArgs e)
    {
        var tag = (sender as Button)?.CommandParameter?.ToString() ?? "single";
        _bundleMode = tag == "bundle";
        ApplyModeState();
    }

    private void ApplyModeState()
    {
        var accentColor = C("AppAccentColor");
        var cardColor = C("AppCardColor");
        var subColor = C("AppTextSubColor");
        var borderColor = C("AppBorderColor");

        ModeSingleBtn.BackgroundColor = _bundleMode ? cardColor : accentColor;
        ModeSingleBtn.TextColor = _bundleMode ? subColor : Colors.White;
        ModeBundleBtn.BackgroundColor = _bundleMode ? accentColor : cardColor;
        ModeBundleBtn.TextColor = _bundleMode ? Colors.White : subColor;
        ModeSingleBtn.BorderColor = borderColor;
        ModeBundleBtn.BorderColor = borderColor;

        ModeHint.Text = _bundleMode
            ? "一条龙：卸载全部勾选项，并深度扫盘清理公共目录与启动项"
            : "单项卸载：只处理勾选项，不动公共残留目录";
    }

    private async void OnActionClick(object? sender, EventArgs e)
    {
        var selected = SelectedRows();
        if (selected.Count == 0)
        {
            StatusText.Text = "请先勾选要清理的产品。";
            return;
        }
        await RunUninstall(selected.Select(r => r.App).ToList(), _bundleMode);
    }

    private async void OnBundleClick(object? sender, EventArgs e)
    {
        var all = _rows.Select(r => r.App).ToList();
        if (all.Count == 0)
        {
            StatusText.Text = "当前没有检测到可清理的产品。";
            return;
        }
        await RunUninstall(all, true);
    }

    private async Task RunUninstall(List<AppDefinition> selected, bool bundle)
    {
        ActionButton.IsEnabled = false;
        BundleButton.IsEnabled = false;
        TechBadgeText.Text = "运行中";
        StatusText.Text = bundle ? "一条龙清除：正在拆解全部检测项…" : "单项卸载：正在处理勾选项…";

        var payload = new WorkerPayload
        {
            Apps = selected,
            ItemsByApp = _itemsByApp,
            ExtraItems = bundle ? _commonItems : null,
            Deep = bundle,
        };

        _worker = new WorkerService();
        Wire(_worker);
        await _worker.RunAsync(WorkerMode.Uninstall, payload);

        ActionButton.IsEnabled = true;
        BundleButton.IsEnabled = true;
        TechBadgeText.Text = "待命";

        var engine = _lastResult?.Engine;
        ShowResidual(engine);
        var didWork = string.IsNullOrEmpty(_lastResult?.Error) && engine != null && (engine.Ok > 0 || engine.Pending > 0);
        if (didWork) ShowRebootPrompt();
    }

    private void ShowResidual(EngineResult? engine)
    {
        _residualRows.Clear();
        if (engine == null) return;
        foreach (var row in engine.Rows)
        {
            var item = new CleanItem
            {
                Kind = row.Kind,
                Target = row.Target,
                Label = row.Label,
                AppName = row.KindLabel,
                Size = row.Size,
            };
            _residualRows.Add(new ResidualRowViewModel(item)
            {
                Status = row.Ok ? row.Detail : "✘ " + row.Detail,
            });
        }
        RefreshResidualSummary();
        ResidualOverlay.IsVisible = _residualRows.Count > 0;
    }

    private void RefreshResidualSummary()
    {
        var size = _residualRows.Sum(r => r.Item.Size);
        ResidualSummary.Text = $"共 {_residualRows.Count} 项，占用 {AppPaths.HumanSize(size)}。";
    }

    private void OnResidualClose(object? sender, EventArgs e) => ResidualOverlay.IsVisible = false;

    private async void OnResidualScan(object? sender, EventArgs e)
    {
        ResidualScan.IsEnabled = false;
        ResidualStatus.Text = "深度扫描残留文件…";
        _worker = new WorkerService();
        Wire(_worker);
        await _worker.RunAsync(WorkerMode.Residual, new WorkerPayload { Deep = true });
        ResidualScan.IsEnabled = true;
    }

    private async void OnResidualClean(object? sender, EventArgs e)
    {
        var items = _residualRows.Where(r => r.IsChecked).Select(r => r.Item).ToList();
        if (items.Count == 0) { ResidualStatus.Text = "没有勾选项目。"; return; }
        ResidualClean.IsEnabled = false;
        ResidualStatus.Text = $"正在删除 {items.Count} 个项目…";
        _worker = new WorkerService();
        Wire(_worker);
        await _worker.RunAsync(WorkerMode.Clean, new WorkerPayload { Items = items });
        ResidualClean.IsEnabled = true;
    }

    private void ApplyResidualResult(WorkerResult result)
    {
        if (!string.IsNullOrEmpty(result.Error))
        {
            ResidualStatus.Text = "任务失败：" + result.Error;
            return;
        }

        if (result.Items != null)
        {
            _residualRows.Clear();
            foreach (var item in result.Items) _residualRows.Add(new ResidualRowViewModel(item));
        }

        if (result.Engine != null)
        {
            foreach (var row in result.Engine.Rows)
            {
                var match = _residualRows.FirstOrDefault(r => r.Item.Target == row.Target);
                if (match != null)
                {
                    match.Item.Size = row.Size;
                    match.Status = row.Ok ? row.Detail : "✘ " + row.Detail;
                }
            }
        }
        RefreshResidualSummary();
        ResidualStatus.Text = "清理完成。";
    }

    private void ShowRebootPrompt()
    {
        RebootBar.IsVisible = true;
        RebootYes.IsVisible = true;
        RebootUndo.IsVisible = false;
        RebootTitle.Text = "清理完成，是否重启以完成残留清理？";
        RebootHint.Text = "安排后 20 秒内可撤销，重启前可随时取消。";
    }

    private void OnRebootYes(object? sender, EventArgs e)
    {
        var (ok, detail) = SystemActions.ScheduleReboot(20);
        if (!ok)
        {
            RebootHint.Text = "重启安排失败：" + detail;
            return;
        }
        _rebootLeft = 20;
        RebootYes.IsVisible = false;
        RebootUndo.IsVisible = true;
        RebootTitle.Text = "已安排 20 秒后重启";
        RebootHint.Text = $"剩余 {_rebootLeft} 秒，点击撤销可取消。";

        _rebootTimer = Dispatcher.CreateTimer();
        _rebootTimer.Interval = TimeSpan.FromSeconds(1);
        _rebootTimer.Tick += (_, _) =>
        {
            _rebootLeft--;
            if (_rebootLeft <= 0)
            {
                HideRebootBar();
                return;
            }
            RebootHint.Text = $"剩余 {_rebootLeft} 秒，点击撤销可取消。";
        };
        _rebootTimer.Start();
    }

    private void OnRebootUndo(object? sender, EventArgs e)
    {
        SystemActions.CancelReboot();
        HideRebootBar();
        StatusText.Text = "已取消重启安排。";
    }

    private void HideRebootBar()
    {
        _rebootTimer?.Stop();
        _rebootTimer = null;
        RebootBar.IsVisible = false;
    }

    private void RenderSolutions(WorkerResult result)
    {
        var solutions = result.Engine != null ? Solutions.Collect(result.Engine.Rows) : new List<Solution>();
        SolBullets.Clear();
        if (solutions.Count == 0)
        {
            SolTitle.Text = "被 360 内核驱动拦截";
            SolTitle.TextColor = C("AppDangerColor");
            AddBullet("先退出 360 托盘并关闭自我保护，再执行清理");
            AddBullet("已有残留驱动就进安全模式清理，正常模式下删不掉是预期行为");
            return;
        }

        var first = solutions[0];
        SolTitle.Text = first.Title;
        SolTitle.TextColor = first.Level == "danger"
            ? C("AppDangerColor")
            : C("AppAccentColor");
        foreach (var step in first.Steps) AddBullet(step);
    }

    private void AddBullet(string text)
    {
        SolBullets.Add(new Label
        {
            Text = "· " + text,
            FontSize = 10,
            TextColor = C("AppTextSubColor"),
            LineBreakMode = LineBreakMode.WordWrap,
        });
    }

    private async void OnCheckUpdateClick(object? sender, EventArgs e) => await CheckUpdateAsync();

    public async Task CheckUpdateAsync()
    {
        UpdateButton.IsEnabled = false;
        UpdateTrack.IsVisible = true;
        UpdateProgress.IsVisible = true;
        UpdateProgress.Text = "正在检查版本…";
        var lastBytes = 0L;
        var lastStamp = DateTime.UtcNow;
        try
        {
            var release = await Updater.FetchLatestAsync();
            var hasUpdate = Updater.IsNewer(release.Tag);
            if (!hasUpdate)
            {
                UpdateStatus.Text = $"当前已是最新（{AppPaths.AppVersion}")";
                HideUpdateProgress();
                return;
            }

            var asset = Updater.PickExeAsset(release);
            if (asset == null)
            {
                UpdateStatus.Text = $"发现新版本 {release.Tag}，但未找到可执行安装包，请手动到 Releases 下载";
                HideUpdateProgress();
                return;
            }

            UpdateStatus.Text = $"发现新版本 {release.Tag}，正在测速选择链路…";
            var urls = Updater.BuildMirrorUrls(asset.Url);
            var url = await Updater.PickFastestAsync(urls, AppendLog);
            var dest = Path.Combine(AppPaths.UpdateDir, "ResidualCleaner-update.exe");
            UpdateProgress.Text = "开始下载…";
            await Updater.DownloadAsync(url, dest, (done, total) =>
            {
                Dispatcher.Dispatch(() =>
                {
                    var pct = total > 0 ? done * 100.0 / total : 0;
                    UpdateFill.WidthRequest = 272 * pct / 100.0;
                    var now = DateTime.UtcNow;
                    var secs = (now - lastStamp).TotalSeconds;
                    var speed = secs > 0.5 ? (done - lastBytes) / secs : 0;
                    lastBytes = done;
                    lastStamp = now;
                    var sizeText = total > 0 ? $"{AppPaths.HumanSize(done)} / {AppPaths.HumanSize(total)}" : AppPaths.HumanSize(done);
                    UpdateProgress.Text = $"{pct:0}%  {sizeText}  {AppPaths.HumanSize(Math.Max(0, speed))}/s";
                });
            });

            UpdateStatus.Text = "下载完成，正在替换程序并重启…";
            var (ok, detail) = Updater.RestartAndInstall(dest);
            UpdateStatus.Text = ok ? "已安排替换并重启" : "替换失败：" + detail;
            if (!ok) HideUpdateProgress();
        }
        catch (Exception ex)
        {
            UpdateStatus.Text = "检查更新失败：" + ex.Message;
            HideUpdateProgress();
        }
        finally
        {
            UpdateButton.IsEnabled = true;
        }
    }

    private void HideUpdateProgress()
    {
        UpdateTrack.IsVisible = false;
        UpdateProgress.IsVisible = false;
        UpdateFill.WidthRequest = 0;
    }

    private void AppendLog(string message)
    {
        TechLog.Text += message + Environment.NewLine;
    }
}
