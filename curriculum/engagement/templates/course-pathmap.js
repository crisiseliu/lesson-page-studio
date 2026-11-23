/*!
 * course-pathmap.js — lesson-page-studio v2.3 游戏化注入层（3/3：关卡地图 / Lesson Path）
 *
 * 来源：2026-11-23 上线的 CSP 站 assets/pathmap.js v1.0.0（HANDOVER §39 / ARCHIVE 坑 54）。
 * 改造：366 / csp- 前缀 / .masonry / 300 节点门槛 / Boss 365-366 / cert==='csp' / CSP 七大域
 *       全部改为运行时读取 window.DROWSY_CERT，由 build_curriculum.py 在目录页注入。
 *
 * 设计（渐进增强、零破坏）：不改任何原有 a.tile，运行时读取既有瓦片的
 *   href / --c / .tile-title / .tile-tag / .locked 生成第二视图；
 *   地图节点同样带 class="tile" + href="dayN.html"，自动复用目录页门禁捕获；
 *   原网格 DOM 完整保留，工具条可切换视图并记忆（<slug>-catalog-view）。
 * 章节：按 --c 主题色变化自动切段；章名优先取 chapterLabels，其次按 domainLabels 映射，
 *       不依赖 bilingual.js 当前语言态。
 * 状态：已学（本地 ∪ 云端） / 当前（呼吸光圈 + START） / 锁定（.locked） / Boss（bossDays 金色 A/B）。
 * 无持久化写入；云端读取失败静默回退。
 */
