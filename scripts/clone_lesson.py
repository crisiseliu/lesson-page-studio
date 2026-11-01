#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""克隆上一课页面，自动完成新增一天所需的全部机械替换，并在首页插入课程卡片。

只做机械工作（编号 / 存储前缀 / 导出文件名 / 首页卡片），
正文内容由调用方（AI）随后改写 7 个区块。

用法示例：
    # 推荐：配置写进 lesson-studio.json，命令就短了
    python clone_lesson.py --from 6 --to 7 \
        --title-zh "考试英语术语系统" --title-en "Exam English Terminology" \
        --summary "蓝图高频术语分类记忆法、词根词缀与易混词对。"

    # 不用配置文件（全部参数写命令行）
    python clone_lesson.py --root D:/CSP-Daily-Learning --from 6 --to 7 \
        --title-zh "考试英语术语系统" --title-en "Exam English Terminology"

    # 只预览不写盘
    python clone_lesson.py --from 6 --to 7 --title-zh X --title-en Y --dry-run
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _config  # noqa: E402


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def write_bytes(p: Path, text: str) -> None:
    # 按字节写入，避免 Windows 把 \n 转成 \r\n 导致线上字节数不一致
    p.write_bytes(text.encode("utf-8"))


def replace_exact(text: str, old: str, new: str, label: str, min_count: int = 1) -> tuple[str, int]:
    n = text.count(old)
    if n < min_count:
        print(f"ERROR: 未找到足够的锚点 [{label}]：期望 ≥{min_count} 处，实际 {n} 处", file=sys.stderr)
        print(f"       锚点内容: {old!r}", file=sys.stderr)
        sys.exit(3)
    return text.replace(old, new), n


