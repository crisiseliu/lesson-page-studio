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
    ap.add_argument("--no-engagement", action="store_true",
                    help="跳过 v2.3 三件套检查（配合 build_curriculum.py 的 --no-engagement）")
    ap.add_argument("--no-wrongbook", action="store_true",
                    help="跳过 v2.5 错题本检查（配合 build_curriculum.py 的 --no-wrongbook）")
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
        if re.search(re.escape(slug) + r"-day\d+-study-days", h):
            errs.append(f"{name}: 自然日键仍是每课独立（应为课程级 {slug}-study-days，否则热力图无法汇总）")

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

    # ---------- v2.3 游戏化三件套体检 ----------
    eng = cert.get("engagement") or {"enabled": True}
    eng_on = eng.get("enabled") is not False and not args.no_engagement
    if eng_on:
        daily_path = os.path.join(d, "daily.html")
        pool_path = os.path.join(d, "assets", "data", "daily_questions.json")
        hm_path = os.path.join(d, "assets", "course-heatmap.js")
        pm_path = os.path.join(d, "assets", "course-pathmap.js")
        qr_path = os.path.join(d, "assets", "qrcode.min.js")
        sc_path = os.path.join(d, "assets", "course-daily-share.js")
        wb_p = os.path.join(d, "assets", "course-wrongbook.js")
        rv_p = os.path.join(d, "review.html")
        qi_p = os.path.join(d, "assets", "data", "quiz_index.json")
        sql_p = os.path.join(d, "assets", "wrongbook_cert.sql")
        wb_cfg = eng.get("wrongbook") or {}
        wb_on = isinstance(wb_cfg, dict) and wb_cfg.get("enabled") is not False and not args.no_wrongbook
        products = [("每日一题页", daily_path), ("题池", pool_path),
                    ("热力图脚本", hm_path), ("关卡地图脚本", pm_path),
                    ("QR 编码器", qr_path), ("图片分享卡脚本", sc_path)]
        if wb_on:
            products += [("错题本页", rv_p), ("错题本脚本", wb_p),
                         ("错题回填索引", qi_p), ("错题本云迁移模板", sql_p)]
        for label, p in products:
            if not os.path.exists(p):
                errs.append(f"缺少 v2.5 产物：{label} {p}")

        if os.path.exists(daily_path):
            with io.open(daily_path, "r", encoding="utf-8") as f:
                dh = f.read()
            if "{{" in dh:
                errs.append("daily.html 存在未替换的模板 token")
            if f'href="{base}/{slug}/daily.html"' not in dh:
                errs.append("daily.html canonical 不正确")
            if "sb_secret_" in dh or "service_role" in dh:
                errs.append("daily.html 疑似含服务端密钥（只允许 anon/publishable key）")
            if "STATS = null" not in dh and "STATS = {" not in dh:
                errs.append("daily.html 云统计配置未正确注入")
            for s in ['id="dqShareCard"', 'assets/qrcode.min.js?v=1',
                      'assets/course-daily-share.js?v=1',
                      "window.DROWSY_DAILY_CONFIG", "DrowsyDailyShare.open",
                      '"shareUrl"']:
                if s not in dh:
                    errs.append(f"daily.html 缺少图片分享卡接入：{s}")
            if "eeybslhshcldirbgoviz" in dh:
                errs.append("daily.html 残留生产 Supabase 项目 ID（新证书必须自包含）")

        if os.path.exists(pool_path):
            try:
                with io.open(pool_path, "r", encoding="utf-8") as f:
                    pool = json.load(f)
                qs = pool.get("questions") or []
                if not qs:
                    errs.append("题池为空")
                if pool.get("cert") != slug:
                    errs.append("题池 cert 与证书 slug 不一致")
                excl = set(int(x) for x in ((eng.get("daily") or {}).get("exclude_blocks") or []))
                expect = len([b for b in cert["blocks"] if int(b.get("no", 0)) not in excl])
                if len(qs) != expect:
                    errs.append(f"题池题数 {len(qs)} != 可用块数 {expect}（排除 {sorted(excl)}）")
                for q in qs:
                    if len(q.get("o") or []) != 4 or not isinstance(q.get("a"), int) or not (0 <= q["a"] <= 3):
                        errs.append(f"题池 Day {q.get('day')} 选项/答案格式错误")
                    if not q.get("q") or len(q.get("w") or []) != 2:
                        errs.append(f"题池 Day {q.get('day')} 缺少中文题干或中英解析")
                    if not q.get("bi"):
                        errs.append(f"题池 Day {q.get('day')} 缺少双语标记 bi")
            except Exception as e:
                errs.append("题池 JSON 解析失败：" + str(e))

        script_checks = [("热力图", hm_path, ["window.DROWSY_CERT"]),
                         ("关卡地图", pm_path, ["window.DROWSY_CERT"]),
                         ("QR 编码器", qr_path, ["QRCodeLite"]),
                         ("图片分享卡", sc_path, ["DrowsyDailyShare"])]
        if wb_on:
            script_checks.append(("错题本", wb_p, ["window.WrongBook"]))
        for label, p, apis in script_checks:
            if not os.path.exists(p):
                continue
            with io.open(p, "r", encoding="utf-8") as f:
                js = f.read()
            for bad in ["'csp-day'", "TOTAL = 366", "csp-catalog-view",
                        "csp-study-days", "csp-vocab-v1",
                        "eeybslhshcldirbgoviz", "drowsyhse.com",
                        "sb_publishable_", "sb_secret_", "service_role"]:
                if bad in js:
                    errs.append(f"{label} 脚本残留 CSP/生产凭据硬编码：{bad}")
            for api in apis:
                if api not in js:
                    errs.append(f"{label} 脚本缺少全局入口 {api}")

        # ---------- 错题本 + 间隔复习（v2.5） ----------
        if wb_on:
            for name in pages:
                with io.open(os.path.join(d, name), "r", encoding="utf-8") as f:
                    ph = f.read()
                if "assets/course-wrongbook.js?v=1" not in ph:
                    errs.append(f"{name}: 缺少错题本采集脚本")
            if os.path.exists(daily_path):
                with io.open(daily_path, "r", encoding="utf-8") as f:
                    dh = f.read()
                if "assets/course-wrongbook.js?v=1" not in dh:
                    errs.append("daily.html: 缺少错题本采集脚本")
            if os.path.exists(rv_p):
                with io.open(rv_p, "r", encoding="utf-8") as f:
                    rh = f.read()
                if "{{" in rh:
                    errs.append("review.html 存在未替换的模板 token")
                if f'href="{base}/{slug}/review.html"' not in rh:
                    errs.append("review.html canonical 不正确")
                for s in ["window.DROWSY_CERT", "window.DROWSY_WRONGBOOK_CONFIG",
                          "assets/course-wrongbook.js?v=1", 'id="stats"', 'id="tabs"',
                          "WrongBook.ready", "待复习 / Due", "已掌握 / Mastered"]:
                    if s not in rh:
                        errs.append(f"review.html 缺少错题本接入：{s}")
                for bad in ["eeybslhshcldirbgoviz", "drowsyhse.com", "sb_secret_",
                            "service_role", "csp-wrongbook", "csp-day"]:
                    if bad in rh:
                        errs.append(f"review.html 残留 CSP/生产凭据硬编码：{bad}")
                i_ctx, i_wb = rh.find("window.DROWSY_CERT"), rh.find("course-wrongbook.js")
                if not (0 <= i_ctx < i_wb):
                    errs.append("review.html 证书上下文必须注入在错题本脚本之前")
            if os.path.exists(qi_p):
                try:
                    with io.open(qi_p, "r", encoding="utf-8") as f:
                        qi = json.load(f)
                    if qi.get("cert") != slug or not qi.get("count"):
                        errs.append("错题回填索引 cert/count 不正确")
                    for day, rec in (qi.get("questions") or {}).items():
                        if len(rec.get("o") or []) != 4 or not isinstance(rec.get("a"), int) or not (0 <= rec["a"] <= 3):
                            errs.append(f"错题回填索引 Day {day} 选项/答案格式错误")
                        if not rec.get("q") or len(rec.get("w") or []) != 2:
                            errs.append(f"错题回填索引 Day {day} 缺少题干或中英解析")
                except Exception as e:
                    errs.append("错题回填索引 JSON 解析失败：" + str(e))
            if os.path.exists(cat) and 'href="review.html"' not in ch:
                errs.append("目录页缺少错题本入口")

        if os.path.exists(cat):
            for s in ["assets/course-heatmap.js", "assets/course-pathmap.js",
                      'href="daily.html"', "bossDays", "domainLabels"]:
                if s not in ch:
                    errs.append(f"目录页缺少游戏化注入：{s}")
            i_ctx = ch.find("window.DROWSY_CERT =")
            i_hm = ch.find("course-heatmap.js")
            i_pm = ch.find("course-pathmap.js")
            if not (0 <= i_ctx < i_hm and i_ctx < i_pm):
                errs.append("目录页 DROWSY_CERT 上下文必须注入在两个游戏化脚本之前")

    if errs:
        print(f"FAIL {len(errs)} 项：")
        for e in errs[:25]:
            print("  -", e)
        sys.exit(1)
    print(f"PASS {slug}: {total} 页 + 目录，canonical / 键隔离 / DOM / 判题属性全部正确")


if __name__ == "__main__":
    main()