(function () {
  'use strict';
  var CFG = window.DROWSY_CERT;
  if (!CFG || !CFG.slug) return;
  if (document.getElementById('dvPathMap')) return;

  var SLUG = CFG.slug;
  var GRID_SEL = CFG.gridSelector || '.masonry';
  var TILE_SEL = CFG.tileSelector || 'a.tile';
  var MIN_NODES = +(CFG.minNodes || 5);
  var VIEW_KEY = SLUG + '-catalog-view';
  var BOSS = (CFG.bossDays && CFG.bossDays.length === 2) ? CFG.bossDays : [0, 0];
  var CHAPTER_LABELS = CFG.chapterLabels || {};
  var DOMAIN_LABELS = CFG.domainLabels || {};

  var grid = document.querySelector(GRID_SEL);
  if (!grid) return;
  var tileEls = [].slice.call(grid.querySelectorAll(TILE_SEL));
  if (tileEls.length < MIN_NODES) return;

  var C = {
    ink: '#17211F', muted: '#66736E', soft: '#F1F5F1', line: '#E2E9E4',
    green: '#176B55', gold: '#FFC72C', navy: '#0F2A43', goldDark: '#8A5A00'
  };

  /* ---------- 读取既有瓦片（唯一数据源） ---------- */
  var nodes = tileEls.map(function (a) {
    var m = /day(\d+)\.html/i.exec(a.getAttribute('href') || '');
    if (!m) return null;
    var titleEl = a.querySelector('.tile-title');
    var tagEl = a.querySelector('.tile-tag');
    return {
      day: +m[1],
      href: a.getAttribute('href'),
      color: (a.style.getPropertyValue('--c') || '#5D6D7E').trim(),
      title: (titleEl ? titleEl.textContent : '').replace(/\s+/g, ' ').trim(),
      tag: (tagEl ? tagEl.textContent : '').replace(/\s+/g, ' ').trim(),
      locked: a.classList.contains('locked')
    };
  }).filter(Boolean).sort(function (a, b) { return a.day - b.day; });
  if (nodes.length < MIN_NODES) return;
  var TOTAL = nodes.length;

  /* 按主题色变化自动切分章节 */
  var chapters = [];
  nodes.forEach(function (n) {
    var last = chapters[chapters.length - 1];
    if (!last || last.color !== n.color) {
      chapters.push({ start: n.day, color: n.color, items: [] });
      last = chapters[chapters.length - 1];
    }
    last.items.push(n);
  });
  function chapterLabel(ch) {
    if (CHAPTER_LABELS[ch.start]) return CHAPTER_LABELS[ch.start];
    var tag = (ch.items[0] && ch.items[0].tag) || '';
    var code = tag.split('·')[0].trim();
    if (DOMAIN_LABELS[code]) return code + ' · ' + DOMAIN_LABELS[code];
    var dm = /Domain\s*(\d+)/i.exec(tag);
    if (dm) return 'Domain ' + dm[1] + ' · ' + (DOMAIN_LABELS['Domain ' + dm[1]] || '');
    var t = tag.replace(/已发布课程.*$/, '').replace(/完成\s*\d+%\s*解锁.*$/, '').trim();
    return t.slice(0, 30) || ('Day ' + ch.start);
  }

  /* ---------- 进度数据：本地 ∪ 云端 ---------- */
  var cloudDays = [];
  function doneSet() {
    var set = {};
    try {
      for (var n = 1; n <= TOTAL; n++) {
        var raw = localStorage.getItem(SLUG + '-day' + n + '-checks') ||
          (n === 1 ? localStorage.getItem(SLUG + 'day1checks') : null);
        var v = JSON.parse(raw || '[]');
        if (Array.isArray(v) && v.some(Boolean)) set[n] = true;
      }
    } catch (e) {}
    cloudDays.forEach(function (d) { if (d >= 1 && d <= TOTAL) set[+d] = true; });
    return set;
  }
  function nextDay(set) {
    var n = 1;
    while (set[n] && n <= TOTAL) n++;
    return n > TOTAL ? null : n;
  }

  /* ---------- 注入样式（视图切换由 JS 直接控制 grid/map 的 display，不依赖类名） ---------- */
  var css = [
    '#dvPathMap{margin:0 20px 8px;}',
    '.pm-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:#fff;border:1px solid ' + C.line + ';border-radius:12px;padding:10px 14px;margin:16px 20px 14px;}',
    '.pm-bar .pm-t{font-size:13px;font-weight:700;margin-right:auto;}',
    '.pm-bar .pm-hint{font-size:11.5px;color:' + C.muted + ';}',
    '.pm-btn{border:1px solid ' + C.line + ';background:#fff;color:' + C.ink + ';border-radius:99px;padding:6px 14px;font-size:12px;font-weight:700;cursor:pointer;transition:all .15s;}',
    '.pm-btn:hover{border-color:' + C.green + ';}',
    '.pm-btn.on{background:' + C.green + ';border-color:' + C.green + ';color:#fff;}',
    '.pm-ch{background:#fff;border:1px solid ' + C.line + ';border-radius:16px;margin:0 0 16px;padding:14px 12px 18px;overflow:hidden;}',
    '.pm-ch-head{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;border-left:4px solid var(--ch);padding-left:10px;margin-bottom:16px;}',
    '.pm-ch-no{font-size:12px;font-weight:800;color:var(--ch);letter-spacing:1px;}',
    '.pm-ch-name{font-size:14px;font-weight:700;}',
    '.pm-ch-range{font-size:11px;color:' + C.muted + ';}',
    '.pm-ch-prog{margin-left:auto;font-size:11px;color:' + C.green + ';font-weight:700;}',
    '.pm-track{position:relative;width:100%;}',
    '.pm-track svg{position:absolute;left:0;top:0;pointer-events:none;overflow:visible;}',
    '.pm-line-bg{fill:none;stroke:' + C.soft + ';stroke-width:7;stroke-linecap:round;stroke-dasharray:2 12;}',
    '.pm-line-done{fill:none;stroke:var(--ch);stroke-width:6;stroke-linecap:round;opacity:.85;}',
    '#dvPathMap .pm-node{position:absolute;display:flex;align-items:center;justify-content:center;',
    '  border-radius:50%;text-decoration:none;background:#fff;border:2px solid var(--c);color:var(--c);',
    '  font-weight:800;font-size:13px;line-height:1;z-index:2;margin:0;padding:0;break-inside:auto;',
    '  box-shadow:0 2px 7px rgba(23,33,31,.10);transition:transform .15s,box-shadow .15s;}',
    '#dvPathMap .pm-node:hover{transform:scale(1.13);box-shadow:0 6px 16px rgba(23,33,31,.18);}',
    '#dvPathMap .pm-node.done{background:var(--c);color:#fff;border-color:var(--c);}',
    '#dvPathMap .pm-node.locked{background:#FFFCF3;border:2px dashed #C99A2E;color:' + C.goldDark + ';}',
    '#dvPathMap .pm-node.boss{border:2px solid #C99A2E;background:linear-gradient(160deg,#FFE9A8,#FFC72C);color:#5A3C00;box-shadow:0 3px 12px rgba(255,199,44,.55);}',
    '#dvPathMap .pm-node.current{box-shadow:0 0 0 4px rgba(23,107,85,.20);animation:pmPulse 2.1s ease-in-out infinite;}',
    '@keyframes pmPulse{0%,100%{box-shadow:0 0 0 4px rgba(23,107,85,.20)}50%{box-shadow:0 0 0 10px rgba(23,107,85,.06)}}',
    '.pm-n{font-variant-numeric:tabular-nums;}',
    '.pm-ck,.pm-lk{position:absolute;right:-5px;top:-6px;font-size:10px;font-style:normal;',
    '  width:16px;height:16px;border-radius:50%;display:flex;align-items:center;justify-content:center;}',
    '.pm-ck{background:' + C.green + ';color:#fff;border:1.5px solid #fff;}',
    '.pm-lk{background:#FFF3D6;border:1px solid #ECD5A4;}',
    '.pm-here{position:absolute;top:-25px;left:50%;transform:translateX(-50%);white-space:nowrap;',
    '  background:' + C.green + ';color:#fff;font-size:9.5px;font-weight:700;padding:2px 7px;border-radius:99px;z-index:3;}',
    '@media(max-width:560px){#dvPathMap{margin:0 12px 8px}',
    '.pm-bar{margin:10px 12px 10px;padding:8px 10px;gap:6px}',
    '.pm-bar .pm-t{width:100%;font-size:12px;margin-right:0}',
    '.pm-bar .pm-hint{display:none}',
    '.pm-btn{padding:5px 10px;font-size:11px}',
    '.pm-ch{padding:12px 8px 16px}.pm-ch-name{font-size:13px}}'
  ].join('');
  var st = document.createElement('style');
  st.appendChild(document.createTextNode(css));
  document.head.appendChild(st);

  /* ---------- 工具条 + 地图容器 ---------- */
  var bar = document.createElement('div');
  bar.className = 'pm-bar';
  bar.id = 'pmBar';
  bar.innerHTML =
    '<span class="pm-t">课程地图 / Your learning path</span>' +
    '<span class="pm-hint">已学点亮 · 光圈=当前 · 🔒=解锁条件 · ★=模拟卷</span>' +
    '<button type="button" class="pm-btn" id="pmBtnPath">🗺️ 关卡地图 / Path</button>' +
    '<button type="button" class="pm-btn" id="pmBtnGrid">▦ 课程网格 / Grid</button>' +
    '<button type="button" class="pm-btn" id="pmBtnHere">📍 定位 / Find me</button>';
  grid.parentNode.insertBefore(bar, grid);

  var map = document.createElement('div');
  map.id = 'dvPathMap';
  grid.parentNode.insertBefore(map, grid);

  function setView(v, save) {
    var isPath = v !== 'grid';
    /* 不依赖 .masonry 类名：直接切换原网格与地图的显示 */
    grid.style.display = isPath ? 'none' : '';
    map.style.display = isPath ? '' : 'none';
    document.getElementById('pmBtnPath').classList.toggle('on', isPath);
    document.getElementById('pmBtnGrid').classList.toggle('on', !isPath);
    if (save) { try { localStorage.setItem(VIEW_KEY, isPath ? 'path' : 'grid'); } catch (e) {} }
    if (isPath) render();
  }
  document.getElementById('pmBtnPath').addEventListener('click', function () { setView('path', true); });
  document.getElementById('pmBtnGrid').addEventListener('click', function () { setView('grid', true); });
  document.getElementById('pmBtnHere').addEventListener('click', function () {
    setView('path', false);
    var el = map.querySelector('.pm-node.current');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  });

  /* ---------- 布局 ---------- */
  function f(n) { return Math.round(n * 10) / 10; }
  function buildPath(pts, a, b) {
    if (b <= a) return '';
    var s = 'M ' + f(pts[a].x) + ' ' + f(pts[a].y);
    for (var i = a + 1; i <= b; i++) {
      var p = pts[i - 1], q = pts[i];
      var dx = q.x - p.x, dy = q.y - p.y;
      if (Math.abs(dy) < 40) {
        s += ' C ' + f(p.x + dx * 0.3) + ' ' + f(p.y - 13) + ' ' +
          f(q.x - dx * 0.3) + ' ' + f(q.y - 13) + ' ' + f(q.x) + ' ' + f(q.y);
      } else {
        s += ' C ' + f(p.x) + ' ' + f(p.y + dy * 0.45) + ' ' +
          f(q.x) + ' ' + f(q.y - dy * 0.45) + ' ' + f(q.x) + ' ' + f(q.y);
      }
    }
    return s;
  }

  function render() {
    /* W 必须是 .pm-track 的内容宽度（坑 54：用 map.clientWidth 会右侧溢出） */
    var outerW = map.clientWidth || grid.clientWidth || 900;
    var chPadX = window.innerWidth <= 560 ? 8 : 12;
    var W = Math.max(240, outerW - chPadX * 2);
    var set = doneSet();
    var next = nextDay(set);
    var small = W < 560;
    var d = small ? 38 : (W < 900 ? 42 : 46);
    var gx = small ? 13 : 18;
    var gy = small ? 30 : 38;
    var pad = small ? 8 : 16;
    var colsMax = Math.max(3, Math.floor((W - pad * 2 + gx) / (d + gx)));
    var html = '';

    chapters.forEach(function (ch, ci) {
      var items = ch.items, len = items.length;
      /* 单行短章节按实际节点数居中；多行保持固定列数，蛇形折返才上下对齐 */
      var perRow = Math.min(colsMax, len);
      var rowW = perRow * d + (perRow - 1) * gx;
      var x0 = (W - rowW) / 2;
      var rows = Math.ceil(len / perRow);
      var H = pad + rows * (d + gy) - gy + pad + 8;
      var pts = [];
      items.forEach(function (n, k) {
        var r = Math.floor(k / perRow), j = k % perRow;
        var col = (r % 2 === 0) ? j : (perRow - 1 - j);
        var x = x0 + col * (d + gx) + d / 2;
        var y = pad + r * (d + gy) + Math.sin((j + r * 0.6) * 0.8) * 6 + d / 2;
        pts.push({ x: x, y: y, n: n });
      });
      var doneEnd = -1;
      for (var i = 0; i < len; i++) {
        if (items[i].day < (next || TOTAL + 1)) doneEnd = i; else break;
      }
      var doneCount = items.filter(function (n) { return !!set[n.day]; }).length;
      html += '<section class="pm-ch" style="--ch:' + ch.color + '">' +
        '<div class="pm-ch-head"><span class="pm-ch-no">' +
        String(ci + 1).padStart(2, '0') + '</span><span class="pm-ch-name">' + chapterLabel(ch) +
        '</span><span class="pm-ch-range">Day ' + items[0].day + '–' + items[len - 1].day +
        '</span><span class="pm-ch-prog">' + doneCount + ' / ' + len + ' ✓</span></div>' +
        '<div class="pm-track" style="height:' + f(H) + 'px">' +
        '<svg width="' + f(W) + '" height="' + f(H) + '" viewBox="0 0 ' + f(W) + ' ' + f(H) + '" aria-hidden="true">' +
        '<path class="pm-line-bg" d="' + buildPath(pts, 0, len - 1) + '"/>' +
        (doneEnd > 0 ? '<path class="pm-line-done" d="' + buildPath(pts, 0, doneEnd) + '"/>' : '') +
        '</svg>';

      pts.forEach(function (p) {
        var n = p.n;
        var isDone = !!set[n.day];
        var isCur = n.day === next;
        var bossIdx = BOSS.indexOf(n.day);
        var isBoss = bossIdx >= 0;
        var cls = 'tile pm-node' + (isDone ? ' done' : '') + (isCur ? ' current' : '') +
          (n.locked ? ' locked' : '') + (isBoss ? ' boss' : '');
        var inner = isBoss
          ? '<span class="pm-n">' + (bossIdx === 0 ? 'A' : 'B') + '</span>'
          : '<span class="pm-n">' + n.day + '</span>';
        if (isDone) inner += '<i class="pm-ck">✓</i>';
        if (n.locked) inner += '<i class="pm-lk">🔒</i>';
        if (isCur) inner += '<span class="pm-here">START / 你在这里</span>';
        var tip = 'Day ' + n.day + ' · ' + n.title.replace(/"/g, '&quot;');
        html += '<a class="' + cls + '" href="' + n.href + '" style="--c:' + n.color +
          ';left:' + f(p.x - d / 2) + 'px;top:' + f(p.y - d / 2) + 'px;width:' + d +
          'px;height:' + d + 'px" title="' + tip + '" aria-label="' + tip + '">' + inner + '</a>';
      });
      html += '</div></section>';
    });
    map.innerHTML = html;
  }

  /* ---------- 云端进度并集（按 cert_slug 过滤，失败静默回退） ---------- */
  try {
    if (window.DrowsySync && typeof DrowsySync.progressList === 'function') {
      DrowsySync.progressList().then(function (arr) {
        if (!Array.isArray(arr)) return;
        for (var i = 0; i < arr.length; i++) {
          if (arr[i] && (arr[i].cert === SLUG || (SLUG === 'csp' && arr[i].cert === undefined))) {
            cloudDays = (arr[i].days || []).map(Number);
            render();
            break;
          }
        }
      }).catch(function () {});
    }
  } catch (e) {}

  /* 视图记忆 + 首屏渲染 */
  var saved = 'path';
  try { saved = localStorage.getItem(VIEW_KEY) || 'path'; } catch (e) {}
  setView(saved, false);

  var t = null;
  window.addEventListener('resize', function () {
    clearTimeout(t);
    t = setTimeout(function () { if (map.style.display !== 'none') render(); }, 160);
  });
  window.addEventListener('storage', function (e) {
    if (e.key && e.key.indexOf(SLUG + '-day') === 0) render();
  });
  window.addEventListener('pm:progress', render);
})();