def main() -> int:
    ap = argparse.ArgumentParser(description="克隆上一课并完成机械替换")
    ap.add_argument("--config", help="配置文件 lesson-studio.json 路径（不填则自动查找）")
    ap.add_argument("--root", help="项目根目录，例如 D:/CSP-Daily-Learning")
    ap.add_argument("--from", dest="src", type=int, required=True, help="源课程编号（已有）")
    ap.add_argument("--to", dest="dst", type=int, required=True, help="目标课程编号（新建）")
    ap.add_argument("--site-dir", help="站点目录名，默认取配置或 edgeone-release")
    ap.add_argument("--file-pattern", help="页面文件名模板，默认 day{n}.html")
    ap.add_argument("--prefix-base", help="localStorage 前缀基名，默认 csp-day")
    ap.add_argument("--export-base", help="导出文件名模板，默认 CSP_Day{n}_Learning_Record.png")
    ap.add_argument("--doc-title-base", help="<title> 前缀模板，默认 CSP Day {n}")
    ap.add_argument("--brand-line", help="页头与画布上的品牌行模板，默认 CSP DAILY LEARNING · DAY {n}")
    ap.add_argument("--title-zh", default="", help="中文标题（写入首页卡片）")
    ap.add_argument("--title-en", default="", help="英文标题（写入首页卡片与 <title>）")
    ap.add_argument("--summary", default="", help="首页卡片摘要（双语一句话）")
    ap.add_argument("--no-index", action="store_true", help="不修改 index.html")
    ap.add_argument("--dry-run", action="store_true", help="只打印将做的改动，不写盘")
    args = ap.parse_args()

    cfg = _config.load(args.config)
    root_raw = _config.pick(args.root, cfg, "project_root")
    if not root_raw:
        print("ERROR: 未指定项目根目录。加 --root <路径>，或建 lesson-studio.json 填 project_root", file=sys.stderr)
        return 4
    args.site_dir = _config.pick(args.site_dir, cfg, "site_dir", "edgeone-release")
    args.file_pattern = _config.pick(args.file_pattern, cfg, "file_pattern", "day{n}.html")
    args.prefix_base = _config.pick(args.prefix_base, cfg, "prefix_base", "csp-day")
    args.export_base = _config.pick(args.export_base, cfg, "export_base", "CSP_Day{n}_Learning_Record.png")
    args.doc_title_base = _config.pick(args.doc_title_base, cfg, "doc_title_base", "CSP Day {n}")
    args.brand_line = _config.pick(args.brand_line, cfg, "brand_line", "CSP DAILY LEARNING · DAY {n}")

    root = Path(root_raw)
    site = root / args.site_dir
    src_html = site / args.file_pattern.format(n=args.src)
    dst_html = site / args.file_pattern.format(n=args.dst)

    if not src_html.exists():
        print(f"ERROR: 源页面不存在: {src_html}", file=sys.stderr)
        return 2
    if dst_html.exists():
        print(f"ERROR: 目标页面已存在，拒绝覆盖: {dst_html}", file=sys.stderr)
        print("       如需重建请先手动删除或备份。", file=sys.stderr)
        return 2

    html = read(src_html)
    log = []

    # 1) <title>
    old_title, cnt = replace_exact(
        html,
        args.doc_title_base.format(n=args.src),
        args.doc_title_base.format(n=args.dst),
        "<title> 中的课程编号",
    )
    html = old_title
    log.append(f"<title> 编号替换 {cnt} 处")

    # 1b) <title> 中的英文标题（提供了 --title-en 才替换）
    if args.title_en:
        new_t = args.doc_title_base.format(n=args.dst) + " · " + args.title_en
        html, n = re.subn(r"<title>.*?</title>", f"<title>{new_t}</title>", html, count=1, flags=re.S)
        if n:
            log.append(f"<title> 英文标题更新为：{new_t}")

    # 2) 品牌行（页头 small + canvas fillText，通常 2 处）
    html, cnt = replace_exact(
        html,
        args.brand_line.format(n=args.src),
        args.brand_line.format(n=args.dst),
        "品牌行 DAY 编号",
        min_count=2,
    )
    log.append(f"品牌行 DAY 编号替换 {cnt} 处")

    # 3) localStorage 前缀：不同模板写法不同（逐键字面量可能 9 处，常量拼接可能只 1 处）
    html, cnt = replace_exact(
        html,
        f"{args.prefix_base}{args.src}-",
        f"{args.prefix_base}{args.dst}-",
        "localStorage 前缀",
        min_count=1,
    )
    log.append(f"存储前缀替换 {cnt} 处")
    if cnt < 4:
        log.append(f"⚠️  前缀只命中 {cnt} 处，模板可能用常量拼接；创建后请自检："
                   f'grep -c "{args.prefix_base}{args.src}-" 新页面 → 必须为 0')

    # 4) 导出文件名
    html, cnt = replace_exact(
        html,
        args.export_base.format(n=args.src),
        args.export_base.format(n=args.dst),
        "导出 PNG 文件名",
    )
    log.append(f"导出文件名替换 {cnt} 处")

    # 5) 首页卡片
    index = site / "index.html"
    index_new = None
    if not args.no_index:
        if not index.exists():
            print(f"WARN: 找不到 {index}，跳过首页卡片插入", file=sys.stderr)
        else:
            idx = read(index)
            if args.file_pattern.format(n=args.dst) in idx:
                print("INFO: 首页已存在该课程卡片，跳过插入")
            else:
                if not (args.title_zh and args.title_en):
                    print("ERROR: 需要 --title-zh 与 --title-en 才能生成首页卡片", file=sys.stderr)
                    return 2
                card_tpl = _config.pick(None, cfg, "index_card_title", "Day {n} · {zh} / {en}")
                link_tpl = _config.pick(None, cfg, "index_card_link", "打开第 {n} 天课程 / Open Day {n} lesson →")
                card_title = card_tpl.format(n=args.dst, zh=args.title_zh, en=args.title_en)
                card_link = link_tpl.format(n=args.dst, zh=args.title_zh, en=args.title_en)
                card = (
                    f'<section class="card"><h2>{card_title}</h2>'
                    f'<p>{args.summary}</p>'
                    f'<a href="{args.file_pattern.format(n=args.dst)}">{card_link}</a></section>'
                )
                if "<main>" not in idx:
                    print("ERROR: index.html 中找不到 <main> 锚点", file=sys.stderr)
                    return 2
                index_new = idx.replace("<main>", "<main>" + card, 1)
                log.append("首页已插入新课程卡片（置于最上方）")

    print("将执行：")
    for line in log:
        print("  -", line)

    if args.dry_run:
        print("\n[dry-run] 未写入任何文件")
        return 0

    write_bytes(dst_html, html)
    if index_new is not None:
        write_bytes(index, index_new)

    print(f"\n✅ 已创建 {dst_html.relative_to(root)}（{dst_html.stat().st_size} 字节）")
    print("\n下一步（必须手写，不要自动化）：")
    print("  1. 改写 7 个区块正文：今日目标 / 核心概念 / 术语起步 / 备考情景 / 巩固练习 / 学习打卡 / 可靠来源")
    print("  2. 替换页头下方的橙色徽章文案（主题中文名 + 英文名 + 副标题）")
    print("  3. 跑 verify_site.py 与无头浏览器回归，再部署")
    return 0


if __name__ == "__main__":
    sys.exit(main())
