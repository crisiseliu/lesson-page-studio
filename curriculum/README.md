# Curriculum Builder · 多证书课程包

从「证书名 + 专业方向 + 领域权重」生成一整套与 CSP 同构的学习课程，并注入站点首页与 CSP 课程卡并列展示。

**v2.5 起，构建一次会同时产出游戏化三件套 + 图片分享卡 + 错题本**：热力图 + streak 冻结 + 徽章、
每日一题（中英对照 / 战报 / **一键生成带网址与二维码的 PNG 分享卡**）、
关卡地图（章节蛇形路径 / Boss / 双视图）、
错题本（自动收集错题 / **1/3/7 天间隔复习** / 中英解析）。自包含、零改生产站、零外部依赖。
契约见 `../references/engagement_spec.md`。

## 五个脚本

| 脚本 | 作用 |
|---|---|
| `scaffold_cert.py` | 脚手架：生成 `cert.json`（全部字段为 `__TODO__`）+ `*-TODO.md` 待办清单 |
| `build_curriculum.py` | 构建：校验内容完整 → 生成 `dayN.html` + 课程目录 `index.html`；**校验不过不写盘** |
| `inject_cert_card.py` | 注入：在站点首页插入/更新并列卡片（幂等，带 `<!--cert:slug:start-->` 标记，`--remove` 可删） |
| `verify_curriculum.py` | 体检：页数、占位符、canonical、存储键隔离、必备 DOM、目录卡数、**三件套 + 分享卡 + 错题本资源 + 题池/索引口径** |
| `build_engagement.py` | **v2.5**：生成热力图 / 关卡地图脚本、每日一题页与题池、图片分享卡、错题本资源，输出目录页 `DROWSY_CERT` 上下文 |

## 标准流程（以 NEBOSH IGC 为例）

```bash
# 1) 脚手架（证书名 + 方向 → 块计划按领域权重自动分配）
python curriculum/scaffold_cert.py \
  --slug nebosh-igc --name-zh "NEBOSH IGC 备考课程" --name-en "NEBOSH IGC Exam Prep" \
  --issuer NEBOSH --days 360 \
  --domains "IG1=管理安全=Management of safety=50,IG2=风险控制=Risk control=50" \
  --out ./nebosh-igc.json

# 2) 填内容：编辑 nebosh-igc.json，把所有 __TODO__ 换成真实内容
#    标准见 references/curriculum_authoring.md（双语逐段对照、数值须核对官方来源）

# 3) 校验 + 构建（输出到站点子目录 <site>/nebosh-igc/；校验不过不写盘）
python curriculum/build_curriculum.py --cert nebosh-igc.json --site <站点目录> --check
python curriculum/build_curriculum.py --cert nebosh-igc.json --site <站点目录>
#    同时生成（v2.5 默认）：
#      <site>/nebosh-igc/daily.html                          每日一题页（含图片分享卡按钮）
#      <site>/nebosh-igc/assets/course-heatmap.js           热力图 + streak + 徽章
#      <site>/nebosh-igc/assets/course-pathmap.js           关卡地图
#      <site>/nebosh-igc/assets/data/daily_questions.json   题池（来自各块 scenario）
#      <site>/nebosh-igc/assets/qrcode.min.js               离线 QR 编码器（MIT 单文件）
#      <site>/nebosh-igc/assets/course-daily-share.js       图片分享卡脚本（与生产站共用）
#      <site>/nebosh-igc/review.html                        错题本页（统计 / tab / 重做）
#      <site>/nebosh-igc/assets/course-wrongbook.js         采集 + SRS + 可选同步（零 token）
#      <site>/nebosh-igc/assets/data/quiz_index.json        历史错题回填索引
#      <site>/nebosh-igc/assets/wrongbook_cert.sql          可选云同步迁移（独立表）
#    退回纯 v2.1 产物：加 --no-engagement；只关错题本：加 --no-wrongbook

# 4) 体检（含三件套 / 分享卡 / 错题本资源 / 题池与索引 / 无 CSP 硬编码 / 无密钥）
python curriculum/verify_curriculum.py --cert nebosh-igc.json --site <站点目录>

# 5) 首页并列卡片（与 CSP 课程卡同层）
python curriculum/inject_cert_card.py --index <站点>/index.html \
  --slug nebosh-igc --href nebosh-igc/index.html \
  --name-zh "NEBOSH IGC 备考课程" --name-en "NEBOSH IGC Exam Prep" \
  --desc-zh "按 NEBOSH 大纲组织的全年双语课程。" \
  --desc-en "A full year of bilingual lessons mapped to the NEBOSH syllabus." \
  --color "#7A4BA8"
```

