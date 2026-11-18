"""失败归因与解决方案：把“删不掉”翻成用户能照做的下一步

每种失败都给三件事：为什么、现在能做什么、做不到时的退路。
不给“绕过安全机制”的野路子，只给正常的系统操作。
"""

from dataclasses import dataclass, field

DENIED = ("拒绝访问", "access is denied", "access denied", "0x5", "error 5")
LOCKED = ("正被使用", "being used", "占用", "另一个程序", "sharing violation", "32")
DRIVER = ("驱动", "内核", "driver", "fsflt", "antihijack", "selfprotection")
REG_PROTECT = ("注册表", "regdelete", "regopen", "自我保护的注册表")


@dataclass
class Solution:
    code: str
    title: str
    level: str = "warn"
    steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"code": self.code, "title": self.title, "level": self.level,
                "steps": list(self.steps)}


def _hit(text: str, words) -> bool:
    low = str(text or "").lower()
    return any(w.lower() in low for w in words)


def for_failure(kind: str, detail: str, pending: int = 0) -> Solution | None:
    """按清理项类型和报错文本给一条解决方案；正常成功返回 None。"""
    if pending:
        return Solution(
            "REBOOT_DELETE",
            "已登记重启删除",
            "info",
            ["文件句柄还被内核占着，删除动作已挂到下次开机执行",
             "重启后系统会在 360 自保护加载之前完成删除",
             "重启后打开本工具点「复查」确认是否清干净"],
        )

    if _hit(detail, DENIED) or _hit(kind, ("registry",)) and _hit(detail, REG_PROTECT):
        return Solution(
            "ACL_TAKEOVER",
            "权限被拒绝",
            "warn",
            ["工具会自动接管所有权并给 Administrators 完全控制，然后重试",
             "仍失败说明 360 自保护在内核层拦写，先在 360 主界面关闭「自我保护」",
             "关不掉就重启进安全模式，在安全模式下再跑一次一条龙"],
        )

    if _hit(detail, DRIVER):
        return Solution(
            "KERNEL_PROTECT",
            "被 360 内核驱动拦截",
            "danger",
            ["ZhuDongFangYu / 360FsFlt / 360AntiHijack 在驱动层拒绝删除",
             "先退出 360 托盘并关闭自我保护，再执行清理",
             "已有残留驱动就进安全模式清理，正常模式下删不掉是预期行为"],
        )

    if _hit(detail, LOCKED):
        return Solution(
            "FILE_LOCKED",
            "文件被占用",
            "warn",
            ["在任务管理器结束对应的 360 进程，或用工具里的「结束占用」",
             "关掉正在占用该目录的程序（解压软件、浏览器、壁纸客户端）",
             "仍占用就点清理，工具会把删除登记到下次重启"],
        )

    if kind in ("dir", "file", "dll"):
        return Solution(
            "RETRY_ADMIN",
            "删除未完成",
            "warn",
            ["确认程序是以管理员身份启动（标题栏应有「管理员」标记）",
             "点「重新扫描」定位剩余项后单独重试",
             "反复失败时进安全模式做一次全量清理"],
        )

    return Solution(
        "GENERIC",
        "这一项没删干净",
        "warn",
        ["右键「以管理员身份运行」后重试一次",
         "在日志里搜索该项路径，确认是否真的还在磁盘上",
         "把日志反馈到仓库 Issue，附上这项的类型和报错"],
    )


def for_protected(count: int, pack: str = "") -> Solution:
    return Solution(
        "REG_SAFE_PACK",
        f"{count} 项注册表被自我保护拦截",
        "danger",
        [f"工具已把这些键导出成安全模式清理脚本：{pack}" if pack else
         "工具已把这些键记入安全模式清理清单",
         "重启进安全模式（开机按 F8 或在系统设置里选「高级启动」）",
         "安全模式下运行生成的脚本，或在安全模式里再跑一次一条龙"],
    )


def collect(rows: list[dict]) -> list[Solution]:
    """把一次清理结果里所有失败行聚合成去重后的解决方案列表。"""
    out: dict[str, Solution] = {}
    for row in rows or []:
        if row.get("ok"):
            continue
        sol = row.get("solution")
        if isinstance(sol, dict):
            key = sol.get("code", "GEN")
            if key not in out:
                out[key] = Solution(key, sol.get("title", "未清理干净"),
                                    sol.get("level", "warn"),
                                    list(sol.get("steps", [])))
        else:
            sol = for_failure(row.get("kind", ""), row.get("detail", ""),
                              int(row.get("pending", 0) or 0))
            if sol and sol.code not in out:
                out[sol.code] = sol
    return list(out.values())
