---
name: lesson-page-studio
description: 在既有「单页自包含」学习站模板上生产新课页面、分享卡与宣传海报，并发布到 EdgeOne Pages 与 GitHub/Vercel。适用于：给现有学习站新增一课/一天、在同一模板上开新科目系列、重做某天海报或学习记录卡、批量补发漏课。触发词：新增一课、加一天课程、生成学习页面、生成海报、学习记录卡、补课、学习网站新内容、lesson page。
version: 1.2.0
agent_created: true
---

# Lesson Page Studio

## 用途

把「新增一课学习内容」从手工改代码变成可控流水线：
**自检 → 克隆模板 → 机械替换 → 写正文 → 体检 → 浏览器回归 → 海报/分享卡 → 发布验证**。

配置驱动、依赖可缺省：没有 Node 或没有部署 CLI 时，能跑到哪一步就跑哪一步，并在报告里说清楚哪一步被跳过。

## 适用与不适用

**适用**：已有一个可跑的同类静态学习站（每课一个自包含 HTML，内联 CSS/JS + Canvas 导出），要沿用它继续加课。

**不适用**：从零建站、需要框架构建（Next/Vite）、需要后端或数据库。这些情况先建站，再来用本技能加内容。

## 第 0 步：配置（只做一次）

```bash
cp scripts/config.example.json <项目根目录>/lesson-studio.json
# 改三处必填：project_root、site_dir、site_url
python scripts/preflight.py --config <项目根目录>/lesson-studio.json
```

**第一次用先跑技能自检**（用 demo，不碰你的项目）：

```bash
python scripts/selftest.py          # 9 项断言：克隆 + 替换 + 体检
```

`preflight.py` 输出两项结论：

1. **逐项检查**：Python / 配置文件 / 项目目录 / 模板页 / Node / playwright-core / qrcode / 浏览器内核 / git 与提交邮箱 / EdgeOne CLI / 换行保护。
2. **能力矩阵**：第 1–6 步哪些能跑、哪些降级，缺什么、怎么补。

**先看能力矩阵再动手**，不要假设环境齐全。

## 工作流程

### 第 1 步：克隆模板（脚本）

```bash
python scripts/clone_lesson.py \
  --from 6 --to 7 \
  --title-zh "考试英语术语系统" --title-en "Exam English Terminology" \
  --summary "词根词缀、易混词对与情景记忆。"
```

自动完成五处机械替换 + 首页插卡：

| 替换项 | 预期计数 |
|---|---|
| `<title>` 编号与英文标题 | 1 |
| 品牌行 `DAY N`（页头 + Canvas） | 2 |
| localStorage 前缀（`<prefix_base>N-`） | 4–9（模板用常量拼接时可能只 1 处） |
| 导出 PNG 文件名 | 1 |
| 首页卡片（置于 `<main>` 最上方） | 1 |

先加 `--dry-run` 看计数。**计数为 0 说明锚点对不上，停下来核对模板，不要强行改**。
前缀命中少于 4 处时，脚本会提示自检：`grep -c "<prefix_base>6-" 新页面` 必须为 0，否则新旧课会共用同一份本地记录。

换科目系列时用 `--prefix-base` / `--file-pattern` / `--doc-title-base` / `--brand-line` 适配命名，或直接写进配置。

### 第 2 步：写正文

改写 7 个区块，**结构与 class 一律不动**，只换文字与数据：

| 区块 | 中 / 英标题 | 内容要求 |
|---|---|---|
| 1 | 今日目标 / Learning objectives | 3–4 条，双语逐条对照 |
| 2 | 核心概念 / Key concepts | 定义、公式（变量 + 单位 + 算例） |
| 3 | 术语起步 / Starter glossary | 5–8 个中英对照术语 |
| 4 | 备考情景 / Study scenario | 真实工作场景 + 设问 |
| 5 | 巩固练习 / Quick review | 2 题 + 参考答案，标注"自编，非官方真题" |
| 6 | 学习打卡与笔记 / Progress & notes | 固定 4 项勾选，不多不少 |
| 7 | 可靠来源 / Official references | 政府/协会官网等可核验来源 |

同时替换页头下方的**橙色徽章**主题名与副标题（唯一需要手改的视觉文案）。
字段与锚点见 `references/page_spec.md`。

### 第 3 步：体检（脚本）

```bash
python scripts/verify_site.py --config <项目根目录>/lesson-studio.json
```

检查：标签配对、id 唯一、内联 JS 语法（`node --check`）、本地资源存在、编号四处一致、Vercel 注入残留、品牌标识、favicon。

