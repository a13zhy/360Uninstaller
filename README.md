# 残留清理卫士 ResidualCleaner

Windows 10 / 11 上的 360 系列软件深度卸载与残留清理工具。
不调用官方卸载程序，直接按项拆除：进程、服务、安装目录、注册表、计划任务、快捷方式，并在卸载后自动检查残留。

![界面预览](https://github.com/a13zhy/360Uninstaller/releases/download/v1.2.5.261109/preview-main.png)

## 功能

| 功能 | 说明 |
| --- | --- |
| 应用识别 | 12 款 360 系应用（安全卫士、杀毒、浏览器、极速浏览器、压缩、驱动大师、软件管家、云盘、手机助手、游戏大厅、影视、桌面） |
| 自动提权 | 启动即以管理员身份运行（UAC manifest 内置 `requireAdministrator`） |
| 左右分栏 | 左侧应用清单，右侧实时控制台（日志 / 进度 / 已清理 / 失败 / 释放空间） |
| 逐项卸载 | 按类型顺序拆除，过程中逐条回报成功与失败原因 |
| 残余检查 | 卸载后弹出小窗，扫描并列出残余项目，勾选后删除，失败项可重试 |
| 强力删除 | 普通删除失败时用 `takeown` + `icacls` 接管所有权、清除只读/系统/隐藏属性后重删 |
| 深度扫盘 | 在受控目录范围内检索 360 相关文件与目录（排除 System32、WinSxS 等系统目录） |
| 360 一键清除 | 一次处理全部已检测到的 360 组件，执行前列出完整清单供确认 |
| 注册表备份 | 删除注册表项前自动 `reg export` 备份到 `%LOCALAPPDATA%\ResidualCleaner\reg_backup` |
| 检查更新 | 从 GitHub Releases 读取最新版本，程序内下载、校验大小和文件头后自动替换并重启 |
| 托盘常驻 | 关闭窗口最小化到右下角托盘，任务继续后台执行，右键托盘可扫描 / 检查更新 / 退出 |
| 源码公开 | 仓库内附完整源码，Python 3.12 + PySide6 6.12，可自行构建 |

## 使用

1. 双击 `ResidualCleaner.exe`，同意 UAC 提示。
2. 首次启动阅读免责说明并确认。
3. 程序自动扫描，左侧列出检测到的 360 应用（勾选需要卸载的）。
4. 点「卸载选中应用」或「360 一键清除」，确认清单后执行。
5. 卸载完成后自动弹出「残余项目检查」小窗，勾选残留项删除。
6. 清理完成后建议手动重启电脑，释放被占用的文件句柄。

关闭主窗口 = 最小化到右下角托盘，程序不会退出；要真正退出，右键托盘图标选「退出」。

日志：`%LOCALAPPDATA%\ResidualCleaner\cleaner.log`

## 版本与更新

- 当前版本 **v1.2.5.261109**
- 顶栏「检查更新」按钮会读取 GitHub Releases 的最新发布：有新版时按钮变为「有新版本 vX」，点开可直接下载、校验并调用 PowerShell 脚本替换当前 exe 后重新启动。
- 启动 4 秒后会自动检查一次，24 小时内不重复打扰；也可在托盘右键菜单手动检查。
- 检测逻辑只读取公开的 `releases/latest` API，不上传任何本机信息。

## 安全设计

- **先列清单、再执行**：批量操作前展示条目数与类型统计，用户确认后才动。
- **逐项回报**：每一个成功/失败都写进控制台与日志文件。
- **不做后台静默删除**：没有守护进程、没有开机自启、不自动重启系统。
- **不碰系统目录**：深度扫描显式排除系统关键路径。
- **注册表先备份**：删除前导出 `.reg` 备份，可手工恢复。

## 系统要求

- Windows 10 / 11，64 位
- 管理员权限（程序会自动请求）

## 从源码运行

```bat
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python tools\make_icon.py
run.bat
```

`tools\make_icon.py` 会用 Pillow 生成 `assets\app_icon.ico` / `app_icon.png` / `check.png`
（仓库不提交这三张二进制图片，构建前生成即可，`build_exe.bat` 会自动执行）。

或直接 `python main.py`。

## 打包

```bat
build_exe.bat
```

产物：`dist\ResidualCleaner.exe`（单文件，内置 UAC 管理员清单与图标）。

## 目录结构

```
main.py                 启动入口（提权 / 主题 / 主窗口）
preview.py              界面渲染预览（不触发真实扫描）
app/constants.py        品牌、12 款应用定义、扫描与清理路径
app/elevation.py        管理员检测与自提权
app/process_utils.py    进程 / 服务 / 计划任务命令行封装
app/registry_utils.py   注册表读写、备份、删除
app/cleanup.py          文件删除三轮策略 + 强力删除
app/scanner.py          应用检测、清理项枚举、残留扫描、深度扫盘
app/uninstaller.py      拆除引擎（不使用官方卸载器）
app/updater.py          GitHub Releases 检查更新 / 下载 / 自替换安装
app/tray.py             系统托盘控制器（菜单、气泡、最小化）
app/worker.py           四模式后台线程
app/icon_provider.py    程序化图标与徽标
app/ui/theme.py         配色与 QSS
app/ui/widgets.py       应用行 / 统计卡 / 控制台 / 宣传卡
app/ui/residual_dialog.py  残余项目检查小窗
app/ui/update_dialog.py 更新对话框（更新说明 / 进度 / 安装）
app/ui/main_window.py   左右分栏主窗口
tools/make_icon.py      生成 ICO / PNG / 对勾资源
```

## 许可证

源码随仓库一并公开，供阅读、学习与自行构建使用；发行包与代码的再分发限制见 [LICENSE](LICENSE)。

## 声明

本项目为第三方独立工具，与奇虎 360 无任何关联，未获得其授权或认可。
卸载与删除操作不可恢复，请在使用前确认数据已备份。
