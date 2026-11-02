# -*- coding: utf-8 -*-
"""把「证书配置 + 课程内容 JSON」构建成整套学习页与课程目录页。

用法：
  python curriculum/build_curriculum.py --cert <cert.json> --site <站点目录> [--check] [--force]

产物：
  <site>/<slug>/day1.html … dayN.html   每课一个自包含页（含 Canvas 学习记录卡）
  <site>/<slug>/index.html              该证书的课程目录（瀑布流卡片 + 本地进度）

校验不过（占位符未填、选项数不对、答案非 A-D 等）一律不写盘，退出码 2。
"""
import argparse
import html
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "templates", "page.html")
TYPES = [("概念", "Concept"), ("进阶", "In Depth"), ("术语", "Terminology"),
         ("情景", "Scenario"), ("复盘", "Review")]
PLACEHOLDER = "__TODO__"


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=False)


def attr(s):
    return html.escape(str(s if s is not None else ""), quote=True)


# ---------- 校验 ----------

def validate(cert):
    errs = []
    for k in ("slug", "name_zh", "name_en", "site_url", "blocks"):
        if not cert.get(k):
            errs.append(f"缺少字段 {k}")
    if errs:
        return errs
    blocks = cert["blocks"]
    days = int(cert.get("days") or len(blocks) * int(cert.get("lessons_per_block", 5)))
    if days != len(blocks) * int(cert.get("lessons_per_block", 5)):
        errs.append(f"days({days}) 与 blocks({len(blocks)}) × lessons_per_block 不一致")
    for b in blocks:
        no = b.get("no", "?")
        for k in ("zh", "en", "domain"):
            if not b.get(k) or PLACEHOLDER in str(b.get(k)):
                errs.append(f"块 {no}: {k} 未填写")
        pts = b.get("points") or []
        if len(pts) < 3:
            errs.append(f"块 {no}: points 至少 3 条（当前 {len(pts)}）")
        for p in pts:
            if len(p) != 2 or any((not x) or PLACEHOLDER in str(x) for x in p):
                errs.append(f"块 {no}: points 存在未填写的双语条目")
                break
        terms = b.get("terms") or []
        if len(terms) < 4:
            errs.append(f"块 {no}: terms 至少 4 个")
        for t in terms:
            if len(t) != 2 or any((not x) or PLACEHOLDER in str(x) for x in t):
                errs.append(f"块 {no}: terms 存在未填写的条目")
                break
        sc = b.get("scenario") or {}
        opts = sc.get("options") or []
        if len(opts) != 4:
            errs.append(f"块 {no}: scenario.options 必须 4 个（当前 {len(opts)}）")
        if (sc.get("answer") or "").strip().upper() not in list("ABCD"):
            errs.append(f"块 {no}: scenario.answer 必须是 A/B/C/D")
        for k in ("zh", "en", "why_zh", "why_en"):
            if not sc.get(k) or PLACEHOLDER in str(sc.get(k)):
                errs.append(f"块 {no}: scenario.{k} 未填写")
        for o in opts:
            if not o or PLACEHOLDER in str(o):
                errs.append(f"块 {no}: scenario.options 有未填写项")
                break
        prac = b.get("practice") or []
        if len(prac) != 2:
            errs.append(f"块 {no}: practice 必须 2 条")
        for p in prac:
            if len(p) != 2 or any((not x) or PLACEHOLDER in str(x) for x in p):
                errs.append(f"块 {no}: practice 存在未填写条目")
                break
    if not cert.get("domains"):
        errs.append("缺少 domains（领域与权重）")
    return errs


# ---------- 区块渲染 ----------

