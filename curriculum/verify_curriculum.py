# -*- coding: utf-8 -*-
"""校验一门证书课程的构建产物（页数 / 占位符 / canonical / 键隔离 / 必备 DOM / 目录卡）。

用法：python curriculum/verify_curriculum.py --cert <cert.json> --site <站点目录>
退出码：0 全过；1 有问题（逐条打印）。
"""
import argparse
import io
import json
import os
import re
import sys

REQUIRED_IDS = ["checkBtn", "a1", "a2", "bar", "progress", "exportBtn", "exportPreview", "status"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cert", required=True)
    ap.add_argument("--site", required=True)
    args = ap.parse_args()

    with io.open(args.cert, "r", encoding="utf-8") as f:
        cert = json.load(f)
    slug = cert["slug"]
    total = int(cert.get("days") or len(cert["blocks"]) * 5)
    d = os.path.join(args.site, slug)
    errs = []

    if not os.path.isdir(d):
        print(f"FAIL 目录不存在：{d}")
        sys.exit(1)

    pages = sorted([f for f in os.listdir(d) if re.fullmatch(r"day\d+\.html", f)],
                   key=lambda x: int(re.findall(r"\d+", x)[0]))
    if len(pages) != total:
        errs.append(f"页数 {len(pages)} != 期望 {total}")

    base = cert["site_url"].rstrip("/")
    prefixes = {}
    for i, name in enumerate(pages, 1):
        p = os.path.join(d, name)
        with io.open(p, "r", encoding="utf-8") as f:
            h = f.read()
        if "__TODO__" in h:
            errs.append(f"{name}: 仍有 __TODO__ 占位符")
        if "{{" in h and "}}" in h:
            errs.append(f"{name}: 仍有未替换的模板 token")
        if f'href="{base}/{slug}/{name}"' not in h:
            errs.append(f"{name}: canonical 不正确（期望 {base}/{slug}/{name}）")
        m = re.search(re.escape(slug) + r"-day(\d+)-checks", h)
        if not m:
            errs.append(f"{name}: 缺少本课程的 localStorage 键（{slug}-dayN-checks）")
        elif int(m.group(1)) != i:
            errs.append(f"{name}: localStorage 键的日号({m.group(1)}) 与文件名({i}) 不一致")
        prefixes.setdefault(m.group(1), []).append(name)
        for rid in REQUIRED_IDS:
            if f'id="{rid}"' not in h:
                errs.append(f"{name}: 缺少 DOM id {rid}")
        if name not in h and 'href="index.html"' not in h:
            errs.append(f"{name}: 缺少返回目录链接")
        if "data-answer=" not in h:
            errs.append(f"{name}: 判题按钮缺少 data-answer")

    cat = os.path.join(d, "index.html")
    if not os.path.exists(cat):
        errs.append("缺少课程目录 index.html")
    else:
        with io.open(cat, "r", encoding="utf-8") as f:
            ch = f.read()
        tiles = len(re.findall(r'class="tile"', ch))
        if tiles != total:
            errs.append(f"目录卡数 {tiles} != {total}")
        if f'href="{base}/{slug}/"' not in ch:
            errs.append("目录页 canonical 不正确")

    if errs:
        print(f"FAIL {len(errs)} 项：")
        for e in errs[:25]:
            print("  -", e)
        sys.exit(1)
    print(f"PASS {slug}: {total} 页 + 目录，canonical / 键隔离 / DOM / 判题属性全部正确")


if __name__ == "__main__":
    main()
