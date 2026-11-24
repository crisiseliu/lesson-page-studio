# 游戏化注入层规范 · Engagement Spec（v2.5）

> 回溯 2026-11-23 CSP 站上线的三项效果，把它们沉淀为「新证书课程包构建时一键产出」的可复用能力。
> 维护：Louis LIu

## 1. 背景与来源

2026-11-23 站点 `drowsyhse.com` 分两次上线了游戏化路线图的前三项（HANDOVER §38 / §39）：

| 项 | 效果 | 生产实现 | 部署 ID |
|---|---|---|---|
| 1 | 热力图 + streak 冻结桥接 + 成就徽章 | `assets/heatmap.js v1.0.0`（注入 `csp.html`） | `dpon2auy760c` |
| 2 | 每日一题（全球同题 / 全网正确率 / 中英对照 / Wordle 战报） | `daily.html` + `assets/data/daily_questions.json`（426 题）+ 迁移 006 | `dpon2auy760c` |
| 3 | 关卡地图（蛇形路径 / 11 段主题色 / Boss 关 / 双视图） | `assets/pathmap.js v1.0.0`（注入 `csp.html`） | `dpectzihmzqp` |

**本技能 v2.3 做的事情**：把这三项从「CSP 专用、硬编码」改造成「任意证书课程通用、参数化」，
并接进 `build_curriculum.py` —— 以后生成新课程包，一条命令即自带 1/2/3。

**v2.4 增补**：2026-11-23 晚，生产站 `daily.html` 的「分享」从纯文本战报升级为
**一键生成图片分享卡**（题目 + 作答结果 + 网址 + 可扫码二维码），同步回灌技能包，
成为第 4 个随课程包一键产出的资产。二维码完全离线生成，不引入任何服务端或凭据。

**v2.5 增补**：2026-11-24 生产站上线「错题本 + 间隔复习」（CSP HANDOVER §41），
同日回灌技能包：构建课程包时一键产出 `review.html` + `course-wrongbook.js` +
`quiz_index.json` + 可选 `wrongbook_cert.sql`。做错的题自动收集，按 1 / 3 / 7 天重考，
答对三次毕业；默认纯本地零凭据，可选按 `(owner_id, cert_slug, item_id)` 跨设备同步。

**红线**：不修改、不重新生成、不引用生产站的 `heatmap.js` / `pathmap.js` / `daily.html`；
三件套自包含在新课程的 `<site>/<slug>/` 子目录，站点根 `assets/` 一行都不动。

## 2. 产物清单（一次 build 全部产出）

```
<site>/<slug>/
├── day1.html … dayN.html           课程页（v2.1 起，本次只修 STUDY_DAYS_KEY）
├── index.html                      课程目录（注入完整上下文 + 三件套引用 + 每日一题入口）
├── daily.html                      ← 新增·效果 2
├── review.html                     ← v2.5 新增·效果 4 错题本（统计 / tab / 重做）
└── assets/
    ├── course-heatmap.js           ← 新增·效果 1（零构建 token）
    ├── course-pathmap.js           ← 新增·效果 3（零构建 token）
    ├── qrcode.min.js               ← v2.4 新增·离线 QR 编码器（node-qrcode MIT 单文件打包）
    ├── course-daily-share.js       ← v2.4 新增·图片分享卡脚本（与生产站共用同一份）
    ├── course-wrongbook.js         ← v2.5 新增·效果 4 采集 + SRS + 可选同步（零构建 token）
    ├── wrongbook_cert.sql          ← v2.5 新增·可选云同步迁移（独立新表，绝不改 CSP 生产表）
    └── data/
        ├── daily_questions.json    ← 新增·效果 2 题池（从 cert.json 的 blocks[].scenario 提取）
        └── quiz_index.json         ← v2.5 新增·效果 4 回填索引（按页面原始选项顺序）
```

模板在 `curriculum/engagement/templates/`：

