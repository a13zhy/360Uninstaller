这版只盯一个事：注册表清理时那串"拒绝访问"。先说你贴的日志到底发生了什么，再说程序改了什么。

## 一、日志里的三类结果，其实不是一回事

```
✘ HKLM\SOFTWARE\WOW6432Node\360Safe — 错误: 拒绝访问。
✘ HKLM\SOFTWARE\360Safe — 错误: 系统找不到指定的注册表项或值。
✘ HKCU\Software\360Safe — 错误: 拒绝访问。
```

- **"系统找不到指定的注册表项或值"** 不是错误。它表示这个键本来就不存在（64 位系统上 360 只写 32 位视图，`HKLM\SOFTWARE\360Safe` 常常是空的）。上一版把它当失败计数，属误报。
- **"拒绝访问"** 才是真问题，但成因有三种，处理方式完全不同：
  1. 进程没有真正提权（只有 Medium 完整性级别）；
  2. 键的 ACL 被写死（属主是 TrustedInstaller，或挂着 Deny ACE，Deny 优先于 Allow，加 Allow 没用）；
  3. 360 的自我保护驱动在内核层直接拦截注册表写入——ACL 看起来完全正常（Administrators 完全控制、没有 Deny），照样返回拒绝访问。

## 二、这版怎么处理

**1. 不存在就是已清理**
先判断键到底在不在，再决定要不要动手。`ERROR_FILE_NOT_FOUND` 统一按"已清理"上报，不再计入失败。

**2. 权限接管：取得所有权 → 重建 DACL → 再删**
`reg delete` 失败后，程序不再直接放弃，而是走原生注册表 API：

- 启用 `SeTakeOwnershipPrivilege`、`SeRestorePrivilege`、`SeBackupPrivilege`、`SeSecurityPrivilege`；
- 以 `WRITE_OWNER` 打开键，把属主改成 `Administrators`（用内置 SID `S-1-5-32-544`，不受系统语言影响）；
- 以 `WRITE_DAC` 打开，**整条 DACL 重建成"Administrators 完全控制"**——这一步会连带清掉所有 Deny ACE，只加 Allow 是删不掉 Deny 的；
- 递归处理子键（每个子键有自己的安全描述符，不逐个接管，删到子键仍会被拒）；
- 最后 `RegDeleteTree` + `RegDeleteKeyEx`，按 64/32 位视图分别执行。

**3. 32 位视图不再重复重定向**
路径里已经写了 `WOW6432Node` 时，不再叠加 `KEY_WOW64_32KEY`，避免变成 `WOW6432Node\WOW6432Node` 这种实际不存在的路径——这也是上一版把"存在"误判成"不存在"的一个来源。

**4. 认得出"驱动拦截"，不再甩一句拒绝访问**
删除彻底失败时，程序会检查正在运行的 `ZhuDongFangYu.exe`、`360tray.exe`、`360Safe.exe`、`360sd.exe`，以及 `ZhuDongFangYu`、`360SelfProtection`、`360AntiHacker`、`QHActiveDefense`、`360rp` 等服务。命中就明确写"被 360 自我保护拦截（XXX 运行中），在线无法删除"，而不是让你对着"拒绝访问"猜。

**5. 自动生成安全模式清理包**
被拦截的键会汇总进一个清理包，放在 `%LOCALAPPDATA%\ResidualCleaner\safe_mode\`：

- `安全模式清理_时间戳.cmd`：只删除清单里那几个键，逐条回显；
- `待清理清单_时间戳.txt`：清单 + 操作步骤。

安全模式不加载 360 的自保护驱动，这些键在那时是可直接删除的。程序不会替你改启动配置、不会自动重启，什么时候进安全模式由你决定。

## 三、怎么用

1. 正常卸载/一键清除，能删的当场删掉；
2. 控制台出现 `N 项注册表被 360 自我保护拦截` 时，说明剩下的必须离线处理；
3. 重启 → 开机按住 Shift（或 `msconfig` 选安全模式）→ 进安全模式后以管理员身份双击那个 `.cmd`；
4. 正常重启回系统，再打开本程序扫一遍，清单应该空了。

如果不想进安全模式，也可以在 360 设置里临时关闭"自我保护"，再跑一次清理——但这一步得你在 360 界面里手动确认，程序不会替你去关别人的防护。

## 四、下载

- `ResidualCleaner.exe` — 免安装单文件，双击即用（内置 UAC 管理员清单）。
- `ResidualCleaner-v1.2.6.261110-win64.zip` — 程序 + 使用说明 + 许可 + 本说明。
- `ResidualCleaner-v1.2.6.261110-src.zip` — 完整源码。

系统要求：Windows 10 / 11 64 位，管理员权限。

## 说明

- 仍然不做后台静默删除、不开机自启、不自动重启系统；被占用的文件只登记到下次开机由系统删除。
- 删除前仍会 `reg export` 备份到 `%LOCALAPPDATA%\ResidualCleaner\reg_backup\`。
- 权限接管只针对要清理的那棵子树，不碰其它注册表内容。
- 本工具是第三方独立项目，与奇虎 360 无任何关联，删除操作不可恢复。
