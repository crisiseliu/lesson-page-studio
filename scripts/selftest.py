#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""技能自检：把 demo 复制到临时目录，完整跑一遍「克隆 → 体检」，验证技能本身可用。

不碰你的真实项目，跑完自动清理。

用法：
    python scripts/selftest.py
    python scripts/selftest.py --keep     # 保留临时目录，便于查看生成结果

退出码：0 = 全部通过；1 = 有失败项。
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
DEMO = SKILL_ROOT / "demo"

results: list[tuple[bool, str]] = []


def check(ok: bool, msg: str) -> None:
    results.append((ok, msg))
    print(("  ✅ " if ok else "  ❌ ") + msg)


def run(args: list[str], cwd: Path) -> tuple[int, str]:
    p = subprocess.run([sys.executable] + args, cwd=str(cwd), capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    ap = argparse.ArgumentParser(description="Lesson Page Studio 自检")
    ap.add_argument("--keep", action="store_true", help="保留临时目录")
    opts = ap.parse_args()

    print("=" * 60)
    print("Lesson Page Studio · 技能自检（demo 全链路）")
    print("=" * 60)

    if not (DEMO / "demo-site" / "day1.html").exists():
        print("ERROR: 找不到 demo/demo-site/day1.html，技能包不完整", file=sys.stderr)
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="lps-selftest-"))
    try:
        shutil.copytree(DEMO / "demo-site", tmp / "demo-site")

        cfg = json.loads((DEMO / "lesson-studio.json").read_text(encoding="utf-8"))
        cfg["project_root"] = str(tmp).replace("\\", "/")
        cfg_path = tmp / "lesson-studio.json"
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n临时工作区：{tmp}\n")

        print("[1] 克隆 Day 1 → Day 2")
        code, out = run([str(HERE / "clone_lesson.py"), "--config", str(cfg_path),
                         "--from", "1", "--to", "2",
                         "--title-zh", "自检课程", "--title-en", "Self Test Lesson",
                         "--summary", "技能自检生成的课程。"], tmp)
        if code != 0:
            print(out)
            check(False, "clone_lesson 执行失败")
            return 1
        for line in out.strip().splitlines():
            if line.strip().startswith("-"):
                print("     " + line.strip())
        check(True, "clone_lesson 执行成功")

        day2 = tmp / "demo-site" / "day2.html"
        html = day2.read_text(encoding="utf-8") if day2.exists() else ""
        print("\n[2] 机械替换结果")
        check(day2.exists(), "day2.html 已生成")
        check("Demo Day 2" in html, "<title> 编号已改为 Day 2")
        check("DEMO LEARNING · DAY 2" in html, "品牌行编号已改为 DAY 2")
        check("demo-day2-" in html, "存储前缀已改为 demo-day2-")
        check("demo-day1-" not in html, "旧前缀 demo-day1- 无残留")
        check("Demo_Day2_Record.png" in html, "导出文件名已改为 Day 2")
        idx = (tmp / "demo-site" / "index.html").read_text(encoding="utf-8")
        check('href="day2.html"' in idx, "首页已插入 Day 2 卡片")

        print("\n[3] 站点体检")
        code, out = run([str(HERE / "verify_site.py"), "--config", str(cfg_path)], tmp)
        tail = [l for l in out.strip().splitlines() if l.strip().startswith(("[FAIL]", "结果"))]
        for line in tail:
            print("     " + line.strip())
        check(code == 0, "verify_site 全通过")

        print("\n[4] 课程包模块（curriculum）")
        demo_cert = DEMO / "demo-cert.json"
        if not demo_cert.exists():
            print("     （跳过：找不到 demo/demo-cert.json）")
        else:
            site = tmp / "cert-site"
            site.mkdir()
            code, out = run([str(SKILL_ROOT / "curriculum" / "build_curriculum.py"),
                             "--cert", str(demo_cert), "--site", str(site), "--check"], tmp)
            check(code == 0, "build --check 内容校验通过")

            code, out = run([str(SKILL_ROOT / "curriculum" / "build_curriculum.py"),
                             "--cert", str(demo_cert), "--site", str(site)], tmp)
            check(code == 0 and "构建完成" in out, "build 生成 10 页 + 目录")

            code, out = run([str(SKILL_ROOT / "curriculum" / "verify_curriculum.py"),
                             "--cert", str(demo_cert), "--site", str(site)], tmp)
            check(code == 0 and "PASS" in out, "verify_curriculum 全通过")

            idx = site / "index.html"
            idx.write_text("<!doctype html><html><body><main><a class=\"card\" href=\"x.html\">A</a></main></body></html>",
                           encoding="utf-8")
            code, out = run([str(SKILL_ROOT / "curriculum" / "inject_cert_card.py"), "--index", str(idx),
                             "--slug", "demo", "--href", "demo/index.html",
                             "--name-zh", "示例课程", "--name-en", "Demo Prep"], tmp)
            code2, _ = run([str(SKILL_ROOT / "curriculum" / "inject_cert_card.py"), "--index", str(idx),
                            "--slug", "demo", "--href", "demo/index.html",
                            "--name-zh", "示例课程", "--name-en", "Demo Prep"], tmp)
            once = idx.read_text(encoding="utf-8").count("cert:demo:start")
            check(code == 0 and code2 == 0 and once == 1, "首页卡片注入且幂等（重复执行仅 1 张）")

            page1 = (site / "demo" / "day1.html").read_text(encoding="utf-8")
            check("demo-day1-checks" in page1 and "csp-day1" not in page1, "存储键按课程前缀隔离")
            check("data-answer=" in page1, "判题按钮携带 data-answer（数据驱动）")
            check('slug: "demo"' in page1 and 'total: 10' in page1 and "{{" not in page1,
                  "页面注入证书上下文（slug + total，无占位符残留）")
            check('src="/assets/sync.js' in page1, "同步脚本用根绝对路径（子目录页可命中）")
            check('assets/bilingual.js' in page1, "双语布局脚本已引入")
            check('lesson-nav' in page1 and 'rel="next"' in page1 and "nv off" in page1,
                  "导航键齐全（Day 1 无上一天 + 底部下一课）")
            check('class="logo"' in page1 and "__drowsyLogo" in page1, "页头与导出卡接入 LOGO")
            check("最长连续段" in page1 and "CERT_SLUG" in page1, "天数按完成课时统计（证书感知）")
            cat = (site / "demo" / "index.html").read_text(encoding="utf-8")
            check('"slug": "demo"' in cat and "/assets/sync.js" in cat,
                  "目录页同样接入云同步（v2.3 完整证书上下文）")
            check('class="logo"' in cat, "目录页页头有 LOGO")

            print("\n[5] 游戏化三件套（v2.3 · 热力图 / 每日一题 / 关卡地图）")
            eng = site / "demo"
            daily_p = eng / "daily.html"
            hm_p = eng / "assets" / "course-heatmap.js"
            pm_p = eng / "assets" / "course-pathmap.js"
            pool_p = eng / "assets" / "data" / "daily_questions.json"
            check(daily_p.exists() and hm_p.exists() and pm_p.exists() and pool_p.exists(),
                  "构建一次即产出 4 个游戏化文件")
            pool = json.loads(pool_p.read_text(encoding="utf-8")) if pool_p.exists() else {}
            qs = pool.get("questions") or []
            check(pool.get("count") == 2 and len(qs) == 2, "题池题数 = 块数（demo 2 块）")
            check(all(len(q.get("o") or []) == 4 and isinstance(q.get("a"), int)
                      and 0 <= q["a"] <= 3 and q.get("bi") for q in qs),
                  "题池题目均四选一、答案合法、带双语标记")
            dh = daily_p.read_text(encoding="utf-8") if daily_p.exists() else ""
            check("{{" not in dh and "STATS = null" in dh,
                  "每日一题默认纯本地模式且无未替换 token")
            check("sb_secret_" not in dh and "eeybslhshcldirbgoviz" not in dh and
                  "service_role" not in dh, "每日一题页零生产凭据")
            check('href="http://127.0.0.1:8000/demo/daily.html"' in dh,
                  "每日一题 canonical 指向课程子目录")
            check("course-heatmap.js" in cat and "course-pathmap.js" in cat and
                  'href="daily.html"' in cat, "目录页注入三件套引用与每日一题入口")
            check('"bossDays": [9, 10]' in cat and '"domainLabels"' in cat and
                  '"gridSelector"' in cat, "目录页上下文含 Boss 关 / 领域章名 / 网格选择器")
            hm = hm_p.read_text(encoding="utf-8") if hm_p.exists() else ""
            pm = pm_p.read_text(encoding="utf-8") if pm_p.exists() else ""
            check("'csp-day'" not in hm + pm and "TOTAL = 366" not in hm + pm and
                  "csp-catalog-view" not in pm, "游戏化脚本已去除 CSP 硬编码")
            check("window.DROWSY_CERT" in hm and "window.DROWSY_CERT" in pm,
                  "游戏化脚本按证书上下文参数化")
            check("demo-study-days" in page1 and "demo-day1-study-days" not in page1,
                  "课程页自然日键改为课程级（热力图可汇总 streak）")
            idx_ctx, idx_hm, idx_pm = (cat.find("window.DROWSY_CERT ="),
                                       cat.find("course-heatmap.js"), cat.find("course-pathmap.js"))
            check(0 <= idx_ctx < idx_hm and idx_ctx < idx_pm,
                  "证书上下文注入顺序在两个游戏化脚本之前")

            print("\n[6] 每日一题图片分享卡（v2.4）")
            qr_p = eng / "assets" / "qrcode.min.js"
            share_p = eng / "assets" / "course-daily-share.js"
            check(qr_p.exists() and share_p.exists(),
                  "一键生成 QR 编码器 + 图片分享卡脚本")
            qr_js = qr_p.read_text(encoding="utf-8") if qr_p.exists() else ""
            sc_js = share_p.read_text(encoding="utf-8") if share_p.exists() else ""
            check("QRCodeLite" in qr_js and "create" in qr_js,
                  "QR 编码器暴露 QRCodeLite.create 全局入口（零依赖）")
            check("DrowsyDailyShare" in sc_js and "toDataURL" in sc_js,
                  "分享卡脚本可同步生成 PNG（无图片异步加载）")
            check("drowsyhse.com" not in sc_js and "eeybslhshcldirbgoviz" not in sc_js
                  and "sb_secret_" not in sc_js and "sb_publishable_" not in sc_js,
                  "分享卡脚本零生产域名 / 凭据硬编码")
            check('id="dqShareCard"' in dh and "DrowsyDailyShare.open" in dh,
                  "每日一题页有常驻「生成分享卡」按钮并已接线")
            check("assets/qrcode.min.js?v=1" in dh and
                  "assets/course-daily-share.js?v=1" in dh and
                  "window.DROWSY_DAILY_CONFIG" in dh,
                  "分享卡资源引用与 DAILY_CONFIG 上下文注入齐全")
            check('"shareUrl"' in dh and "http://127.0.0.1:8000/demo/daily.html" in dh,
                  "二维码目标 URL 指向本课程每日一题页")

        fails = [m for ok, m in results if not ok]
        print("\n" + "-" * 60)
        if fails:
            print(f"结果：{len(fails)} 项失败")
            return 1
        print(f"结果：{len(results)} 项全部通过 ✅ 技能可用")
        return 0
    finally:
        if opts.keep:
            print(f"\n临时目录已保留：{tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