| 文件 | 用途 |
|---|---|
| `course-heatmap.js` | 参数化热力图，运行时读 `window.DROWSY_CERT` |
| `course-pathmap.js` | 参数化关卡地图，同上 |
| `course-daily.html` | 每日一题页（构建期替换 `{{TOKEN}}`；含图片分享卡按钮与三份脚本引用） |
| `qrcode.min.js` | **v2.4**：`QRCodeLite.create(text)` → `{modules:{size,data}}`，纯浏览器、零依赖 |
| `course-daily-share.js` | **v2.4**：`DrowsyDailyShare.open(data)` → 同步 PNG + 预览弹层，读 `DROWSY_DAILY_CONFIG` |
| `course-wrongbook.js` | **v2.5**：错题采集 + 1/3/7 天 SRS + 可选云同步，运行时读 `window.DROWSY_WRONGBOOK_CONFIG` |
| `course-review.html` | **v2.5**：错题本页模板（构建期替换 `{{TOKEN}}`，含统计 / 筛选 / 重做） |
| `wrongbook_cert.sql` | **v2.5 可选**云同步迁移（独立 `user_wrongbook` 表，绝不改 CSP 生产表） |
| `daily_challenge_cert.sql` | **可选**云统计迁移（独立新表，绝不改 CSP 生产 `daily_answers`） |

`qrcode.min.js` 由 `tools/_make_qrcode_bundle.js`（CSP 项目侧）从 `node-qrcode@1.5.4`
的 `lib/core/qrcode.js` + `dijkstrajs` 离线打包成 IIFE（23 模块 / ~70KB / MIT），
**不是从 CDN 下载、运行时也不访问网络**。重新生成时 `node tools/_make_qrcode_bundle.js <输出路径>`，
再把产物同时放到生产站 `assets/` 与技能包模板目录。

`curriculum/build_engagement.py` 是构建器，被 `build_curriculum.py` 自动调用；也可单独重跑：

```bash
python curriculum/build_engagement.py --cert <cert.json> --site <站点根目录>
```

## 3. 参数化契约：`window.DROWSY_CERT`

目录页 `<script>` 注入一个 JSON 对象（由 `build_engagement.build_context()` 生成），
**热力图 / 关卡地图 / 错题本三份 JS 的证书上下文都来自它**，因此同一份脚本服务任意证书、无需为每个课程改代码。

| 字段 | 类型 | 默认 | 作用 |
|---|---|---|---|
| `slug` | string | 必填 | localStorage 键前缀、云端 `cert_slug` 过滤 |
| `total` | int | 必填 | 热力格数、进度分母、徽章阈值缩放 |
| `label` | string | `short` | 课程短名（预留） |
| `gridSelector` | string | `.grid` | 原课程网格容器（热力图插入锚点 + 视图切换对象） |
| `tileSelector` | string | `.tile[href^="day"]` | 瓦片选择器，读 `href` / `--c` / `.tile-title` / `.tile-tag` |
| `minNodes` | int | `min(5, total)` | 地图最少节点门槛（生产 CSP 是 300，短课程必须放宽，否则 demo 10 课不渲染） |
| `bossDays` | [int,int] | `[total-1, total]` | 金色 A/B Boss 关；显式 `[]` = 关闭 |
| `chapterLabels` | object | `{}` | `{起始 day: 自定义章名}`，优先级最高 |
| `domainLabels` | object | 由 domains 生成 | `{领域 code: 中文名}`，章名兜底；同时生成 `Domain N` 别名 |
| `vocabKey` | string | `''` | 可选词汇表键；非空才显示「词汇入门/进阶」徽章 |
| `dailyEpoch` | string | 构建当天 | UTC 取模起期；**固定它**，否则改题池长度会改变历史出题映射 |
| `dailyPoolUrl` | string | `assets/data/daily_questions.json?v=1` | 题池相对路径 |
| `domainCount` | int | domains 数 | 体检/报告用 |

**顺序要求**：`window.DROWSY_CERT` 必须在三个 JS 之前注入（`verify_curriculum.py` 会断言）。
热力图与地图 JS 放在 `</body>` 前；热力图脚本在前、地图脚本在后，保证 DOM 插入顺序为
「热力面板 → 工具条 → 地图 → 原网格」。

### 3b. 图片分享卡上下文：`window.DROWSY_DAILY_CONFIG`（v2.4）

每日一题页在 `<head>` 之后的脚本区注入一个 JSON 对象（由 `build_engagement.render_daily()`
用 `js_literal()` 生成），是**分享卡脚本的唯一配置源**：

| 字段 | 默认 | 作用 |
|---|---|---|
| `certName` | `cert.name_zh` | 卡片标题/战报的证书名 |
| `brand` | `cert.brand` 或 `<SLUG> DAILY LEARNING` | 卡片顶部 eyebrow 品牌行 |
| `shareUrl` | `daily.share_url` 或 `<site>/<slug>/daily.html` | **二维码编码的落地页 + 卡上印刷的网址** |
| `slug` | `cert.slug` | 下载文件名前缀（`<slug>-challenge-YYYYMMDD.png`） |

