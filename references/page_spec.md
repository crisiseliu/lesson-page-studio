# 页面结构规范（单页自包含模板）

> 文中的 `CSP DAILY LEARNING · DAY N`、`csp-dayN-`、`CSP_DayN_Learning_Record.png` 都是**当前模板的示例值**。
> 你项目里的真实值由 `lesson-studio.json` 的 `brand_line`、`prefix_base`、`export_base`、`file_pattern`、`brand_mark` 决定。

## 1. 文件形态

- 每页一个 `.html`，CSS 在 `<style>`，JS 在 `<script>`，**无外部依赖**。
- 唯一外部资产：`static/streak1-6.webp`（打卡配图，可选）。
- 页面体积参考：Day 5 ≈ 31.5KB、Day 6 ≈ 32.8KB。明显偏小（<20KB）通常是内容被截断。

## 2. DOM 骨架

```
<header>  品牌标识 + <small>CSP DAILY LEARNING · DAY N</small> + 标题
  橙色徽章：主题中文名 / 英文名 / 副标题
<main>
  .card × 7（固定顺序，见下）
  学习打卡卡：图片上传 + 4 项勾选 + 昵称 + 2 道简答 + 笔记 + 导出按钮
</main>
```

7 个 `.card` 顺序固定：

1. `今日目标 | Learning objectives`
2. `核心概念 | Key concepts`
3. `术语起步 | Starter glossary`
4. `备考情景 | Study scenario`
5. `巩固练习 | Quick review`
6. `学习打卡与笔记 | Progress &amp; notes`
7. `可靠来源 | Official references`

## 3. 必须替换的机械字段

| 字段 | 锚点 | 出现次数 |
|---|---|---|
| 文档标题 | `<title>CSP Day N · English Title</title>` | 1 |
| 品牌行（页头） | `<small>CSP DAILY LEARNING · DAY N</small>` | 1 |
| 品牌行（导出画布） | `context.fillText('CSP DAILY LEARNING · DAY N', 540, 112)` | 1 |
| 存储前缀 | `csp-dayN-`（`PHOTO_KEY`、`storageSet`、`storageGet`） | 8–9 |
| 导出文件名 | `link.download = 'CSP_DayN_Learning_Record.png'` | 1 |
| 橙色徽章文案 | 页头 `main` 内首个带主题名的元素 | 1（需手改） |

`clone_lesson.py` 覆盖前五项；徽章文案与正文由人/AI 改写。

## 4. localStorage 键清单

单课键（前缀必须与页面编号一致）：

```
csp-dayN-photo         上传图片（Base64，压缩后）
csp-dayN-learnerName   学员昵称（新）
csp-dayN-learner       学员昵称（旧，兼容读取）
csp-dayN-a1            简答 1
csp-dayN-a2            简答 2
csp-dayN-notes         笔记
csp-dayN-checks        4 项勾选状态（JSON 数组）
csp-dayN-quiz          测验状态
```

全局键：

```
csp-study-days         学习天数（连续 / 累计），所有课程共用
```

> 前缀不一致会导致：新页读不到旧页数据（体验断裂），或新页覆盖老数据（数据丢失）。两种都不能接受。

## 5. 交互要点（不要破坏）

| 功能 | 实现要点 |
|---|---|
| 图片上传 | `FileReader` → `<canvas>` 圆形裁切 → `toDataURL('image/jpeg', 0.82)`；存储失败降级不抛错 |
| 导出 PNG | 尺寸以模板为准（本项目 1350×1813）；`loadImage()` 返回 Promise，**必须含 `img.decode()` 或 `onload` 后 confirm 解码完成**，否则偶发照片空白 |
| 导出防抖 | 按钮点击后禁用，完成后恢复（避免重复导出） |
| `roundRect` | 优先 `ctx.roundRect`，否则用 `arcTo` 手工绘制（老浏览器兼容） |
| 存储读写 | 全部经 `storageGet/storageSet/storageRemove` 包装，捕获异常（隐私模式会抛） |
| streak 计算 | 依赖 `csp-study-days`；只有发生有效学习活动才写入，不能一进页面就记 |

## 6. 首页 index.html

单行压缩 HTML。新卡片插入位置：`<main>` 之后（最新课在最上方）。

卡片格式：

```html
<section class="card"><h2>Day N · 中文标题 / English Title</h2>
<p>一句话摘要（中英混合，仿现有风格）</p>
<a href="dayN.html">打开第 N 天课程 / Open Day N lesson →</a></section>
```

## 7. 内容红线

- 中英文必须逐段对照，不能中英各写一份互不相同的版本。
- 公式必须给：表达式、变量含义、单位、算例。
- 练习题必须标注"自编练习题，不是 BCSP 官方真题"（或对应考试）。
- 引用来源须可核实（官网 URL 或标准编号），不编造。
- 品牌标识（`lesson-studio.json` 的 `brand_mark`，本项目为 `LOUIS 来自 昏昏睡睡HSE`）不得删改。
