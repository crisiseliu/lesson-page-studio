# -*- coding: utf-8 -*-
"""从「证书名 + 专业方向 + 领域权重」生成课程内容脚手架（cert.json + CONTENT_TODO.md）。

用法：
  python curriculum/scaffold_cert.py \
    --slug niosh --name-zh "NIOSH 安全管理" --name-en "NIOSH Safety Management" \
    --issuer NIOSH --days 360 \
    --domains "D1=管理领导=Management Leadership=25,D2=风险评估=Risk Assessment=20,D3=控制=Controls=20,D4=法规=Regulation=20,D5=应急=Emergency=15" \
    --out ./niosh.json

  # 也可用文件：--domains-file domains.txt（每行 code=中文=英文=权重）

产物 cert.json 里每个块的文字字段都是 __TODO__，必须由作者（人或 AI）按
references/curriculum_authoring.md 的标准逐块填实；build_curriculum.py 会拒绝构建。
"""
import argparse
import io
import json
import math
import os
import sys

PLACEHOLDER = "__TODO__"


def parse_domains(spec):
    out = []
    for item in [x.strip() for x in spec.split(",") if x.strip()]:
        parts = item.split("=")
        if len(parts) != 4:
            sys.exit(f"领域格式错误：{item}（应为 code=中文=英文=权重）")
        code, zh, en, w = parts
        out.append({"code": code.strip(), "zh": zh.strip(), "en": en.strip(), "weight": float(w)})
    return out


def allocate(domains, blocks):
    """按权重把 blocks 个块分给各领域（最大余数法，保证每域至少 1 块）。"""
    if blocks < len(domains):
        sys.exit(f"块数({blocks}) 少于领域数({len(domains)})，请增加 --days")
    total_w = sum(d["weight"] for d in domains) or 1
    raw = [(d, blocks * d["weight"] / total_w) for d in domains]
    base = {d["code"]: max(1, int(math.floor(v))) for d, v in raw}
    used = sum(base.values())
    # 剩余块按小数部分从大到小分配
    order = sorted(raw, key=lambda x: -(x[1] - math.floor(x[1])))
    i = 0
    while used < blocks:
        base[order[i % len(order)][0]["code"]] += 1
        used += 1
        i += 1
    while used > blocks:  # 极端权重下回退
        for code in base:
            if used <= blocks:
                break
            if base[code] > 1:
                base[code] -= 1
                used -= 1
    return base


def block_stub(no, domain, idx_in_domain):
    return {
        "no": no,
        "domain": domain,
        "zh": PLACEHOLDER,
        "en": PLACEHOLDER,
        "points": [[PLACEHOLDER, PLACEHOLDER] for _ in range(5)],
        "terms": [[PLACEHOLDER, PLACEHOLDER] for _ in range(6)],
        "scenario": {
            "zh": PLACEHOLDER, "en": PLACEHOLDER,
            "options": [PLACEHOLDER] * 4, "answer": "A",
            "why_zh": PLACEHOLDER, "why_en": PLACEHOLDER,
        },
        "practice": [[PLACEHOLDER, PLACEHOLDER], [PLACEHOLDER, PLACEHOLDER]],
        "memory": PLACEHOLDER,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True, help="英文短标识，用于目录与本地存储键，如 niosh")
    ap.add_argument("--name-zh", required=True)
    ap.add_argument("--name-en", required=True)
    ap.add_argument("--issuer", default="")
    ap.add_argument("--short", default="", help="标题里的缩写，如 CSP；缺省用 slug 大写")
    ap.add_argument("--brand", default="", help="页头品牌行，如 CSP DAILY LEARNING")
    ap.add_argument("--file-base", default="", help="导出文件名前缀，如 CSP")
    ap.add_argument("--site-url", default="https://www.drowsyhse.com")
    ap.add_argument("--days", type=int, default=360, help="总课数，必须能被 5 整除")
    ap.add_argument("--domains", default="", help="code=中文=英文=权重，逗号分隔")
    ap.add_argument("--domains-file", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.days % 5:
        sys.exit("--days 必须是 5 的倍数（每块 5 课：概念/进阶/术语/情景/复盘）")
    spec = args.domains
    if args.domains_file:
        with io.open(args.domains_file, "r", encoding="utf-8") as f:
            spec = ",".join(line.strip() for line in f if line.strip() and not line.startswith("#"))
    if not spec:
        sys.exit("必须提供 --domains 或 --domains-file")
    domains = parse_domains(spec)

    blocks_n = args.days // 5
    alloc = allocate(domains, blocks_n)
    blocks, no = [], 1
    for d in domains:
        for i in range(alloc[d["code"]]):
            blocks.append(block_stub(no, d["code"], i))
            no += 1

    cert = {
        "slug": args.slug,
        "name_zh": args.name_zh,
        "name_en": args.name_en,
        "issuer": args.issuer,
        "short": args.short or args.slug.upper(),
        "brand": args.brand or (args.slug.upper() + " DAILY LEARNING"),
        "file_base": args.file_base or args.slug.upper(),
        "site_url": args.site_url,
        "days": args.days,
        "lessons_per_block": 5,
        "source_note_zh": ("官方机构不公开历年真题，也不公布官方题库。本页所有题目均由本站依据官方考试蓝图与公开考试规格自行编制，"
                           "仅作练习与自测参考，不代表真实考试的题目、难度或表述。"),
        "source_note_en": ("The certifying body does not release past exam questions or an official item bank. Every item here "
                           "was written from the published blueprint and exam specifications — for practice only, not a "
                           "representation of real exam items or difficulty."),
        "references": [{"zh": "官方考试蓝图 / Official blueprint", "en": "Blueprint", "url": "https://example.org/blueprint"}],
        "domains": domains,
        "blocks": blocks,
    }
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cert, f, ensure_ascii=False, indent=1)

    todo = [f"# {args.name_zh} 内容待办（{blocks_n} 块 × 5 课 = {args.days} 课）", "",
            "每块按下表填写 `cert.json` 的对应字段，标准见 `references/curriculum_authoring.md`。", "",
            "| 块 | 领域 | 覆盖课次 | 主题中文/英文 |", "|---|---|---|---|"]
    for b in blocks:
        start = (b["no"] - 1) * 5 + 1
        todo.append(f"| {b['no']} | {b['domain']} | Day {start}–{start + 4} | TODO |")
    todo += ["", "## 每块必填字段", "",
             "- `zh` / `en`：主题名，具体到考试任务，不要写“综合”“其他”",
             "- `points`：5 条要点，每条中英成对，含可执行做法或判断标准",
             "- `terms`：6 个英文术语 + 中文释义（考场原文用词优先）",
             "- `scenario`：四选一情景题 + 正确项 + 中英解析",
             "- `practice`：2 道简答（中英成对）",
             "- `memory`：一句中文记忆句", ""]
    todo_path = os.path.splitext(args.out)[0] + "-TODO.md"
    with io.open(todo_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(todo))

    print(f"脚手架已生成：{args.out}")
    print(f"块数 {blocks_n} / 课数 {args.days}；分配：{ {k: v for k, v in alloc.items()} }")
    print(f"待办清单：{todo_path}")
    print("下一步：逐块填写内容 → python curriculum/build_curriculum.py --cert <cert.json> --site <站点> --check")


if __name__ == "__main__":
    main()