- 顺序：`DROWSY_DAILY_CONFIG` → `qrcode.min.js` → `course-daily-share.js` → 页面主脚本。
  分享卡脚本**必须在 `open()` / `build()` 时动态读取配置**，不能在 IIFE 顶层缓存
  （顶层缓存会因加载顺序拿到空对象，品牌静默回退成通用 `DAILY LEARNING`，见 §8 坑 12）。
- 页面主脚本调 `DrowsyDailyShare.open({date, issueNo, question, questionEn, options,
  answered, correct, accuracy, shareUrl, brand, slug, shareText})`；`correct=null` 表示未答题，
  卡片渲染成「等你来挑战」邀请态（金色），答题后才显示绿/红结果条。
- **答案不上卡**：四个选项一律不标对错，只显示作答结果，保留传播悬念。

### 3c. 错题本上下文：`window.DROWSY_WRONGBOOK_CONFIG`（v2.5）

`build_engagement.wrongbook_inject()` 把配置注入每节课页与 `daily.html`，
`render_review()` 把同一份配置注入 `review.html`。**slug 不写进配置**：脚本运行时从
`window.DROWSY_CERT` → `window.DROWSY_DAILY_CONFIG` → `<meta name="drowsy-cert">` 依次读取，
因此 `course-wrongbook.js` 是零构建 token 的纯通用脚本。

| 字段 | 默认 | 作用 |
|---|---|---|
| `intervals` | `[1,3,7]` | 三个复习间隔（天），对应 level 0/1/2；第三次答对毕业 |
| `sync` | `null` | `null` = 纯本地；对象 `{url, anonKey}` = 开启 `user_wrongbook` 跨设备同步 |
| `indexUrl` | `assets/data/quiz_index.json?v=1` | 首次回填索引的相对路径 |

- `review.html` 顺序：`DROWSY_CERT` → `WRONGBOOK_CONFIG` → `/assets/sync.js` →
  `course-wrongbook.js` → 页面主脚本（同步脚本必须先于错题脚本，否则会话拿不到）。
- 课页已有 `/assets/sync.js`，注入片段不再重复引入；`daily.html` 没有，注入片段会补一行。
- `sync` 只在 `engagement.wrongbook.sync=true` 且凭据合法时注入；key 来自用户 cert.json，
  构建器拒绝 `secret` / `service_role`，技能包本身不含任何密钥。

## 4. cert.json 的 `engagement` 配置

`scaffold_cert.py` 自动生成下列骨架；老 cert.json 没有该字段时默认全开（向后兼容）。

```jsonc
"engagement": {
  "enabled": true,                 // false = 整层关闭（或 build 时加 --no-engagement）
  "boss_days": [359, 360],         // 可省（默认最后两课）；[] = 不显示 Boss
  "chapter_labels": {"1": "启程 · Orientation"},   // 可选，按起始 day 覆盖章名
  "domain_labels": {"IG1": "管理安全"},            // 可选，覆盖领域中文名
  "min_nodes": 5,                  // 可选
  "vocab_key": "",                 // 可选，站点有词汇表时填 <slug>-vocab-v1
  "daily": {
    "epoch": "2026-11-23",         // 必填建议固定；挑题起期
    "pool_version": 1,             // 题池 URL 的 ?v=
    "stats": false,                // true = 开全网正确率（见 §7）
    "exclude_blocks": [7, 32],     // 剔除「学习方法/备考策略/目的类」块的块号
    "pool_label_zh": "本课程内容 / Course lesson",
    "pool_label_en": "课程练习题 / Course practice",
    "share_url": "https://…/<slug>/daily.html",   // v2.4：二维码落地页，省略则用 canonical
      "supabase": {                  // 仅 stats=true 时必填
        "url": "https://xxx.supabase.co",
        "anon_key": "sb_publishable_…",   // 只允许 anon / publishable
        "submit_fn": "daily_challenge_submit_cert",
        "stats_fn": "daily_challenge_stats_cert"
      }
    },
    "wrongbook": {
      "enabled": true,               // false = 只关错题本（或 build 时加 --no-wrongbook）
      "intervals": [1, 3, 7],        // 可选；三个正整数，第三次答对毕业
      "sync": false,                 // true = 跨设备同步（先执行 wrongbook_cert.sql）
      "supabase": {                  // 可选；省略则复用 daily.supabase
        "url": "https://xxx.supabase.co",
        "anon_key": "sb_publishable_…"   // 只允许 anon / publishable
      }
    }
  }
```

