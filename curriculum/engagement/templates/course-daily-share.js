/* DrowsyDailyShare — 每日一题图片分享卡
   生产站（assets/daily_share_card.js）与 lesson-page-studio 课程包
   （assets/course-daily-share.js）共用同一份文件，零构建 token。

   依赖：window.QRCodeLite（assets/qrcode.min.js，node-qrcode MIT 单文件打包）。
   全部绘制同步完成：二维码由模块矩阵直接画进 Canvas，无图片异步加载、
   无跨域 taint，toDataURL 立即可用。答案不落在卡上（只显示结果，不标哪个选项对）。

   配置（可选）：window.DROWSY_DAILY_CONFIG = { certName, brand, shareUrl, slug }
   用法：DrowsyDailyShare.open({
     date, issueNo, question, questionEn, options:[A,B,C,D],
     answered:bool, correct:bool|null, accuracy:0-100|null,
     shareUrl, certName, brand, slug, shareText
   })
*/
(function () {
  'use strict';

  /* 配置必须在 open()/build() 时动态读取：本脚本可能排在 DROWSY_DAILY_CONFIG
     注入之前加载，顶层缓存会拿到空对象（曾导致品牌回退成通用 DAILY LEARNING）。 */
  function getCfg() { return window.DROWSY_DAILY_CONFIG || {}; }
  var FONT = '"Noto Sans SC","PingFang SC","Microsoft YaHei",Inter,sans-serif';
  var EN = 'Inter,"Segoe UI",Arial,sans-serif';
  var SERIF = 'Georgia,"Times New Roman",serif';
  var NAVY = '#0F2A43', GREEN = '#176B55', RED = '#C4453A', INK = '#141414',
      MUTED = '#8A8578', LINE = '#E0DCD2', SOFT = '#EFECE6';

  /* ---------- 基础绘制工具（与站点 share_card.js 同口径） ---------- */
  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }
  function fitOneLine(ctx, text, maxW, cssFont, startPx, minPx) {
    var px = startPx;
    while (px > minPx) {
      ctx.font = cssFont.replace(/(\d+(\.\d+)?)px/, px + 'px');
      if (ctx.measureText(String(text)).width <= maxW) break;
      px -= 2;
    }
    return px;
  }
  /* 混合换行：拉丁单词不断行、CJK 逐字断行，最多 maxLines 行 */
  function wrapMixed(ctx, text, maxW, maxLines) {
    var units = String(text || '').match(/[A-Za-z0-9\u00C0-\u024F'’\-]+|[^A-Za-z0-9\u00C0-\u024F'’\-]/g) || [];
    var line = '', lines = [];
    for (var i = 0; i < units.length; i++) {
      var u = units[i], cand = line + u;
      if (ctx.measureText(cand).width > maxW && line.replace(/\s+$/, '')) {
        lines.push(line.replace(/\s+$/, ''));
        line = (u === ' ') ? '' : u;
      } else line = cand;
    }
    if (line.replace(/\s+$/, '')) lines.push(line.replace(/\s+$/, ''));
    if (lines.length > maxLines) {
      lines = lines.slice(0, maxLines);
      lines[maxLines - 1] = lines[maxLines - 1].replace(/.$/, '…');
    }
    return lines;
  }
  function wrapEn(ctx, text, maxW, maxLines) {
    var words = String(text || '').split(' '), line = '', lines = [];
    for (var i = 0; i < words.length; i++) {
      var t = line ? line + ' ' + words[i] : words[i];
      if (ctx.measureText(t).width > maxW && line) { lines.push(line); line = words[i]; }
      else line = t;
    }
    if (line) lines.push(line);
    if (lines.length > maxLines) {
      lines = lines.slice(0, maxLines);
      lines[maxLines - 1] = lines[maxLines - 1].replace(/.$/, '…');
    }
    return lines;
  }
  function circle(ctx, x, y, r, color) {
    ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
  }
  function eyebrow(ctx, x, y, w, left, right) {
    ctx.fillStyle = MUTED; ctx.font = 'bold 22px ' + EN;
    ctx.textAlign = 'left'; ctx.fillText(left, x, y);
    ctx.textAlign = 'right'; ctx.fillText(right, x + w, y);
    ctx.textAlign = 'left';
  }

  /* ---------- 二维码：由矩阵同步画进 Canvas（无需任何图片请求） ----------
     整数像素对齐：cell 必须取整数、黑块严格 cell×cell，否则相邻模块互相重叠
     会侵蚀矩阵（肉眼看着正常，但 RS 解码会报 locator degree does not match）。
     留白 4 模块（QR 规范推荐），整体在给定方框内居中。 */
  function drawQR(ctx, text, x, y, size) {
    if (!window.QRCodeLite) return false;
    try {
      var qr = QRCodeLite.create(String(text), { errorCorrectionLevel: 'M' });
      var n = qr.modules.size, data = qr.modules.data, quiet = 4;
      var span = n + quiet * 2;
      var cell = Math.max(1, Math.floor(size / span));
      var real = cell * span;
      var ox = Math.round(x + (size - real) / 2);
      var oy = Math.round(y + (size - real) / 2);
      ctx.fillStyle = '#FFFFFF'; roundRect(ctx, x, y, size, size, 14); ctx.fill();
      ctx.fillStyle = NAVY;
      for (var r = 0; r < n; r++) {
        for (var c = 0; c < n; c++) {
          if (data[r * n + c]) {
            ctx.fillRect(ox + (c + quiet) * cell, oy + (r + quiet) * cell, cell, cell);
          }
        }
      }
      return true;
    } catch (e) { return false; }
  }

  /* ---------- 卡片主绘制 1080×1440 ---------- */
  function draw(ctx, W, H, d) {
    var CFG = getCfg();
    var PAD = 104, CW = W - PAD * 2;
    var brand = (d.brand || CFG.brand || 'DAILY LEARNING').toUpperCase();
    /* 零站点硬编码：URL 由页面配置注入；缺省时退回当前页面地址，任何课程包都可用 */
    var url = d.shareUrl || CFG.shareUrl ||
              (typeof location !== 'undefined' ? String(location.href).split('#')[0] : '');
    var urlPretty = url.replace(/^https?:\/\//, '').replace(/\/$/, '');

    ctx.fillStyle = '#F2EFE9'; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = '#FFFFFF'; roundRect(ctx, 36, 36, W - 72, H - 72, 48); ctx.fill();

    eyebrow(ctx, PAD, 140, CW, brand + ' · DAILY CHALLENGE', 'NO. ' + (d.issueNo || '—'));
    ctx.fillStyle = LINE; ctx.fillRect(PAD, 162, CW, 2);

    /* 标题 */
    ctx.fillStyle = INK;
    fitOneLine(ctx, '每日一题', CW, 'bold 72px ' + FONT, 72, 50);
    ctx.fillText('每日一题', PAD, 258);
    ctx.fillStyle = GREEN; ctx.font = 'bold 28px ' + EN;
    ctx.fillText('DAILY CHALLENGE', PAD, 306);
    ctx.fillStyle = MUTED; ctx.font = '24px ' + EN;
    ctx.textAlign = 'right'; ctx.fillText(d.date || '', W - PAD, 306);
    ctx.textAlign = 'left';

    /* 题目块 */
    var qy = 344, qh = 330;
    ctx.fillStyle = SOFT; roundRect(ctx, PAD, qy, CW, qh, 24); ctx.fill();
    ctx.fillStyle = MUTED; ctx.font = 'bold 22px ' + EN;
    ctx.fillText('QUESTION · 今日题目', PAD + 32, qy + 52);
    ctx.fillStyle = INK; ctx.font = '32px ' + FONT;
    var ql = wrapMixed(ctx, d.question || '', CW - 64, 4);
    var y = qy + 106;
    for (var i = 0; i < ql.length; i++) { ctx.fillText(ql[i], PAD + 32, y); y += 46; }
    if (d.questionEn) {
      ctx.fillStyle = MUTED; ctx.font = 'italic 20px ' + SERIF;
      var el = wrapEn(ctx, d.questionEn, CW - 64, 2);
      y += 12;
      for (var j = 0; j < el.length; j++) { ctx.fillText(el[j], PAD + 32, y); y += 28; }
    }

    /* 选项（不标答案） */
    var oy = 726;
    ctx.fillStyle = MUTED; ctx.font = 'bold 22px ' + EN;
    ctx.fillText('OPTIONS · 选项', PAD, oy);
    oy += 30;
    var opts = (d.options || []).slice(0, 4);
    for (var k = 0; k < 4; k++) {
      var top = oy + k * 68;
      circle(ctx, PAD + 24, top + 24, 23, '#EDE9E0');
      ctx.fillStyle = NAVY; ctx.font = 'bold 24px ' + EN; ctx.textAlign = 'center';
      ctx.fillText('ABCD'.charAt(k), PAD + 24, top + 33);
      ctx.textAlign = 'left';
      ctx.fillStyle = INK; ctx.font = '26px ' + FONT;
      var ol = wrapMixed(ctx, opts[k] || '', CW - 76, 2);
      for (var m = 0; m < ol.length; m++) ctx.fillText(ol[m], PAD + 62, top + 22 + m * 32);
    }

    /* 结果条：不泄露答案，只显示作答结果 + 全网正确率 */
    var ry = 1038, rh = 96;
    var answered = !!d.answered, correct = d.correct === true;
    var bg = !answered ? '#FFF6DC' : (correct ? '#EDF7F2' : '#FBEFEE');
    var fg = !answered ? '#8A6A00' : (correct ? GREEN : RED);
    ctx.fillStyle = bg; roundRect(ctx, PAD, ry, CW, rh, 20); ctx.fill();
    var glyph = !answered ? '❓' : (correct ? '🟩' : '🟥');
    var head = !answered ? '等你来挑战 / Can you solve it?'
                         : (correct ? '我答对了 / I got it right' : '我答错了 / Not quite');
    ctx.fillStyle = fg;
    fitOneLine(ctx, glyph + '  ' + head, CW - 260, 'bold 34px ' + FONT, 34, 22);
    ctx.fillText(glyph + '  ' + head, PAD + 28, ry + 60);
    if (d.accuracy !== null && d.accuracy !== undefined) {
      ctx.fillStyle = fg; ctx.font = 'bold 26px ' + EN; ctx.textAlign = 'right';
      ctx.fillText('全网正确率 ' + d.accuracy + '%', W - PAD - 28, ry + 58);
      ctx.textAlign = 'left';
    }

    /* 底部分隔 + 二维码 + 网址 */
    ctx.fillStyle = LINE; ctx.fillRect(PAD, 1180, CW, 2);
    var qs = 190, qx = W - PAD - qs, qy2 = 1204;
    var ok = drawQR(ctx, url, qx, qy2, qs);
    ctx.fillStyle = NAVY; ctx.font = 'bold 28px ' + FONT;
    ctx.fillText('扫码来挑战 / Scan & try', PAD, 1248);
    ctx.fillStyle = MUTED; ctx.font = '22px ' + EN;
    fitOneLine(ctx, urlPretty, CW - qs - 36, '22px ' + EN, 22, 15);
    ctx.fillText(urlPretty, PAD, 1290);
    ctx.fillStyle = MUTED; ctx.font = '21px ' + FONT;
    ctx.fillText('每天一道题，全球同题 · 中英解析', PAD, 1332);
    ctx.fillStyle = '#B4AA98'; ctx.font = '18px ' + EN;
    ctx.fillText('One question a day, same worldwide', PAD, 1364);
    if (!ok) {  /* 极端兜底：二维码库缺失时至少把网址写清楚 */
      ctx.fillStyle = NAVY; ctx.font = 'bold 20px ' + EN;
      ctx.textAlign = 'right'; ctx.fillText(urlPretty, W - PAD, 1248); ctx.textAlign = 'left';
    }
  }

  function build(d) {
    var W = 1080, H = 1440;
    var cv = document.createElement('canvas');
    cv.width = W; cv.height = H;
    draw(cv.getContext('2d'), W, H, d || {});
    return cv.toDataURL('image/png');
  }

  /* ---------- 预览弹层 ---------- */
  var CSS = [
    '.dqsc-mask{position:fixed;inset:0;background:rgba(10,22,32,.66);z-index:9998;display:flex;align-items:center;justify-content:center;padding:16px;overflow:auto}',
    '.dqsc-panel{background:#fff;border-radius:18px;width:100%;max-width:520px;max-height:92vh;display:flex;flex-direction:column;box-shadow:0 24px 70px rgba(0,0,0,.35);overflow:hidden;font-family:' + FONT + '}',
    '.dqsc-head{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid #E2E9E4;font-weight:700;font-size:15px;color:#17211F}',
    '.dqsc-head .dqsc-x{border:0;background:#F1F5F1;width:32px;height:32px;border-radius:50%;font-size:20px;line-height:1;cursor:pointer;color:#66736E}',
    '.dqsc-body{overflow:auto;background:#F2EFE9;padding:14px;display:flex;justify-content:center}',
    '.dqsc-img{max-width:100%;height:auto;display:block;border-radius:10px;box-shadow:0 6px 20px rgba(0,0,0,.12)}',
    '.dqsc-foot{padding:12px 16px 16px;border-top:1px solid #E2E9E4}',
    '.dqsc-tip{font-size:12px;color:#66736E;line-height:1.5}',
    '.dqsc-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}',
    '.dqsc-btn{flex:1 1 auto;min-width:130px;border:1px solid #E2E9E4;background:#fff;color:#17211F;border-radius:10px;padding:11px 14px;font:inherit;font-weight:600;cursor:pointer;font-size:14px}',
    '.dqsc-btn.primary{background:#176B55;border-color:#176B55;color:#fff}',
    '@media(max-width:560px){.dqsc-mask{padding:8px}.dqsc-panel{max-height:94vh}.dqsc-body{padding:8px}.dqsc-head{padding:11px 13px}.dqsc-foot{padding:10px 12px 12px}}'
  ].join('\n');

  var mask = null;
  function ensureDom() {
    if (mask) return;
    var st = document.createElement('style');
    st.textContent = CSS;
    document.head.appendChild(st);
    mask = document.createElement('div');
    mask.className = 'dqsc-mask';
    mask.innerHTML =
      '<div class="dqsc-panel" role="dialog" aria-label="每日一题分享卡">' +
      '  <div class="dqsc-head"><span>每日一题分享卡 / Share card</span><button class="dqsc-x" aria-label="关闭">×</button></div>' +
      '  <div class="dqsc-body"><img class="dqsc-img" alt="每日一题分享卡"></div>' +
      '  <div class="dqsc-foot">' +
      '    <div class="dqsc-tip">长按图片即可保存，或点下方按钮下载 / Long-press to save, or tap below.</div>' +
      '    <div class="dqsc-actions">' +
      '      <button class="dqsc-btn primary" data-act="save">保存图片 / Save PNG</button>' +
      '      <button class="dqsc-btn" data-act="copy">复制文字战报 / Copy text</button>' +
      '    </div>' +
      '  </div>' +
      '</div>';
    document.body.appendChild(mask);
    mask.addEventListener('click', function (e) {
      if (e.target === mask || e.target.className === 'dqsc-x') { close(); return; }
      var b = e.target.closest ? e.target.closest('[data-act]') : null;
      if (!b) return;
      if (b.getAttribute('data-act') === 'save') save();
      else copyText();
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
  }
  function close() { if (mask) mask.style.display = 'none'; }
  var current = null;
  function save() {
    if (!current) return;
    var a = document.createElement('a');
    a.href = current.url;
    a.download = (current.slug || 'daily') + '-challenge-' + String(current.date || '').replace(/-/g, '') + '.png';
    document.body.appendChild(a); a.click(); a.remove();
  }
  function copyText() {
    if (!current || !current.shareText) return;
    var t = current.shareText;
    function done(btn) {
      var old = btn.textContent;
      btn.textContent = '已复制 / Copied!';
      setTimeout(function () { btn.textContent = old; }, 1600);
    }
    var btn = mask.querySelector('[data-act="copy"]');
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(t).then(function () { done(btn); }, function () { fallback(t); done(btn); });
    } else { fallback(t); done(btn); }
  }
  function fallback(t) {
    var ta = document.createElement('textarea');
    ta.value = t; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); } catch (e) {}
    document.body.removeChild(ta);
  }

  function open(d) {
    ensureDom();
    var url = build(d);
    var CFG = getCfg();
    current = {
      url: url,
      date: d.date || '',
      slug: d.slug || CFG.slug || 'daily',
      shareText: d.shareText || ''
    };
    mask.querySelector('.dqsc-img').src = url;
    mask.style.display = 'flex';
    try { mask.querySelector('.dqsc-body').scrollTop = 0; } catch (e) {}
  }

  window.DrowsyDailyShare = { open: open, build: build, close: close };
})();
