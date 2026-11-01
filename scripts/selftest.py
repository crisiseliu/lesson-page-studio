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