## 5. 四项效果的实现口径（与生产站对齐）

### 1 热力图 + streak 冻结 + 徽章
- 数据 = 本地 `<slug>-dayN-checks` ∪ `DrowsySync.progressList()` 中 `cert === <slug>` 的 `days`；
  读失败静默回退纯本地（游客/离线可用）。
- 已学格填该课瓦片 `--c` 主题色；悬浮显示 Day + 课名。
- 冻结卡：历史每个自然日连段 `floor(段长/7)` 累计、上限 3 张；断档恰好 1 天自动桥接；
  **桥接不越过最早学习日**（生产踩过「还没开始学也算 streak」的坑）。
- 自然日数组统一写 **课程级** `<slug>-study-days`（v2.1 模板曾写成 `<slug>-dayN-study-days`，
  每课一个键导致无法汇总，v2.3 已修）。
- 徽章阈值按 `total` 缩放（10%/30%/55%），短课程也有可达目标；`vocabKey` 为空时不显示词汇徽章。

### 2 每日一题
- **题源就是 `blocks[].scenario`**：每个块的四选一情景题 = 1 道题，`day` = 该块首课
  `(no-1)*lessons_per_block + 1`，出处链到 `dayN.html`。
- 中文主显 + 英文次级：`q`=中文题干 / `qe`=英文原文；`o`=中文选项 / `oe`=英文选项（可选
  `scenario.options_en`）；`w`=[中文解析, 英文原文]，英文原文默认折叠在 `<details>`；
  `t`/`te` = 领域中英标签。译文缺字段不会留空题面。
- **按块号种子确定性洗牌选项**（`Random(90125 + no)`，中英选项同步换位），避免正确答案集中在 B。
- 挑题 = UTC 天数对题池长度取模（起期 `daily.epoch`）；已答状态 `<slug>-daily-<date>`，
  刷新不重答；Wordle 式战报复制按钮。
- **题池口径（Louis 2026-11-23 定）**：只用与实际考试内容相关的题，不出现学习方法/备考策略/
  目的类题目。新证书由作者判断，把这类块号写进 `daily.exclude_blocks`（生产站当时硬剔了 11 道）。
- **默认纯本地模式**：`STATS = null`，不请求任何外部服务、不内嵌任何凭据。

### 2b 图片分享卡（v2.4）

- 每日一题页**常驻**「生成分享卡 / Share card」按钮（`id="dqShareCard"`），不依赖答题状态：
  未答题也能生成邀请卡；答题后卡片带作答结果。原「复制文字战报」保留为次要按钮。
- 点击 → `DrowsyDailyShare.open()` 同步生成 **1080×1440 PNG**（Canvas），弹层预览，
  提供「保存图片」（`<a download>`）与「复制文字战报」，移动端提示长按保存、Esc/× 可关闭。
- 卡片版式：顶部品牌 + 期号 + 日期 → 题目块（中文主显 + 英文斜体次级）→ 四个选项
  （A/B/C/D，**不标对错**）→ 结果条（未答金色 / 答对绿 / 答错红 + 全网正确率）→
  底部网址 + 二维码 + 「扫码来挑战 / Scan & try」。
- **二维码**：`QRCodeLite.create(shareUrl)` 得到 `modules.{size,data}` 矩阵，逐模块
  `fillRect` 画进同一张 Canvas。全程同步、无图片请求、无跨域 taint，`toDataURL` 立即可用。
- 零外部依赖：不访问 CDN、不需要 Node / `qrcode` npm 包 / Python `qrcode` 库、不含任何凭据。
  生产站与技能包**共用同一份** `course-daily-share.js`（生产站文件名为 `daily_share_card.js`）。

### 3 关卡地图
- 渐进增强：运行时只读既有 `.tile`，生成第二视图；**原网格 DOM、SEO 链接、门禁捕获全部保留**
  （地图节点同样带 `class="tile"` + `href="dayN.html"`，自动命中门禁）。
