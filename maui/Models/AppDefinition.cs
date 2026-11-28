namespace ResidualCleaner.Maui.Models;

public sealed class AppDefinition
{
    public string Key { get; set; } = "";
    public string Name { get; set; } = "";
    public string Desc { get; set; } = "";
    public List<string> Processes { get; set; } = new();
    public List<string> Services { get; set; } = new();
    public List<string> Dirs { get; set; } = new();
    public List<string> Regs { get; set; } = new();
    public List<string> Tasks { get; set; } = new();
    public List<string> Shortcuts { get; set; } = new();
    public List<string> Keywords { get; set; } = new();
    public string Category { get; set; } = "tool";
}
