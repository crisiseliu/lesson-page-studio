# Lesson Page Studio

在**已有的**单页自包含学习站上，流水线式生产新课页面、学习记录卡与宣传海报，并发布到 EdgeOne Pages 与 Git 托管（Vercel 等）。

适用于任何"一课一个 HTML、内联 CSS/JS、Canvas 导出"的静态学习站，不限主题。

仓库：<https://github.com/crisiseliu/lesson-page-studio> ｜ 版本：v2.5.0 ｜ 许可：MIT

---

## 安装

**方式 A：用 zip（最快）**

解压到 WorkBuddy 的技能目录，保持外层文件夹名为 `lesson-page-studio`：

```
Windows:  C:\Users\<你>\.workbuddy\skills\lesson-page-studio\
macOS:    ~/.workbuddy/skills/lesson-page-studio/
```

解压后目录里应能直接看到 `SKILL.md`（不是再多一层文件夹）。重启会话即生效。

**方式 B：从 Git 仓库（便于跟进更新）**

```bash
git clone https://github.com/crisiseliu/lesson-page-studio.git ~/.workbuddy/skills/lesson-page-studio
```

**方式 C：项目级技能**（只对某个项目生效）

放到 `<项目>/.workbuddy/skills/lesson-page-studio/`。

---

## v2.0 多证书课程包 / v2.3 游戏化三件套 / v2.5 错题本（Curriculum Builder）

给 **证书名 + 专业方向 + 领域权重**，即可生成一整套与 CSP 同构的全年课程：

```bash
python curriculum/scaffold_cert.py --slug <id> --name-zh "…" --name-en "…" \
  --issuer <机构> --days 360 --domains "D1=中文=EN=25,…" --out ./cert.json
# 逐块把 __TODO__ 填成真实内容（标准见 references/curriculum_authoring.md）
python curriculum/build_curriculum.py  --cert cert.json --site <站点> --check
python curriculum/build_curriculum.py  --cert cert.json --site <站点>
python curriculum/verify_curriculum.py --cert cert.json --site <站点>
python curriculum/inject_cert_card.py  --index <站点>/index.html --slug <id> \
  --href <id>/index.html --name-zh "…" --name-en "…" --desc-zh "…" --desc-en "…"
```

产出 `<站点>/<slug>/dayN.html` + 课程目录，并在首页插入与既有课程**并列**的卡片。
页面能力与 CSP 课程页同构（双语 / 判题 / 打卡进度 / 照片 / Canvas 导出卡 / 题目来源提示），
存储键按课程前缀隔离。详见 `curriculum/README.md`。

**v2.3 起第 3 步构建会一键附带三项效果；v2.4 自带图片分享卡；v2.5 再自带错题本 + 间隔复习**（无需额外命令、零改生产站）：

| 效果 | 产物 |
|---|---|
| 热力图 + streak 冻结 + 成就徽章 | `<slug>/assets/course-heatmap.js` |
| 每日一题（中英对照 / Wordle 战报） | `<slug>/daily.html` + `assets/data/daily_questions.json` |
| **图片分享卡（网址 + 可扫码二维码）** | `<slug>/assets/qrcode.min.js` + `assets/course-daily-share.js` |
| 关卡地图（章节蛇形路径 / Boss / 双视图） | `<slug>/assets/course-pathmap.js` |
| **错题本 + 1/3/7 天间隔复习** | `<slug>/review.html` + `assets/course-wrongbook.js` + `assets/data/quiz_index.json` |

四组脚本从 `window.DROWSY_CERT` / `window.DROWSY_DAILY_CONFIG` / `window.DROWSY_WRONGBOOK_CONFIG`
读配置，按证书 slug 隔离所有本地键与云端进度；默认纯本地、零凭据。
分享卡二维码在浏览器端离线生成；错题本自动收集课页与每日一题的错题，答对三次毕业，
可选 `engagement.wrongbook.sync=true` 开启跨设备同步（只放 anon key）。
都不依赖 CDN / Node / Python 库，不含任何凭据。契约与升级见 `references/engagement_spec.md`。

---
---

## 60 秒上手

**先验证技能能用**（不碰你的项目）：

```bash
cd ~/.workbuddy/skills/lesson-page-studio
python scripts/selftest.py
```

它把 `demo/` 复制到临时目录，跑一遍「克隆 Day1 → Day2 → 体检 → 课程包构建 → 三件套 + 分享卡 + 错题本」，
共 54 项断言，逐项打印结果后自动清理。全 ✅ 再往下走。

也可以直接双击 `demo/demo-site/day1.html` 看模板长什么样（上传照片、勾选、导出都能用）。

**再接自己的项目**：

```bash
# 1) 生成配置：复制模板到你自己的项目根目录
cp scripts/config.example.json <项目根目录>/lesson-studio.json

# 2) 改三处必填：project_root / site_dir / site_url（其余可留默认）

# 3) 自检：会告诉你六步里哪几步能跑
python scripts/preflight.py --config <项目根目录>/lesson-studio.json
```

