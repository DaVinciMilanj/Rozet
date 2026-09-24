/* ═══════════════════════════════════════════════════════════════════════════
   رُزِت — موتور صفحه‌ی ثبت سفارش
   ───────────────────────────────────────────────────────────────────────────
   ماژول ۱ : سوییچ تم
   ماژول ۲ : وضعیت سفارش و خواندن سبد
   ماژول ۳ : نحوه‌ی دریافت
   ماژول ۴ : روز و ساعت
   ماژول ۵ : مشخصات و نشانی (از حساب کاربری پر می‌شود)
   ماژول ۶ : جزئیات و کد تخفیف
   ماژول ۷ : خلاصه و جمع‌ها
   ماژول ۸ : اعتبارسنجی و ثبت

   نسخه‌ی جنگو: سبد، نرخ‌ها، بازه‌های تحویل و روزها همه از سرور می‌آیند
   و سفارش واقعاً در دیتابیس ثبت می‌شود. هیچ عددی از این فایل به سرور
   نمی‌رود — جمع‌ها اینجا فقط برای نمایش حساب می‌شوند و سرور هنگام ثبت
   همه را از نو می‌سازد.

   درگاه پرداخت هنوز وصل نیست؛ جای اتصالش در apps/orders/checkout.py
   (تابع _start_payment) علامت خورده و این فایل از قبل آماده است که
   اگر سرور نشانی درگاه را فرستاد، کاربر را بفرستد.
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ══ داده‌ی صفحه ══
     نرخ‌ها، بازه‌های تحویل، روزها و مشخصات کاربر — همه از سرور.
     هیچ عددی اینجا ثابت نیست: کرایه‌ی پیک و بسته‌ی هدیه با تورم عوض
     می‌شوند و مدیر باید بتواند از پنل تغییرشان بدهد. */
  var SEED = (function () {
    var tag = document.getElementById('checkout-data');
    if (!tag) return null;
    try { return JSON.parse(tag.textContent); } catch (e) { return null; }
  })();

  if (!SEED) return;

  var BRIDGE = window.ROZET || {};
  var FEES = SEED.fees || {};

  var COURIER_ENABLED = !!FEES.courier;
  var SHIP_FEE = FEES.ship || 0;
  var GIFT_FEE = FEES.gift || 0;
  var FREE_SHIP_OVER = FEES.freeOver || 0;
  var VAT_PERCENT = FEES.vat || 0;

  var byId = function (i) { return document.getElementById(i); };
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fa = function (n) { return Number(n).toLocaleString('fa-IR'); };
  var faD = function (s) {
    return String(s).replace(/\d/g, function (d) { return String.fromCharCode(0x06F0 + (+d)); });
  };
  var toLatin = function (s) {
    return String(s)
      .replace(/[۰-۹]/g, function (d) { return d.charCodeAt(0) - 0x06F0; })
      .replace(/[٠-٩]/g, function (d) { return d.charCodeAt(0) - 0x0660; });
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

  /* ══ تماس با سرور ══
     یک اندپوینت، تقسیم روی action — همان الگوی بقیه‌ی صفحه‌ها. */
  function api(action, payload) {
    var body = { action: action };
    Object.keys(payload || {}).forEach(function (k) { body[k] = payload[k]; });
    return fetch(BRIDGE.checkoutApi, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': BRIDGE.csrf || '' },
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.json().catch(function () { return { ok: false }; });
    });
  }

  /* ══ ۲. وضعیت ══ */
  var cart = RozetCart.load();
  var S = {
    method: 'pickup',
    day: null, dayLabel: '',
    slot: null,
    addrId: null,      /* شناسه‌ی آدرس ذخیره‌شده، یا 'new' */
    gift: false,
    pay: 'online',
    off: 0, promo: ''
  };

  /* حساب کاربری اگر پیش‌تر پر شده باشد، فرم را کوتاه می‌کند */
  /* مشخصات و نشانی‌ها از دیتابیس می‌آیند، نه از انبار مرورگر. */
  var acc = SEED.profile || { name: '', phone: '', addresses: [] };

  var toastEl = byId('coToast'), toastT = null;
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.hidden = false;
    clearTimeout(toastT);
    toastT = setTimeout(function () { toastEl.hidden = true; }, 2600);
  }
  function setErr(id, msg) {
    var el = byId(id);
    if (!el) return;
    el.textContent = msg || '';
    el.classList.toggle('is-on', !!msg);
  }

  /* سبد خالی → بقیه‌ی صفحه اصلاً ساخته نمی‌شود */
  if (!cart.length) {
    byId('coEmpty').hidden = false;
    return;
  }
  byId('coShell').hidden = false;
  byId('coBar').hidden = false;

  /* ══ ۳. نحوه‌ی دریافت ══ */
  byId('feeHint').textContent = fa(SHIP_FEE) + ' تومان';
  byId('giftFee').textContent = fa(GIFT_FEE);

  (function courierGate() {
    if (COURIER_ENABLED) return;
    var b = document.querySelector('[data-method="courier"]');
    if (!b) return;
    b.disabled = true;
    b.setAttribute('aria-disabled', 'true');
    b.setAttribute('aria-checked', 'false');
    b.classList.add('is-off');
    b.querySelector('small').textContent = 'فعلاً راه‌اندازی نشده است';
    var tag = document.createElement('span');
    tag.className = 'co-pick__soon';
    tag.textContent = 'به‌زودی';
    b.appendChild(tag);
    /* وقتی تنها یک راه دریافت هست، جمله‌ی مرحله هم باید همان را بگوید */
    byId('methodNote').textContent =
      'فعلاً فقط تحویل حضوری در کافه انجام می‌شود. کیک را در جعبه‌ی مخصوص و سرد تحویل می‌گیرید.';
  })();

  byId('methodPicks').addEventListener('click', function (e) {
    var b = e.target.closest('.co-pick');
    if (!b || b.disabled) return;
    S.method = b.getAttribute('data-method');
    byId('methodPicks').querySelectorAll('.co-pick').forEach(function (x) {
      var on = x === b;
      x.classList.toggle('is-on', on);
      x.setAttribute('aria-checked', on ? 'true' : 'false');
    });
    byId('methodNote').textContent = S.method === 'pickup'
      ? 'کیک را در جعبه‌ی مخصوص و سرد تحویل می‌گیرید.'
      : 'پیک فقط داخل مشهد می‌رود. کیک تا لحظه‌ی تحویل در جعبه‌ی سرد می‌ماند.';
    byId('addrBlock').hidden = (S.method !== 'courier');
    buildSlots();
    paintTotals();
    marks();
  });

  /* ══ ۴. روز و ساعت ══ */
  /* تاریخ شمسی را خود مرورگر می‌دهد؛ کتابخانه‌ی جداگانه لازم نیست */
  function faDate(d, opts) {
    try { return d.toLocaleDateString('fa-IR', opts); }
    catch (e) { return d.toLocaleDateString('en-US', opts); }
  }

  /* بازه‌ها از جدول DeliverySlot می‌آیند تا مدیر بتواند ساعت کار را
     عوض کند بدون اینکه کسی کد را دست بزند. */
  var SLOTS = SEED.slots || [];

  /* روزها با تاریخ شمسیِ آماده از سرور می‌آیند. نسخه‌ی قبلی
     toLocaleDateString('fa-IR') را صدا می‌زد که روی هر مرورگر و
     سیستم‌عاملی می‌تواند فرق کند — و تاریخی که مشتری می‌بیند باید
     همانی باشد که روی برگه‌ی آشپزخانه می‌نشیند. */
  var days = SEED.days || [];
  (function paintDays() {
    byId('dayPicks').innerHTML = days.map(function (d) {
      return '<button class="co-day" type="button" role="radio" aria-checked="false" data-day="' + d.i + '">' +
        '<b>' + esc(d.top) + '</b><span>' + esc(d.num) + '</span></button>';
    }).join('');
  })();

  /* بازه‌های گذشته‌ی امروز قابل انتخاب نیستند — دو ساعت هم فرصت آماده‌سازی */
  function buildSlots() {
    var now = new Date();
    var isToday = S.day === 0;
    byId('slotPicks').innerHTML = SLOTS.map(function (s) {
      var dead = isToday && s.from < now.getHours() + 2;
      return '<button class="co-slot' + (S.slot === s.id && !dead ? ' is-on' : '') + '" type="button" ' +
        'role="radio" aria-checked="' + (S.slot === s.id ? 'true' : 'false') + '" ' +
        'data-slot="' + s.id + '"' + (dead ? ' disabled title="این بازه گذشته است"' : '') + '>' +
        s.label + '</button>';
    }).join('');
    /* اگر بازه‌ی انتخابی با تغییر روز نامعتبر شد، پاکش کن */
    var still = byId('slotPicks').querySelector('.co-slot.is-on');
    if (!still) S.slot = null;
  }

  byId('dayPicks').addEventListener('click', function (e) {
    var b = e.target.closest('.co-day');
    if (!b) return;
    S.day = +b.getAttribute('data-day');
    S.dayLabel = days[S.day].top + '، ' + days[S.day].num;
    byId('dayPicks').querySelectorAll('.co-day').forEach(function (x) {
      var on = x === b;
      x.classList.toggle('is-on', on);
      x.setAttribute('aria-checked', on ? 'true' : 'false');
    });
    buildSlots();
    setErr('whenErr', '');
    marks();
  });

  byId('slotPicks').addEventListener('click', function (e) {
    var b = e.target.closest('.co-slot');
    if (!b || b.disabled) return;
    S.slot = b.getAttribute('data-slot');
    byId('slotPicks').querySelectorAll('.co-slot').forEach(function (x) {
      var on = x === b;
      x.classList.toggle('is-on', on);
      x.setAttribute('aria-checked', on ? 'true' : 'false');
    });
    setErr('whenErr', '');
    marks();
  });

  buildSlots();

  /* ══ ۵. مشخصات و نشانی ══ */
  if (acc && acc.profile) {
    byId('coName').value = ((acc.profile.first || '') + ' ' + (acc.profile.last || '')).trim();
    byId('coPhone').value = acc.profile.phone || '';
  }
  byId('coPhone').addEventListener('input', function (e) {
    e.target.value = toLatin(e.target.value).replace(/\D/g, '').slice(0, 11);
  });

  (function buildAddrs() {
    var list = (acc && acc.addresses) || [];
    var html = list.map(function (a) {
      return '<button class="co-addr" type="button" role="radio" aria-checked="false" data-addr="' + a.id + '">' +
        '<b>' + esc(a.t) + '</b><small>' + esc(a.x) + '</small></button>';
    }).join('');
    html += '<button class="co-addr" type="button" role="radio" aria-checked="false" data-addr="new">' +
      '<b>نشانی تازه</b><small>یک آدرس دیگر وارد می‌کنم</small></button>';
    byId('addrPicks').innerHTML = html;

    /* آدرس پیش‌فرض حساب، از پیش انتخاب می‌شود */
    var def = list.filter(function (a) { return a.def; })[0] || list[0];
    if (def) {
      S.addrId = def.id;
      var el = byId('addrPicks').querySelector('[data-addr="' + def.id + '"]');
      if (el) { el.classList.add('is-on'); el.setAttribute('aria-checked', 'true'); }
    } else {
      S.addrId = 'new';
      var n = byId('addrPicks').querySelector('[data-addr="new"]');
      n.classList.add('is-on'); n.setAttribute('aria-checked', 'true');
      byId('newAddrField').hidden = false;
    }
  })();

  byId('addrPicks').addEventListener('click', function (e) {
    var b = e.target.closest('.co-addr');
    if (!b) return;
    var id = b.getAttribute('data-addr');
    S.addrId = (id === 'new') ? 'new' : +id;
    byId('addrPicks').querySelectorAll('.co-addr').forEach(function (x) {
      var on = x === b;
      x.classList.toggle('is-on', on);
      x.setAttribute('aria-checked', on ? 'true' : 'false');
    });
    byId('newAddrField').hidden = (S.addrId !== 'new');
    setErr('whoErr', '');
    marks();
  });

  ['coName', 'coPhone', 'coAddr'].forEach(function (id) {
    byId(id).addEventListener('input', function () { setErr('whoErr', ''); marks(); });
  });

  /* ══ ۶. جزئیات و کد تخفیف ══ */
  byId('coPlaque').addEventListener('input', function () {
    byId('plaqueCount').textContent = faD(this.value.length);
  });

  byId('coGift').addEventListener('change', function () {
    S.gift = this.checked;
    paintTotals();
  });

  byId('payPicks').addEventListener('click', function (e) {
    var b = e.target.closest('.co-pick');
    if (!b) return;
    S.pay = b.getAttribute('data-pay');
    byId('payPicks').querySelectorAll('.co-pick').forEach(function (x) {
      var on = x === b;
      x.classList.toggle('is-on', on);
      x.setAttribute('aria-checked', on ? 'true' : 'false');
    });
    byId('payNote').textContent = S.pay === 'online'
      ? 'پس از پرداخت، کد پیگیری برایتان پیامک می‌شود.'
      : 'سفارش ثبت می‌شود و مبلغ را هنگام تحویل می‌پردازید.';
    byId('placeBtn').querySelector('.co-place__l').textContent =
      S.pay === 'online' ? 'پرداخت و ثبت سفارش' : 'ثبت سفارش';
    marks();
  });

  byId('coTerms').addEventListener('change', function () {
    if (this.checked) setErr('payErr', '');
    marks();
  });

  /* اعتبار کد را سرور می‌سنجد — نه فهرستی در جاوااسکریپت که هر کسی
     با باز کردن سورس می‌خواندش. مصرف کد هم اینجا شمرده نمی‌شود؛ فقط
     هنگام ثبت سفارش. */
  byId('promoBtn').addEventListener('click', function () {
    var code = byId('coPromo').value.trim();
    var msg = byId('promoMsg');
    var btn = this;
    msg.className = 'co-promo__msg';
    if (!code) { msg.textContent = 'کد تخفیف را وارد کنید.'; msg.classList.add('is-bad'); return; }

    btn.disabled = true;
    api('promo', { code: code }).then(function (res) {
      btn.disabled = false;
      msg.className = 'co-promo__msg';
      if (res && res.ok) {
        S.off = res.off || 0;
        S.promo = res.code;
        msg.textContent = fa(S.off) + ' تومان تخفیف اعمال شد.';
        msg.classList.add('is-ok');
      } else {
        S.off = 0; S.promo = '';
        msg.textContent = (res && res.error) || 'این کد معتبر نیست یا منقضی شده.';
        msg.classList.add('is-bad');
      }
      paintTotals();
    }).catch(function () {
      btn.disabled = false;
      msg.textContent = 'ارتباط با سرور برقرار نشد.';
      msg.classList.add('is-bad');
    });
  });

  /* ══ ۷. خلاصه و جمع‌ها ══ */
  function itemsSum() {
    return cart.reduce(function (s, i) { return s + i.price * i.qty; }, 0);
  }
  function shipCost() {
    if (S.method !== 'courier') return 0;
    return itemsSum() >= FREE_SHIP_OVER ? 0 : SHIP_FEE;
  }
  function grand() {
    /* S.off مبلغ تخفیف است (تومان)، نه نرخ: سرور عددش را می‌دهد چون
       تخفیف می‌تواند درصدی یا مبلغ ثابت و سقف‌دار باشد. */
    var base = Math.max(0, itemsSum() - S.off) + (S.gift ? GIFT_FEE : 0) + shipCost();
    return base + Math.round(base * VAT_PERCENT / 100);
  }

  function paintItems() {
    byId('coItems').innerHTML = cart.map(function (i, idx) {
      return '<div class="co-item">' +
        '<img class="co-item__img" src="' + esc(i.img) + '" alt="" loading="lazy">' +
        '<div class="co-item__b">' +
          '<p class="co-item__n">' + esc(i.name) +
            (i.meta ? '<small class="co-item__m">' + esc(i.meta) + '</small>' : '') + '</p>' +
          '<div class="co-item__row">' +
            '<span class="co-qty">' +
              '<button type="button" data-q="dec" data-i="' + idx + '" aria-label="کاهش تعداد">−</button>' +
              '<span>' + faD(i.qty) + '</span>' +
              '<button type="button" data-q="inc" data-i="' + idx + '" aria-label="افزایش تعداد">+</button>' +
            '</span>' +
            '<span class="co-item__p">' + fa(i.price * i.qty) + '</span>' +
          '</div>' +
        '</div></div>';
    }).join('');
  }

  function paintTotals() {
    var sub = itemsSum();
    var off = Math.min(sub, S.off);
    var ship = shipCost();

    byId('tSub').textContent = fa(sub);
    byId('rowGift').hidden = !S.gift;
    byId('tGift').textContent = fa(GIFT_FEE);
    byId('rowShip').hidden = (S.method !== 'courier');
    byId('tShip').textContent = ship === 0 ? 'رایگان' : fa(ship);
    byId('rowOff').hidden = !off;
    byId('tOff').textContent = '− ' + fa(off);

    var g = grand();
    byId('tGrand').textContent = fa(g) + ' تومان';
    byId('barGrand').textContent = fa(g) + ' تومان';
  }

  byId('coItems').addEventListener('click', function (e) {
    var b = e.target.closest('[data-q]');
    if (!b) return;
    var idx = +b.getAttribute('data-i');
    var item = cart[idx];
    if (!item) return;
    if (b.getAttribute('data-q') === 'inc') {
      item.qty = Math.min(99, item.qty + 1);
    } else {
      item.qty -= 1;
      if (item.qty < 1) {
        cart.splice(idx, 1);
        toast('«' + item.name + '» از سبد برداشته شد.');
      }
    }
    RozetCart.save(cart);
    if (!cart.length) { location.reload(); return; }
    paintItems();
    paintTotals();
  });

  /* ══ ۸. اعتبارسنجی و ثبت ══ */

  /* تیکِ کنار هر مرحله فقط وقتی می‌خورد که آن مرحله واقعاً کامل باشد */
  function stepOk(name) {
    if (name === 'method') return !!S.method;
    if (name === 'when') return S.day !== null && !!S.slot;
    if (name === 'who') {
      if (byId('coName').value.trim().length < 3) return false;
      if (!/^09\d{9}$/.test(toLatin(byId('coPhone').value))) return false;
      if (S.method === 'courier') {
        if (S.addrId === 'new') return byId('coAddr').value.trim().length >= 10;
        return S.addrId != null;
      }
      return true;
    }
    if (name === 'extra') return true;
    if (name === 'pay') return byId('coTerms').checked;
    return false;
  }
  function marks() {
    document.querySelectorAll('.co-step').forEach(function (s) {
      var n = s.getAttribute('data-step');
      s.classList.toggle('is-done', n !== 'extra' && stepOk(n));
    });
  }

  function jumpTo(name, id, msg) {
    setErr(id, msg);
    var el = document.querySelector('.co-step[data-step="' + name + '"]');
    if (el) el.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'center' });
  }

  function validate() {
    if (!stepOk('when')) {
      jumpTo('when', 'whenErr', 'روز و بازه‌ی ساعت را انتخاب کنید.');
      return false;
    }
    if (byId('coName').value.trim().length < 3) {
      jumpTo('who', 'whoErr', 'نام و نام خانوادگی را کامل بنویسید.');
      return false;
    }
    if (!/^09\d{9}$/.test(toLatin(byId('coPhone').value))) {
      jumpTo('who', 'whoErr', 'شماره باید با ۰۹ شروع شود و ۱۱ رقم باشد.');
      return false;
    }
    if (S.method === 'courier' && S.addrId === 'new' && byId('coAddr').value.trim().length < 10) {
      jumpTo('who', 'whoErr', 'نشانی تحویل را کامل بنویسید.');
      return false;
    }
    if (!byId('coTerms').checked) {
      jumpTo('pay', 'payErr', 'برای ثبت سفارش باید شرایط را بپذیرید.');
      return false;
    }
    return true;
  }





  var placing = false;
  function submit(btn) {
    if (placing) return;
    if (!validate()) return;
    placing = true;
    btn.classList.add('is-busy');

    /* هیچ عددی فرستاده نمی‌شود — نه قیمت، نه جمع، نه کد سفارش. سرور
       اقلام را از سبدِ دیتابیس برمی‌دارد و همه‌چیز را خودش حساب می‌کند.
       اینجا فقط انتخاب‌های کاربر می‌رود. */
    var payload = {
      method: S.method,
      day: S.day,
      slot: S.slot,
      name: byId('coName').value.trim(),
      phone: toLatin(byId('coPhone').value),
      addrId: (S.addrId === 'new' ? null : S.addrId),
      addr: byId('coAddr').value.trim(),
      plaque: byId('coPlaque').value.trim(),
      gift: S.gift,
      allergy: byId('coAllergy').value.trim(),
      note: byId('coNote').value.trim(),
      pay: S.pay,
      promo: S.promo,
      terms: byId('coTerms').checked
    };

    api('place', payload).then(function (res) {
      btn.classList.remove('is-busy');
      placing = false;
      if (!res || !res.ok) {
        var where = res && res.field;
        if (where === 'when') jumpTo('when', 'whenErr', res.error);
        else if (where === 'who') jumpTo('who', 'whoErr', res.error);
        else if (where === 'pay') jumpTo('pay', 'payErr', res.error);
        else toast((res && res.error) || 'ثبت سفارش انجام نشد. دوباره تلاش کنید.');
        return;
      }
      /* سبد را سرور خالی کرده؛ این فقط آینه‌ی مرورگر را هم‌تراز می‌کند. */
      RozetCart.clear();
      /* وقتی درگاه وصل شود، سرور نشانی‌اش را در redirect می‌فرستد و
         کاربر همین‌جا به بانک می‌رود. */
      if (res.redirect) { location.href = res.redirect; return; }
      finish(res, payload);
    }).catch(function () {
      btn.classList.remove('is-busy');
      placing = false;
      toast('ارتباط با سرور برقرار نشد.');
    });
  }

  byId('placeBtn').addEventListener('click', function () { submit(this); });
  byId('barPlace').addEventListener('click', function () { submit(byId('placeBtn')); });

  function finish(res, sent) {
    byId('coShell').hidden = true;
    byId('coBar').hidden = true;
    byId('coDone').hidden = false;
    /* کد پیگیری و زمان تحویل را سرور می‌دهد، نه مرورگر: همان چیزی که
       در دیتابیس نشسته باید به مشتری نشان داده شود. */
    byId('doneCode').textContent = res.code;
    var line = sent.method === 'courier'
      ? 'پیک، سفارش را ' + res.when + ' به دستتان می‌رساند. برای هماهنگی با شماره‌ی ' +
        faD(sent.phone) + ' تماس می‌گیریم.'
      : 'سفارشتان ' + res.when + ' در کافه آماده است. برای هماهنگی با شماره‌ی ' +
        faD(sent.phone) + ' تماس می‌گیریم.';
    if (res.note) line += ' ' + res.note;
    byId('doneText').textContent = line;
    /* طول واقعی مسیر خوانده می‌شود تا خط دقیق کشیده شود، نه حدسی */
    document.querySelectorAll('.co-done__circle, .co-done__tick').forEach(function (p) {
      p.style.setProperty('--len', Math.ceil(p.getTotalLength()));
    });
    window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' });
  }

  /* ══ راه‌اندازی ══ */
  paintItems();
  paintTotals();
  marks();

  window.rozetCheckout = { state: function () { return S; }, cart: function () { return cart; } };
})();
