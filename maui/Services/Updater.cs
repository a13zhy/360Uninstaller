using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace ResidualCleaner.Maui.Services;

public sealed class ReleaseAsset
{
    public string Name { get; set; } = "";
    public string Url { get; set; } = "";
    public long Size { get; set; }
}

public sealed class ReleaseInfo
{
    public string Tag { get; set; } = "";
    public string Name { get; set; } = "";
    public string Body { get; set; } = "";
    public string Page { get; set; } = "";
    public string PublishedAt { get; set; } = "";
    public List<ReleaseAsset> Assets { get; set; } = new();
}

public static class Updater
{
    private const string Repo = "a13zhy/360Uninstaller";
    private static readonly string ApiLatest = $"https://api.github.com/repos/{Repo}/releases/latest";
    public static readonly string ReleasePage = $"https://github.com/{Repo}/releases";
    private static readonly string UserAgent = $"{AppPaths.AppNameEn}/{AppPaths.AppVersion}";

    public static bool IsNewer(string remote, string? local = null)
    {
        var r = Normalize(remote);
        var l = Normalize(local ?? AppPaths.AppVersion);
        var width = Math.Max(r.Count, l.Count);
        for (var i = 0; i < width; i++)
        {
            var rv = i < r.Count ? r[i] : 0;
            var lv = i < l.Count ? l[i] : 0;
            if (rv != lv) return rv > lv;
        }
        return false;
    }

    private static List<int> Normalize(string text)
    {
        var nums = System.Text.RegularExpressions.Regex.Matches(text ?? "", @"\d+")
            .Select(m => int.Parse(m.Value)).Take(4).ToList();
        return nums.Count > 0 ? nums : new List<int> { 0 };
    }

    public static async Task<ReleaseInfo> FetchLatestAsync(int timeout = 12)
    {
        using var http = new HttpClient();
        http.DefaultRequestHeaders.Add("User-Agent", UserAgent);
        http.DefaultRequestHeaders.Add("Accept", "application/vnd.github+json");
        var json = await http.GetStringAsync(ApiLatest).WaitAsync(TimeSpan.FromSeconds(timeout));
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        var release = new ReleaseInfo
        {
            Tag = root.GetProperty("tag_name").GetString() ?? "",
            Name = root.GetProperty("name").GetString() ?? "",
            Body = root.GetProperty("body").GetString() ?? "",
            Page = root.GetProperty("html_url").GetString() ?? ReleasePage,
            PublishedAt = root.GetProperty("published_at").GetString() ?? "",
        };
        if (root.TryGetProperty("assets", out var assets))
        {
            foreach (var a in assets.EnumerateArray())
            {
                release.Assets.Add(new ReleaseAsset
                {
                    Name = a.GetProperty("name").GetString() ?? "",
                    Url = a.GetProperty("browser_download_url").GetString() ?? "",
                    Size = a.TryGetProperty("size", out var s) ? s.GetInt64() : 0,
                });
            }
        }
        return release;
    }

    public static ReleaseAsset? PickExeAsset(ReleaseInfo release) =>
        release.Assets.FirstOrDefault(a => a.Name.EndsWith(".exe", StringComparison.OrdinalIgnoreCase)
                                            && !a.Name.Contains("verify", StringComparison.OrdinalIgnoreCase));

    public static string Sha256File(string path)
    {
        using var sha = SHA256.Create();
        using var fs = File.OpenRead(path);
        return Convert.ToHexString(sha.ComputeHash(fs)).ToUpperInvariant();
    }

    private static HttpClient NewClient()
    {
        var http = new HttpClient();
        http.DefaultRequestHeaders.Add("User-Agent", UserAgent);
        http.DefaultRequestHeaders.Add("Accept", "application/octet-stream");
        http.Timeout = TimeSpan.FromSeconds(15);
        return http;
    }

    public static List<string> BuildMirrorUrls(string githubUrl)
    {
        var list = new List<string> { githubUrl };
        if (githubUrl.StartsWith("https://github.com/", StringComparison.OrdinalIgnoreCase))
        {
            list.Add("https://gh-proxy.com/" + githubUrl);
            list.Add("https://ghproxy.net/" + githubUrl);
        }
        return list.Distinct().ToList();
    }