自检通过后，对 AI 说：**"用 lesson-page-studio 加一课，主题是 XXX"**，它会按第 1–6 步执行。

手工跑也可以：

```bash
python scripts/clone_lesson.py --from 6 --to 7 \
  --title-zh "考试英语术语系统" --title-en "Exam English Terminology" \
  --summary "词根词缀、易混词对与情景记忆。" --dry-run   # 先看计数，去掉 --dry-run 才写盘

python scripts/verify_site.py --config <项目根目录>/lesson-studio.json
```

---

## 依赖与降级

| 组件 | 用途 | 缺了会怎样 |
|---|---|---|
| Python 3.9+ | 跑三个脚本 | 全流程不可用 |
| Node 18+ | JS 语法检查、浏览器回归、海报 | 跳过 JS 检查 / 回归 / 海报 |
| playwright-core | 无头浏览器驱动 | 无自动回归，无分享卡截图 |
| Edge 或 Chrome | 渲染内核 | 同上（可用 `browser.executable` 指定路径） |
| qrcode（npm） | 海报二维码 | 海报无二维码 |
| git + 远程仓库 | 触发 Vercel 等构建 | 只走 EdgeOne |
| EdgeOne CLI | 正式站部署 | 只走 Git 构建 |

`preflight.py` 会把这张表算成「能力矩阵」，逐项告诉你缺什么、补的命令是什么。**没有 Node 也能生成页面并部署**，只是少几项自动验证。

---

## 目录结构

```
lesson-page-studio/
├── SKILL.md                        # 技能主文档（AI 读这个）
├── README.md                       # 本文件（人读这个）
├── demo/
│   ├── README.md                   # demo 玩法说明
│   ├── lesson-studio.json          # demo 专用配置
│   └── demo-site/                  # 示例站（day1.html + index.html + favicon）
├── scripts/
│   ├── preflight.py                # 环境与依赖自检 + 能力矩阵
│   ├── selftest.py                 # 技能自检（demo 全链路，用临时目录）
│   ├── clone_lesson.py             # 克隆上一课 + 机械替换 + 首页插卡
│   ├── verify_site.py              # 站点体检
│   ├── _config.py                  # 配置读取（命令行 > 配置 > 默认）
│   └── config.example.json         # 配置模板
├── curriculum/                     # 多证书课程包（v2.0+）
│   ├── README.md                   # 模块说明与数据模型
│   ├── scaffold_cert.py            # 脚手架：证书名 + 领域权重 → cert.json
│   ├── build_curriculum.py         # 构建：课程页 + 目录 +（v2.5）三件套 + 分享卡 + 错题本
│   ├── build_engagement.py         # v2.5 游戏化注入层构建器
│   ├── verify_curriculum.py        # 课程包体检（含分享卡 / 错题本资源 / 密钥扫描）
│   ├── inject_cert_card.py         # 首页并列卡片（幂等）
│   ├── templates/page.html         # 课程页模板
│   └── engagement/templates/       # v2.5 参数化热力图 / 关卡地图 / 每日一题 / QR / 分享卡 / 错题本 / 可选迁移
├── references/
│   ├── page_spec.md                # 页面结构、锚点、存储键
│   ├── curriculum_authoring.md     # 课程内容创作标准
│   ├── engagement_spec.md          # v2.5 游戏化契约（DROWSY_CERT / 分享卡 / 错题本 / 口径 / 坑）
│   ├── poster_spec.md              # 海报 JSON 字段与设计规范
│   └── deploy_runbook.md           # 发布、验证、故障排查、回滚
├── demo/
│   └── demo-cert.json              # 2 块 = 10 课的示例证书配置
└── assets/
    └── poster.json                  # 海报配置样板
```

---

## 前提：你的站长得像这样

`clone_lesson.py` 靠**锚点字符串**做替换，所以模板必须满足：

- 每课一个自包含 HTML，文件名形如 `dayN.html`（可用 `file_pattern` 改）
- `<title>` 含课程编号；页头有一行品牌文案含 `DAY N`
- localStorage 键带 `csp-dayN-` 这类前缀（`prefix_base` 可配置）
- 导出文件名含课程编号
- 首页 `index.html` 有 `<main>` 锚点，课程卡片是 `<section class="card">`

锚点对不上时脚本会**直接报错退出**，不会写出半改的文件——这是刻意设计，避免静默损坏。遇到报错就用 `--dry-run` 对照计数核对模板，或改配置适配你的命名。

---

## 常见问题

**Q：能直接给不写代码的人用吗？**
能。自检 + 脚本负责所有机械工作，人只需要提供主题、标题和三个配置值。

**Q：会覆盖我已有的课程吗？**
不会。目标文件已存在时脚本拒绝覆盖；历史课程不做任何改动。唯一动到的老文件是 `index.html`（插入一张新卡片）。

