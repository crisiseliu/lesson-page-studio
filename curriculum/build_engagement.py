# -*- coding: utf-8 -*-
"""游戏化注入层构建器（lesson-page-studio v2.3）。

由 build_curriculum.py 在构建课程包时自动调用，一条命令产出「今天 1/2/3 效果」：
  1) 热力图 + streak 冻结 + 成就徽章  -> <site>/<slug>/assets/course-heatmap.js
  3) 关卡地图（蛇形路径 / 双视图 / Boss）-> <site>/<slug>/assets/course-pathmap.js
  2) 每日一题（中英对照 / 图片分享卡）  -> <site>/<slug>/daily.html
                                          + assets/data/daily_questions.json（从 cert.json 块情景题提取）
                                          + assets/qrcode.min.js（MIT 单文件 QR 编码器）
                                          + assets/course-daily-share.js（与生产站共用的卡片脚本）

设计要点：
- 三件套自包含在 <site>/<slug>/，不碰站点根 assets、不改已上线的 CSP 脚本。
- 两个 JS 零构建 token，运行时读目录页注入的 window.DROWSY_CERT（本模块生成 context）。
- 分享卡二维码按 SHARE_URL 运行时生成（默认 <站点>/<slug>/daily.html），不预置图片、
  不依赖 CDN / Node / Python 库；答案不上卡，只显示作答结果。
- 每日一题默认【纯本地模式】：零外部依赖、零凭据。仅当 cert.json 显式配置
  engagement.daily.stats + supabase.{url,anon_key} 时才注入云统计（凭据来自用户配置，
  绝不写进技能包；只用 anon/publishable key，禁止 service_role / sb_secret_）。
- 题池按块号种子确定性洗牌选项（对齐站点 gen_daily_pool.py 口径），答案分布均匀。

用法（一般不由人直接跑）：
    python curriculum/build_engagement.py --cert <cert.json> --site <站点目录>
"""
import argparse
import datetime
import html
import io
import json
import os
import random
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(HERE, "engagement", "templates")
ANS_MAP = {"A": 0, "B": 1, "C": 2, "D": 3}
SHUFFLE_SEED = 90125  # 与站点 gen_daily_pool.py 同口径


# ---------- 配置 ----------

def engagement_config(cert):
    """取 engagement 配置；enabled=false 返回 None（整层关闭）。"""
    eng = cert.get("engagement")
    if eng is None:
        eng = {"enabled": True}          # 未配置时默认开启（向后兼容老 cert.json）
    if not isinstance(eng, dict):
        raise ValueError("engagement 必须是对象")
    if eng.get("enabled") is False:
        return None
    return eng


def total_days(cert):
    return int(cert.get("days") or len(cert["blocks"]) * int(cert.get("lessons_per_block", 5)))


def domain_maps(cert):
    labels = {}
    for i, d in enumerate(cert.get("domains", [])):
        labels[str(d["code"])] = d.get("zh", d["code"])
        labels["Domain " + str(i + 1)] = d.get("zh", d["code"])
    return labels


def build_context(cert, eng, total):
    """生成目录页 window.DROWSY_CERT 的完整上下文（两个 JS 的唯一配置源）。"""
    domains = cert.get("domains", [])
    boss = eng.get("boss_days", None)
    if boss is None:
        boss_days = [total - 1, total]
    elif isinstance(boss, list) and len(boss) == 2:
        boss_days = [int(boss[0]), int(boss[1])]
    elif isinstance(boss, list) and len(boss) == 0:
        boss_days = [0, 0]               # 显式空数组 = 关闭 Boss 关
    else:
        raise ValueError("engagement.boss_days 必须是长度为 2 的数组或空数组")
    chapter = eng.get("chapter_labels") or {}
    return {
        "slug": cert["slug"],
        "total": total,
        "label": cert.get("short") or cert["slug"].upper(),
        "gridSelector": eng.get("grid_selector") or ".grid",
        "tileSelector": eng.get("tile_selector") or '.tile[href^="day"]',
        "minNodes": int(eng.get("min_nodes") or min(5, total)),
        "bossDays": boss_days,
        "chapterLabels": {str(k): v for k, v in chapter.items()},
        "domainLabels": domain_maps(cert),
        "vocabKey": eng.get("vocab_key") or "",
        "dailyEpoch": (eng.get("daily") or {}).get("epoch") or datetime.date.today().isoformat(),
        "dailyPoolUrl": "assets/data/daily_questions.json?v=" +
                        str((eng.get("daily") or {}).get("pool_version", 1)),
        "domainCount": len(domains),
    }


