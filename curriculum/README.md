# Curriculum Builder · 多证书课程包

从「证书名 + 专业方向 + 领域权重」生成一整套与 CSP 同构的学习课程，并注入站点首页与 CSP 课程卡并列展示。

## 三个脚本

| 脚本 | 作用 |
|---|---|
| `scaffold_cert.py` | 脚手架：生成 `cert.json`（全部字段为 `__TODO__`）+ `*-TODO.md` 待办清单 |
| `build_curriculum.py` | 构建：校验内容完整 → 生成 `dayN.html` + 课程目录 `index.html`；**校验不过不写盘** |
| `inject_cert_card.py` | 注入：在站点首页插入/更新并列卡片（幂等，带 `<!--cert:slug:start-->` 标记，`--remove` 可删） |
| `verify_curriculum.py` | 体检：页数、占位符、canonical、存储键隔离、必备 DOM、目录卡数 |

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

# 3) 校验 + 构建（输出到站点子目录 <site>/nebosh-igc/）
python curriculum/build_curriculum.py --cert nebosh-igc.json --site <站点目录> --check
python curriculum/build_curriculum.py --cert nebosh-igc.json --site <站点目录>

# 4) 体检
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

## 当前边界（如实告知）

- **进度为纯本机**（localStorage）。云同步目前仅覆盖 CSP（`user_progress.days` 单数组按用户存储）；
  给新证书上云同步需要把表改为 `(owner_id, cert_slug)` 复合键并改造 `assets/sync.js`，属后续升级项。
- 模拟卷/考试引擎不包含在本模块（CSP 的 `generate_exams.py` 为专用实现）。
- 新证书目录为 `<site>/<slug>/`，与 CSP（根目录）互不干扰。