def sec_objective(cert, blk, n, t_zh, t_en):
    zh = "；".join(p[0] for p in blk["points"][:3])
    en = "; ".join(p[1] for p in blk["points"][:3])
    return f"""  <section class="card">
    <h2>今日目标 | Learning objectives</h2>
    <p>Day {n} · {esc(blk['zh'])}（{t_zh}）。完成本课后，你应能：{esc(zh)}。</p>
    <p class="muted">Day {n} · {esc(blk['en'])} ({t_en}). By the end you should be able to: {esc(en)}.</p>
    <div class="upload-line">
      <img id="avatarPreview" class="avatar-preview" alt="图片预览 / Photo preview">
      <label for="learnerPhoto"><b>上传个人图片（可选）/ Add a photo (optional)</b>
        <input id="learnerPhoto" type="file" accept="image/*">
      </label>
      <button type="button" id="clearPhotoBtn" class="clear-photo">清除已上传图片 / Remove photo</button>
    </div>
    <p class="hint">图片经过压缩后保存在当前浏览器，学习记录卡会带上它。/ The photo is compressed and stored in this browser and appears on your learning card.</p>
  </section>"""


def sec_concept(cert, blk, t_zh):
    items = "\n".join(
        f"      <li><b>{esc(p[0])}</b> — <span class=\"muted\">{esc(p[1])}</span></li>"
        for p in blk["points"])
    extra = ""
    if blk.get("memory"):
        extra = (f"\n    <div class=\"step\"><b>记忆句 / Memory aid:</b> {esc(blk['memory'])}</div>")
    if t_zh == "进阶":
        extra += ("\n    <p class=\"muted\">进阶要求：把上面的要点各配一个本单位/本行业的真实例子，"
                  "并写出一条可量化的改进指标。/ In-depth: pair each point with a real example "
                  "from your own site and one measurable improvement indicator.</p>")
    return f"""  <section class="card">
    <h2>核心概念 | Key concepts</h2>
    <ol>
{items}
    </ol>{extra}
  </section>"""


def sec_terms(cert, blk, t_zh):
    terms = blk["terms"] if t_zh == "术语" else blk["terms"][:4]
    lis = "\n".join(f"      <li><b>{esc(t[0])}</b> — {esc(t[1])}。</li>" for t in terms)
    tail = ("把以上术语全部加入英文术语表，并用每个词各写一句工作场景句。"
            "/ Add all terms to your glossary and write one workplace sentence for each."
            if t_zh == "术语" else
            "课后把本课术语补进你的英文术语表（每课 3–5 个）。"
            "/ Extend your glossary with 3–5 new terms after every lesson.")
    return f"""  <section class="card">
    <h2>术语起步 | Starter glossary</h2>
    <ol>
{lis}
    </ol>
    <p class="muted">{tail}</p>
  </section>"""


def sec_quiz(cert, blk, n, t_zh):
    sc = blk["scenario"]
    labels = "ABCD"
    opts = "\n".join(
        f"      <label><input type=\"radio\" name=\"q\" value=\"{labels[i]}\"> {labels[i]}. {esc(o)}</label>"
        for i, o in enumerate(sc["options"]))
    note = ""
    if cert.get("source_note_zh"):
        note = f"""    <div id="examNote" style="margin:0 0 14px;padding:12px 14px;border:1px solid #E7D6AC;border-left:4px solid #C99A2E;background:#FFFCF3;border-radius:10px;font-size:.85rem;line-height:1.7;color:#5B4A1E">
      <b style="display:block;margin-bottom:5px;color:#8A5A00">⚠️ 关于题目来源 / About these questions</b>
      {esc(cert['source_note_zh'])}<br><span style="color:#7A6A3E">{esc(cert.get('source_note_en', ''))}</span>
    </div>
"""
    return f"""  <section class="card">
    <h2>备考情景 | Study scenario</h2>
    <p>{esc(sc['zh'])}</p>
    <p class="muted">{esc(sc['en'])}</p>
{note}    <div id="quiz">
{opts}
    </div>
    <button id="checkBtn" type="button" data-answer="{attr(sc['answer'])}" data-why-zh="{attr(sc['why_zh'])}" data-why-en="{attr(sc['why_en'])}">提交答案 / Check answer</button>
    <div id="feedback" class="feedback" aria-live="polite"></div>
    <p class="muted">自编练习题，非官方真题，仅作学习参考。 / Original practice item, not an official exam question.</p>
  </section>"""


