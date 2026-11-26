using ResidualCleaner.Maui.Data;
using ResidualCleaner.Maui.Services;

namespace ResidualCleaner.Maui.Models;

public sealed class CleanItem
{
    public string Kind { get; set; } = "";
    public string Target { get; set; } = "";
    public string Label { get; set; } = "";
    public string AppKey { get; set; } = "";
    public string AppName { get; set; } = "";
    public long Size { get; set; }
    public Dictionary<string, string> Extra { get; } = new();

    public string KindLabel => AppCatalog.KindLabels.TryGetValue(Kind, out var label) ? label : Kind;

    public string SizeText => Size > 0 ? AppPaths.HumanSize(Size) : "-";

    public string Key => $"{Kind}|{Target}";
}