# ---------- 每日一题题池 ----------

def build_question_pool(cert, eng, total):
    """从每个块的 scenario 四选一情景题生成题池（中文主显 + 英文次级）。"""
    daily = eng.get("daily") or {}
    exclude = set(int(x) for x in (daily.get("exclude_blocks") or []))
    lpb = int(cert.get("lessons_per_block", 5))
    dom = {d["code"]: d for d in cert.get("domains", [])}
    questions, skipped = [], 0
    for b in cert["blocks"]:
        no = int(b.get("no", 0))
        if no in exclude:
            skipped += 1
            continue
        sc = b.get("scenario") or {}
        opts = sc.get("options") or []
        ans = str(sc.get("answer", "")).strip().upper()
        if len(opts) != 4 or ans not in ANS_MAP or not sc.get("zh"):
            skipped += 1
            continue
        opts_en = sc.get("options_en") or []
        idx = list(range(4))
        random.Random(SHUFFLE_SEED + no).shuffle(idx)
        d = dom.get(b.get("domain"), {"code": b.get("domain", ""), "zh": "", "en": ""})
        day = (no - 1) * lpb + 1
        if day > total:
            skipped += 1
            continue
        questions.append({
            "day": day,
            "q": sc["zh"],
            "qe": sc.get("en", ""),
            "o": [opts[i] for i in idx],
            "oe": [opts_en[i] for i in idx] if len(opts_en) == 4 else [],
            "a": idx.index(ANS_MAP[ans]),
            "w": [sc.get("why_zh", ""), sc.get("why_en", "")],
            "t": (str(d["code"]) + " · " + str(d.get("zh", ""))).strip(' ·'),
            "te": d.get("en", ""),
            "src": "course",
            "bi": True,
        })
    questions.sort(key=lambda q: q["day"])
    pool = {
        "version": 1,
        "generated": datetime.date.today().isoformat(),
        "cert": cert["slug"],
        "count": len(questions),
        "questions": questions,
    }
    return pool, skipped


# ---------- 云统计配置（可选） ----------

def stats_config(cert, eng):
    daily = eng.get("daily") or {}
    if not daily.get("stats"):
        return None
    sb = daily.get("supabase") or {}
    url, key = sb.get("url"), sb.get("anon_key")
    if not url or not key:
        raise ValueError("engagement.daily.stats=true 时必须提供 supabase.url 与 supabase.anon_key")
    if "secret" in str(key).lower() or "service_role" in str(key).lower():
        raise ValueError("只允许 anon / publishable key；禁止 service_role / sb_secret_ 进入前端")
    return {
        "url": url.rstrip("/"),
        "anonKey": key,
        "submit": sb.get("submit_fn") or "daily_challenge_submit_cert",
        "stats": sb.get("stats_fn") or "daily_challenge_stats_cert",
    }


def js_literal(obj):
    """JSON -> 内联 <script> 字面量，防 </script> 提前闭合。"""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


# ---------- daily.html 渲染 ----------

