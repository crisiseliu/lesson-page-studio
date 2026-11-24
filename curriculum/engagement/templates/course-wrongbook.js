/*!
 * Drowsy HSE · 课程包错题本 + 间隔复习 (Wrong Book / SRS) v1.0.0 — 2026-11-24
 * ---------------------------------------------------------------------------
 * 通用模板：零构建 token、零凭据、自包含在 <site>/<slug>/assets/。
 * 从 window.DROWSY_CERT / window.DROWSY_DAILY_CONFIG / <meta name="drowsy-cert">
 * 运行时读取 slug；从 window.DROWSY_WRONGBOOK_CONFIG 读可选同步与间隔配置。
 *
 * 本地键：<slug>-wrongbook-items / <slug>-wrongbook-backfilled-v1
 * 云同步：仅当配置含 sync={url, anonKey} 时启用，沿用站点 /assets/sync.js 会话，
 *         写 user_wrongbook 表 (owner_id, cert_slug, item_id)，RLS 仅本人。
 *
 * SRS：错 -> level 0 / 1 天；对 -> 1(3 天) -> 2(7 天) -> 3 毕业；中途错回 0。
 */
(function () {
  'use strict';
  var VERSION = '1.0.0';
  var LETTERS = ['A', 'B', 'C', 'D'];
  var CFG = window.DROWSY_WRONGBOOK_CONFIG || {};
  var INTERVALS = (CFG.intervals && CFG.intervals.length === 3) ? CFG.intervals.slice() : [1, 3, 7];
  var SYNC = (CFG.sync && CFG.sync.url && CFG.sync.anonKey) ? CFG.sync : null;
  var INDEX_URL = CFG.indexUrl || 'assets/data/quiz_index.json?v=1';

  function readSlug() {
    if (window.DROWSY_CERT && window.DROWSY_CERT.slug) return String(window.DROWSY_CERT.slug).trim();
    if (window.DROWSY_DAILY_CONFIG && window.DROWSY_DAILY_CONFIG.slug) return String(window.DROWSY_DAILY_CONFIG.slug).trim();
    var m = document.querySelector('meta[name="drowsy-cert"]');
    return (m && m.content) ? String(m.content).trim() : 'course';
  }
  var slug = readSlug();
  var STORE_KEY = slug + '-wrongbook-items';
  var BACKFILL_KEY = slug + '-wrongbook-backfilled-v1';
  var QUIZ_KEY = slug + '-day';

  var items = {};
  var cloudReady = false;
  var pushTimer = null;
  var listeners = [];

  /* ------------------------------ 工具 ------------------------------ */
  function nowISO() { return new Date().toISOString(); }
  function dayISO(n) { return new Date(Date.now() + n * 86400000).toISOString(); }
  function txt(el) { return el ? (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim() : ''; }
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function load() {
    try { items = JSON.parse(localStorage.getItem(STORE_KEY) || '{}') || {}; }
    catch (e) { items = {}; }
    if (!items || Object.prototype.toString.call(items) !== '[object Object]') items = {};
  }
  function save() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(items)); } catch (e) {}
    listeners.forEach(function (fn) { try { fn(); } catch (e) {} });
    schedulePush();
  }
  function onChange(fn) { if (typeof fn === 'function') listeners.push(fn); }

  /* ------------------------------ SRS ------------------------------ */
  function newRecord(rec) {
    rec.firstWrong = rec.firstWrong || nowISO();
    rec.lastWrong = rec.lastWrong || rec.firstWrong;
    rec.lastReview = rec.lastReview || null;
    rec.level = typeof rec.level === 'number' ? rec.level : 0;
    rec.reviews = rec.reviews || 0;
    rec.due = rec.due || dayISO(INTERVALS[rec.level] || INTERVALS[0]);
    rec.updatedAt = nowISO();
    return rec;
  }
  function markWrong(rec, choice) {
    rec.wrongChoice = choice;
    rec.lastWrong = nowISO();
    rec.level = 0;
    rec.due = dayISO(INTERVALS[0]);
    rec.reviews = (rec.reviews || 0) + 1;
    rec.updatedAt = nowISO();
    return rec;
  }
  function markRight(rec) {
    rec.level = Math.min(3, (rec.level || 0) + 1);
    rec.due = rec.level >= 3 ? null : dayISO(INTERVALS[rec.level] || INTERVALS[2]);
    rec.lastReview = nowISO();
    rec.reviews = (rec.reviews || 0) + 1;
    rec.updatedAt = nowISO();
    return rec;
  }
  function record(rec) {
    if (!rec || !rec.id) return;
    var old = items[rec.id];
    if (old && old.updatedAt && rec.updatedAt && old.updatedAt > rec.updatedAt) return;
    items[rec.id] = newRecord(rec);
    save();
  }
  function due() {
    var t = Date.now(), out = [];
    Object.keys(items).forEach(function (k) {
      var r = items[k];
      if (r && r.due && Date.parse(r.due) <= t) out.push(r);
    });
    return out.sort(function (a, b) { return Date.parse(a.due) - Date.parse(b.due); });
  }
  function all() {
    return Object.keys(items).map(function (k) { return items[k]; })
      .sort(function (a, b) { return (b.updatedAt || '').localeCompare(a.updatedAt || ''); });
  }
  function stats() {
    var list = all(), mastered = 0;
    list.forEach(function (r) { if (!r.due) mastered++; });
    return { total: list.length, due: due().length, mastered: mastered, learning: list.length - mastered };
  }
  function review(id, correct) {
    var r = items[id];
    if (!r) return false;
    if (correct) markRight(r); else markWrong(r, r.wrongChoice);
    save();
    return true;
  }
  function remove(id) { if (items[id]) { delete items[id]; save(); return true; } return false; }

  /* ------------------------------ 页面采集 ------------------------------ */
  function stripLetter(s, letter) {
    return String(s || '').replace(new RegExp('^\\s*' + letter + '\\s*[\\.、:：]\\s*'), '').trim();
  }
  function questionFromLesson() {
    var box = document.getElementById('quiz');
    if (!box) return null;
    var opts = [], labels = box.querySelectorAll('label');
    for (var i = 0; i < labels.length; i++) {
      var input = labels[i].querySelector('input[name="q"]');
      if (input) opts.push(stripLetter(txt(labels[i]), input.value));
    }
    if (opts.length < 2) return null;
    var ps = [], scope = (box.closest && box.closest('section')) || box.parentNode;
    var nodes = scope.querySelectorAll('p');
    for (var j = 0; j < nodes.length; j++) {
      var t = txt(nodes[j]);
      if (!t || /自编练习题|not an official exam question|关于题目来源|About these questions/.test(t)) continue;
      // Node.DOCUMENT_POSITION_FOLLOWING = 4：题干段落必须在 #quiz 之前
      if ((nodes[j].compareDocumentPosition(box) & 4) && ps.length < 2) ps.push(t);
    }
    return { q: ps.join(' / '), o: opts };
  }
  function correctFromFeedback() {
    var s = txt(document.getElementById('feedback'));
    var m = s.match(/正确答案是\s*([ABCD])/) || s.match(/answer is\s*([ABCD])/i);
    return m ? LETTERS.indexOf(m[1]) : -1;
  }
  function hookLesson() {
    var btn = document.getElementById('checkBtn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      setTimeout(function () {
        var sel = document.querySelector('input[name="q"]:checked');
        if (!sel) return;
        var picked = LETTERS.indexOf(sel.value);
        var dataAns = btn.getAttribute('data-answer');
        var correct = dataAns && LETTERS.indexOf(dataAns.trim().toUpperCase()) >= 0
          ? LETTERS.indexOf(dataAns.trim().toUpperCase()) : correctFromFeedback();
        if (correct < 0 || picked === correct) return;
        var info = questionFromLesson() || {};
        var day = parseInt((location.pathname.match(/day(\d+)\.html/i) || [0, 0])[1], 10);
        if (!day) return;
        var why = btn.getAttribute('data-why-zh') || '';
        var whyEn = btn.getAttribute('data-why-en') || '';
        var w = [why, whyEn].filter(Boolean).join(' / ') || txt(document.getElementById('feedback'));
        record({ id: 'day' + day, kind: 'lesson', day: day,
          q: info.q || ('Day ' + day + ' 课内测验 / Lesson quiz'),
          o: info.o || [], a: correct, w: w, wrongChoice: picked });
      }, 0);
    });
  }
  function hookRecap() {
    var btns = document.querySelectorAll('.rqBtn');
    if (!btns.length) return;
    Array.prototype.forEach.call(btns, function (btn) {
      btn.addEventListener('click', function () {
        setTimeout(function () {
          var name = btn.getAttribute('data-name'), ok = btn.getAttribute('data-ok');
          var sel = document.querySelector('input[name="' + name + '"]:checked');
          if (!sel || !ok) return;
          var picked = LETTERS.indexOf(sel.value), correct = LETTERS.indexOf(ok);
          if (picked < 0 || correct < 0 || picked === correct) return;
          var block = btn.closest ? btn.closest('.rq') : null;
          if (!block) return;
          var opts = [], labels = block.querySelectorAll('label');
          for (var i = 0; i < labels.length; i++) {
            var inp = labels[i].querySelector('input');
            opts.push(stripLetter(txt(labels[i]), inp ? inp.value : LETTERS[i]));
          }
          var day = parseInt((location.pathname.match(/day(\d+)\.html/i) || [0, 0])[1], 10);
          if (!day) return;
          record({ id: 'day' + day + '-' + name, kind: 'recap', day: day,
            q: txt(block.querySelector('p')), o: opts, a: correct,
            w: (block.getAttribute('data-expl-zh') || '') + ' / ' + (block.getAttribute('data-expl-en') || ''),
            wrongChoice: picked });
        }, 0);
      });
    });
  }
  function hookDaily() {
    var btn = document.getElementById('dqSubmit');
    if (!btn) return;
    btn.addEventListener('click', function () {
      setTimeout(function () {
        var right = document.querySelector('#dqOpts .right');
        var pickedEl = document.querySelector('#dqOpts .sel');
        var wrongEl = document.querySelector('#dqOpts .wrong');
        if (!right) return;
        var opts = document.querySelectorAll('#dqOpts .opt');
        var correct = Array.prototype.indexOf.call(opts, right);
        var picked = pickedEl ? Array.prototype.indexOf.call(opts, pickedEl) : -1;
        if (picked < 0 && wrongEl) picked = Array.prototype.indexOf.call(opts, wrongEl);
        if (correct < 0 || picked < 0 || picked === correct) return;
        var meta = txt(document.getElementById('dqMeta'));
        var m = meta.match(/\d{4}-\d{2}-\d{2}/);
        var d = m ? m[0] : new Date().toISOString().slice(0, 10);
        var os = [];
        for (var i = 0; i < opts.length; i++) {
          var t = opts[i].querySelector('.txt');
          os.push(txt(t || opts[i]));
        }
        var qe = txt(document.getElementById('dqQe'));
        record({ id: 'daily-' + d, kind: 'daily', date: d,
          q: txt(document.getElementById('dqQ')) + (qe ? ' / ' + qe : ''),
          o: os, a: correct, w: txt(document.getElementById('dqResult')), wrongChoice: picked });
      }, 0);
    });
  }

  /* ------------------------------ 首次回填 ------------------------------ */
  function backfill() {
    if (localStorage.getItem(BACKFILL_KEY)) return Promise.resolve();
    return fetch(INDEX_URL).then(function (r) {
      if (!r.ok) throw new Error('index ' + r.status);
      return r.json();
    }).then(function (idx) {
      var qs = idx.questions || {};
      Object.keys(qs).forEach(function (k) {
        if (items['day' + k]) return;
        var raw = null;
        try { raw = localStorage.getItem(QUIZ_KEY + k + '-quiz'); } catch (e) {}
        if (!raw || !/^[ABCD]$/.test(raw)) return;
        var picked = LETTERS.indexOf(raw), rec = qs[k];
        if (picked < 0 || !rec || typeof rec.a !== 'number' || picked === rec.a) return;
        items['day' + k] = newRecord({ id: 'day' + k, kind: 'lesson', day: Number(k),
          q: rec.q, o: rec.o || [], a: rec.a, wrongChoice: picked,
          w: rec.w ? (rec.w[0] || '') + (rec.w[1] ? ' / ' + rec.w[1] : '') : '' });
      });
      localStorage.setItem(BACKFILL_KEY, '1');
      save();
    }).catch(function () {});
  }

  /* ------------------------------ 云同步（可选） ------------------------------ */
  function request(method, path, token, body) {
    return new Promise(function (resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.open(method, SYNC.url.replace(/\/$/, '') + path, true);
      xhr.timeout = 15000;
      xhr.setRequestHeader('apikey', SYNC.anonKey);
      xhr.setRequestHeader('Authorization', 'Bearer ' + token);
      if (body) xhr.setRequestHeader('Content-Type', 'application/json');
      if (method === 'POST') xhr.setRequestHeader('Prefer', 'resolution=merge-duplicates,return=minimal');
      xhr.onload = function () {
        if (xhr.status >= 200 && xhr.status < 300) {
          var out = null;
          try { out = xhr.responseText ? JSON.parse(xhr.responseText) : null; } catch (e) {}
          resolve(out);
        } else reject(new Error('HTTP ' + xhr.status));
      };
      xhr.onerror = function () { reject(new Error('network')); };
      xhr.ontimeout = function () { reject(new Error('timeout')); };
      xhr.send(body ? JSON.stringify(body) : null);
    });
  }
  function session() {
    if (!SYNC) return Promise.resolve(null);
    if (!window.DrowsySync || !window.DrowsySync.getSession) return Promise.resolve(null);
    return window.DrowsySync.getSession().then(function (res) {
      if (!res || !res.data || !res.data.user || !res.data.user.id) return null;
      var s = null;
      try { s = JSON.parse(localStorage.getItem('drowsy_sb_session') || 'null'); } catch (e) {}
      if (!s || !s.access_token) return null;
      return { token: s.access_token, uid: res.data.user.id };
    }).catch(function () { return null; });
  }
  function schedulePush() {
    if (!cloudReady) return;
    clearTimeout(pushTimer);
    pushTimer = setTimeout(push, 2000);
  }
  function push() {
    if (!cloudReady) return Promise.resolve(false);
    return session().then(function (s) {
      if (!s) return false;
      var rows = Object.keys(items).map(function (k) {
        var r = items[k];
        return { owner_id: s.uid, cert_slug: slug, item_id: k,
          state: r, updated_at: r.updatedAt || nowISO() };
      });
      if (!rows.length) return true;
      return request('POST', '/rest/v1/user_wrongbook?on_conflict=owner_id,cert_slug,item_id',
        s.token, rows).then(function () { return true; }, function () { return false; });
    }).catch(function () { return false; });
  }
  function sync() {
    if (!SYNC) return Promise.resolve({ ok: false, reason: 'local' });
    return session().then(function (s) {
      if (!s) { cloudReady = false; return { ok: false, reason: 'guest' }; }
      return request('GET', '/rest/v1/user_wrongbook?cert_slug=eq.' + encodeURIComponent(slug) +
        '&select=item_id,state,updated_at', s.token).then(function (rows) {
        cloudReady = true;
        var changed = false;
        (rows || []).forEach(function (row) {
          var r = row.state || {};
          if (!r.id) r.id = row.item_id;
          var old = items[r.id];
          if (!old || !old.updatedAt || (row.updated_at && row.updated_at > old.updatedAt)) {
            items[r.id] = newRecord(r); changed = true;
          }
        });
        if (changed) { try { localStorage.setItem(STORE_KEY, JSON.stringify(items)); } catch (e) {} }
        return push().then(function () { return { ok: true, pulled: (rows || []).length, changed: changed }; });
      }, function () { return { ok: false, reason: 'network' }; });
    }).catch(function () { return { ok: false, reason: 'network' }; });
  }

  /* ------------------------------ 启动 ------------------------------ */
  load();
  if (document.getElementById('checkBtn')) hookLesson();
  if (document.querySelector('.rqBtn')) hookRecap();
  if (document.getElementById('dqSubmit')) hookDaily();
  var ready = backfill().then(function () { return sync(); });
  window.addEventListener('pagehide', function () { if (pushTimer) { clearTimeout(pushTimer); push(); } });

  window.WrongBook = {
    version: VERSION,
    slug: slug,
    ready: ready,
    all: all,
    due: due,
    stats: stats,
    review: review,
    remove: remove,
    record: record,
    sync: sync,
    push: push,
    onChange: onChange,
    intervals: INTERVALS.slice(),
    cloud: !!SYNC
  };
})();
