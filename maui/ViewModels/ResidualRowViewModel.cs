using Microsoft.Maui.Controls;
using ResidualCleaner.Maui.Data;
using ResidualCleaner.Maui.Models;

namespace ResidualCleaner.Maui.ViewModels;

public sealed class ResidualRowViewModel : System.ComponentModel.INotifyPropertyChanged
{
    private bool _isChecked = true;
    private string _status = "";
    private ImageSource? _iconSource;
    private bool _hasRealIcon;

    public CleanItem Item { get; }

    public ResidualRowViewModel(CleanItem item)
    {
        Item = item;
        IconResource = AppCatalog.IconForKind(item.Kind);
        if (item.IsEmptyDir) IconResource = AppCatalog.CategoryIcon["trash"];
    }

    public bool IsChecked
    {
        get => _isChecked;
        set { _isChecked = value; PropertyChanged?.Invoke(this, new System.ComponentModel.PropertyChangedEventArgs(nameof(IsChecked))); }
    }

    public string KindLabel => Item.KindLabel;
    public string Label => Item.Label;
    public string Target => Item.Target;
    public string SizeText => Item.SizeText;
    public string IconResource { get; }

    public bool HasRealIcon
    {
        get => _hasRealIcon;
        private set
        {
            _hasRealIcon = value;
            PropertyChanged?.Invoke(this, new System.ComponentModel.PropertyChangedEventArgs(nameof(HasRealIcon)));
            PropertyChanged?.Invoke(this, new System.ComponentModel.PropertyChangedEventArgs(nameof(ShowFallback)));
        }
    }

    public bool ShowFallback => !_hasRealIcon;

    public ImageSource? IconSource
    {
        get => _iconSource;
        set
        {
            _iconSource = value;
            HasRealIcon = value != null;
            PropertyChanged?.Invoke(this, new System.ComponentModel.PropertyChangedEventArgs(nameof(IconSource)));
        }
    }

    public string Status
    {
        get => _status;
        set { _status = value; PropertyChanged?.Invoke(this, new System.ComponentModel.PropertyChangedEventArgs(nameof(Status))); }
    }

    public event System.ComponentModel.PropertyChangedEventHandler? PropertyChanged;
}
