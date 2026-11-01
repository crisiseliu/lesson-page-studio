#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""学习站点发布目录体检：结构 / JS 语法 / 资源 / 编号一致性。

可对任意同类静态学习站点目录运行。

用法：
    python verify_site.py --config ./lesson-studio.json     # 推荐
    python verify_site.py --root D:/CSP-Daily-Learning
    python verify_site.py --dir D:/CSP-Daily-Learning/edgeone-release

退出码：0 全通过；1 有 FAIL。
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _config  # noqa: E402

PAIRED = ["html", "head", "body", "div", "section", "main", "script", "style", "p", "h2", "span", "button", "textarea", "label"]

problems = []
EXPORT_RE = r"CSP_Day(\d+)_Learning_Record"
BRAND_MARK = ""
FILE_PATTERN = "day{n}.html"


def export_regex(base: str) -> str:
    """把 CSP_Day{n}_Learning_Record.png 这类模板转成带捕获组的正则。"""
    parts = re.split(r"\{n\}", base)
    return r"(\d+)".join(re.escape(p) for p in parts)


def fail(f: str, msg: str) -> None:
    problems.append(f"[FAIL] {f}: {msg}")


def warn(f: str, msg: str) -> None:
    print(f"  [WARN] {f}: {msg}")


def check_tags(name: str, html: str) -> None:
    for tag in PAIRED:
        opens = len(re.findall(rf"<{tag}(?=[\s>])", html, re.I))
        closes = len(re.findall(rf"</{tag}\s*>", html, re.I))
        if opens != closes:
            fail(name, f"<{tag}> 标签不配对：开 {opens} / 闭 {closes}")


def check_ids(name: str, html: str) -> None:
    # 注意：不能用 \bid= ——会误匹配 data-id=
    ids = re.findall(r'(?<![\w-])id="([^"]+)"', html)
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        fail(name, f"重复 id：{sorted(dup)}")
    return ids


def check_inline_js(name: str, html: str) -> None:
    node = shutil.which("node")
    if not node:
        warn(name, "未安装 node，跳过内联 JS 语法检查")
        return
    scripts = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S | re.I)
    if not scripts:
        return
    for i, code in enumerate(scripts, 1):
        if not code.strip():
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fh:
            fh.write(code)
            tmp = fh.name
        proc = subprocess.run([node, "--check", tmp], capture_output=True, text=True, encoding="utf-8", errors="replace")
        Path(tmp).unlink(missing_ok=True)
        if proc.returncode != 0:
            tail = (proc.stderr or "").strip().splitlines()
            fail(name, f"内联脚本 #{i} 语法错误：{tail[-1] if tail else 'unknown'}")
        else:
            print(f"  [ OK ] {name}: 内联脚本 #{i} 语法通过")


def check_resources(name: str, html: str, site: Path) -> None:
    refs = re.findall(r'(?:src|href)="([^"]+)"', html)
    for r in refs:
        if r.startswith(("http://", "https://", "//", "#", "mailto:", "tel:", "data:")):
            continue
        target = (site / r.split("?")[0].split("#")[0]).resolve()
        if not target.exists():
            fail(name, f"引用的本地资源不存在：{r}")


def check_day_consistency(name: str, html: str) -> None:
    stem_prefix = FILE_PATTERN.split("{n}")[0]
    m_file = re.match(rf"{re.escape(stem_prefix)}(\d+)", Path(name).stem, re.I)
    day_file = int(m_file.group(1)) if m_file else None
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    day_title = None
    if title:
        m = re.search(r"Day\s*(\d+)", title.group(1))
        day_title = int(m.group(1)) if m else None
    brand = re.findall(r"DAY\s+(\d+)", html)
    export = re.findall(EXPORT_RE, html)

    if day_file and day_title and day_file != day_title:
        fail(name, f"<title> 编号 Day {day_title} 与文件名 day{day_file} 不一致")
    if day_file and brand:
        bad = {b for b in brand if int(b) != day_file}
        if bad:
            fail(name, f"品牌行 DAY 编号 {sorted(bad)} 与文件名 day{day_file} 不一致")
    if day_file and export:
        bad = {e for e in export if int(e) != day_file}
        if bad:
            fail(name, f"导出文件名编号 {sorted(bad)} 与文件名 day{day_file} 不一致")

    prefixes = sorted(set(re.findall(r"['\"]([a-z0-9-]*day(\d+))-\w+", html)))
    if prefixes:
        print(f"  [info] {name}: 存储前缀 {sorted({p[0] for p in prefixes})}")


def main() -> int:
    global EXPORT_RE, BRAND_MARK, FILE_PATTERN
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", help="配置文件 lesson-studio.json 路径")
    ap.add_argument("--root", help="项目根目录（自动拼 site_dir）")
    ap.add_argument("--dir", help="直接指定站点目录")
    args = ap.parse_args()

    cfg = _config.load(args.config)
    BRAND_MARK = _config.pick(None, cfg, "brand_mark", "")
    FILE_PATTERN = _config.pick(None, cfg, "file_pattern", "day{n}.html")
    EXPORT_RE = export_regex(_config.pick(None, cfg, "export_base", "CSP_Day{n}_Learning_Record.png"))

    site_dir = cfg.get("site_dir", "edgeone-release")
    if args.dir:
        site = Path(args.dir)
    elif args.root:
        site = Path(args.root) / site_dir
    elif cfg.get("project_root"):
        site = Path(cfg["project_root"]) / site_dir
    else:
        print("ERROR: 请用 --config、--root 或 --dir 指定目标（不要依赖别人的默认路径）", file=sys.stderr)
        return 2

    if not site.exists():
        print(f"ERROR: 目录不存在: {site}", file=sys.stderr)
        return 2

    pages = sorted(site.glob("*.html"))
    if not pages:
        print(f"ERROR: {site} 下没有 html 文件", file=sys.stderr)
        return 2

    print(f"体检目录: {site}\n发现 {len(pages)} 个页面\n")

    for p in pages:
        html = p.read_text(encoding="utf-8")
        print(f"— {p.name} ({p.stat().st_size} 字节)")
        check_tags(p.name, html)
        check_ids(p.name, html)
        check_inline_js(p.name, html)
        check_resources(p.name, html, site)
        check_day_consistency(p.name, html)

        if "vercel.live" in html:
            fail(p.name, "残留 Vercel 注入脚本（vercel.live）")
        if "http://127.0.0.1" in html or "localhost:" in html:
            warn(p.name, "含本地调试地址引用")
        if BRAND_MARK and BRAND_MARK not in html and p.name.startswith(FILE_PATTERN.split("{n}")[0]):
            warn(p.name, f"未找到品牌标识「{BRAND_MARK}」")

    # 站点级
    if not (site / "favicon.ico").exists():
        warn("(site)", "缺少 favicon.ico")
    if not (site / "index.html").exists():
        fail("(site)", "缺少 index.html")

    print()
    if problems:
        print(f"结果：{len(problems)} 项 FAIL")
        for x in problems:
            print(" ", x)
        return 1
    print("结果：全部通过 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
