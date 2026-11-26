# 残留清理卫士 · .NET MAUI 版（maui/）

本目录是同一清理工具的 .NET 8 MAUI 跨平台重写版源码。仓库根目录的 Python / PySide6 版本仍为旧版，二者并存，互不影响。

## 当前状态

- 当前只保证 **Windows** 目标可编译、可运行（`net8.0-windows10.0.19041.0`）。
- macOS（MacCatalyst）平台目录与 360 for Mac 残留规则已预留，但**未在 Mac 上构建、签名或实测**；`Data/MacCatalog.cs` 里的 Bundle ID、`.app` 名与残留路径是占位底稿，必须在真实 Mac 上探查核对后才能用于删除。
- 托盘常驻、独立巡检小窗尚未在 MAUI 版接线；残余项目目前以主窗内的覆盖层呈现。

## 从源码构建

前置条件：.NET 8 SDK，并已安装 `maui-windows` workload。

```powershell
dotnet build ResidualCleaner.Maui.csproj -f net8.0-windows10.0.19041.0 -p:Platform=x64
dotnet publish ResidualCleaner.Maui.csproj -c Release -f net8.0-windows10.0.19041.0 -p:Platform=x64
```

## 目录结构

- `Models/`：应用定义、清理项模型
- `Data/`：Windows 应用清单、Mac 预留规则
- `Services/`：扫描、卸载引擎、注册表/进程/服务/强删/更新/重启等服务
- `ViewModels/`：列表行视图模型
- `Platforms/Windows/`：Windows 平台入口与清单
- `Platforms/MacCatalyst/`：macOS 预留入口（当前不参与 Windows 编译）
- `Resources/Styles/`：火绒浅色主题色板与控件样式

## 暂未随仓库上传的二进制资源

下列文件通过接口仅能上传文本，因此本次未提交，本地还原后需自行补齐同名字段：

- `Resources/Fonts/OpenSans-Regular.ttf`
- `Resources/Fonts/OpenSans-Semibold.ttf`
- `Resources/Images/dotnet_bot.png`

可替换为任意同名的常规/半粗体无衬线字体与占位图片。

## 许可

与仓库根目录 LICENSE 一致；本工具为第三方独立清理程序，与奇虎 360 无任何关联。