**Q：海报会不会出现中文乱码？**
不会，海报是 HTML + 浏览器渲染成图，不是 AI 生图。

**Q：里面有我的密钥吗？**
没有。技能包不含 token、账号、EdgeOne 登录态；配置文件里只有路径和项目名。发布所需的登录态由你本机的 CLI 自己维护。
v2.4 的每日一题默认纯本地、零凭据，图片分享卡的二维码也完全在浏览器端生成；
v2.5 的错题本同样默认纯本地。只有你显式配置 `engagement.daily.stats` 或
`engagement.wrongbook.sync` 才会把 anon/publishable key 写进**生成的站点页面**（不是技能包），
且构建器会拒绝 secret / service_role。

**Q：新证书会自动带上热力图、每日一题、关卡地图、图片分享卡和错题本吗？**
会。`build_curriculum.py` 一条命令就产出，默认开启；`--no-engagement` 或 cert.json 里
`engagement.enabled=false` 可全部关闭， `--no-wrongbook` 只关错题本。
分享卡二维码在浏览器端离线生成，扫码落地页由 `engagement.daily.share_url` 决定（默认本课程 daily.html）。
错题本按 1/3/7 天间隔复习，默认纯本地；要跨设备同步先执行随包 `wrongbook_cert.sql`，
再设 `engagement.wrongbook.sync=true`（anon key 可复用 `daily.supabase`）。详见 `references/engagement_spec.md`。

**Q：怎么改成我自己的科目？**
改配置里的 `prefix_base`、`brand_line`、`doc_title_base`、`export_base`，第 2 步写正文时按你的领域替换 7 个区块即可。

---

## 版本

- **2.5.0** —— **错题本 + 间隔复习**：构建课程包时一键产出 `review.html` + `course-wrongbook.js` + `quiz_index.json` + 可选 `wrongbook_cert.sql`；课页 `#checkBtn`（读 `data-answer` / `data-why-*`）与每日一题 `#dqSubmit` 自动采集错题，首次打开回填本机历史答错记录；答错 1 天、答对 3 天 → 7 天 → 毕业，中途错回 1 天；四统计卡 + 四 tab + 重做 / 移除，中英对照；本地键 `<slug>-wrongbook-items` 按课程隔离，云同步可选且只接受 anon key；`--no-wrongbook` 可单独关闭。自检增至 54 项，课程包真实浏览器 E2E 29/29（采集 / SRS / 回填 / 重做 / 移动端）。
- **2.4.0** —— **每日一题图片分享卡**：点「生成分享卡」直接产出 1080×1440 PNG（题目 + 四选项 + 作答结果 + 网址 + 二维码），预览弹层可保存 / 复制文字战报 / 长按保存，答案不上卡；二维码由随包落盘的 `qrcode.min.js`（node-qrcode MIT 离线单文件打包）按 `share_url` 运行时同步生成，整数像素对齐保证可扫，不依赖 CDN / Node / Python 库、不含凭据；`window.DROWSY_DAILY_CONFIG` 参数化品牌与落地页。生产站与技能包共用同一份卡片脚本。自检增至 42 项，生产站 E2E 29/29、课程包 E2E 18/18（二维码均真实反解验证）。
- **2.3.0** —— **游戏化注入层**：构建课程包时一键生成热力图/streak 冻结/徽章、每日一题（中英对照题池 + 战报）、关卡地图（按领域分段蛇形路径 / Boss / 双视图）；三件套按 `window.DROWSY_CERT` 参数化、按 slug 隔离、自包含零改生产站；修正 `STUDY_DAYS_KEY` 与 `CERT_SLUG` 两个模板 bug；自检增至 35 项，真实浏览器 E2E 29/29。
- **2.2.0** —— 课程页内置导航键（上一天/课程首页/下一课）、按完成课时统计连续与累计天数、双语布局脚本（`/assets/bilingual.js`）、页头与导出卡接入站点 LOGO；自检增至 23 项。
- **2.1.0** —— 多证书云同步：课程页与目录页输出 `window.DROWSY_CERT = {slug, total}`，同步脚本改根绝对路径 `/assets/sync.js?v=N`（子目录页不再 404）；自检增至 18 项。
- **2.0.0** —— 新增 `curriculum/` 多证书课程包模块：脚手架 → 构建 → 体检 → 首页并列卡片注入。
- **1.2.1** —— 修正 `preflight.py` 能力矩阵：非 git 仓库目录不再把「第 6a 步 git/Vercel」标为可用。
- **1.2.0** —— 新增 `demo/` 可跑示例站与 `scripts/selftest.py` 全链路自检（9 项断言，临时目录，不碰真实项目）。
- **1.1.0** —— 配置驱动（`lesson-studio.json`）、新增 `preflight.py` 能力矩阵、脚本去掉硬编码路径与域名、降级路径成文、前缀替换自检提示。
- **1.0.0** —— 首版：克隆 + 体检 + 海报 + 双站发布流水线。

---

维护：Louis LIu