def sec_review(cert, blk, t_zh):
    p1, p2 = blk["practice"][0], blk["practice"][1]
    return f"""  <section class="card">
    <h2>巩固练习 | Quick review</h2>
    <p><b>1.</b> {esc(p1[0])}</p>
    <textarea id="a1" placeholder="用中英文简要回答 / Answer briefly"></textarea>
    <button class="shortBtn" data-id="a1" data-model-zh="{attr(p1[0])}" data-model-en="{attr(p1[1])}" type="button">确认提交 / Submit Answer</button>
    <div id="a1feedback" class="feedback" aria-live="polite"></div>
    <p><b>2.</b> {esc(p2[0])}</p>
    <textarea id="a2" placeholder="写下你的答案 / Write your answer"></textarea>
    <button class="shortBtn" data-id="a2" data-model-zh="{attr(p2[0])}" data-model-en="{attr(p2[1])}" type="button">确认提交 / Submit Answer</button>
    <div id="a2feedback" class="feedback" aria-live="polite"></div>
  </section>"""


def sec_progress(cert, n):
    return f"""  <section class="card">
    <h2>学习打卡与笔记 | Progress &amp; notes</h2>
    <label><input type="checkbox" class="task"> 完成情景题与两道巩固练习 / Complete the scenario and both prompts</label>
    <label><input type="checkbox" class="task"> 把本课术语加入英文术语表 / Add this lesson's terms to your glossary</label>
    <label><input type="checkbox" class="task"> 复习 Day {max(n - 1, 1)} 的要点 / Review the key points of Day {max(n - 1, 1)}</label>
    <label><input type="checkbox" class="task"> 向同伴复述本课一个要点（费曼法）/ Explain one key point to a partner (Feynman method)</label>
    <div class="bar" role="progressbar" aria-label="学习任务完成进度 / Learning task progress" aria-valuemin="0" aria-valuemax="4" aria-valuenow="0">
      <div id="bar"></div>
    </div>
    <p id="progress">已完成 0/4 项 / 0/4 tasks complete</p>
    <div class="step" id="streakStatus"><b>连续学习 / Learning streak:</b> 0 天 / 0 days</div>
    <textarea id="notes" placeholder="错题、现场案例、复习计划 / Errors, field examples, review plan"></textarea>
    <button id="saveBtn" type="button">保存本机进度 / Save on this device</button>
    <button class="alt" id="exportBtn" type="button">生成 PNG 学习记录 / Create PNG learning card</button>
    <p id="status" class="muted" role="status" aria-live="polite">进度保存在当前浏览器，不会自动跨设备同步。/ Progress is stored in this browser only.</p>
    <img id="exportPreview" alt="PNG 学习记录预览；可长按图片保存 / PNG card preview; long-press to save">
  </section>"""


def sec_refs(cert):
    refs = cert.get("references") or []
    lis = "\n".join(
        f"    <p><a href=\"{attr(r['url'])}\" target=\"_blank\" rel=\"noopener noreferrer\">{esc(r.get('zh') or r['url'])}</a></p>"
        for r in refs)
    return f"""  <section class="card">
    <h2>可靠来源 | Official references</h2>
{lis}
    <p class="muted">本课为一般性学习资料，不替代现场专业评估、法规要求或组织程序。/ Educational content only.</p>
    <a href="index.html">← 返回课程目录 / Back to catalog</a>
  </section>"""