## 数据模型（cert.json）

```jsonc
{
  "slug": "nebosh-igc",           // 目录名 + localStorage 前缀（nebosh-igc-dayN-checks）
  "name_zh": "…", "name_en": "…", "issuer": "NEBOSH",
  "short": "IGC",                  // <title> 缩写
  "brand": "NEBOSH IGC DAILY LEARNING",  // 页头品牌行 + 导出卡品牌行
  "file_base": "IGC",              // 导出文件名前缀 IGC_Day1_Learning_Record.png
  "site_url": "https://www.drowsyhse.com",
  "days": 360,                     // 必须是 5 的倍数
  "engagement": {                  // v2.5，可整个省略（默认全开）
    "enabled": true,
    "daily": {
      "epoch": "2026-11-23", "pool_version": 1, "stats": false, "exclude_blocks": [],
      "share_url": "https://…/<slug>/daily.html"   // 可选；省略则用 canonical = <site_url>/<slug>/daily.html
    },
    "wrongbook": {                 // v2.5，可省略（默认开启、纯本地）
      "enabled": true,
      "intervals": [1, 3, 7],      // 答错后 1 天 / 答对依次 3 天、7 天 / 第三次毕业
      "sync": false                // true = 跨设备同步；先执行 assets/wrongbook_cert.sql
      // "supabase": {"url": "https://xxx.supabase.co", "anon_key": "sb_publishable_…"}
      // 省略 supabase 时复用 daily.supabase；禁止 secret / service_role
    }
  },
  "source_note_zh/en": "题目来源提示（官方不公开真题）",
  "references": [{"zh": "…", "en": "…", "url": "…"}],
  "domains": [{"code": "IG1", "zh": "…", "en": "…", "weight": 50}],
  "blocks": [ /* 72 块，见下 */ ]
}
```

每个 block（→ 5 课：概念 / 进阶 / 术语 / 情景 / 复盘）：

```jsonc
{
  "no": 1, "domain": "IG1",
  "zh": "主题中文", "en": "Topic EN",
  "points": [["中文要点", "EN point"]],        // ≥5 条
  "terms": [["Term", "释义"]],                 // 6 个
  "scenario": {"zh": "…", "en": "…", "options": ["A","B","C","D"],
               "answer": "B", "why_zh": "…", "why_en": "…"},
  "practice": [["中文","EN"],["中文","EN"]],   // 恰好 2 条
  "memory": "一句中文记忆句"
}
```

> CSP 的 72 块数据（`curriculum_data_*.py`）与此模型一一对应，可机械转换后复用。

## 页面能力（与 CSP 课程页同构）

自包含单页：双语区块、四选一情景题（数据驱动判题）、2 道简答（参考答案）、
4 项打卡 + 进度条 + 连续学习、个人照片上传、**Canvas 导出学习记录卡 1350×1813**、
题目来源提示框（`#examNote`）、手机端适配、canonical 指向自身。

## 目录页能力（v2.5 · 1/2/3 效果 + 图片分享卡 + 错题本）

- **热力图**：N 格按瓦片主题色点亮、streak 冻结卡桥接、按总课数缩放的成就徽章；
  数据 = 本地 `<slug>-dayN-checks` ∪ 云端进度（按 `cert_slug` 过滤，失败静默回退）。
