#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""依赖与环境自检：告诉你能跑到第几步、缺什么、怎么补。

用法：
    python scripts/preflight.py                          # 自动找 lesson-studio.json
    python scripts/preflight.py --config ./lesson-studio.json
    python scripts/preflight.py --root D:/MySite

退出码：0 = 无 FAIL（可继续）；1 = 有 FAIL（第 1 步就跑不了）。
WARN 不影响退出码，但会在"能力矩阵"里标明哪几步会降级。
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _config  # noqa: E402

OK, WARN, FAIL = "OK", "WARN", "FAIL"
rows: list[tuple[str, str, str]] = []


def add(level: str, item: str, detail: str) -> None:
    rows.append((level, item, detail))
    tag = {"OK": "[ OK ]", "WARN": "[WARN]", "FAIL": "[FAIL]"}[level]
    print(f"{tag} {item}" + (f" —— {detail}" if detail else ""))


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=25)
        return p.returncode, (p.stdout or p.stderr or "").strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)


def find_browser(cfg: dict) -> str | None:
    explicit = _config.deep(cfg, "browser", "executable")
    if explicit and Path(explicit).exists():
        return explicit
    env = os.environ.get("BROWSER_PATH")
    if env and Path(env).exists():
        return env
    cands = [
        r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        r"C:/Program Files/Microsoft/Edge/Application/msedge.exe",
        r"C:/Program Files/Google/Chrome/Application/chrome.exe",
        r"C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for c in cands:
        if Path(c).exists():
            return c
    for name in ("microsoft-edge", "google-chrome", "chromium", "chromium-browser"):
        p = shutil.which(name)
        if p:
            return p
    return None


def node_resolves(module: str, cwd: Path | None) -> bool:
    code, _ = run(["node", "-e", f"require.resolve('{module}')"], cwd=cwd)
    return code == 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Lesson Page Studio 环境自检")
    ap.add_argument("--config", help="配置文件路径（lesson-studio.json）")
    ap.add_argument("--root", help="项目根目录，覆盖配置里的 project_root")
    args = ap.parse_args()

    cfg_path = _config.find_config(args.config)
    cfg = _config.load(args.config)

    print("=" * 62)
    print("Lesson Page Studio · 环境自检")
    print("=" * 62)

    # --- 1. Python ---
    if sys.version_info >= (3, 9):
        add(OK, f"Python {platform.python_version()}", "")
    else:
        add(FAIL, f"Python {platform.python_version()} 过低", "需要 3.9+（用到类型注解与 Path.unlink(missing_ok)）")

    # --- 2. 配置 ---
    if cfg_path and Path(cfg_path).exists():
        add(OK, f"配置文件 {Path(cfg_path).name}", str(cfg_path))
    else:
        add(WARN, "未找到 lesson-studio.json", "将只用命令行参数与内置默认值；建议先复制 scripts/config.example.json 到项目根目录改名")

    root_raw = args.root or cfg.get("project_root")
    if not root_raw:
        add(FAIL, "未指定项目根目录", "加 --root <路径>，或在 lesson-studio.json 里填 project_root")
        root = None
    else:
        root = Path(root_raw)
        if root.is_dir():
            add(OK, f"项目根目录 {root}", "")
        else:
            add(FAIL, f"项目根目录不存在: {root}", "检查 project_root / --root")
            root = None

    site_dir = cfg.get("site_dir", "edgeone-release")
    site = root / site_dir if root else None
    file_pattern = cfg.get("file_pattern", "day{n}.html")

    # --- 3. 站点目录与模板页 ---
    if site and site.is_dir():
        add(OK, f"站点目录 {site.name}/", str(site))
        pages = sorted(site.glob("*.html"))
        tpl_num, tpl_path = None, None
        prefix = file_pattern.split("{n}")[0]
        for p in pages:
            stem = p.stem[len(prefix):] if p.stem.startswith(prefix) else ""
            if stem.isdigit():
                n = int(stem)
                if tpl_num is None or n > tpl_num:
                    tpl_num, tpl_path = n, p
        if tpl_path:
            add(OK, f"模板页 {tpl_path.name}", f"{tpl_path.stat().st_size} 字节，克隆源 = Day {tpl_num}")
        else:
            add(FAIL, f"站点目录下没有符合 {file_pattern} 的页面", "第 1 步需要一页现成模板；先手工做一页，或改用 --file-pattern")
        idx = site / "index.html"
        add(OK if idx.exists() else WARN, "index.html", "" if idx.exists() else "缺首页，克隆时会跳过卡片插入")
    elif site:
        add(FAIL, f"站点目录不存在: {site}", "检查 site_dir 配置")

    # --- 4. Node 与前端依赖 ---
    node = shutil.which("node")
    node_ok = False
    if node:
        code, out = run(["node", "-v"])
        ver = out.lstrip("v").split(".")[0] if out else "?"
        node_ok = ver.isdigit() and int(ver) >= 18
        add(OK if node_ok else WARN, f"Node {out or '?'}",
            "" if node_ok else "建议 18+（playwright-core 与 qrcode 需要）")
    else:
        add(WARN, "未安装 Node", "无 Node：JS 语法检查跳过、浏览器回归与海报生成不可用（页面生成与部署仍可做）")

    tools_dir = root / "tools" if root else None
    probe_cwd = tools_dir if tools_dir and tools_dir.is_dir() else root
    has_playwright = bool(node) and probe_cwd is not None and node_resolves("playwright-core", probe_cwd)
    has_qrcode = bool(node) and probe_cwd is not None and node_resolves("qrcode", probe_cwd)
    if node:
        where = str(probe_cwd) if probe_cwd else "项目根目录（或 tools/）"
        add(OK if has_playwright else WARN, "playwright-core",
            "" if has_playwright else f"在 {where} 下 npm i playwright-core（第 4 步回归 / 第 5 步海报需要）")
        add(OK if has_qrcode else WARN, "qrcode",
            "" if has_qrcode else f"在 {where} 下 npm i qrcode（海报二维码需要；没有则海报无码）")

    browser = find_browser(cfg)
    add(OK if browser else WARN, "浏览器内核", browser or "未探测到 Edge/Chrome；用 browser.executable 配置指定")

    # --- 5. Git ---
    git = shutil.which("git")
    is_repo = False
    if git:
        add(OK, "git", shutil.which("git"))
        if root:
            code, _ = run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root)
            if code == 0:
                is_repo = True
                _, remote = run(["git", "remote", "get-url", "origin"], cwd=root)
                expect = _config.deep(cfg, "deploy", "git_remote_contains")
                if expect and expect not in remote:
                    add(WARN, "git remote 与配置不符", f"实际 {remote or '(无)'}，配置期望含 {expect}")
                else:
                    add(OK, "git remote", remote or "(无)")
                _, mail = run(["git", "config", "user.email"], cwd=root)
                want_mail = _config.deep(cfg, "deploy", "git_author_email")
                if want_mail and mail and mail != want_mail:
                    add(WARN, "提交邮箱与配置不符", f"实际 {mail}；Vercel 会以作者无权限为由拦截构建（如需改：git config user.email {want_mail}）")
                else:
                    add(OK, "提交邮箱", mail or "(未设置)")
            else:
                add(WARN, "不是 git 仓库", "第 6 步的 Vercel 自动构建不可用；可只走 EdgeOne")
    else:
        add(WARN, "未安装 git", "无法通过 push 触发 Vercel 构建；EdgeOne 部署不受影响")

    # --- 6. EdgeOne CLI ---
    edgeone = shutil.which("edgeone")
    proj = _config.deep(cfg, "deploy", "edgeone_project")
    if edgeone:
        add(OK, "EdgeOne CLI", edgeone)
    else:
        add(WARN, "未安装 EdgeOne CLI", "正式站部署不可用；安装：npm i -g edgeone（或按官方文档）" + (f"，项目名 {proj}" if proj else ""))

    # --- 7. 换行风格 ---
    if root and (root / ".gitattributes").exists():
        txt = (root / ".gitattributes").read_text(encoding="utf-8", errors="replace")
        if "-text" in txt:
            add(OK, "换行保护 .gitattributes", "已禁用自动换行转换（避免线上字节数与本地不一致）")
        else:
            add(WARN, ".gitattributes 未禁用换行转换", "建议加一行 `* -text`，否则 Windows 提交后线上字节数会不一致")
    elif root:
        add(WARN, "无 .gitattributes", "建议创建并写入 `* -text`")

    # --- 能力矩阵 ---
    can_clone = root is not None and bool(site and site.is_dir())
    can_verify = can_clone and bool(node)
    can_regress = can_verify and has_playwright and bool(browser)
    can_poster = can_regress and has_qrcode
    can_git = bool(git) and is_repo
    can_edgeone = bool(edgeone)

    print("\n" + "-" * 62)
    print("能力矩阵（能跑到哪一步）")
    print("-" * 62)
    steps = [
        ("第1步 克隆模板", can_clone, "缺项目目录/模板页"),
        ("第2步 写正文", can_clone, "AI 手工改写，无外部依赖"),
        ("第3步 静态体检", can_verify, "无 Node：标签/ID/资源检查可用，内联 JS 语法检查跳过"),
        ("第4步 浏览器回归", can_regress, "缺 playwright-core 或浏览器：跳过截图与导出验证"),
        ("第5步 海报与分享卡", can_poster, "缺 qrcode：海报可出但无二维码"),
        ("第6a步 git/Vercel", can_git, "缺 git，或该目录不是 git 仓库"),
        ("第6b步 EdgeOne", can_edgeone, "缺 CLI 或未登录"),
    ]
    for name, ok, why in steps:
        print(f"  {'✅' if ok else '⚠️ '} {name:<20} {'' if ok else why}")

    fails = [r for r in rows if r[0] == FAIL]
    warns = [r for r in rows if r[0] == WARN]
    print(f"\n合计：{len(rows) - len(fails) - len(warns)} 项通过 / {len(warns)} 项告警 / {len(fails)} 项失败")
    if fails:
        print("结论：存在阻塞项，先修 FAIL 再跑第 1 步。")
        return 1
    if warns:
        print("结论：可继续，但按上面的能力矩阵选择路径（降级步骤会跳过对应验证，需人工确认）。")
        return 0
    print("结论：环境齐备，六步全流程可跑。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