def render_page(cert, blk, lesson_idx, n, total):
    t_zh, t_en = TYPES[lesson_idx % 5]
    title_zh = f"{blk['zh']} · {t_zh}"
    title_en = f"{blk['en']} · {t_en}"
    h1 = f"{esc(title_zh)} | {esc(title_en)}"
    title = f"{cert.get('short', cert['slug'].upper())} Day {n} · {esc(blk['en'])} · {t_en}"
    sections = "\n".join([
        sec_objective(cert, blk, n, t_zh, t_en),
        sec_concept(cert, blk, t_zh),
        sec_terms(cert, blk, t_zh),
        sec_quiz(cert, blk, n, t_zh),
        sec_review(cert, blk, t_zh),
        sec_progress(cert, n),
        sec_refs(cert),
    ])
    base = cert["site_url"].rstrip("/")
    tokens = {
        "{{TITLE}}": title,
        "{{DESC}}": f"{cert['name_zh']} Day {n}: {title_en}",
        "{{CANONICAL}}": f"{base}/{cert['slug']}/day{n}.html",
        "{{BRAND}}": f"{cert.get('brand', cert['slug'].upper() + ' DAILY LEARNING')} · DAY {n}",
        "{{H1}}": h1,
        "{{SUB}}": f"{esc(title_zh)} / {esc(title_en)}",
        "{{FOOT}}": f"{t_zh} · Day {n} / {t_en}",
        "{{FILEBASE}}": f"{cert.get('file_base', cert['slug'].upper())}_Day{n}_Learning_Record",
        "{{PREFIX}}": f"{cert['slug']}-day{n}",
        "{{SECTIONS}}": sections,
    }
    with io.open(TEMPLATE, "r", encoding="utf-8") as f:
        out = f.read()
    for k, v in tokens.items():
        out = out.replace(k, v)
    return out


COLORS = ["#155BA1", "#7A4BA8", "#B4600F", "#8A6D00", "#3F6E9E", "#B03A2E", "#2E7D32", "#5D6D7E"]


def render_catalog(cert, total):
    blocks = cert["blocks"]
    domains = {d["code"]: d for d in cert.get("domains", [])}
    cards = []
    for bi, b in enumerate(blocks):
        d = domains.get(b["domain"], {"zh": b["domain"], "en": b["domain"]})
        color = COLORS[bi % len(COLORS)]
        for li in range(int(cert.get("lessons_per_block", 5))):
            n = bi * 5 + li + 1
            t_zh, t_en = TYPES[li]
            cards.append(
                f"""      <a class="tile" href="day{n}.html" style="--c:{color}">
        <div class="tile-top"><span class="tile-no">DAY {n}</span><span class="tile-date">{esc(t_zh)}</span></div>
        <div class="tile-title">{esc(b['zh'])} · {esc(t_zh)}</div>
        <div class="tile-tag">{esc(d['code'])} · {esc(d['zh'])}</div>
      </a>""")
    legend = "\n".join(
        f'    <span class="lg"><i style="background:{COLORS[i % len(COLORS)]}"></i>{esc(d["code"])} · {esc(d["zh"])}</span>'
        for i, d in enumerate(cert.get("domains", [])))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(cert['name_zh'])} · 课程目录 | {esc(cert['name_en'])}</title>
