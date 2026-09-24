/* ═══════════════════════════════════════════════════════════════════════════
   رُزِت — موتور صفحه‌ی جزئیات سفارش (پنل مدیریت)
   ───────────────────────────────────────────────────────────────────────────
   ماژول ۱ : سوییچ تم
   ماژول ۲ : یافتن سفارش از روی ?code=
   ماژول ۳ : سربرگ، خط زمانی و دکمه‌ی گام بعد
   ماژول ۴ : اقلام، مشخصات، عکس‌ها
   ماژول ۵ : ستون کناری و تاریخچه
   ماژول ۶ : بزرگ‌نمایی عکس
   ماژول ۷ : یادداشت داخلی و کارهای مدیر

   داده از سرور می‌آید (static/js/staff-data.js) و هر کار به /staff/api/
   می‌رود. کادر «کارهای مدیر» و دکمه‌ی «برگرد» فقط برای کسی رسم می‌شوند
   که دسترسی‌اش را دارد (DB.caps)؛ سرور هم هر کار را دوباره می‌سنجد.
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var DB = window.RozetOrders;
  var CAN = DB.caps;
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


  /* ══ توست ══ */
  var toastEl = byId('bdToast'), toastT = null;
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.hidden = false;
    clearTimeout(toastT);
    toastT = setTimeout(function () { toastEl.hidden = true; }, 2400);
  }

  /* ══ ۲. یافتن سفارش ══ */
  var JS_ = new Intl.DateTimeFormat('fa-IR', { weekday: 'long', day: 'numeric', month: 'long' });
  function dayLabel(isoStr) {
    var d = DB.daysFromToday(isoStr);
    if (d === 0) return 'امروز';
    if (d === 1) return 'فردا';
    if (d === -1) return 'دیروز';
    return JS_.format(DB.fromIso(isoStr));
  }
  function fullDate(isoStr) { return JS_.format(DB.fromIso(isoStr)); }

  var code = DB.code || '';
  var order = DB.find(code);

  if (!order) {
    byId('odMain').innerHTML =
      '<div class="bd-empty">' +
        '<span class="bd-empty__mark" aria-hidden="true"></span>' +
        '<p>' + (code ? 'سفارشی با کد «' + esc(code) + '» پیدا نشد.' : 'کد سفارش مشخص نشده است.') + '</p>' +
        '<a class="btn btn-primary" href="' + DB.urls.board + '">بازگشت به تابلو</a>' +
      '</div>';
    byId('odCode').textContent = '—';
    byId('odDue').textContent = '';
    return;
  }

  function isOpen() { return order.status !== 'delivered' && order.status !== 'canceled'; }
  function isLate() { return isOpen() && DB.daysFromToday(order.due) < 0; }

  /* ══ ۳. سربرگ ══ */
  function paintHero() {
    var st = DB.STATE[order.status];
    var at = DB.STEPS.map(function (s) { return s.k; }).indexOf(order.status);

    byId('odCode').textContent = faD(order.code);
    byId('odDue').textContent = faD(order.time) + ' · ' + dayLabel(order.due);
    document.title = order.who + ' — ' + order.code + ' — رُزِت';

    var hero = byId('odHero');
    hero.setAttribute('data-s', order.status);
    hero.setAttribute('data-late', isLate() ? '1' : '0');

    hero.innerHTML = '' +
      '<div class="od-when">' +
        '<b class="od-when__t">' + faD(order.time) + '</b>' +
        '<span class="od-when__d">' + dayLabel(order.due) + '</span>' +
      '</div>' +
      '<div class="od-hero__who">' +
        '<h1 class="od-hero__n">' + esc(order.who) + '</h1>' +
        '<p class="od-hero__meta">' + faD(order.code) + ' · تحویل ' + fullDate(order.due) + '</p>' +
      '</div>' +
      '<div class="od-track">' + DB.STEPS.map(function (s, i) {
        return '<div class="od-track__s ' + (i <= at ? 'is-on' : '') + '">' + s.l + '</div>';
      }).join('') + '</div>' +
      (isLate() ? '<p class="bd-note bd-note--warn" style="flex-basis:100%;margin:0">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M12 9v4.5"/><circle cx="12" cy="17" r="0.9" fill="currentColor" stroke="none"/><path d="M10.3 4.2 2.9 17.4A1.9 1.9 0 0 0 4.6 20.3h14.8a1.9 1.9 0 0 0 1.7-2.9L13.7 4.2a1.9 1.9 0 0 0-3.4 0z"/></svg>' +
          'زمان تحویل گذشته و هنوز تحویل نشده است.</p>' : '') +
      (order.cancel ? '<p class="bd-note bd-note--warn" style="flex-basis:100%;margin:0">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M12 9v4.5"/><circle cx="12" cy="17" r="0.9" fill="currentColor" stroke="none"/><path d="M10.3 4.2 2.9 17.4A1.9 1.9 0 0 0 4.6 20.3h14.8a1.9 1.9 0 0 0 1.7-2.9L13.7 4.2a1.9 1.9 0 0 0-3.4 0z"/></svg>' +
          '<span><b>این سفارش لغو شده است</b>' +
          (order.cancel.reason ? ' — ' + esc(order.cancel.reason) : '') +
          (order.cancel.by ? ' (' + esc(order.cancel.by) + ')' : '') + '</span></p>' : '') +
      '<div class="od-hero__act">' +
        (st.next
          ? '<button class="bd-next" type="button" data-to="' + st.next + '">' + st.btn + '</button>'
          : '') +
        /* برگرداندن کارِ انجام‌شده فقط از دست مدیر برمی‌آید */
        (DB.PREV[order.status] && CAN.back
          ? '<button class="bd-undo" type="button" data-back="1">برگرد</button>'
          : '') +
      '</div>';
  }

  /* ══ ۴. اقلام ══ */
  function shotsHtml(title, note, list, cls) {
    return '<div class="od-shots">' +
      '<p class="od-shots__h">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3.5" y="5.5" width="17" height="13" rx="2.4"/><circle cx="9" cy="10" r="1.6"/><path d="m4.5 16.5 4.2-3.8 3.6 3 3-2.4 4.2 3.7"/></svg>' +
        title + (note ? ' <span>' + esc(note) + '</span>' : '') +
      '</p>' +
      '<div class="od-shots__row">' + list.map(function (src, i) {
        return '<button class="od-shot ' + (cls || '') + '" type="button" data-img="' + DB.IMG + esc(src) + '" ' +
               'data-cap="' + esc(title) + ' — ' + faD(i + 1) + '">' +
          '<img src="' + DB.IMG + esc(src) + '" alt="' + esc(title) + '" loading="lazy">' +
          '<span class="od-shot__z" aria-hidden="true">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="6"/><path d="M11 8.5v5M8.5 11h5"/><path d="m15.5 15.5 3 3"/></svg>' +
          '</span>' +
        '</button>';
      }).join('') + '</div>' +
    '</div>';
  }

  function itemHtml(it) {
    var custom = it.kind === 'custom';
    var extras = '';

    if (custom && it.refs && it.refs.length) {
      extras += shotsHtml('عکس‌هایی که مشتری فرستاده', 'برای نمونه — عیناً کپی نشود', it.refs);
      if (it.refNote) extras += '<p class="od-refnote">' + esc(it.refNote) + '</p>';
    }
    if (it.print) {
      extras += '<div class="od-shots"><div class="od-print">' +
        '<img src="' + DB.IMG + esc(it.print) + '" alt="عکس چاپ روی کیک" ' +
             'data-img="' + DB.IMG + esc(it.print) + '" data-cap="عکس چاپ روی کیک" loading="lazy">' +
        '<p class="od-print__x"><b>این عکس روی کیک چاپ می‌شود</b>' +
          esc(it.printNote || 'چاپ روی کاغذ خوراکی') + '</p>' +
      '</div></div>';
    }
    if (it.write) {
      extras += '<p class="bd-note bd-note--write" style="margin-top:0.9rem">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="m4.5 19.5 1-4 10-10 3 3-10 10z"/><path d="M14.5 6.5l3 3"/></svg>' +
        'روی کیک نوشته شود: <b>«' + esc(it.write) + '»</b></p>';
    }

    return '<article class="od-item ' + (custom ? 'od-item--custom' : '') + '">' +
      '<div class="od-item__top">' +
        '<img class="od-item__img" src="' + DB.IMG + esc(it.img) + '" alt="' + esc(it.n) + '" ' +
             'data-img="' + DB.IMG + esc(it.img) + '" data-cap="' + esc(it.n) + '" loading="lazy">' +
        '<div class="od-item__h">' +
          '<h3 class="od-item__n">' + esc(it.n) +
            (custom ? ' <em class="bd-tag">اختصاصی</em>' : '') + '</h3>' +
          '<p class="od-item__s">' + esc(it.s) + ' · ' + fa(it.p) + ' تومان</p>' +
        '</div>' +
        '<div class="od-item__q"><b>' + faD(it.q) + '</b><small>عدد</small></div>' +
      '</div>' +
      (it.spec && it.spec.length
        ? '<dl class="od-spec">' + it.spec.map(function (s) {
            return '<div><dt>' + esc(s.l) + '</dt><dd>' + esc(s.v) + '</dd></div>';
          }).join('') + '</dl>'
        : '') +
      (extras ? '<div class="od-item__foot">' + extras + '</div>' : '') +
    '</article>';
  }

  function paintItems() {
    var html = order.items.map(itemHtml).join('');
    if (order.warn) {
      html += '<p class="bd-note bd-note--warn">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M12 9v4.5"/><circle cx="12" cy="17" r="0.9" fill="currentColor" stroke="none"/><path d="M10.3 4.2 2.9 17.4A1.9 1.9 0 0 0 4.6 20.3h14.8a1.9 1.9 0 0 0 1.7-2.9L13.7 4.2a1.9 1.9 0 0 0-3.4 0z"/></svg>' +
        '<span><b>یادداشت مهم:</b> ' + esc(order.warn) + '</span></p>';
    }
    byId('odItems').innerHTML = html;
  }

  /* ══ ۵. ستون کناری و تاریخچه ══ */
  function paintSide() {
    byId('odCustomer').innerHTML =
      '<h2 class="od-box__t">مشتری</h2>' +
      '<dl>' +
        '<div class="od-row"><dt>نام</dt><dd>' + esc(order.who) + '</dd></div>' +
        '<div class="od-row"><dt>شماره</dt><dd dir="ltr">' + faD(order.tel) + '</dd></div>' +
        '<div class="od-row"><dt>سابقه</dt><dd>' +
          (order.pastOrders ? faD(order.pastOrders) + ' سفارش پیشین' : 'اولین سفارش') + '</dd></div>' +
        '<div class="od-row"><dt>عضو از</dt><dd>' + fullDate(order.since) + '</dd></div>' +
      '</dl>' +
      '<a class="od-call" href="tel:' + esc(order.tel) + '">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M6 4.8h3l1.4 3.6-1.8 1.3a10 10 0 0 0 4.7 4.7l1.3-1.8 3.6 1.4v3a1.5 1.5 0 0 1-1.7 1.5A14 14 0 0 1 4.5 6.5 1.5 1.5 0 0 1 6 4.8z"/></svg>' +
        'تماس با مشتری</a>';

    byId('odDelivery').innerHTML =
      '<h2 class="od-box__t">تحویل</h2>' +
      '<dl>' +
        '<div class="od-row"><dt>روش</dt><dd>' + esc(order.method) + '</dd></div>' +
        '<div class="od-row"><dt>ساعت</dt><dd>' + faD(order.slot || order.time) + '</dd></div>' +
        '<div class="od-row"><dt>روز</dt><dd>' + fullDate(order.due) + '</dd></div>' +
        '<div class="od-row"><dt>محل</dt><dd>' + esc(order.where) + '</dd></div>' +
        (order.gift ? '<div class="od-row"><dt>هدیه</dt><dd>' + esc(order.gift) + '</dd></div>' : '') +
      '</dl>';

    var remain = order.total - order.paid;
    byId('odPay').innerHTML =
      '<h2 class="od-box__t">پرداخت</h2>' +
      '<dl>' +
        '<div class="od-row"><dt>روش</dt><dd>' + esc(order.payMethod) + '</dd></div>' +
        '<div class="od-row"><dt>پرداخت‌شده</dt><dd>' + fa(order.paid) + ' تومان</dd></div>' +
        (remain > 0
          ? '<div class="od-row od-row--due"><dt>مانده هنگام تحویل</dt><dd>' + fa(remain) + ' تومان</dd></div>'
          : '<div class="od-row"><dt>وضعیت</dt><dd>تسویه شده</dd></div>') +
        '<div class="od-row od-row--total"><dt>جمع کل' + (order.estimate ? ' (برآورد)' : '') +
          '</dt><dd>' + fa(order.total) + ' تومان</dd></div>' +
      '</dl>';
  }

  function paintHist() {
    byId('odHist').innerHTML = DB.history(order).map(function (h) {
      /* تاریخچه‌ی واقعی: کی و به دست چه کسی */
      return '<li>' + esc(h.l) + '<small>' + fullDate(h.d) +
        (h.t ? ' · ' + faD(h.t) : '') + (h.by ? ' · ' + esc(h.by) : '') + '</small></li>';
    }).join('');
  }

  function paintAll() {
    paintHero(); paintItems(); paintSide(); paintHist(); paintNote(); paintManage();
  }

  /* ══ ۷. یادداشت داخلی و کارهای مدیر ══ */

  /* یادداشتی که در حال نوشتن است با تازه‌شدن صفحه پاک نمی‌شود */
  var noteDirty = false;
  function paintNote() {
    var box = byId('odNote');
    if (!CAN.note) { box.hidden = true; return; }
    if (noteDirty) return;
    box.innerHTML =
      '<h2 class="od-box__t">یادداشت داخلی</h2>' +
      '<p class="od-hint">فقط کارکنان می‌بینند، نه مشتری.</p>' +
      '<textarea class="od-input" id="odNoteText" rows="3" maxlength="1000" ' +
        'placeholder="مثلاً: مشتری گفت ساعت ۶ زنگ می‌زند">' + esc(order.staffNote) + '</textarea>' +
      '<button class="od-call" type="button" data-act="note">ذخیره‌ی یادداشت</button>';
  }

  function paintManage() {
    var box = byId('odManage');
    var parts = [];
    var remain = order.total - order.paid;
    var closed = order.status === 'canceled';

    if (CAN.settle && !closed && remain > 0) {
      parts.push('<div class="od-act">' +
        '<p class="od-act__t">دریافت مانده: <b>' + fa(remain) + '</b> تومان</p>' +
        '<div class="od-act__row">' +
          '<select class="od-input" id="odChannel" aria-label="روش دریافت">' +
            '<option value="cash">نقدی</option>' +
            '<option value="card">کارت‌خوان</option>' +
            '<option value="transfer">کارت به کارت</option>' +
          '</select>' +
          '<button class="od-call" type="button" data-act="settle">ثبت دریافت</button>' +
        '</div></div>');
    }
    if (CAN.quote && !closed && order.custom) {
      parts.push('<div class="od-act">' +
        '<p class="od-act__t">' + (order.estimate
          ? 'قیمت نهایی کیک — جمع فعلی برآورد است'
          : 'اصلاح قیمت نهایی کیک') + '</p>' +
        '<div class="od-act__row">' +
          '<input class="od-input" id="odPrice" inputmode="numeric" dir="ltr" ' +
            'placeholder="به تومان" aria-label="قیمت نهایی به تومان" value="' +
            (order.estimate ? '' : fa(order.total)) + '">' +
          '<button class="od-call" type="button" data-act="quote">ثبت قیمت</button>' +
        '</div></div>');
    }
    if (CAN.cancel && isOpen()) {
      parts.push('<div class="od-act">' +
        '<p class="od-act__t">لغو سفارش</p>' +
        '<input class="od-input" id="odReason" maxlength="200" ' +
          'placeholder="دلیل لغو — در تاریخچه می‌ماند" aria-label="دلیل لغو">' +
        (order.paid > 0
          ? '<p class="od-hint">' + fa(order.paid) + ' تومان پرداخت شده؛ بازگشت وجه جداگانه ثبت شود.</p>'
          : '') +
        '<button class="od-call od-call--danger" type="button" data-act="cancel">لغو این سفارش</button>' +
      '</div>');
    }

    box.hidden = !parts.length;
    box.innerHTML = parts.length ? '<h2 class="od-box__t">کارهای مدیر</h2>' + parts.join('') : '';
  }

  document.addEventListener('input', function (e) {
    if (e.target.id === 'odNoteText') noteDirty = true;
  });

  var MSG = {
    advance: function () { return 'وضعیت شد: ' + DB.STATE[order.status].l; },
    back: function () { return 'برگشت به «' + DB.STATE[order.status].l + '»'; },
    note: function () { return 'یادداشت ذخیره شد.'; },
    settle: function () { return 'دریافت ثبت شد.'; },
    quote: function () { return 'قیمت نهایی ثبت شد.'; },
    cancel: function () { return 'سفارش لغو شد.'; }
  };

  /* هر کار به سرور می‌رود و پاسخ سرور جای سفارش می‌نشیند. اگر کسی
     همزمان همین سفارش را عوض کرده باشد، سرور ۴۰۹ و نسخه‌ی تازه را
     می‌دهد و صفحه با همان رسم می‌شود. */
  var busy = false;
  function act(btn, body) {
    if (busy) return;
    busy = true;
    btn.disabled = true;
    DB.api(body).then(function (res) {
      busy = false;
      btn.disabled = false;
      if (res.order) order = DB.replace(res.order);
      if (res.ok && body.action === 'note') noteDirty = false;
      paintAll();
      toast(res.ok ? MSG[body.action]() : (res.error || 'کار انجام نشد.'));
    });
  }

  function base(action) { return { action: action, code: order.code, version: order.version }; }

  /* تغییر وضعیت از همین صفحه */
  byId('odHero').addEventListener('click', function (e) {
    var fwd = e.target.closest('.bd-next');
    if (fwd) {
      var body = base('advance');
      body.to = fwd.getAttribute('data-to');
      act(fwd, body);
      return;
    }
    var back = e.target.closest('[data-back]');
    if (back && DB.PREV[order.status]) act(back, base('back'));
  });

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-act]');
    if (!btn) return;
    var kind = btn.getAttribute('data-act');
    var body = base(kind);
    if (kind === 'note') body.text = byId('odNoteText').value;
    if (kind === 'settle') body.channel = byId('odChannel').value;
    if (kind === 'quote') {
      body.price = byId('odPrice').value.trim();
      if (!body.price) { toast('قیمت را به تومان بنویسید.'); byId('odPrice').focus(); return; }
    }
    if (kind === 'cancel') {
      body.reason = byId('odReason').value.trim();
      if (body.reason.length < 3) { toast('دلیل لغو را بنویسید.'); byId('odReason').focus(); return; }
      if (!window.confirm('سفارش ' + order.who + ' لغو شود؟ این کار برگشت ندارد.')) return;
    }
    act(btn, body);
  });

  /* برگشتن به تب: شاید همکاری در این فاصله کاری کرده باشد */
  document.addEventListener('visibilitychange', function () {
    if (document.hidden || busy) return;
    DB.load(order.code).then(function (res) {
      if (res.ok && res.order && !busy) { order = DB.replace(res.order); paintAll(); }
    });
  });

  paintAll();

  /* ══ ۶. بزرگ‌نمایی عکس ══ */
  var lb = byId('odLightbox');
  function openShot(src, cap) {
    byId('odLightboxImg').src = src;
    byId('odLightboxImg').alt = cap || '';
    byId('odLightboxCap').textContent = cap || '';
    lb.hidden = false;
    lb.querySelector('[data-close]').focus();
  }
  function closeShot() { lb.hidden = true; byId('odLightboxImg').src = ''; }

  document.addEventListener('click', function (e) {
    var shot = e.target.closest('[data-img]');
    if (shot && !lb.contains(shot)) {
      openShot(shot.getAttribute('data-img'), shot.getAttribute('data-cap'));
      return;
    }
    if (e.target.closest('[data-close]') || e.target === lb) closeShot();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !lb.hidden) closeShot();
  });

  byId('odPrint').addEventListener('click', function () { window.print(); });

  /* برای تست دستی */
  window.rozetDetail = { order: function () { return order; }, open: openShot, close: closeShot };
})();