**任何 FAIL 不得进入部署。**

### 第 4 步：浏览器回归

```bash
cd <项目根目录>/tools && node test_site.mjs    # 先把测试目标改成新 dayN
```

要求：渲染正常、无横向溢出、导出 PNG 尺寸与模板一致、控制台零错误。随后用看图工具逐张检查截图（文字 / 布局 / 裁切 / 双语）。

无 playwright-core 时跳过，改为人工在浏览器打开新页面确认，并在报告里注明"未做自动回归"。

### 第 5 步：海报与分享卡

1. 按 `references/poster_spec.md` 写 `linkedin/dayN/poster.json`（可复制 `assets/poster.json` 改）
2. `cd tools && node make_poster.mjs dayN` —— 打印的「内容高度」必须等于画布高度
3. `cd tools && node export_card.mjs "<绝对路径>/CSP_DayN_Learning_Record.png" dayN`
4. **看图验收**：无乱码、无裁切、无重叠、双语完整、二维码指向正式域名

海报必须用 HTML 渲染成图，**不要用 AI 生图**（中文术语必出乱码）。

### 第 6 步：发布与验证

```bash
git add -A && git commit -m "Day N: <主题>" && git push     # → Vercel/其他 Git 构建
cd <site_dir> && PAGES_SOURCE=skills edgeone pages deploy -n <项目名> -a overseas --skip-ai-gateway-sync
```

随后逐域名 `curl` 校验 200 且**线上字节数 == 本地字节数**。
细节、故障排查与回滚见 `references/deploy_runbook.md`。

## 降级路径（环境不全时）

| 缺什么 | 影响 | 替代做法 |
|---|---|---|
| Node | 跳过内联 JS 语法检查、浏览器回归、海报 | 人工在浏览器点一遍；海报改用项目已有的成品模板图 |
| playwright-core | 无自动回归、无法导出分享卡 | 人工截图核对；分享卡取页面自带导出功能 |
| qrcode | 海报无二维码 | 海报改放短链文字 |
| git / 远程仓库 | 无 Git 构建备份 | 只走 EdgeOne |
| EdgeOne CLI | 无正式站部署 | 只走 Git 构建，或手工上传 zip |
| `*.edgeone.cool` 临时域名 | 3 小时过期、有鉴权 | **只用永久自定义域名** |

## 硬约束

1. **不改模板骨架**：CSS 框架、布局、导出机制、连续打卡逻辑一律不动，只换文案与数据。
2. **新页必须换存储前缀**，否则会覆盖老学员的本地学习记录。
3. **历史课程不返工**，除非用户明确要求。
4. **二维码与分享链接只用永久域名**，不用带 token 的临时预览链接。
5. **检查不过不部署**；部署失败如实报告，不谎报成功，不隐瞒降级。
6. 原创练习题标注非官方；引用来源须真实可查。
7. 不提交任何密钥、token、账号信息到仓库或技能包。

## 资源索引

- `scripts/selftest.py` —— 技能自检：demo 复制到临时目录跑通「克隆 → 体检」（**新环境先跑**）
- `scripts/preflight.py` —— 环境与依赖自检 + 能力矩阵（接自己项目时先跑）
- `scripts/clone_lesson.py` —— 克隆上一课 + 机械替换 + 首页插卡
- `scripts/verify_site.py` —— 站点体检（可对任意同类目录运行）
- `scripts/_config.py` —— 配置读取（命令行 > 配置 > 内置默认）
- `scripts/config.example.json` —— 配置模板，复制改名后填
- `references/page_spec.md` —— 页面结构、锚点位置、存储键清单
- `references/poster_spec.md` —— 海报 JSON 字段、设计规范、常见坑
- `references/deploy_runbook.md` —— 发布命令、验证、故障排查、回滚
- `assets/poster.json` —— 海报配置样板
- `demo/` —— 可跑的示例站（day1.html + index.html）与示例配置，用于验证与对照结构

## 交付清单

- [ ] 自检跑过，降级项已记录在案
- [ ] 新页面生成，编号四处一致
- [ ] 存储前缀已换，旧前缀残留为 0
- [ ] 首页卡片已加（最新在最上）
- [ ] 体检全通过
- [ ] 回归通过；若降级，已注明"人工确认"
- [ ] 海报高度不溢出，逐张看图合格
- [ ] 分享卡照片非空白
- [ ] 部署后各域名 200 且字节一致
- [ ] 海报配置与帖子草稿归档到 `linkedin/dayN/`
