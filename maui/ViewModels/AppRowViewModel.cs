using Microsoft.Maui.Controls;
using ResidualCleaner.Maui.Data;
using ResidualCleaner.Maui.Models;

namespace ResidualCleaner.Maui.ViewModels;

public sealed class AppRowViewModel : System.ComponentModel.INotifyPropertyChanged
{
    private bool _isChecked;
    private string _note = "";
    private string _detail = "";
    private ImageSource? _iconSource;
    private bool _hasRealIcon;

    public AppRowViewModel(AppDefinition app)
    {
        App = app;
        IconResource = AppCatalog.IconForCategory(app.Category);
    }

    public AppDefinition App { get; }

    public bool IsChecked
    {
        get => _isChecked;
        set { _isChecked = value; PropertyChanged?.Invoke(this, new System.ComponentModel.PropertyChangedEventArgs(nameof(IsChecked))); }
    }

    public string Name => App.Name;
    public string Desc => App.Desc;
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

    public string Note
    {
        get => _note;
        set
        {
            _note = value;
            PropertyChanged?.Invoke(this, new System.ComponentModel.PropertyChangedEventArgs(nameof(Note)));
            PropertyChanged?.Invoke(this, new System.ComponentModel.PropertyChangedEventArgs(nameof(Running)));
        }
    }

    public string Detail
    {
        get => _detail;
        set { _detail = value; PropertyChanged?.Invoke(this, new System.ComponentModel.PropertyChangedEventArgs(nameof(Detail))); }
    }

    public bool Running => _note == "正在运行";

    public event System.ComponentModel.PropertyChangedEventHandler? PropertyChanged;
}
