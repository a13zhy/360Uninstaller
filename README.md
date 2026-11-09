# 残留清理卫士 ResidualCleaner

Windows 10 / 11 上的 360 系列软件深度卸载与残留清理工具。不调用官方卸载程序，直接按项拆除，卸载完自动扫盘查残留。

界面用 PySide6 写成，Win11 风格，右侧控制台逐项回报执行过程。闭源分发，只提供 exe / zip。

## 下载

最新版本 **[v1.2.4.261109](https://github.com/a13zhy/360Uninstaller/releases/tag/v1.2.4.261109)**

| 文件 | 说明 |
| --- | --- |
| `ResidualCleaner.exe` | 单文件版，双击后按 UAC 提示允许管理员权限即可运行 |
| `ResidualCleaner-v1.2.4.261109-win64.zip` | 程序 + 使用说明 + 许可协议 + 两张界面图 + build-info |

## 它能做什么

- **自己拆，不用官方卸载器**：按 进程 → 服务 → 计划任务 → 目录 → 文件 → 注册表 → 快捷方式 的顺序逐项拆除，每一项单独报成功或失败。
- **无权访问也能删**：清属性 → Restart Manager 查出占用进程（只结束 360 的进程）→ `icacls /reset` + `takeown /a` 接管所有权 → 递归重删 → 仍被锁住的登记为下次开机由系统删除。
- **残余检查小窗**：卸载结束后自动扫盘，按类型彩色标记，可勾选删除；删失败的项留在列表里，点“重试删除选中项”再试一次。
- **360 一键全部移除**：主界面宣传卡一键勾选全部已检测组件，先出确认清单，再开始执行。
- **逐项回报**：右侧控制台实时写进度和失败原因（翻译成“拒绝访问（ACL 或系统保护）”“文件正在使用”这类人话），同时落到日志文件。

## 界面

![主界面](https://github.com/a13zhy/360Uninstaller/releases/download/v1.2.4.261109/preview-main.png)

![残余项目检查](https://github.com/a13zhy/360Uninstaller/releases/download/v1.2.4.261109/preview-residual.png)

## 怎么用

1. 双击 `ResidualCleaner.exe`，UAC 提示点“是”。
2. 首次启动会显示使用说明，读完点“我已了解，继续”。
3. 程序自动扫描，左侧列出检测到的应用，勾选要卸载的。
4. 点“卸载选中应用”或“360 一键清除”，确认清单后开始执行。
5. 结束后自动弹出残余检查小窗，勾选残留项并删除，失败项可重试。
6. 若提示“已登记重启后删除”，重启一次即可由系统在开机时清掉。

## 本版更新 v1.2.4.261109

这一版只解决一件事：360 卸载后那些报“拒绝访问”“文件正在使用”、怎么都删不掉的文件夹。

- **删除链路重写**：清属性（只读 / 系统 / 隐藏）→ 长路径自动加 `\\?\` 前缀 → Restart Manager 查占用进程并只结束 360 自己的进程 → `icacls /reset` 去掉拒绝项、恢复继承 → `takeown /a` 交给 Administrators → 递归重删 → 兜底用 `MoveFileEx` 登记到下次开机删除。
- **只 takeown 不够**：ACL 里的 DENY 项优先，必须先 `/reset` 再 takeown，否则照样拒绝访问。
- **占用检测修好**：Restart Manager 只认文件，目录要先展开成文件列表再登记，否则永远查不到占用者。
- **失败原因说人话**：拒绝访问 / 文件正在使用 / 已标记删除等待句柄释放 / 当前被 xxx.exe 占用；非管理员运行会额外提示需要管理员权限。
- **界面同步**：结果行新增“N 项待重启后删除”，登记项不再算失败；残余小窗写明“重启一次即完成”。
- **360 自我保护**：服务关键词扩到 10 个，补 `360selfprotection`、`360antihacker`、`360fsflt`、`qhactivedefense`、`qhsafemonitor` 等。

## 安全说明

- 所有批量操作先列清单，确认后才执行；不做静默批量删除。
- 没有后台守护进程，不会开机自启，不会自动重启系统。
- 重启删除走的是系统自带的 `PendingFileRenameOperations`，不需要常驻程序。
- 注册表删除前备份到 `%LOCALAPPDATA%\ResidualCleaner\reg_backup`，日志在 `%LOCALAPPDATA%\ResidualCleaner\cleaner.log`。
- 删除不可恢复，请先备份重要数据。

## 校验值

```
SHA-256 (ResidualCleaner.exe)
E554614C240CC6C6EB5B5A49E3CE0BBFE671B20BCBDF8E7907C533CFA94CF1A1

SHA-256 (ResidualCleaner-v1.2.4.261109-win64.zip)
B19148D897CE61131B427D71F6D5CEC01D15CE3324AAC65D57099E06F2D264F4
```

## 系统要求

Windows 10 / 11 64 位，管理员权限。单文件 exe 首次启动需要解包，约 3-5 秒才出窗口。

## 声明

本工具为第三方独立工具，与奇虎 360 无任何关联，仅用于卸载自己电脑上的相关软件。源码不公开，Issue 和反馈请直接开在本仓库。