def render_daily(cert, eng, ctx, stats):
    site = cert["site_url"].rstrip("/")
    canonical = site + "/" + cert["slug"] + "/daily.html"
    daily = eng.get("daily") or {}
    tokens = {
        "{{CERT_NAME_ZH}}": html.escape(cert["name_zh"], quote=False),
        "{{CERT_NAME_EN}}": html.escape(cert["name_en"], quote=False),
        "{{BRAND}}": html.escape(cert.get("brand") or (cert["slug"].upper() + " DAILY LEARNING"), quote=False),
        "{{SITE_URL}}": site + "/",
        "{{SLUG}}": cert["slug"],
        "{{CANONICAL}}": canonical,
        "{{EPOCH}}": ctx["dailyEpoch"],
        "{{POOL_URL}}": ctx["dailyPoolUrl"],
        "{{POOL_LABEL_ZH}}": daily.get("pool_label_zh") or "本课程内容 / Course lesson",
        "{{POOL_LABEL_EN}}": daily.get("pool_label_en") or "课程练习题 / Course practice",
        "{{SHARE_URL}}": daily.get("share_url") or canonical,
        "{{STATS_CONFIG}}": js_literal(stats),
        "{{DAILY_CONFIG}}": js_literal({
            "certName": cert["name_zh"],
            "brand": cert.get("brand") or (cert["slug"].upper() + " DAILY LEARNING"),
            "shareUrl": daily.get("share_url") or canonical,
            "slug": cert["slug"],
        }),
    }
    with io.open(os.path.join(TPL, "course-daily.html"), "r", encoding="utf-8") as f:
        out = f.read()
    for k, v in tokens.items():
        out = out.replace(k, v)
    if "{{" in out:
        raise ValueError("daily.html 模板存在未替换 token")
    return out


# ---------- 主入口 ----------

def build(cert, out_dir):
    """生成三件套，返回目录页上下文 dict；engagement.enabled=false 时返回 None。"""
    eng = engagement_config(cert)
    if eng is None:
        return None
    total = total_days(cert)
    pool, skipped = build_question_pool(cert, eng, total)
    if not pool["questions"]:
        raise ValueError("题池为空：cert.json 的 blocks[].scenario 均不可用，无法生成每日一题")
    stats = stats_config(cert, eng)      # 校验放在写盘前
    ctx = build_context(cert, eng, total)
    daily_html = render_daily(cert, eng, ctx, stats)

    out = out_dir
    assets = os.path.join(out, "assets")
    data_dir = os.path.join(assets, "data")
    os.makedirs(data_dir, exist_ok=True)
    shutil.copyfile(os.path.join(TPL, "course-heatmap.js"), os.path.join(assets, "course-heatmap.js"))
    shutil.copyfile(os.path.join(TPL, "course-pathmap.js"), os.path.join(assets, "course-pathmap.js"))
    # 每日一题图片分享卡：二维码编码器（MIT 单文件）+ 与生产站共用的卡片脚本
    shutil.copyfile(os.path.join(TPL, "qrcode.min.js"), os.path.join(assets, "qrcode.min.js"))
    shutil.copyfile(os.path.join(TPL, "course-daily-share.js"), os.path.join(assets, "course-daily-share.js"))
    with io.open(os.path.join(data_dir, "daily_questions.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(pool, f, ensure_ascii=False, separators=(",", ":"))
    with io.open(os.path.join(out, "daily.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(daily_html)
    return ctx, {"questions": pool["count"], "skipped": skipped,
                 "stats": "cloud" if stats else "local", "bossDays": ctx["bossDays"],
                 "domains": ctx["domainCount"]}


def main():
    ap = argparse.ArgumentParser(description="单独构建某证书课程的游戏化三件套")
    ap.add_argument("--cert", required=True)
    ap.add_argument("--site", required=True, help="站点根目录（不是 <site>/<slug>）")
    args = ap.parse_args()
    with io.open(args.cert, "r", encoding="utf-8") as f:
        cert = json.load(f)
    out = os.path.join(args.site, cert["slug"])
    if not os.path.isdir(out):
        sys.exit("课程目录不存在，请先跑 build_curriculum.py：" + out)
    res = build(cert, out)
    if res is None:
        print("engagement.enabled=false，已跳过")
        return
    ctx, meta = res
    print("游戏化三件套已生成 ->", out)
    print("  热力图 course-heatmap.js / 关卡地图 course-pathmap.js / daily.html / 题池",
          meta["questions"], "题（跳过", meta["skipped"], "块）")
    print("  图片分享卡 qrcode.min.js + course-daily-share.js（二维码指向 SHARE_URL）")
    print("  每日一题模式:", meta["stats"], "| Boss:", meta["bossDays"], "| 领域:", meta["domains"])


if __name__ == "__main__":
    main()
