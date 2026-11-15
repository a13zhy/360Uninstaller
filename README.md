# 残留清理卫士 ResidualCleaner

Windows 10 / 11 上用于深度卸载 360 系软件、清理安装残留的桌面工具。不调官方卸载器，直接逐项拆除进程、服务、目录、注册表、计划任务、开机启动项、DLL 与驱动、快捷方式；无权访问的文件会先接管所有权再强删。界面配色跟随系统的深/浅色模式与强调色。

![主界面预览](https://aka.doubaocdn.com/s/8E2t95utab)

![残余检查小窗](https://aka.doubaocdn.com/s/WtjaxC7GSy)

![右下角扫描浮窗](https://aka.doubaocdn.com/s/9JI7xAljAa)

## 当前版本

**v1.2.8.261115**（配色跟随 Windows · 对话框重排 · 右下角扫描浮窗 · 启动项/DLL 清理）

## 功能

- **扫描**：注册表卸载项、安装目录、进程、服务、驱动、计划任务、启动项、DLL、快捷方式，支持磁盘深扫残留；覆盖 17 款 360 组件。
- **卸载**：按依赖顺序拆除，删除注册表前自动导出备份，失败项归类归因，被占用文件登记为重启后删。
- **一键清除**：一次选出全部 360 组件，清完自动跳残余检查。
- **深度扫描浮窗**：扫盘进度显示在右下角无边框小窗里，可随时取消，扫完自动收起。
- **强力删除**：owner / ACL 重置 + 结束占用进程 + 长路径逐层删，仍失败则登记到 PendingFileRenameOperations。
- **系统配色**：读 `AppsUseLightTheme` 与 `ColorizationColor`，深/浅色与强调色跟着 Windows 走；对话框文字颜色全部显式指定，不发灰。
- **真实图标**：安装目录里能找到程序 exe/ico 的，列表直接显示程序自己的图标。
- **检查更新**：从 GitHub Releases 拉版本，可下载并静默安装后自动重启。
- **托盘常驻**：关闭窗口不退出，任务在后台跑，结束后托盘弹提示；托盘菜单可扫描 / 查更新 / 退出。
- **日志**：界面控制台实时输出，同时落盘到 `%APPDATA%\ResidualCleaner\logs\`（含注册表备份）。

## 安全边界

- 不做后台静默批量删除（每个清理项都要你先看过再确认）；
- 不写开机自启项、不自动重启系统；
- 被系统锁住的文件只登记“下次开机由系统删除”，不反复硬干。

## 使用

1. 下载 Release 里的 `ResidualCleaner-vX-win64.zip`，解压后双击 `ResidualCleaner.exe`（会请求管理员权限）。
2. 首次启动会弹出免责声明，读完后勾选“我已了解”。
3. 扫描完勾选要卸的应用 → “卸载选中应用”，或者直接用底部“360 一键全部移除”；想先看全盘有什么，点顶栏“深度扫描”。
4. 卸载完成会自动弹残余检查小窗，勾选后删除；建议重启一次。

> 需要管理员权限才能动服务和受保护目录。非管理员启动时顶栏会显示“受限模式”，点一下可直接提权重启。

## 从源码构建

```powershell
python -m venv .venv
.venv\Scripts\pip install PySide6==6.12.0 Pillow pyinstaller
.venv\Scripts\python tools\make_icon.py
.venv\Scripts\pyinstaller --noconfirm --onefile --windowed --uac-admin ^
  --name ResidualCleaner --icon assets\app_icon.ico ^
  --add-data "assets;assets" main.py
```

## 界面

- 左侧主界面：读数条 + 应用列表（真实程序图标，取不到才用字母徽章；状态/占用列）；
- 右侧控制台：等宽字体日志流、渐变进度条、已清理/失败/释放空间三列读数；
- 配色跟随 Windows：深/浅色模式与系统强调色自动同步，方角细线、无卡片阴影；1200×800 起可缩，最低 1080×720。

## 许可

个人使用，按现状提供，删错东西自己负责（删前会列清单让你确认）。与奇虎 360 无任何关系。
