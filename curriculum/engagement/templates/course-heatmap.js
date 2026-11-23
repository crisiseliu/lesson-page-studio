/*!
 * course-heatmap.js — lesson-page-studio v2.3 游戏化注入层（1/3：热力图 + streak 冻结 + 成就徽章）
 *
 * 来源：2026-11-23 上线的 CSP 站 assets/heatmap.js v1.0.0（HANDOVER §38.1）。
 * 改造：所有硬编码（366 / csp- 前缀 / .masonry / Boss 365/366 / cert==='csp'）改为
 *       运行时读取 window.DROWSY_CERT，由 build_curriculum.py 在目录页注入。
 * 同一份文件服务任意证书课程，零构建期 token；产物自包含在 <site>/<slug>/assets/。
 *
 * 数据源：<slug>-dayN-checks（本地）∪ DrowsySync.progressList() 云端（读失败静默回退）；
 *         <slug>-study-days（自然日数组，供 streak/冻结卡）、可选 <slug>-vocab-v1（词汇徽章）。
 * 冻结卡：历史每满 7 个自然日连续学习攒 1 张（上限 3），断档恰好 1 天自动桥接；
 *         桥接不越过最早学习日。纯函数、零持久化，天然免同步。
 */
(function () {
  'use strict';
  var CFG = window.DROWSY_CERT;
  if (!CFG || !CFG.slug) return;                 /* 只在注入了证书上下文的目录页生效 */
  if (document.getElementById('dvHeatPanel')) return;
  var SLUG = CFG.slug;
  var TOTAL = +CFG.total || 366;
  var BOSS = (CFG.bossDays && CFG.bossDays.length === 2) ? CFG.bossDays : [TOTAL - 1, TOTAL];
  var VOCAB_KEY = CFG.vocabKey || '';
  var GRID_SEL = CFG.gridSelector || '.masonry';
  var TILE_SEL = CFG.tileSelector || '.tile[href^="day"]';
  var STUDY_KEY = SLUG + '-study-days';
  var C = {
    ink: '#17211F', muted: '#66736E', soft: '#F1F5F1', line: '#E2E9E4',
    green: '#176B55', gold: '#FFC72C', navy: '#0F2A43', paper: '#FBFCFA',
    goldDark: '#8A5A00'
  };

  /* ---------- 数据读取 ---------- */
  function daySetLocal() {
    var set = {};
    try {
      for (var n = 1; n <= TOTAL; n++) {
        var raw = localStorage.getItem(SLUG + '-day' + n + '-checks');
        if (n === 1 && !raw) raw = localStorage.getItem(SLUG + 'day1checks');
        var v = JSON.parse(raw || '[]');
        if (Array.isArray(v) && v.some(Boolean)) set[n] = true;
      }
    } catch (e) {}
    return set;
  }
  function studyDates() {
    try {
      var a = JSON.parse(localStorage.getItem(STUDY_KEY) || '[]');
      if (Array.isArray(a)) return a.slice();
    } catch (e) {}
    return [];
  }
  function vocabCount() {
    if (!VOCAB_KEY) return 0;
    try {
      var a = JSON.parse(localStorage.getItem(VOCAB_KEY) || '[]');
      if (Array.isArray(a)) return a.length;
    } catch (e) {}
    return 0;
  }
  function dateKey(d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function parseKey(s) {
    var p = String(s || '').split('-');
    if (p.length !== 3) return null;
    var d = new Date(+p[0], +p[1] - 1, +p[2]);
    return isNaN(d.getTime()) ? null : d;
  }

  /* ---------- 连续天数（含冻结桥接） ---------- */
  function freezeInventory(dates) {
    var days = dates.map(parseKey).filter(Boolean).sort(function (a, b) { return a - b; });
    var tokens = 0, run = 0, prev = null;
    for (var j = 0; j < days.length; j++) {
      if (prev && Math.round((days[j] - prev) / 86400000) === 1) run++;
      else { tokens += Math.floor(run / 7); run = 1; }
      prev = days[j];
    }
    tokens += Math.floor(run / 7);
    return Math.min(3, tokens);
  }
  function computeStreak() {
    var dates = studyDates();
    var set = {};
    dates.forEach(function (x) { if (x) set[x] = true; });
    var cur = new Date(); cur.setHours(0, 0, 0, 0);
    if (!set[dateKey(cur)]) cur.setDate(cur.getDate() - 1);
    if (!set[dateKey(cur)]) return { streak: 0, bridged: 0 };
    var tokens = freezeInventory(dates);
    var oldest = null;
    dates.forEach(function (x) { var d = parseKey(x); if (d && (!oldest || d < oldest)) oldest = d; });
    var run = 0, bridged = 0, miss = 0;
    while (run + bridged < 3650) {
      if (set[dateKey(cur)]) { run++; miss = 0; }
      else {
        if (miss > 0) break;
        if (tokens <= bridged) break;
        if (oldest && cur <= oldest) break;   /* 学习史之前的日子不桥接 */
        bridged++; miss = 1;
      }
      cur.setDate(cur.getDate() - 1);
    }
    return { streak: run + bridged, bridged: bridged };
  }
  function bestStreak() {
    var days = studyDates().map(parseKey).filter(Boolean).sort(function (a, b) { return a - b; });
    var best = 0, run = 0, prev = null;
    for (var i = 0; i < days.length; i++) {
      if (prev && Math.round((days[i] - prev) / 86400000) === 1) run++;
      else run = 1;
      if (run > best) best = run;
      prev = days[i];
    }
    return best;
  }

  /* ---------- 徽章（阈值按总课数缩放，短课程也有可达目标） ---------- */
  function computeBadges(doneCount, best, vocab, doneSet) {
    var q1 = Math.max(3, Math.round(TOTAL * 0.10));
    var q2 = Math.max(7, Math.round(TOTAL * 0.30));
    var q3 = Math.max(10, Math.round(TOTAL * 0.55));
    var list = [
      { id: 'first', zh: '启程', en: 'First Step', ok: doneCount >= 1 },
      { id: 'd7', zh: '七日不辍', en: '7 Days', ok: best >= 7 },
      { id: 'd30', zh: '三成立业', en: q1 + ' Lessons', ok: doneCount >= q1 },
      { id: 's30', zh: '月度连胜', en: 'Streak 30', ok: best >= 30 },
      { id: 'd100', zh: '百日坚持', en: q2 + ' Lessons', ok: doneCount >= q2 },
      { id: 'd200', zh: '半程里程', en: q3 + ' Lessons', ok: doneCount >= q3, rare: true },
      { id: 'mockA', zh: '模拟卷 A', en: 'Mock A', ok: !!doneSet[BOSS[0]], rare: true },
      { id: 'mockB', zh: '模拟卷 B', en: 'Mock B', ok: !!doneSet[BOSS[1]], rare: true }
    ];
    if (VOCAB_KEY) {
      list.splice(6, 0,
        { id: 'v20', zh: '词汇入门', en: '20 Terms', ok: vocab >= 20 },
        { id: 'v50', zh: '词汇进阶', en: '50 Terms', ok: vocab >= 50 });
    }
    return list;
  }

  /* ---------- 样式 ---------- */
  var CSS = [
    '#dvHeatPanel{background:#fff;border:1px solid ' + C.line + ';border-radius:14px;margin:16px 20px;padding:16px 18px;}',
    '#dvHeatPanel .hm-h{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;}',
    '#dvHeatPanel .hm-t{font-size:14px;font-weight:700;}',
    '#dvHeatPanel .hm-sub{font-size:12px;color:' + C.muted + ';}',
    '#dvHeatPanel .hm-stats{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0;}',
    '#dvHeatPanel .hm-stat{background:' + C.soft + ';border-radius:10px;padding:10px 14px;min-width:108px;}',
    '#dvHeatPanel .hm-stat .n{font-size:20px;font-weight:700;color:' + C.green + ';}',
    '#dvHeatPanel .hm-stat .n.freeze{color:' + C.navy + ';}',
    '#dvHeatPanel .hm-stat .l{font-size:11px;color:' + C.muted + ';margin-top:2px;}',
    '#dvHeatPanel .hm-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(15px,1fr));gap:3px;}',
    '#dvHeatPanel .hm-cell{aspect-ratio:1/1;border-radius:4px;background:' + C.soft + ';position:relative;}',
    '#dvHeatPanel .hm-cell.done{border:none;}',
    '#dvHeatPanel .hm-cell.lock{opacity:.55;}',
    '#dvHeatPanel .hm-cell:hover::after{content:attr(data-tip);position:absolute;bottom:calc(100% + 6px);left:50%;transform:translateX(-50%);',
    'background:' + C.navy + ';color:#fff;font-size:11px;line-height:1.4;padding:5px 9px;border-radius:8px;white-space:nowrap;z-index:20;pointer-events:none;}',
    '#dvHeatPanel .hm-legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:10px;font-size:11px;color:' + C.muted + ';}',
    '#dvHeatPanel .hm-legend i{width:10px;height:10px;border-radius:3px;display:inline-block;margin-right:4px;vertical-align:-1px;}',
    '#dvHeatPanel .hm-badges{display:flex;gap:12px;flex-wrap:wrap;margin-top:14px;padding-top:14px;border-top:1px dashed ' + C.line + ';}',
    '#dvHeatPanel .hm-badge{text-align:center;width:64px;}',
    '#dvHeatPanel .hm-badge .b{width:44px;height:44px;border-radius:50%;margin:0 auto 5px;display:flex;align-items:center;justify-content:center;',
    'font-size:11px;font-weight:700;background:' + C.soft + ';color:' + C.muted + ';border:1.5px dashed ' + C.line + ';}',
    '#dvHeatPanel .hm-badge.on .b{background:' + C.green + ';color:#fff;border:1.5px solid ' + C.green + ';}',
    '#dvHeatPanel .hm-badge.rare.on .b{background:' + C.goldDark + ';border-color:' + C.goldDark + ';}',
    '#dvHeatPanel .hm-badge .t{font-size:10.5px;color:' + C.muted + ';line-height:1.3;}',
    '#dvHeatPanel .hm-badge.on .t{color:' + C.ink + ';}',
    '@media(max-width:560px){#dvHeatPanel{margin:12px 12px;padding:14px 12px;}#dvHeatPanel .hm-badge{width:56px;}}'
  ].join('');

  /* ---------- 渲染 ---------- */
  function tileColors() {
    var map = {};
    try {
      var tiles = document.querySelectorAll(TILE_SEL);
      for (var i = 0; i < tiles.length; i++) {
        var m = (tiles[i].getAttribute('href') || '').match(/day(\d+)\.html/);
        if (m) map[+m[1]] = tiles[i].style.getPropertyValue('--c') || C.muted;
      }
    } catch (e) {}
    return map;
  }
  function render(cloudDays) {
    var panel = document.getElementById('dvHeatPanel');
    if (!panel) return;
    var local = daySetLocal();
    var set = {};
    Object.keys(local).forEach(function (k) { if (local[k]) set[+k] = true; });
    (cloudDays || []).forEach(function (d) { if (d >= 1 && d <= TOTAL) set[+d] = true; });
    var doneCount = Object.keys(set).length;
    var st = computeStreak();
    var best = bestStreak();
    var colors = tileColors();
    var pct = Math.round(doneCount / TOTAL * 100);
    var streakHtml = st.streak + (st.bridged ? '<span style="font-size:12px;font-weight:400;color:' + C.muted + ';">(含' + st.bridged + '次冻结)</span>' : '');
    var statsHtml =
      '<div class="hm-stat"><div class="n freeze">' + streakHtml + '</div><div class="l">连续学习 / Streak</div></div>' +
      '<div class="hm-stat"><div class="n">' + best + '</div><div class="l">最佳连续 / Best</div></div>' +
      '<div class="hm-stat"><div class="n">' + doneCount + ' / ' + TOTAL + '</div><div class="l">已学课程 / Lessons</div></div>' +
      '<div class="hm-stat"><div class="n">' + pct + '%</div><div class="l">总进度 / Progress</div></div>';
    var cells = '';
    for (var n = 1; n <= TOTAL; n++) {
      var tip = 'Day ' + n, title = null;
      try {
        var tEl = document.querySelector(TILE_SEL.replace('[href^="day"]', '[href="day' + n + '.html"]') + ' .tile-title');
        if (tEl) title = tEl.textContent.replace(/🔒/, '').trim();
      } catch (e) {}
      if (title) tip = 'Day ' + n + ' · ' + title;
      tip = tip.replace(/"/g, '');
      if (set[n]) cells += '<div class="hm-cell done" data-tip="' + tip + '" style="background:' + (colors[n] || C.green) + ';"></div>';
      else cells += '<div class="hm-cell lock" data-tip="' + tip + '"></div>';
    }
    var badges = computeBadges(doneCount, best, vocabCount(), set);
    var badgeHtml = badges.map(function (b) {
      return '<div class="hm-badge' + (b.ok ? ' on' : '') + (b.rare ? ' rare' : '') + '"><div class="b">' +
        (b.ok ? '✓' : '') + '</div><div class="t">' + b.zh + ' / ' + b.en + '</div></div>';
    }).join('');
    panel.innerHTML =
      '<div class="hm-h"><span class="hm-t">我的 ' + TOTAL + ' 天 / My ' + TOTAL + ' days</span>' +
      '<span class="hm-sub">连续满 7 天得 1 张冻结卡（最多 3 张），断档 1 天自动补记</span></div>' +
      '<div class="hm-stats">' + statsHtml + '</div>' +
      '<div class="hm-grid">' + cells + '</div>' +
      '<div class="hm-legend"><span><i style="background:' + C.green + ';"></i>已学 / Learned</span>' +
      '<span><i style="background:' + C.soft + ';border:1px solid ' + C.line + ';"></i>未学 / Not yet</span>' +
      '<span style="color:#8A5A00;">金色徽章 = 模拟卷 / 半程里程碑</span></div>' +
      '<div class="hm-badges">' + badgeHtml + '</div>';
  }

  function init() {
    var style = document.createElement('style');
    style.id = 'dvHeatCSS';
    style.textContent = CSS;
    document.head.appendChild(style);
    var grid = document.querySelector(GRID_SEL);
    if (!grid) return;
    var panel = document.createElement('section');
    panel.id = 'dvHeatPanel';
    grid.parentNode.insertBefore(panel, grid);
    render(null);
    /* 云端进度并集：按 cert_slug 过滤，读失败静默回退本地 */
    try {
      if (window.DrowsySync && typeof DrowsySync.progressList === 'function') {
        DrowsySync.progressList().then(function (arr) {
          if (!Array.isArray(arr)) return;
          for (var i = 0; i < arr.length; i++) {
            if (arr[i] && (arr[i].cert === SLUG || (SLUG === 'csp' && arr[i].cert === undefined))) {
              render(arr[i].days || []);
              break;
            }
          }
        }).catch(function () {});
      }
    } catch (e) {}
    try {
      window.addEventListener('storage', function (ev) {
        if (!ev || !ev.key) return;
        if (ev.key === STUDY_KEY || ev.key === VOCAB_KEY || ev.key.indexOf(SLUG + '-day') === 0) render(null);
      });
    } catch (e) {}
    window.addEventListener('pm:progress', function () { render(null); });
  }

  /* 脚本放在 body 末尾：网格已解析时立即 init，保证「热力图 → 工具条 → 地图」的插入顺序
     （若等 DOMContentLoaded，会被立即执行的 pathmap 抢先，面板掉到地图下面）。 */
  if (document.querySelector(GRID_SEL)) init();
  else if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