- 目录页颜色改为**按领域分配**（v2.1 是按块循环 8 色，会把 72 块切成 72 章）；
  地图按 `--c` 变化切段，因此章节数 = 领域数，章名走 `chapterLabels` → `domainLabels` → tag 兜底。
- 蛇形折返 + 正弦起伏 + SVG 底层虚线 / 已完成段章节色实线；短章节按实际节点数居中。
- 状态：已学 ✓ / 当前呼吸光圈 + `START / 你在这里` / 锁定 `.locked` 🔒 / Boss 金色 A/B。
- 双视图工具条，记忆键 `<slug>-catalog-view`；**视图切换直接操作 grid/map 的 `style.display`**，
  不依赖 `.masonry` 类名（生产脚本硬编码了它）。
- 移动端宽度取 `.pm-track` 内容宽（`outerW - 2*chPadX`），否则右侧溢出约 8px（ARCHIVE 坑 54）。

### 4 错题本 + 1/3/7 天间隔复习（v2.5）

- **采集点两处**（课程包没有生产站的五题复盘 `.rqBtn`，但脚本保留兼容）：
  - 课页 `#checkBtn`：选项 / 题面从 `#quiz` 现场抽取；正确项优先读按钮的 `data-answer`，
    解析读 `data-why-zh` / `data-why-en`（课程包模板已带），再回退反馈文本正则。
    题面取 `#quiz` 前同 section 的最多两个 `<p>`（中英主次），跳过「自编练习题 / About these questions」提示。
  - 每日一题 `#dqSubmit`：正确项取 `#dqOpts .right`，所选取 `.sel`（刷新后已答态回退 `.wrong`），
    itemId 用 `daily-YYYY-MM-DD`，题面拼 `#dqQ` + `#dqQe`。
  - 所有采集都在 `setTimeout(0)` 后读 DOM，不改原判分逻辑；答对不入本。
- **首次回填**：`quiz_index.json` 由 `build_wrongbook_index()` 从 `blocks[].scenario` 生成，
  选项顺序**必须是课页原始顺序**（不能复用每日一题的洗牌顺序，否则历史答案对错判反）；
  与 `<slug>-dayN-quiz` 里的历史字母比对，只收错的。回填标记 `<slug>-wrongbook-backfilled-v1`，只跑一次。
- **SRS**：错 → level 0 / `intervals[0]` 天后；答对 → level 1 / `intervals[1]` 天 →
  level 2 / `intervals[2]` 天 → level 3 毕业（`due=null`）；中途答错回 level 0 重新计时。
  「待复习」tab 只显示 `due <= now` 的条目，所以**刚答错的题在「学习中」tab**，这是预期行为。
- **页面**：`review.html` 四统计卡（待复习 / 学习中 / 已掌握 / 累计）+ 四筛选 tab，
  卡片含题目、四选项（错项红 / 对项绿）、中英解析、重做 / 回本课 / 移除；重做即时更新 SRS。
- **存储与同步**：本地 `<slug>-wrongbook-items`（itemId → record），零登录可用；
  仅显式开启 `sync` 时走 `user_wrongbook` 表，按 `(owner_id, cert_slug, item_id)` upsert，
  last-write-wins（比较 `updated_at`），2s 防抖 + `pagehide` 兜底；未登录静默降级。

## 6. 键隔离清单

| 键 | 作用域 | 说明 |
|---|---|---|
| `<slug>-dayN-checks` | 每课 | 勾选进度（v2.1 已有） |
| `<slug>-dayN-photo` / `-notes` / `-quiz` / `-a1` / `-a2` | 每课 | 页内数据（v2.1 已有） |
| `<slug>-study-days` | **课程级** | 自然日数组，热力图 streak / 冻结卡（v2.3 修正） |
| `<slug>-daily-<date>` | 课程级 | 每日一题已答状态 |
| `<slug>-catalog-view` | 课程级 | 关卡地图/网格视图记忆 |
| `<slug>-wrongbook-items` | **课程级** | 错题本全部记录（itemId → SRS 状态），v2.5 |
| `<slug>-wrongbook-backfilled-v1` | **课程级** | 历史错题回填标记，只跑一次，v2.5 |
| `drowsy_device_id` | 全站 | 仅云统计模式用于防刷（与生产同口径） |

云同步 `DrowsySync.progressList()` 按 `cert === <slug>` 过滤；`slug === 'csp'` 时额外兼容
旧数据里 `cert === undefined` 的记录，其他证书**绝不**回退，防止串进度。

