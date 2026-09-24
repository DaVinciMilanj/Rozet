/* ═══════════════════════════════════════════════════════════════════════════
   رُزِت — موتور تابلوی سفارش‌های آشپزخانه
   ───────────────────────────────────────────────────────────────────────────
   ماژول ۱ : سوییچ تم
   ماژول ۲ : تاریخ و ساعت
   ماژول ۳ : داده و انبار محلی
   ماژول ۴ : دسته‌بندی سفارش‌ها
   ماژول ۵ : لیست پخت امروز
   ماژول ۶ : کارت‌ها و تغییر وضعیت
   ماژول ۷ : جست‌وجو، فیلتر، چاپ

   داده از سرور می‌آید (static/js/staff-data.js ← json_script «panel-data»)
   و هر تغییر وضعیت به /staff/api/ می‌رود؛ پاسخ سرور جای سفارش می‌نشیند.
   دکمه‌ی «برگرد» فقط برای کسی رسم می‌شود که caps.back دارد (مدیر).
   تاریخ‌ها میلادیِ ISO می‌آیند و فقط موقع نمایش با Intl شمسی می‌شوند.
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

    var byId = function (i) { return document.getElementById(i); };
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fa = function (n) { return Number(n).toLocaleString('fa-IR'); };
  var faD = function (s) {
    return String(s).replace(/\d/g, function (d) { return String.fromCharCode(0x06F0 + (+d)); });
  };
  var esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };

  /* ══ ۱. سوییچ تم ══ */
  (function themeSwitch() {
    var btn = document.querySelector('.theme-toggle');
    var lightLink = byId('theme-light'), darkLink = byId('theme-dark');
    if (!btn || !lightLink || !darkLink) return;
    var root = document.documentElement;
    function current() { return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light'; }
    function paint(theme) {
      var isDark = theme === 'dark';
      if (isDark) { darkLink.disabled = false; lightLink.disabled = true; }
      else { lightLink.disabled = false; darkLink.disabled = true; }
      root.setAttribute('data-theme', theme);
      btn.setAttribute('aria-checked', isDark ? 'true' : 'false');
      btn.setAttribute('aria-label', isDark ? 'تغییر تم به روشن' : 'تغییر تم به تیره');
      try { localStorage.setItem('rozet-theme', theme); } catch (e) {}
    }
    paint(current());
    btn.addEventListener('click', function () {
      var next = current() === 'dark' ? 'light' : 'dark';
      var done = false;
      function apply() { if (done) return; done = true; paint(next); }
      if (document.startViewTransition && !reduced) {
        try {
          var vt = document.startViewTransition(apply);
          ['ready', 'updateCallbackDone', 'finished'].forEach(function (k) {
            if (vt && vt[k] && vt[k].catch) vt[k].catch(function () {});
          });
        } catch (e) { apply(); }
        setTimeout(apply, 260);
      } else { apply(); }
    });
  })();

  /* ══ ۲. تاریخ و ساعت ══ */
  var JD = new Intl.DateTimeFormat('fa-IR', { weekday: 'long', day: 'numeric', month: 'long' });
  var JS_ = new Intl.DateTimeFormat('fa-IR', { day: 'numeric', month: 'long' });

  function daysFromToday(s) { return window.RozetOrders.daysFromToday(s); }
  function dayLabel(isoStr) {
    var d = daysFromToday(isoStr);
    if (d === 0) return 'امروز';
    if (d === 1) return 'فردا';
    if (d === -1) return 'دیروز';
    return JS_.format(window.RozetOrders.fromIso(isoStr));
  }

  function tickClock() {
    byId('bdToday').textContent = JD.format(new Date());
    byId('bdNow').textContent = faD(new Intl.DateTimeFormat('en-GB', {
      hour: '2-digit', minute: '2-digit', hour12: false
    }).format(new Date()));
  }
  tickClock();
  setInterval(tickClock, 20000);

  /* ══ ۳. داده ══ (از سرور — static/js/staff-data.js) ══ */
  var DB = window.RozetOrders;
  var orders = DB.all();
  var CAN = DB.caps;


  /* ══ توست ══ */
  var toastEl = byId('bdToast'), toastT = null;
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.hidden = false;
    clearTimeout(toastT);
    toastT = setTimeout(function () { toastEl.hidden = true; }, 2400);
  }

  /* ══ ۴. دسته‌بندی ══ */
  var STATE = DB.STATE, PREV = DB.PREV;

  function isOpen(o) { return o.status !== 'delivered'; }
  function isLate(o) { return isOpen(o) && daysFromToday(o.due) < 0; }
  function isToday(o) { return daysFromToday(o.due) === 0; }

  /* دو کلید مرتب‌سازی: اول روز تحویل، بعد ساعت */
  function sortKey(o) { return o.due + ' ' + o.time; }
  function byTime(a, b) { return sortKey(a) < sortKey(b) ? -1 : 1; }

  var filter = 'open', query = '';

  function matches(o) {
    if (query) {
      var hay = o.code + ' ' + o.who + ' ' + o.tel + ' ' +
        o.items.map(function (i) { return i.n; }).join(' ');
      if (hay.toLowerCase().indexOf(query.toLowerCase()) === -1) return false;
    }
    /* گروه‌بندی خودش عقب‌افتاده/امروز/بعد را جدا می‌کند، پس فیلتر فقط
       یک سؤال دارد: تحویل‌شده‌ها هم دیده شوند یا نه. */
    if (filter === 'open') return isOpen(o);
    return true;
  }

  /* ══ ۵. لیست پخت امروز ══ */
  function paintPrep() {
    /* هرچه امروز باید از فر دربیاید، به‌علاوه‌ی عقب‌افتاده‌ها که هنوز مانده‌اند */
    var need = orders.filter(function (o) { return isOpen(o) && (isToday(o) || isLate(o)); });
    var bag = {};
    need.forEach(function (o) {
      o.items.forEach(function (it) {
        var k = it.n + '|' + it.s;
        if (!bag[k]) bag[k] = { n: it.n, s: it.s, q: 0, who: [] };
        bag[k].q += it.q;
        if (bag[k].who.indexOf(o.who) === -1) bag[k].who.push(o.who);
      });
    });
    var rows = Object.keys(bag).map(function (k) { return bag[k]; })
      .sort(function (a, b) { return b.q - a.q; });

    byId('prepCount').textContent = rows.length
      ? faD(rows.length) + ' قلم برای ' + faD(need.length) + ' سفارش'
      : 'چیزی برای امروز نمانده';

    byId('prepList').innerHTML = rows.length
      ? rows.map(function (r) {
          return '<li>' +
            '<span class="bd-prep__q">' + faD(r.q) + '×</span>' +
            '<span>' + esc(r.n) + ' <small style="color:var(--text-subtle)">' + esc(r.s) + '</small></span>' +
            '<span class="bd-prep__for">' + esc(r.who.join('، ')) + '</span>' +
          '</li>';
        }).join('')
      : '<li style="justify-content:center;color:var(--text-subtle)">همه‌ی سفارش‌های امروز تحویل شده‌اند.</li>';
  }

  /* ══ خلاصه — یک جمله، نه چهار عدد ══ */
  function paintSummary() {
    var late = orders.filter(isLate);
    var left = orders.filter(function (o) { return isOpen(o) && (isToday(o) || isLate(o)); });
    var next = left.slice().sort(byTime)[0];

    var bits = [];
    bits.push(left.length
      ? '<b>' + faD(left.length) + '</b> سفارش برای امروز مانده'
      : 'کار امروز تمام شد');
    if (late.length) {
      bits.push('<b class="bd-line__hot">' + faD(late.length) + '</b> عقب‌افتاده');
    }
    if (next) {
      bits.push('نزدیک‌ترین <b>' + faD(next.time) + '</b> — ' + esc(next.who));
    }
    byId('bdLine').innerHTML = bits.join('<i>·</i>');
  }

  /* ══ ۶. کارت‌ها ══ */
  function cardHtml(o) {
    var late = isLate(o);
    var st = STATE[o.status];
    var remain = o.total - o.paid;

    return '' +
    '<article class="bd-card' + (isNew(o) ? ' is-new' : '') + '" data-code="' + esc(o.code) + '" ' +
             'data-s="' + o.status + '" data-late="' + (late ? 1 : 0) + '">' +
      (isNew(o) ? '<span class="bd-new">تازه رسید</span>' : '') +
      '<div class="bd-card__top">' +
        '<div class="bd-when">' +
          '<b class="bd-when__t">' + faD(o.time) + '</b>' +
          '<span class="bd-when__d">' + dayLabel(o.due) + '</span>' +
        '</div>' +
        '<div class="bd-who">' +
          '<p class="bd-who__n">' + esc(o.who) + '</p>' +
          '<a class="bd-who__tel" href="tel:' + esc(o.tel) + '">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M6 4.8h3l1.4 3.6-1.8 1.3a10 10 0 0 0 4.7 4.7l1.3-1.8 3.6 1.4v3a1.5 1.5 0 0 1-1.7 1.5A14 14 0 0 1 4.5 6.5 1.5 1.5 0 0 1 6 4.8z"/></svg>' +
            faD(o.tel) +
          '</a>' +
        '</div>' +
        '<span class="bd-state" data-s="' + o.status + '">' + st.l + '</span>' +
        /* جزئیات به‌جای یک نوار کامل، یک فلش گوشه‌ی سربرگ است */
        '<a class="bd-go" href="' + DB.detailUrl(o.code) + '" ' +
           'aria-label="جزئیات سفارش ' + esc(o.who) + '" title="جزئیات کامل">' +
          (o.items.some(function (i) { return (i.refs && i.refs.length) || i.print; })
            ? '<svg class="bd-go__cam" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="3.5" y="6.5" width="17" height="12" rx="2.4"/><circle cx="12" cy="12.5" r="3.2"/></svg>'
            : '') +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M14 5l-7 7 7 7"/></svg>' +
        '</a>' +
      '</div>' +

      '<div class="bd-card__body">' +
        '<ul class="bd-items">' + o.items.map(function (it) {
          return '<li>' +
            '<span class="bd-items__q">' + faD(it.q) + '×</span>' +
            '<span class="bd-items__x">' + esc(it.n) +
              (it.kind === 'custom' ? ' <em class="bd-tag">اختصاصی</em>' : '') +
              '<small>' + esc(it.s) + '</small></span>' +
          '</li>';
        }).join('') + '</ul>' +

        /* نوشته‌ی روی کیک در سطح هر قلم ذخیره می‌شود؛ روی کارت همه را کنار هم
           می‌آوریم چون فراموش‌کردنش گران تمام می‌شود. */
        (function () {
          var w = o.items.filter(function (i) { return i.write; })
                         .map(function (i) { return '«' + esc(i.write) + '»'; });
          return w.length
            ? '<p class="bd-note bd-note--write">' +
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="m4.5 19.5 1-4 10-10 3 3-10 10z"/><path d="M14.5 6.5l3 3"/></svg>' +
                'روی کیک: <b>' + w.join(' · ') + '</b></p>'
            : '';
        })() +
        (o.warn
          ? '<p class="bd-note bd-note--warn">' +
              '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M12 9v4.5"/><circle cx="12" cy="17" r="0.9" fill="currentColor" stroke="none"/><path d="M10.3 4.2 2.9 17.4A1.9 1.9 0 0 0 4.6 20.3h14.8a1.9 1.9 0 0 0 1.7-2.9L13.7 4.2a1.9 1.9 0 0 0-3.4 0z"/></svg>' +
              esc(o.warn) + '</p>'
          : '') +

        /* این خط همیشه هست — اگر فقط وقتی پول مانده نشان داده شود، نبودنش
           مبهم می‌ماند و کسی که کیک را تحویل می‌دهد باید حدس بزند. */
        '<p class="bd-meta">' + (remain > 0
          ? '<span class="bd-meta__due">مانده هنگام تحویل: <b>' + fa(remain) + '</b> تومان' +
              /* کیک اختصاصی تا قیمت نهایی، جمعش برآورد است */
              (o.estimate ? ' (برآورد)' : '') + '</span>'
          : 'تسویه شده') + '</p>' +
      '</div>' +

      (st.next
        ? '<div class="bd-card__foot">' +
            '<button class="bd-next" type="button" data-to="' + st.next + '">' + st.btn + '</button>' +
            /* برگرداندن کارِ انجام‌شده فقط از دست مدیر برمی‌آید */
            (PREV[o.status] && CAN.back ? '<button class="bd-undo" type="button" data-back="1">برگرد</button>' : '') +
          '</div>'
        : (CAN.back
          ? '<div class="bd-card__foot">' +
              '<button class="bd-undo" type="button" data-back="1" style="flex:1">بازگرداندن به «آماده‌ی تحویل»</button>' +
            '</div>'
          : '')) +
    '</article>';
  }

  function groupHtml(title, list, mod) {
    if (!list.length) return '';
    return '<section class="bd-group ' + (mod || '') + '">' +
      '<div class="bd-group__h">' +
        '<h2>' + title + '</h2>' +
        '<span class="bd-group__n">' + faD(list.length) + '</span>' +
        '<span class="bd-group__line"></span>' +
      '</div>' +
      '<div class="bd-cards">' + list.map(cardHtml).join('') + '</div>' +
    '</section>';
  }

  function paintBoard() {
    var list = orders.filter(matches).sort(byTime);

    var late = list.filter(isLate);
    var today = list.filter(function (o) { return isToday(o) && isOpen(o); });
    var soon = list.filter(function (o) { return isOpen(o) && daysFromToday(o.due) > 0; });
    var done = list.filter(function (o) { return !isOpen(o); });

    var html =
      groupHtml('عقب‌افتاده — از روزهای قبل', late, 'bd-group--late') +
      groupHtml('امروز', today) +
      groupHtml('روزهای بعد', soon) +
      groupHtml('تحویل‌شده', done);

    byId('bdGroups').innerHTML = html || (
      '<div class="bd-empty">' +
        '<span class="bd-empty__mark" aria-hidden="true"></span>' +
        '<p>' + (query || filter !== 'all'
          ? 'با این فیلتر سفارشی پیدا نشد.'
          : 'سفارشی ثبت نشده است.') + '</p>' +
      '</div>');
  }

  function paintAll() { paintSummary(); paintPrep(); paintBoard(); }

  /* تغییر وضعیت — واگذاری رویداد، چون کارت‌ها بازسازی می‌شوند */
  byId('bdGroups').addEventListener('click', function (e) {
    var card = e.target.closest('.bd-card');
    if (!card) return;
    var o = orders.filter(function (x) { return x.code === card.getAttribute('data-code'); })[0];
    if (!o) return;

    var fwd = e.target.closest('.bd-next');
    if (fwd) {
      act(fwd, { action: 'advance', code: o.code, version: o.version, to: fwd.getAttribute('data-to') },
        function (x) { toast(x.who + ' — ' + STATE[x.status].l); });
      return;
    }
    var back = e.target.closest('[data-back]');
    if (back && PREV[o.status]) {
      act(back, { action: 'back', code: o.code, version: o.version },
        function (x) { toast('برگشت به «' + STATE[x.status].l + '»'); });
    }
  });

  /* هر کار به سرور می‌رود و پاسخ سرور جای سفارش می‌نشیند — نه حدسِ
     صفحه. اگر همکاری همزمان همان کارت را جلو برده باشد، سرور ۴۰۹
     می‌دهد، نسخه‌ی تازه را می‌فرستد و کل تابلو تازه می‌شود. */
  var busy = false;
  function act(btn, body, done) {
    if (busy) return;
    busy = true;
    btn.disabled = true;
    DB.api(body).then(function (res) {
      busy = false;
      if (res.order) DB.replace(res.order);
      prune();
      paintAll();
      if (res.ok) done(res.order);
      else toast(res.error || 'کار انجام نشد.');
      if (res.status === 409) refresh();
    });
  }

  /* لغوشده‌ها روی تابلو نمی‌مانند */
  function prune() {
    DB.setAll(orders.filter(function (o) { return o.status !== 'canceled'; }));
  }

  /* ══ ۷. جست‌وجو، فیلتر، چاپ ══ */
  var searchT = null;
  byId('bdSearch').addEventListener('input', function (e) {
    clearTimeout(searchT);
    var v = e.target.value;
    searchT = setTimeout(function () { query = v.trim(); paintBoard(); }, 200);
  });

  byId('bdFilters').addEventListener('click', function (e) {
    var chip = e.target.closest('.bd-chip');
    if (!chip) return;
    filter = chip.getAttribute('data-f');
    byId('bdFilters').querySelectorAll('.bd-chip').forEach(function (c) {
      c.classList.toggle('is-on', c === chip);
    });
    paintBoard();
  });

  var prepToggle = byId('prepToggle');
  prepToggle.addEventListener('click', function () {
    var open = prepToggle.getAttribute('aria-expanded') === 'true';
    prepToggle.setAttribute('aria-expanded', open ? 'false' : 'true');
    byId('prepBody').hidden = open;
  });

  byId('bdPrint').addEventListener('click', function () { window.print(); });

  /* ══ ۸. اعلان سفارش تازه ══
     سفارشی که هنوز دیده نشده، تا وقتی زنگ باز نشود «تازه» می‌ماند: هم روی
     کارتش نشان می‌خورد، هم در شمارنده‌ی زنگ شمرده می‌شود. */
  /* «دیده‌نشده» به‌ازای هر کاربر در سرور نگه داشته می‌شود (seen_by)؛
     باز کردن زنگ روی گوشی یک نفر، زنگ همکارش را خاموش نمی‌کند. */
  var unseen = DB.unseen.slice();

  function isNew(o) { return unseen.indexOf(o.code) !== -1; }

  var BASE_TITLE = document.title;

  function paintBell() {
    var n = unseen.length;
    /* عنوان تب هم شمارنده بگیرد؛ اگر صفحه در پس‌زمینه باشد همان دیده می‌شود */
    document.title = n ? '(' + faD(n) + ') ' + BASE_TITLE : BASE_TITLE;
    var badge = byId('bdBellN');
    badge.textContent = faD(n);
    badge.hidden = n === 0;
    byId('bdBell').classList.toggle('has-new', n > 0);

    byId('bdBellList').innerHTML = n
      ? unseen.map(function (code) {
          var o = orders.filter(function (x) { return x.code === code; })[0];
          if (!o) return '';
          return '<a class="bd-bellrow" href="' + DB.detailUrl(o.code) + '">' +
            '<b>' + esc(o.who) + '</b>' +
            '<span>' + faD(o.time) + ' · ' + dayLabel(o.due) + ' · ' +
              esc(o.items[0].n) + (o.items.length > 1 ? ' و…' : '') + '</span>' +
          '</a>';
        }).join('')
      : '<p class="bd-bellbox__empty">سفارش تازه‌ای نیست.</p>';
  }

  function openBell(on) {
    byId('bdBellPanel').hidden = !on;
    byId('bdBell').setAttribute('aria-expanded', on ? 'true' : 'false');
    if (!on) return;
    /* باز کردن زنگ یعنی دیدمشان */
    if (unseen.length) {
      setTimeout(function () {
        unseen = [];
        DB.api({ action: 'seen' });
        paintBell(); paintBoard(); paintAlert();
      }, 1400);
    }
  }

  byId('bdBell').addEventListener('click', function (e) {
    e.stopPropagation();
    openBell(byId('bdBellPanel').hidden);
  });
  document.addEventListener('click', function (e) {
    if (!byId('bdBellPanel').hidden && !e.target.closest('.bd-bell__wrap')) openBell(false);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !byId('bdBellPanel').hidden) openBell(false);
  });

  /* اعلان خودش نمی‌رود. کسی که پشت میز کار است هر چند دقیقه یک‌بار به صفحه
     نگاه می‌کند؛ اگر اعلان بعد از چند ثانیه محو شود، همان‌هایی را که برای
     آن‌ها ساخته شده از دست می‌دهد. فقط با ضربدر یا با خواندن بسته می‌شود. */
  function paintAlert() {
    var n = unseen.length;
    var box = byId('bdAlert');
    if (!n) { box.hidden = true; return; }

    var last = orders.filter(function (x) { return x.code === unseen[0]; })[0];
    if (!last) { box.hidden = true; return; }
    byId('bdAlertTitle').textContent = n === 1
      ? 'سفارش تازه'
      : faD(n) + ' سفارش تازه';
    byId('bdAlertText').textContent = n === 1
      ? last.who + ' — ' + faD(last.time) + ' ' + dayLabel(last.due)
      : 'آخری: ' + last.who + ' — ' + faD(last.time) + ' ' + dayLabel(last.due);

    var go = byId('bdAlertGo');
    if (n === 1) {
      go.textContent = 'دیدن';
      go.href = DB.detailUrl(last.code);
    } else {
      /* با چند سفارش، «دیدن» فهرست زنگ را باز می‌کند نه یکی از آن‌ها را */
      go.textContent = 'دیدن همه';
      go.href = '#';
    }
    box.hidden = false;
  }

  byId('bdAlertGo').addEventListener('click', function (e) {
    if (unseen.length <= 1) return;
    e.preventDefault();
    /* بدون این، همین کلیک به document می‌رسد و چون بیرون از زنگ است،
       پنلی را که تازه باز کردیم در همان لحظه می‌بندد. */
    e.stopPropagation();
    openBell(true);
  });
  byId('bdAlertClose').addEventListener('click', function () {
    byId('bdAlert').hidden = true;
  });

  /* ══ ۹. تازه‌کردن از سرور ══
     هر چند ثانیه یک‌بار: سفارش تازه، یا کاری که همکار دیگری کرده. سفارشی
     که تازه به فهرست «دیده‌نشده» اضافه شده، اعلان گوشه را بیدار می‌کند.
     اتصال زنده لازم نیست؛ یک کافه در روز چند ده سفارش دارد نه هزار. */
  function refresh() {
    if (busy) return;
    return DB.load().then(function (res) {
      if (!res.ok || !res.orders || busy) return;
      var incoming = (res.unseen || []).filter(function (c) { return unseen.indexOf(c) === -1; });
      DB.setAll(res.orders);
      unseen = res.unseen || [];
      paintAll();
      paintBell();
      if (incoming.length) paintAlert();
    });
  }

  /* ══ راه‌اندازی ══ */
  paintAll();
  paintBell();

  setInterval(refresh, DB.poll * 1000);
  /* برگشتن به تب یعنی احتمالاً مدتی نگاه نکرده‌اند؛ همان لحظه تازه شود */
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) refresh();
  });

  /* برای تست دستی */
  window.rozetBoard = {
    orders: function () { return orders; },
    setFilter: function (f) { filter = f; paintBoard(); },
    refresh: refresh,
    reset: function () { location.reload(); }
  };
})();
