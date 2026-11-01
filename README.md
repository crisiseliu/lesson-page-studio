# Lesson Page Studio

在**已有的**单页自包含学习站上，流水线式生产新课页面、学习记录卡与宣传海报，并发布到 EdgeOne Pages 与 Git 托管（Vercel 等）。

适用于任何"一课一个 HTML、内联 CSS/JS、Canvas 导出"的静态学习站，不限主题。

仓库：<https://github.com/crisiseliu/lesson-page-studio> ｜ 版本：v1.2.1 ｜ 许可：MIT

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

## 60 秒上手

**先验证技能能用**（不碰你的项目）：

```bash
cd ~/.workbuddy/skills/lesson-page-studio
python scripts/selftest.py
```

它把 `demo/` 复制到临时目录，跑一遍「克隆 Day1 → Day2 → 体检」，逐项打印结果后自动清理。全 ✅ 再往下走。

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
├── references/
│   ├── page_spec.md                # 页面结构、锚点、存储键
│   ├── poster_spec.md              # 海报 JSON 字段与设计规范
│   └── deploy_runbook.md           # 发布、验证、故障排查、回滚
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

**Q：怎么改成我自己的科目？**
改配置里的 `prefix_base`、`brand_line`、`doc_title_base`、`export_base`，第 2 步写正文时按你的领域替换 7 个区块即可。

---

## 版本

- **1.2.1** —— 修正 `preflight.py` 能力矩阵：非 git 仓库目录不再把「第 6a 步 git/Vercel」标为可用。
- **1.2.0** —— 新增 `demo/` 可跑示例站与 `scripts/selftest.py` 全链路自检（9 项断言，临时目录，不碰真实项目）。
- **1.1.0** —— 配置驱动（`lesson-studio.json`）、新增 `preflight.py` 能力矩阵、脚本去掉硬编码路径与域名、降级路径成文、前缀替换自检提示。
- **1.0.0** —— 首版：克隆 + 体检 + 海报 + 双站发布流水线。