- **关卡地图**：按领域着色分段的蛇形路径、已完成实线 + ✓、当前 START 光圈、Boss A/B、
  双视图记忆；原网格 DOM 与门禁完整保留。章节数 = 领域数。
- **每日一题入口** → `<slug>/daily.html`：题源 = 各块 `scenario`，中文主显 + 英文次级 +
  英文解析折叠、UTC 一天一题、已答不重答、Wordle 战报复制。
- **图片分享卡（v2.4）**：每日一题页常驻「生成分享卡」按钮，点击同步生成 1080×1440 PNG
  （题目 + 四选项 + 作答结果 + 网址 + 二维码），预览可保存 / 复制文字战报 / 长按保存。
  **答案不上卡**；二维码由随包的 `qrcode.min.js` 按 `share_url` 运行时生成，
  不预置图片、不依赖 CDN / Node / Python 库、不含凭据。
- **错题本（v2.5）**：`review.html` + `course-wrongbook.js` 在课页 `#checkBtn` 与每日一题
  `#dqSubmit` 处自动收集错题（首次打开回填本机历史答错记录）；答错 → 1 天后重考，
  答对 → 3 天 → 7 天 → 毕业，中途答错回 1 天。四统计卡 + 四筛选 tab + 重做 / 回本课 / 移除，
  中英解析；本地键 `<slug>-wrongbook-items` 按课程隔离。
- 四份 JS 零构建 token，全部从目录页 `window.DROWSY_CERT`、页内 `window.DROWSY_DAILY_CONFIG`
  与 `window.DROWSY_WRONGBOOK_CONFIG` 读配置，产物自包含在 `<site>/<slug>/assets/`，
  不碰站点根 `assets/` 与 CSP 生产脚本。

## 当前边界（如实告知）

- **云同步（v2.1）**：页面与目录页输出 `window.DROWSY_CERT` 并以根绝对路径引入
  `/assets/sync.js?v=N`，站点侧按 `(owner_id, cert_slug)` 隔离；站点若无 `sync.js`，
  引用 404、功能退化为纯本机，不影响阅读与三件套（两者都做了静默回退）。
- **错题本默认纯本地**：不请求任何外部服务、不内嵌凭据。要跨设备同步先执行
  `engagement/templates/wrongbook_cert.sql`（独立 `user_wrongbook` 表，按
  `(owner_id, cert_slug, item_id)` 隔离，绝不改 CSP 生产表），再设
  `engagement.wrongbook.sync=true`；只接受 anon / publishable key。
- **每日一题默认纯本地模式**：不请求外部服务、不内嵌凭据。要开「全网正确率」需按
  `../references/engagement_spec.md` §7 执行**独立新表**迁移并配置 `engagement.daily.stats`；
  该迁移不改 CSP 生产 `daily_answers` 表。
- **图片分享卡默认完全离线**：二维码在浏览器端由 `qrcode.min.js` 编码，不需要任何服务端、
  不需要 `qrcode` Python/npm 包、不访问 CDN。`share_url` 决定扫码落地页；要换落地页改
  `engagement.daily.share_url` 后重新 build 即可。
- **题池口径**：只用考试内容题；学习方法/备考策略/目的类块写进 `daily.exclude_blocks`。
  题池长度或 `epoch` 变化会改变历史出题映射，上线后请固定。
- 模拟卷/考试引擎不包含在本模块（CSP 的 `generate_exams.py` 为专用实现）；
  Boss 关只是把最后两课标成 A/B 挑战节点，不等于真模拟卷。
- 新证书目录为 `<site>/<slug>/`，与 CSP（根目录）互不干扰。
- `engagement.enabled=false` 或 `--no-engagement` 可整体关闭三件套，回到 v2.1 产物；
  `engagement.wrongbook.enabled=false` 或 `--no-wrongbook` 只关闭错题本。

---

维护：Louis LIu
