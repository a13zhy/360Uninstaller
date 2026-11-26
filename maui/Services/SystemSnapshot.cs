namespace ResidualCleaner.Maui.Services;

public sealed class SystemSnapshot
{
    private List<(string Name, string Pid)>? _procs;
    private List<string>? _services;
    private List<string>? _tasks;

    public List<(string Name, string Pid)> Processes => _procs ??= ProcessService.ListProcesses();
    public List<string> Services => _services ??= ProcessService.ListServices();
    public List<string> Tasks => _tasks ??= ProcessService.ListTasks();

    public HashSet<string> ProcessNames => Processes.Select(p => p.Name).ToHashSet(StringComparer.OrdinalIgnoreCase);
}
