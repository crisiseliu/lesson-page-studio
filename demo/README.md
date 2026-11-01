# Demo · 开箱即跑的示例站

一个小而完整的示例：**一页自包含课程 + 一个首页 + 一份配置**。用来验证技能在你机器上能不能跑，以及让你看清"模板该长什么样"。

## 三种玩法

**1) 直接看效果（不装任何东西）**

双击 `demo-site/day1.html`，浏览器打开即可。上传照片、勾选、写笔记、点导出，能看到完整交互与 1350×1813 的记录卡。

**2) 一键自检（推荐）**

```bash
python scripts/selftest.py
```

它会把 demo 复制到临时目录，跑一遍 `克隆 Day1 → Day2 → 体检`，逐项打印结果，跑完自动清理，**不碰你的真实项目**。全部 ✅ 说明技能可用。

想保留生成结果看看：加 `--keep`，它会打印临时目录路径。

**3) 手动演练**

```bash
# 复制到临时目录，避免污染仓库
cp -r demo /tmp/my-demo && cd /tmp/my-demo
# 把 lesson-studio.json 里的 project_root 改成本目录
python <技能目录>/scripts/clone_lesson.py --config lesson-studio.json \
  --from 1 --to 2 --title-zh "我的第二课" --title-en "My Second Lesson" --summary "试一下"
python <技能目录>/scripts/verify_site.py --config lesson-studio.json
```

## demo 与真实项目的差别

| 项 | demo | 真实使用 |
|---|---|---|
| 页面 | 只有 1 课，纯手写最小骨架 | 你已有的站，Day 5/6 那种完整版 |
| 出处 | 结构和锚点与正式模板一致（`DAY N` 品牌行、`demo-dayN-` 前缀、导出文件名、7 区块、4 项勾选） | 改 `brand_line` / `prefix_base` / `export_base` 适配你的命名 |
| 部署 | 不部署 | `git push` + EdgeOne CLI |
| 海报 | 无 | 需要 `tools/make_poster.mjs` 与 `poster.json` |

## 换成你自己的项目

1. 复制 `scripts/config.example.json` 到项目根目录，改名 `lesson-studio.json`
2. 填 `project_root`、`site_dir`、`site_url`，按你的页面命名改 `file_pattern` / `prefix_base` / `brand_line` / `export_base`
3. 跑 `python scripts/preflight.py --config <你的配置>`，看能力矩阵
4. 跑 `python scripts/verify_site.py --config <你的配置>`，先确认**现有页面**全部通过（这一步能提前发现锚点对不上的问题）
5. 再 `clone_lesson.py --dry-run` 看替换计数，计数正常再去掉 `--dry-run`

第 4 步很关键：如果现有页面在体检里就 FAIL，说明你的模板与本技能的假设不同，先别急着克隆。
