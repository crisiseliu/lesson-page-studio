# 宣传海报规范

## 生成方式

`tools/make_poster.mjs` 读取 `linkedin/dayN/poster.json`，用无头浏览器把 HTML 渲染成 PNG。

```bash
cd tools && node make_poster.mjs dayN
```

- 画布 1080×1440 逻辑尺寸，@2x 渲染 → 输出 2160×2880
- 脚本会打印「内容高度」，**必须是 1440**；大于 1440 说明内容溢出会被页脚裁切
- 输出：`linkedin/dayN/CSP_DayN_Promo.png`（路径与文件名取自配置 `poster.out_dir` / `poster.png`）

## poster.json 字段

```json
{
  "day": 7,
  "title_zh": "考试英语术语系统",
  "title_en": "Exam English Terminology",
  "subtitle_zh": "词根词缀 · 易混词对 · 情景记忆",
  "subtitle_en": "Roots & Affixes · Confusable Pairs · Context Memory",
  "domain_zh": "Domain 1 · 安全原理高级应用（基础工具）",
  "domain_en": "Domain 1 · Advanced Safety Principles (Toolkit)",
  "sections": [
    {
      "no": "01",
      "icon": "📘",
      "title_zh": "板块中文名",
      "title_en": "Section English Name",
      "items": [
        "<b>加粗标签：</b>一条要点，尽量控制在 30 字内",
        "<b>标签：</b>第二条",
        "<b>标签：</b>第三条"
      ]
    }
  ],
  "terms": [["中文术语", "English Term"]],
  "reading": ["官方来源 1", "官方来源 2"],
  "qr_url": "https://你的正式域名/"
}
```

## 字段规则

| 字段 | 规则 |
|---|---|
| `title_zh` | ≤ 10 字，超出会换行挤压 |
| `title_en` | ≤ 40 字符 |
| `sections` | **固定 3 个**（01/02/03），每个 3 条 items |
| `items` | 支持 `<b>...</b>` 加粗；总字数过多会导致高度溢出 |
| `terms` | 5 组，中文 + 英文对照 |
| `reading` | 2–3 条，真实可查的官方来源 |
| `qr_url` | 固定为配置里的 `site_url`（永久域名），**不要用带 token 的临时域名或目标地区不可达的域名** |

## 设计规范

- 主色：深蓝 `#0F2A43` + 黄 `#FFC72C`；辅助浅蓝 `#2F7FD1`、橙 `#E8590C`
- 结构：顶部品牌条 → 黄色 Day 徽章 → 中英大标题 → 深蓝领域徽章 → 左栏三板块 / 右栏术语+阅读+二维码 → 底部品牌条
- 竖版手机海报比例，适合 LinkedIn / 微信朋友圈
- 全部文字中英对照

## 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 页面出现字面 `<b>` | 转义函数把标签当文本 | 用 `rich()`：先转义再还原 `<b>` |
| 第三板块被页脚裁掉 | 内容过多，高度 > 1440 | 精简 items 字数或删一条 |
| 中文显示成方框 | 字体缺失 | 用系统字体栈（Microsoft YaHei 等），不要指定不存在的字体 |
| 二维码扫后被墙 | `qr_url` 用错域名 | 改成永久正式域名 |

## 验收方法

生成后用看图工具检查以下几点，全部通过才算合格：

1. 三个板块完整可见，底部无裁切
2. 无字面 `<b>` 等标记泄漏
3. 中文无豆腐块（方框）
4. 右栏术语、来源、二维码完整
5. 与页脚无重叠
6. 标题与领域徽章文字与当日主题一致
