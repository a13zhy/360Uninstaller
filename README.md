# 残留清理卫士 ResidualCleaner

Windows 10 / 11 上深度卸载 360 系、2345 系软件、清理安装残留的桌面工具。当前为 .NET 8 MAUI 重写版，源码位于 `maui/` 目录。

## 当前版本

**v1.3.2.261128**（.NET MAUI / Windows）

## 源码结构

- `maui/`：.NET 8 MAUI 工程（C# / XAML），包含 Models、Data、Services、ViewModels、Platforms、Resources

## 从源码构建

前置条件：.NET 8 SDK，并已安装 `maui-windows` workload。

```powershell
cd maui
dotnet build ResidualCleaner.Maui.csproj -f net8.0-windows10.0.19041.0 -p:Platform=x64
dotnet publish ResidualCleaner.Maui.csproj -c Release -f net8.0-windows10.0.19041.0 -p:Platform=x64
```

## 运行要求

- Windows 10 / 11 64 位（最低 10.0.17763），管理员权限。
- 需安装 .NET 8 Desktop Runtime (x64)；发布包为框架依赖，需解压整个目录运行，不能只拷贝单个 exe。

## 已支持清理

- 360 安全卫士 / 杀毒 / 浏览器 / 压缩 / 软件管家 / 云盘 / 游戏大厅 / 手机助手 / 影视 / 壁纸等 21 款组件与小鸟壁纸。
- 2345 安全卫士、加速浏览器、极速浏览器、好压压缩、看图王、王牌输入法、软件管家、游戏大厅共 8 款组件。
- 公共组件、开机启动项、计划任务、服务、卸载登记项、残留目录与快捷方式多路取证，只列本机已装项。

## 已知边界

- 托盘常驻、独立开机巡检小窗尚未在 MAUI 版接线；残余项目目前在主窗覆盖层呈现。
- macOS（MacCatalyst）目录与 360 for Mac 残留规则仅为预留底稿，未在 Mac 上构建、签名或实测。
- 360 内核自保护驱动（ZhuDongFangYu / 360FsFlt / 360AntiHijack 等）在内核层拦写，2345 守护进程同样可能锁定文件；正常模式删不掉属预期，需先关闭自保护或进安全模式。

## 安全边界

- 不做后台静默批量删除，清理结果必须你确认后才执行。
- 不默认开机自启、不自动重启、不注册后台服务。
- 被锁住的文件只登记“下次开机由系统删除”，不反复硬删。

## 许可

见 `LICENSE`。本工具为第三方独立程序，与奇虎 360、2345 均无任何关联，删除操作不可恢复，使用前请确认重要数据已备份。