<meta name="description" content="{esc(cert['name_zh'])} 全年 {total} 课，按考试蓝图领域组织，中英双语。">
<link rel="canonical" href="{cert['site_url'].rstrip('/')}/{cert['slug']}/">
<style>
:root{{--navy:#0F2A43;--paper:#FBFCFA;--ink:#17211F;--green:#176B55;--line:#E2E9E4;--muted:#66736E}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 Inter,"Noto Sans SC","PingFang SC","Microsoft YaHei",system-ui,sans-serif}}
header{{padding:26px 18px;background:linear-gradient(130deg,#0F2A43,#1C4A75);color:#fff}}
header h1{{margin:6px 0;font-size:1.5rem}}
header p{{margin:4px 0;opacity:.9;font-size:.92rem}}
header a{{color:#FFD98A}}
.wrap{{max-width:1080px;margin:auto;padding:16px}}
.legend{{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 16px}}
.lg{{font-size:.78rem;color:#53615b;background:#fff;border:1px solid var(--line);border-radius:99px;padding:4px 10px;display:inline-flex;align-items:center;gap:6px}}
.lg i{{width:9px;height:9px;border-radius:3px;display:inline-block}}
.pstrip{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:18px}}
.pbar{{height:9px;background:#e7edf5;border-radius:20px;overflow:hidden;margin:8px 0}}
.pbar div{{height:100%;background:var(--green);width:0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}}
.tile{{background:#fff;border:1px solid var(--line);border-top:4px solid var(--c);border-radius:14px;padding:14px;text-decoration:none;color:inherit;display:block}}
.tile-top{{display:flex;justify-content:space-between;font-size:.72rem;color:var(--muted)}}
.tile-no{{font-weight:700;color:var(--c)}}
.tile-title{{margin-top:8px;font-weight:650;font-size:.95rem;line-height:1.45}}
.tile-tag{{display:inline-block;margin-top:8px;font-size:.7rem;color:#53615b;background:#F4F7F4;border-radius:99px;padding:3px 10px}}
footer{{text-align:center;color:var(--muted);font-size:12px;padding:24px 16px 36px}}
</style>
</head>
<body>
<header>
  <div style="font-size:.8rem;opacity:.85">{esc(cert.get('issuer', ''))} · {esc(cert['name_en'])}</div>
  <h1>{esc(cert['name_zh'])} | Lesson Catalog</h1>
  <p>Day 1 – Day {total} · 按考试蓝图领域组织，中英双语 / Organized by blueprint domains, bilingual</p>
  <p><a href="../index.html">← 返回首页 / Home</a></p>
</header>
<div class="wrap">
  <div class="legend">
{legend}
  </div>
  <div class="pstrip">
    <span style="font-size:.85rem;color:var(--muted)">我的学习进度 / My progress：已学 <b id="pDone">0</b> / {total} 天 · <span id="pPct">0%</span></span>
    <div class="pbar" role="progressbar" aria-valuemin="0" aria-valuemax="{total}" aria-valuenow="0"><div id="pFill"></div></div>
  </div>
  <div class="grid">
{chr(10).join(cards)}
  </div>
</div>
<footer>{esc(cert['name_zh'])} · 教育内容，非官方考试材料 / Educational content, not official exam material</footer>
<script>
(function () {{
  var TOTAL = {total}, prefix = '{cert['slug']}-day', done = 0;
  function key(n) {{ return prefix + n + '-checks'; }}
  for (var n = 1; n <= TOTAL; n++) {{
    try {{
      var v = JSON.parse(localStorage.getItem(key(n)) || '[]');
      if (v && v.some(Boolean)) done++;
    }} catch (e) {{}}
  }}
  var pct = TOTAL ? Math.round(done / TOTAL * 100) : 0;
  var d = document.getElementById('pDone'), p = document.getElementById('pPct'), f = document.getElementById('pFill');
  if (d) d.textContent = done;
  if (p) p.textContent = pct + '%';
  if (f) f.style.width = pct + '%';
}})();
</script>
</body>
</html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cert", required=True)
    ap.add_argument("--site", required=True)
    ap.add_argument("--check", action="store_true", help="只校验，不写盘")
    args = ap.parse_args()

    with io.open(args.cert, "r", encoding="utf-8") as f:
        cert = json.load(f)

    errs = validate(cert)
    if errs:
        print(f"校验失败：{len(errs)} 处问题（未写盘）")
        for e in errs[:20]:
            print("  -", e)
        sys.exit(2)

    total = int(cert.get("days") or len(cert["blocks"]) * 5)
    if args.check:
        print(f"校验通过：{len(cert['blocks'])} 块 / {total} 课")
        return

    out_dir = os.path.join(args.site, cert["slug"])
    os.makedirs(out_dir, exist_ok=True)
    for bi, blk in enumerate(cert["blocks"]):
        for li in range(5):
            n = bi * 5 + li + 1
            page = render_page(cert, blk, li, n, total)
            with io.open(os.path.join(out_dir, f"day{n}.html"), "w", encoding="utf-8", newline="\n") as f:
                f.write(page)
    with io.open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(render_catalog(cert, total))

    print(f"构建完成：{total} 页 + 目录 -> {out_dir}")
    print(f"首页卡片注入：python curriculum/inject_cert_card.py --index <站点>/index.html "
          f"--slug {cert['slug']} --href {cert['slug']}/index.html")


if __name__ == "__main__":
    main()