## 7. 可选：给新证书开全网正确率

生产站迁移 006 的 `daily_answers` 表按 `(day_date, device_id)` 唯一，**没有 cert 维度**，
新证书若直接复用会和 CSP 串统计。因此：

1. 默认 `stats=false` → 纯本地，零依赖（推荐先这样上线）。
2. 需要统计时，在 Supabase 执行 `curriculum/engagement/templates/daily_challenge_cert.sql`：
   建**独立新表** `daily_answers_cert` + RPC `daily_challenge_submit_cert` /
   `daily_challenge_stats_cert`（都带 `p_cert`）。**不碰** `daily_answers` 与旧 RPC。
3. 在 cert.json 填 `engagement.daily.stats=true` 与 `supabase.{url, anon_key}`，重新 build。
4. 凭据边界：只接受 `sb_publishable_` / anon key；`build_engagement.py` 会拒绝
   含 `secret` / `service_role` 的 key；`verify_curriculum.py` 扫描产物里的 `sb_secret_` / `service_role`。
   **技能包本身不含任何密钥**。
5. `stats` RPC 是 `STABLE` 函数，提交与统计必须分两次调用（生产踩过同一条 SQL 看不到新行的坑）。

## 8. 已知坑（照抄会翻车）

| # | 坑 | 处理 |
|---|---|---|
| 1 | `chapterLabel()` 用不存在的 `ch.tag` → 首帧 `undefined.replace`、0 节点 | 取 `ch.items[0].tag`（生产 ARCHIVE 坑 54，本模板已用正确字段） |
| 2 | 地图宽度用 `map.clientWidth` → 移动端右溢 8px | 用 `.pm-track` 内容宽 `outerW - 2*chPadX` |
| 3 | E2E 用 `addInitScript` 清视图记忆，每次 reload 都重跑 | 用全新 context，别注入清理 |
| 4 | 热力图等 `DOMContentLoaded`、地图立即执行 → 面板掉到地图下面 | 网格已解析时立即 init（本模板已修） |
| 5 | `minNodes` 沿用 300 → 10 课的 demo 不渲染地图 | 默认 `min(5, total)` |
| 6 | 自然日键带 `dayN` 后缀 → 热力图汇总不到 streak | 统一 `<slug>-study-days`（模板已修） |
| 7 | 页面 `renderStreak()` 用了未定义的 `CERT_SLUG`（被 try/catch 吞掉、恒为 0） | 模板补 `const CERT_SLUG = '…'`（已修） |
| 8 | 目录页颜色按块循环 → 章节数爆炸 | 按领域分配颜色 |
| 9 | 生产凭据写进技能包 / 前端误用 `sb_secret_` | 模板 `STATS_CONFIG` 构建期注入，默认 `null`；校验扫描密钥 |
| 10 | 改题池长度 / 改 `epoch` → 历史出题映射全变 | 上线后固定 `daily.epoch`，增题要接受换题 |
| 11 | QR 黑块用 `Math.ceil(cell)+0.4` 画、步进却是小数 `cell` → 相邻模块互相重叠约 0.6px，矩阵被侵蚀 | **肉眼看二维码完全正常，但 RS 解码报 `locator degree does not match number of roots`**。cell 必须取整数、黑块严格 `cell×cell`、留白 4 模块、整体在方框内居中 |
| 12 | 分享卡脚本在 IIFE 顶层 `var CFG = window.DROWSY_DAILY_CONFIG` 缓存 → 配置 script 排在其后加载时拿到空对象 | 品牌静默回退成通用 `DAILY LEARNING`（二维码 URL 因主脚本显式传入而不受影响，故极易漏测）。改 `getCfg()` 在 `open()`/`build()` 时动态读取，并把配置 script 前置 |
| 13 | 二维码只留 2 模块白边、外围是米色背景 → 扫码容错低 | 4 模块标准留白 + 白色圆角底；**E2E 必须用真实解码器反解 URL**，只断言「画了个方块」不算验证 |
| 14 | 回填索引用了每日一题洗牌后的选项顺序 → 历史答案对错判反 | `build_wrongbook_index()` 必须用 `blocks[].scenario.options` 原始顺序，与课页 `#quiz` 一致 |
| 15 | 错题脚本顶层写死 `slug` / Supabase URL+key → 多课程串数据、泄漏凭据 | slug 运行时从 DROWSY_CERT / DAILY_CONFIG / meta 读；sync 配置按课程注入，模板零 token |
| 16 | 刚答错的题不在「待复习」tab 就以为采集失败 | `due` = 1 天后，先出现在「学习中」tab；E2E 必须切 tab 再断言（v2.5 实测踩过） |
| 17 | `review.html` 把 `/assets/sync.js` 放在 `course-wrongbook.js` 之后 → 云同步永远 guest | 固定顺序：DROWSY_CERT → WRONGBOOK_CONFIG → sync.js → wrongbook.js → 主脚本 |
| 18 | 回填是异步 fetch，测试在它完成前写 localStorage → 被随后的 `save()` 用旧内存对象覆盖成 `{}` | E2E 用 `addInitScript` 在文档脚本前注入种子，或先 `await WrongBook.ready`（CSP 生产 ARCHIVE 坑 56） |

