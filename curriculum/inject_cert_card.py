# -*- coding: utf-8 -*-
"""把一门证书课程作为「并列卡片」注入站点首页（幂等，带 markers）。

用法：
  python curriculum/inject_cert_card.py --index <站点>/index.html \
    --slug niosh --href niosh/index.html \
    --name-zh "NEBOSH IGC 备考" --name-en "NEBOSH IGC Prep" \
    --desc-zh "…" --desc-en "…" --kicker "CERT COURSE · 证书课程" --color "#7A4BA8"

  --remove 删除该卡片。
"""
import argparse
import io
import sys


def card_html(a):
    return f"""    <!--cert:{a.slug}:start-->
    <a class="card" href="{a.href}" style="--c:{a.color}">
      <div class="k">{a.kicker}</div>
      <h2>{a.name_zh} | {a.name_en}</h2>
      <p class="desc">{a.desc_zh}<span class="desc-en">{a.desc_en}</span></p>
      <p class="go">进入课程 / Start learning →</p>
    </a>
    <!--cert:{a.slug}:end-->
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--href", default="")
    ap.add_argument("--name-zh", default="")
    ap.add_argument("--name-en", default="")
    ap.add_argument("--desc-zh", default="")
    ap.add_argument("--desc-en", default="")
    ap.add_argument("--kicker", default="CERT COURSE · 证书课程")
    ap.add_argument("--color", default="#7A4BA8")
    ap.add_argument("--remove", action="store_true")
    args = ap.parse_args()

    with io.open(args.index, "r", encoding="utf-8") as f:
        html = f.read()

    start, end = f"<!--cert:{args.slug}:start-->", f"<!--cert:{args.slug}:end-->"
    has = start in html and end in html
    if args.remove:
        if not has:
            print("未找到该卡片，无需删除")
            return
        pre = html.split(start)[0]
        post = html.split(end, 1)[1].lstrip("\n")
        with io.open(args.index, "w", encoding="utf-8", newline="\n") as f:
            f.write(pre + post)
        print(f"已移除卡片 {args.slug}")
        return

    if not (args.href and args.name_zh and args.name_en):
        sys.exit("注入卡片需要 --href --name-zh --name-en")

    block = card_html(args)
    if has:
        pre = html.split(start)[0]
        post = html.split(end, 1)[1].lstrip("\n")
        new = pre + block + post
        action = "已更新"
    else:
        idx = html.rfind("</main>")
        if idx < 0:
            sys.exit("首页缺少 </main>，无法定位卡片插入点（请检查模板结构）")
        new = html[:idx] + block + html[idx:]
        action = "已插入"

    with io.open(args.index, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)
    print(f"{action}卡片 {args.slug} -> {args.href}")


if __name__ == "__main__":
    main()
