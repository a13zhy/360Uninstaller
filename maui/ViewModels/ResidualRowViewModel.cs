using ResidualCleaner.Maui.Models;

namespace ResidualCleaner.Maui.ViewModels;

public sealed class ResidualRowViewModel : System.ComponentModel.INotifyPropertyChanged
{
    private bool _isChecked = true;
    private string _status = "";

    public CleanItem Item { get; }

    public ResidualRowViewModel(CleanItem item) => Item = item;

    public bool IsChecked
    {
        get => _isChecked;
        set { _isChecked = value; PropertyChanged?.Invoke(this, new System.ComponentModel.PropertyChangedEventArgs(nameof(IsChecked))); }
    }

    public string KindLabel => Item.KindLabel;
    public string Label => Item.Label;
    public string Target => Item.Target;
    public string SizeText => Item.SizeText;

    public string Status
    {
        get => _status;
        set { _status = value; PropertyChanged?.Invoke(this, new System.ComponentModel.PropertyChangedEventArgs(nameof(Status))); }
    }

    public event System.ComponentModel.PropertyChangedEventHandler? PropertyChanged;
}