    public static async Task<(string Url, long Ms)> ProbeAsync(string url, int timeoutMs = 6000)
    {
        var sw = Stopwatch.StartNew();
        using var http = NewClient();
        using var response = await http.GetAsync(url, HttpCompletionOption.ResponseHeadersRead)
            .WaitAsync(TimeSpan.FromMilliseconds(timeoutMs));
        response.EnsureSuccessStatusCode();
        sw.Stop();
        return (url, sw.ElapsedMilliseconds);
    }

    public static async Task<string> PickFastestAsync(IEnumerable<string> urls, Action<string>? log = null)
    {
        var candidates = urls.ToList();
        var probes = candidates.Select(async u =>
        {
            try { return await ProbeAsync(u); }
            catch (Exception ex)
            {
                log?.Invoke($"链路不可用：{u}（{ex.Message}）");
                return (Url: u, Ms: long.MaxValue);
            }
        });
        var results = await Task.WhenAll(probes);
        var best = results.OrderBy(r => r.Ms).First();
        log?.Invoke(best.Ms == long.MaxValue ? "所有链路测速失败，回退直连" : $"选中链路：{best.Url}（首字节 {best.Ms} ms）");
        return best.Ms == long.MaxValue ? candidates[0] : best.Url;
    }

    public static async Task DownloadAsync(string url, string dest, Action<long, long>? progress = null)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(dest) ?? AppPaths.UpdateDir);
        using var http = NewClient();
        using var response = await http.GetAsync(url, HttpCompletionOption.ResponseHeadersRead);
        response.EnsureSuccessStatusCode();
        var total = response.Content.Headers.ContentLength ?? 0;
        var done = 0L;
        await using var stream = await response.Content.ReadAsStreamAsync();
        await using var file = File.Create(dest);
        var buffer = new byte[262144];
        int read;
        while ((read = await stream.ReadAsync(buffer)) > 0)
        {
            await file.WriteAsync(buffer.AsMemory(0, read));
            done += read;
            progress?.Invoke(done, total);
        }
    }

    public static (bool Ok, string Detail) RestartAndInstall(string newExe)
    {
        var target = Environment.ProcessPath ?? "";
        if (string.IsNullOrEmpty(target) || !target.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
            return (false, "源码模式无法自动替换程序文件，请到 Releases 页面手动下载安装");

        var pid = Environment.ProcessId;
        var script = string.Join(Environment.NewLine, new[]
        {
            "$ErrorActionPreference = 'SilentlyContinue'",
            $"$target = '{target.Replace("'", "''")}'",
            $"$new = '{Path.GetFullPath(newExe).Replace("'", "''")}'",
            $"$procId = {pid}",
            "for ($i = 0; $i -lt 120; $i++) {",
            "    if (-not (Get-Process -Id $procId -ErrorAction SilentlyContinue)) { break }",
            "    Start-Sleep -Milliseconds 500",
            "}",
            "Start-Sleep -Milliseconds 1200",
            "$copied = $false",
            "for ($j = 0; $j -lt 60; $j++) {",
            "    try {",
            "        Copy-Item -LiteralPath $new -Destination $target -Force -ErrorAction Stop",
            "        $copied = $true",
            "        break",
            "    } catch { Start-Sleep -Milliseconds 500 }",
            "}",
            "if ($copied) {",
            "    Remove-Item -LiteralPath $new -Force",
            "    Start-Process -FilePath $target",
            "}",
            "Remove-Item -LiteralPath $PSCommandPath -Force",
            "",
        });

        var path = Path.Combine(Path.GetTempPath(), $"rc_update_{pid}.ps1");
        File.WriteAllText(path, script, new UTF8Encoding(true));
        Process.Start(new ProcessStartInfo
        {
            FileName = "powershell",
            ArgumentList = { "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", path },
            CreateNoWindow = true,
            UseShellExecute = false,
        });
        return (true, "");
    }
}