## 9. 验收（v2.5 实测基线）

| 检查 | 结果 |
|---|---|
| `python scripts/selftest.py` | **54/54**（原 42 项 + 12 项错题本断言：产物 / SRS / 零凭据 / 回填索引 / `--no-wrongbook` / anon key 注入与 secret 拦截） |
| `verify_curriculum.py`（demo 10 课） | PASS（页数/canonical/键隔离/DOM/三件套/**分享卡资源 + 全局入口 + 零凭据**/题池/无 CSP 硬编码） |
| 生产站真实浏览器 E2E | **29/29**：分享卡按钮常驻 / 同步 PNG 1080×1440 / 品牌与 URL 参数 / 保存下载 / × 与 Esc 关闭 / 答题闭环 / 移动端 390px 无溢出 / 零 pageerror |
| 课程包真实浏览器 E2E | **18/18**：一键生成的 demo 课程里分享卡可用、品牌为 `DEMO DAILY LEARNING`、下载名 `demo-challenge-*.png`、二维码指向**本课程** daily.html |
| **二维码真实反解** | 两套 E2E 均用 `qrcode-reader` 从生成的 PNG 反解，分别得到 `https://www.drowsyhse.com/daily.html` 与 `http://127.0.0.1:8000/demo/daily.html`，完全一致 |
| **错题本课程包真实浏览器 E2E** | **29/29**：采集（课内测验 / 每日一题）/ 首次回填 / 1→3→7→毕业 / 答错回退 / 移除 / 四 tab / 中英解析 / 移动端无溢出 / 零 pageerror |
| 分支验证 | `--no-engagement` 降级 / `--no-wrongbook` 单关 / 云统计与错题云同步模式 / secret key 拦截 / 自定义 `share_url` 均通过 |
| 生产站改动 | `daily.html` 新增分享卡按钮与 3 处脚本引用；`heatmap.js` / `pathmap.js` / 迁移 006 **未动**。错题本 v1.0.0 于 2026-11-24 独立上线（`review.html` + `wrongbook.js` + 迁移 008，线上探针 48/48），技能包不引用、不改动生产脚本 |

## 10. 版本纪律

- 改 `curriculum/engagement/templates/*.js` 后，`build_curriculum.py` 会把新模板拷进每个课程包；
  已生成的课程需重新 build 才会更新（历史课程不返工，除非明确要求）。
- `course-daily-share.js` 与生产站 `assets/daily_share_card.js` **必须是同一份内容**；
  改完一边要 `cp` 同步另一边，并同时重跑两套 E2E。
- 目录页引用 `assets/course-heatmap.js?v=1` / `assets/course-pathmap.js?v=1`；
  每日一题页引用 `assets/qrcode.min.js?v=1` / `assets/course-daily-share.js?v=1`；
  课页 / 每日一题页 / `review.html` 引用 `assets/course-wrongbook.js?v=1`。
  模板大改时统一 bump 这些 `?v=`，全站只允许一个版本。
- `course-wrongbook.js` 与生产站 `assets/wrongbook.js` **不要求字节一致**（前者零 token、
  按课程参数化，后者 CSP 专用含站点配置），但 SRS 口径与数据表必须一致；任一侧改间隔规则要同步评估另一侧。
- 题池 `?v=` 由 `daily.pool_version` 控制；CDN 有缓存，线上比对带 `?cb=<随机数>` 穿透。

---

维护：Louis LIu
