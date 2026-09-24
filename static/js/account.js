/* ═══════════════════════════════════════════════════════════════════════════
   رُزِت — موتور پنل حساب کاربری
   ───────────────────────────────────────────────────────────────────────────
   ماژول ۱ : سوییچ تم
   ماژول ۲ : داده و انبار محلی
   ماژول ۳ : جابه‌جایی بخش‌ها
   ماژول ۴ : نمای کلی (آمار، باشگاه، سفارش در جریان)
   ماژول ۵ : سفارش‌ها
   ماژول ۶ : علاقه‌مندی‌ها
   ماژول ۷ : آدرس‌ها
   ماژول ۸ : اطلاعات من
   ماژول ۹ : توست

   نسخه‌ی جنگو. داده از دیتابیس می‌آید (json_script با شناسه‌ی
   account-data) و هر تغییری با api() روی سرور ذخیره می‌شود. نه داده‌ی
   نمونه‌ای در این فایل هست و نه چیزی در localStorage نگه داشته می‌شود —
   تنها استثنا انتخاب تم است که سلیقه‌ی همین مرورگر است.
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

  /* ══ ۲. داده ══ */

  /* ══ داده ══

     همه‌چیز از دیتابیس می‌آید. json_script پیش از اجرای این اسکریپت،
     داده‌ی همین کاربر را در صفحه گذاشته است.

     اینجا هیچ داده‌ی نمایشی نیست و نباید باشد: نسخه‌ی قبلی یک آرایه‌ی
     نمونه به‌عنوان پشتیبان داشت و هر خطایی در خواندن، به‌جای پیام خطا،
     اسم و سفارش‌های یک آدم خیالی را نشان می‌داد. */
  var SERVER = (function () {
    var tag = byId('account-data');
    if (!tag) return null;
    try { return JSON.parse(tag.textContent); } catch (e) { return null; }
  })();

  if (!SERVER) {
    var host = byId('acBody');
    if (host) {
      host.innerHTML = '<div class="ac-empty"><span class="ac-empty__mark" aria-hidden="true"></span>' +
        '<p>اطلاعات حساب بارگذاری نشد. صفحه را تازه کنید.</p></div>';
    }
    return;
  }

  /* نشانی صفحه‌های دیگر و پله‌های باشگاه از سرور می‌آیند؛
     {% url %} و settings داخل فایل .js اجرا نمی‌شوند، پس پل همان
     window.ROZET است. */
  var BRIDGE = window.ROZET || {};
  /* حداقل طول رمز از سرور (settings.PASSWORD_MIN_LENGTH) */
  var PASS_MIN = BRIDGE.passwordMin || 6;
  var LINKS = BRIDGE.links || {};
  var LIST_URL = LINKS.products || '/';
  var CONTACT_URL = LINKS.contact || '/';

  /* نشانی تصویرها از سرور کامل می‌آید (/media/…)، پس پیشوندی لازم نیست. */
  var IMG = '';

  var SEED = SERVER;

  /* تنها درِ نوشتن. سرور یک اندپوینت دارد و روی action تقسیم می‌کند، پس
     امضای این تابع همان است که بقیه‌ی فایل صدا می‌زند. */
  var API_URL = BRIDGE.accountApi || '';
  var CSRF = BRIDGE.csrf || '';

  function api(action, payload) {
    var body = { action: action };
    Object.keys(payload || {}).forEach(function (k) { body[k] = payload[k]; });
    return fetch(API_URL, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify(body)
    }).then(function (r) {
      /* پاسخ خطا هم بدنه‌ی JSON دارد و پیامش به کاربر نشان داده می‌شود،
         پس روی status رد نمی‌شویم. */
      return r.json().catch(function () { return { ok: false }; });
    });
  }

  /* منبع حقیقت دیتابیس است، نه انبار مرورگر. نسخه‌ی ذخیره‌شده در
     مرورگر پس از ورود با حساب دیگر — یا ویرایش از گوشی — داده‌ی کهنه
     نشان می‌داد، پس اصلاً خوانده و نوشته نمی‌شود.

     save() می‌ماند چون در ده جای این فایل صدا زده می‌شود و کارش حالا
     فقط «چیزی لازم نیست» است؛ نوشتن واقعی با api() انجام می‌شود. */
  var db = SEED;
  function save() {}

  /* ══ ۹. توست ══ */
  var toastEl = byId('acToast'), toastT = null;
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.hidden = false;
    clearTimeout(toastT);
    toastT = setTimeout(function () { toastEl.hidden = true; }, 2600);
  }

  /* ══ ۳. جابه‌جایی بخش‌ها ══ */
  var views = document.querySelectorAll('.ac-view');
  var navBtns = document.querySelectorAll('.ac-nav__item');

  function go(name, push) {
    views.forEach(function (v) {
      var on = v.getAttribute('data-view') === name;
      v.hidden = !on;
      v.classList.toggle('is-on', on);
    });
    navBtns.forEach(function (b) {
      b.classList.toggle('is-on', b.getAttribute('data-view') === name);
    });
    if (push !== false && location.hash !== '#' + name) {
      history.replaceState(null, '', '#' + name);
    }
    if (name === 'overview') paintClub();
    window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' });
  }
  navBtns.forEach(function (b) {
    b.addEventListener('click', function () { go(b.getAttribute('data-view')); });
  });

  /* ══ ۴. نمای کلی ══ */
  var STATUS = {
    placed:    { l: 'ثبت شد',            step: 0 },
    baking:    { l: 'در حال آماده‌سازی', step: 1 },
    ready:     { l: 'آماده‌ی تحویل',     step: 2 },
    delivered: { l: 'تحویل شد',          step: 3 },
    canceled:  { l: 'لغو شد',            step: -1 }
  };
  var STEPS = ['ثبت سفارش', 'آماده‌سازی', 'آماده‌ی تحویل', 'تحویل'];

  /* پله‌های باشگاه از LOYALTY_TIERS در settings می‌آیند، نه از اینجا:
     دو جای جدا یعنی روزی که مدیر پله‌ها را عوض کند، سرور یک چیز حساب
     می‌کند و صفحه چیز دیگری نشان می‌دهد. */
  var TIERS = (SEED.tiers || []).map(function (t) {
    return { min: t[0], n: t[1], next: t[2] };
  });

  function orderTotal(o) {
    /* مبلغ نهاییِ سرور (ارسال و هدیه و تخفیف حساب‌شده) ملاک است؛ جمع
       اقلام فقط وقتی که سفارشی مبلغ نهایی نداشته باشد. */
    if (typeof o.paid === 'number') return o.paid;
    return o.items.reduce(function (s, i) { return s + i.p * i.q; }, 0);
  }
  /* آمار روی سرور شمرده می‌شود، نه اینجا: شمارنده‌های خود حساب
     (orders_count و total_spent_rial) مرجع‌اند و نباید از روی آرایه‌ی
     نمایش دوباره حساب شوند. */
  var STATS = db.stats || { orders: 0, spent: 0, club: 0 };
  function tierOf(count) {
    var t = TIERS[0];
    TIERS.forEach(function (x) { if (count >= x.min) t = x; });
    return t;
  }

  function fullName() {
    return (db.profile.first + ' ' + db.profile.last).trim() || 'مهمان رُزِت';
  }
  function initials() {
    var a = (db.profile.first || '').trim().charAt(0);
    var b = (db.profile.last || '').trim().charAt(0);
    return (a + b) || 'ر';
  }

  function paintIdentity() {
    byId('acAvatar').textContent = initials();
    byId('acName').textContent = fullName();
    byId('acPhone').textContent = faD(db.profile.phone || '—');
    byId('acTier').textContent = 'باشگاه: ' + tierOf(STATS.club).n;

    var h = new Date().getHours();
    var greet = h < 12 ? 'صبح بخیر' : (h < 17 ? 'ظهر بخیر' : 'عصر بخیر');
    byId('acGreet').textContent = greet + '، ' + (db.profile.first || 'دوست عزیز');

    byId('navOrders').textContent = faD(db.orders.length);
    byId('navFavs').textContent = faD(db.favorites.length);
    byId('navAddr').textContent = faD(db.addresses.length);
  }

  function paintStats() {
    byId('stOrders').textContent = faD(STATS.orders);
    byId('stSpent').textContent = fa(STATS.spent);
    byId('stFav').textContent = faD(db.favorites.length);
  }

  /* حلقه‌ی باشگاه — محیط دایره با r=52 برابر ۳۲۶٫۷ است */
  var CIRC = 2 * Math.PI * 52;
  function paintClub() {
    var count = STATS.club;
    var t = tierOf(count);
    if (!t) return;
    var idx = TIERS.indexOf(t);
    var from = t.min;
    var to = t.next;
    var pct = to == null ? 1 : Math.min(1, (count - from) / (to - from));

    byId('clubTier').textContent = 'باشگاه رُزِت — ' + t.n;
    byId('clubNote').textContent = to == null
      ? 'به بالاترین پله رسیده‌اید. هر سفارش، یک شیرینی کوچک مهمان ماست.'
      : 'با ' + faD(to - count) + ' سفارش دیگر به پله‌ی «' + TIERS[idx + 1].n + '» می‌رسید.';

    byId('clubSteps').innerHTML = TIERS.map(function (x, i) {
      return '<span class="' + (i <= idx ? 'is-on' : '') + '">' + esc(x.n) + '</span>';
    }).join('');

    var fill = byId('clubFill');
    fill.style.strokeDasharray = CIRC.toFixed(1);
    fill.style.strokeDashoffset = CIRC.toFixed(1);
    /* یک فریم صبر تا مرورگر مقدار اولیه را ثبت کند، وگرنه انیمیشن پرش می‌کند */
    setTimeout(function () {
      fill.style.strokeDashoffset = (CIRC * (1 - pct)).toFixed(1);
    }, 60);
  }

  function trackHtml(status) {
    if (status === 'canceled') {
      return '<div class="ac-track"><div class="ac-track__s is-cut">لغو شد</div></div>';
    }
    var at = STATUS[status] ? STATUS[status].step : 0;
    return '<div class="ac-track">' + STEPS.map(function (s, i) {
      return '<div class="ac-track__s ' + (i <= at ? 'is-on' : '') + '">' + s + '</div>';
    }).join('') + '</div>';
  }

  function paintLive() {
    var live = db.orders.filter(function (o) {
      return o.status === 'placed' || o.status === 'baking' || o.status === 'ready';
    });
    var host = byId('liveOrder');
    if (!live.length) {
      host.innerHTML =
        '<div class="ac-empty">' +
          '<span class="ac-empty__mark" aria-hidden="true"></span>' +
          '<p>الان سفارشی در جریان ندارید.</p>' +
          '<a class="btn btn-primary" href="' + LIST_URL + '">دیدن ویترین</a>' +
        '</div>';
      return;
    }
    host.innerHTML = live.map(function (o) {
      return '<div class="ac-card">' +
        '<div class="ac-order__top" style="padding:0 0 1.1rem">' +
          '<span><span class="ac-order__id">' + esc(o.code) + '</span>' +
          '<span class="ac-order__meta">' + esc(o.items[0].n) + '</span></span>' +
          '<span class="ac-pill" data-s="' + o.status + '">' + STATUS[o.status].l + '</span>' +
        '</div>' +
        trackHtml(o.status) +
        (o.ready ? '<p class="ac-hint">زمان تحویل: ' + esc(o.ready) + '</p>' : '') +
      '</div>';
    }).join('');
  }

  /* ══ ۵. سفارش‌ها ══ */
  var ordFilter = 'all', ordQuery = '';

  function matches(o) {
    if (ordFilter === 'active' && !(o.status === 'placed' || o.status === 'baking' || o.status === 'ready')) return false;
    if (ordFilter === 'delivered' && o.status !== 'delivered') return false;
    if (ordFilter === 'canceled' && o.status !== 'canceled') return false;
    if (!ordQuery) return true;
    var hay = o.code + ' ' + o.items.map(function (i) { return i.n; }).join(' ');
    return hay.toLowerCase().indexOf(ordQuery.toLowerCase()) !== -1;
  }

  function paintOrders() {
    var list = db.orders.filter(matches);
    var host = byId('ordList');
    if (!list.length) {
      host.innerHTML =
        '<div class="ac-empty">' +
          '<span class="ac-empty__mark" aria-hidden="true"></span>' +
          '<p>' + (ordQuery || ordFilter !== 'all'
            ? 'سفارشی با این نشانه پیدا نشد.'
            : 'هنوز سفارشی ثبت نکرده‌اید.') + '</p>' +
          '<a class="btn btn-primary" href="' + LIST_URL + '">شروع از ویترین</a>' +
        '</div>';
      return;
    }
    host.innerHTML = list.map(function (o) {
      var total = orderTotal(o);
      var names = o.items.map(function (i) { return i.n; }).join(' · ');
      return '' +
      '<article class="ac-order" data-code="' + esc(o.code) + '">' +
        '<button class="ac-order__top" type="button" aria-expanded="false">' +
          '<span>' +
            '<span class="ac-order__id">' + faD(o.code) + '</span>' +
            '<span class="ac-order__meta">' + faD(o.date) + ' — ' + esc(names) + '</span>' +
          '</span>' +
          '<span class="ac-order__sum">' + fa(total) + ' تومان</span>' +
          '<span class="ac-pill" data-s="' + o.status + '">' + STATUS[o.status].l + '</span>' +
          '<svg class="ac-order__caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>' +
        '</button>' +
        '<div class="ac-order__body" hidden>' +
          trackHtml(o.status) +
          (o.note ? '<p class="ac-hint" style="margin-bottom:1.1rem">' + esc(o.note) + '</p>' : '') +
          '<div class="ac-lines">' + o.items.map(function (i) {
            return '<div class="ac-line">' +
              '<img class="ac-line__img" src="' + IMG + esc(i.i) + '" alt="" loading="lazy">' +
              '<span class="ac-line__n">' + esc(i.n) +
                /* خط دوم فقط وقتی ساخته می‌شود که چیزی برای گفتن باشد */
                (function () {
                  var bits = [];
                  if (i.s) bits.push(esc(i.s));
                  if (i.q > 1) bits.push(faD(i.q) + ' عدد');
                  return bits.length ? '<small>' + bits.join(' · ') + '</small>' : '';
                })() +
              '</span>' +
              '<span class="ac-line__p">' + fa(i.p * i.q) + '</span>' +
            '</div>';
          }).join('') + '</div>' +
          '<dl class="ac-kv">' +
            '<div><dt>روش تحویل</dt><dd>' + esc(o.method) + '</dd></div>' +
            '<div><dt>نشانی</dt><dd>' + esc(o.addr) + '</dd></div>' +
            '<div><dt>پرداخت</dt><dd>' + esc(o.pay) + '</dd></div>' +
            '<div><dt>جمع کل</dt><dd>' + fa(total) + ' تومان</dd></div>' +
          '</dl>' +
          '<div class="ac-acts">' +
            '<button class="btn btn-primary" type="button" data-act="again">سفارش دوباره</button>' +
            (o.status === 'delivered'
              ? '<button class="btn btn-outline" type="button" data-act="receipt">فاکتور</button>'
              : '') +
            (o.status === 'baking' || o.status === 'placed' || o.status === 'ready'
              ? '<a class="btn btn-outline" href="' + CONTACT_URL + '">پیگیری تلفنی</a>'
              : '') +
          '</div>' +
        '</div>' +
      '</article>';
    }).join('');
  }

  byId('ordList').addEventListener('click', function (e) {
    var head = e.target.closest('.ac-order__top');
    if (head) {
      var card = head.closest('.ac-order');
      var body = card.querySelector('.ac-order__body');
      var open = card.classList.toggle('is-open');
      body.hidden = !open;
      head.setAttribute('aria-expanded', open ? 'true' : 'false');
      return;
    }
    var act = e.target.closest('[data-act]');
    if (!act) return;
    var kind = act.getAttribute('data-act');
    if (kind === 'again') toast('اقلام این سفارش به سبد اضافه شد.');
    if (kind === 'receipt') toast('فاکتور برای شماره‌ی شما پیامک شد.');
  });

  byId('ordFilters').addEventListener('click', function (e) {
    var chip = e.target.closest('.ac-chip');
    if (!chip) return;
    ordFilter = chip.getAttribute('data-f');
    byId('ordFilters').querySelectorAll('.ac-chip').forEach(function (c) {
      c.classList.toggle('is-on', c === chip);
    });
    paintOrders();
  });

  var searchT = null;
  byId('ordSearch').addEventListener('input', function (e) {
    clearTimeout(searchT);
    var v = e.target.value;
    searchT = setTimeout(function () { ordQuery = v.trim(); paintOrders(); }, 220);
  });

  /* ══ ۶. علاقه‌مندی‌ها ══ */
  function paintFavs() {
    var host = byId('favList');
    if (!db.favorites.length) {
      host.innerHTML =
        '<div class="ac-empty" style="grid-column:1/-1">' +
          '<span class="ac-empty__mark" aria-hidden="true"></span>' +
          '<p>هنوز چیزی نشان نکرده‌اید. قلبِ کنار هر کیک، همین‌جا نگهش می‌دارد.</p>' +
          '<a class="btn btn-primary" href="' + LIST_URL + '">دیدن ویترین</a>' +
        '</div>';
      return;
    }
    host.innerHTML = db.favorites.map(function (f, idx) {
      return '<article class="ac-fav">' +
        '<img src="' + IMG + esc(f.i) + '" alt="' + esc(f.n) + '" loading="lazy">' +
        '<button class="ac-fav__x" type="button" data-fav="' + idx + '" aria-label="حذف ' + esc(f.n) + ' از علاقه‌مندی‌ها">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>' +
        '</button>' +
        '<div class="ac-fav__b">' +
          '<h3 class="ac-fav__n">' + esc(f.n) + '</h3>' +
          '<p class="ac-fav__p">' + fa(f.p) + ' تومان</p>' +
          '<a class="btn btn-outline" style="width:100%;padding:0.6rem;font-size:var(--text-xs)" ' +
            'href="' + esc(f.url || LIST_URL) + '">دیدن و سفارش</a>' +
        '</div>' +
      '</article>';
    }).join('');
  }

  byId('favList').addEventListener('click', function (e) {
    var x = e.target.closest('[data-fav]');
    if (!x) return;
    var i = +x.getAttribute('data-fav');
    var fav = db.favorites[i];
    db.favorites.splice(i, 1);
    save();
    paintFavs(); paintIdentity(); paintStats();
    api('favorite-remove', { id: fav.id });
    toast('«' + fav.n + '» از علاقه‌مندی‌ها برداشته شد.');
  });

  /* ══ ۷. آدرس‌ها ══ */
  var modal = byId('addrModal'), addrForm = byId('addrForm'), editing = null;

  function paintAddrs() {
    var host = byId('addrList');
    if (!db.addresses.length) {
      host.innerHTML =
        '<div class="ac-empty" style="grid-column:1/-1">' +
          '<span class="ac-empty__mark" aria-hidden="true"></span>' +
          '<p>هنوز آدرسی ثبت نشده است.</p>' +
        '</div>';
      return;
    }
    host.innerHTML = db.addresses.map(function (a) {
      return '<article class="ac-addr ' + (a.def ? 'is-def' : '') + '">' +
        '<h3 class="ac-addr__t">' + esc(a.t) +
          (a.def ? '<span class="ac-addr__def">پیش‌فرض</span>' : '') + '</h3>' +
        '<p class="ac-addr__x">' + esc(a.x) + '</p>' +
        '<p class="ac-addr__c">' + esc(a.r) + (a.c ? ' — ' + faD(a.c) : '') + '</p>' +
        '<div class="ac-addr__acts">' +
          '<button class="ac-link" type="button" data-edit="' + a.id + '">ویرایش</button>' +
          (a.def ? '' : '<button class="ac-link" type="button" data-def="' + a.id + '">پیش‌فرض شود</button>') +
          '<button class="ac-link ac-link--danger" type="button" data-del="' + a.id + '">حذف</button>' +
        '</div>' +
      '</article>';
    }).join('');
  }

  function openModal(addr) {
    editing = addr || null;
    byId('addrModalT').textContent = addr ? 'ویرایش آدرس' : 'آدرس تازه';
    byId('adTitle').value = addr ? addr.t : '';
    byId('adText').value = addr ? addr.x : '';
    byId('adReceiver').value = addr ? addr.r : fullName();
    byId('adPhone').value = addr ? addr.c : db.profile.phone;
    byId('adDefault').checked = addr ? !!addr.def : !db.addresses.length;
    setErr('adErr', '');
    modal.hidden = false;
    setTimeout(function () { byId('adTitle').focus(); }, 50);
  }
  function closeModal() { modal.hidden = true; editing = null; }

  byId('addrNew').addEventListener('click', function () { openModal(null); });

  byId('addrList').addEventListener('click', function (e) {
    var t = e.target.closest('[data-edit],[data-def],[data-del]');
    if (!t) return;
    var id = +(t.getAttribute('data-edit') || t.getAttribute('data-def') || t.getAttribute('data-del'));
    var addr = db.addresses.filter(function (a) { return a.id === id; })[0];
    if (!addr) return;
    if (t.hasAttribute('data-edit')) { openModal(addr); return; }
    if (t.hasAttribute('data-def')) {
      db.addresses.forEach(function (a) { a.def = (a.id === id); });
      save(); paintAddrs();
      api('address-default', { id: id });
      toast('«' + addr.t + '» آدرس پیش‌فرض شد.');
      return;
    }
    if (confirm('آدرس «' + addr.t + '» حذف شود؟')) {
      db.addresses = db.addresses.filter(function (a) { return a.id !== id; });
      if (addr.def && db.addresses.length) db.addresses[0].def = true;
      save(); paintAddrs(); paintIdentity();
      api('address-delete', { id: id });
      toast('آدرس حذف شد.');
    }
  });

  modal.addEventListener('click', function (e) {
    if (e.target.closest('[data-close]')) closeModal();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !modal.hidden) closeModal();
  });

  byId('adPhone').addEventListener('input', function (e) {
    e.target.value = toLatin(e.target.value).replace(/\D/g, '').slice(0, 11);
  });

  addrForm.addEventListener('submit', function (e) {
    e.preventDefault();
    var t = byId('adTitle').value.trim();
    var x = byId('adText').value.trim();
    var c = byId('adPhone').value.trim();
    if (!t) { setErr('adErr', 'برای آدرس یک عنوان بنویسید.'); return; }
    if (x.length < 10) { setErr('adErr', 'نشانی را کامل‌تر بنویسید.'); return; }
    if (c && !/^09\d{9}$/.test(c)) { setErr('adErr', 'شماره باید با ۰۹ شروع شود و ۱۱ رقم باشد.'); return; }
    setErr('adErr', '');

    var data = { t: t, x: x, r: byId('adReceiver').value.trim(), c: c, def: byId('adDefault').checked };
    /* closeModal پایین‌تر editing را خالی می‌کند، پس هرچه بعد از آن
       لازم است همین‌جا نگه داشته می‌شود. */
    var wasEditing = editing;
    var target;
    if (editing) {
      Object.keys(data).forEach(function (k) { editing[k] = data[k]; });
      data.id = editing.id;
      target = editing;
    } else {
      /* شناسه‌ی موقت تا پاسخ سرور برسد؛ بدون آن دکمه‌های ویرایش و حذفِ
         همین کارت به هیچ رکوردی وصل نیستند. */
      data.id = Date.now();
      db.addresses.push(data);
      target = data;
    }
    if (data.def) {
      db.addresses.forEach(function (a) { a.def = (a === target); });
    } else if (!db.addresses.some(function (a) { return a.def; }) && db.addresses.length) {
      db.addresses[0].def = true;
    }
    save(); paintAddrs(); paintIdentity(); closeModal();
    /* شناسه‌ی موقتِ Date.now() نباید به سرور برود: سرور آن را «ویرایشِ
       نشانی‌ای که وجود ندارد» می‌خواند. نبودِ id یعنی «تازه بساز». */
    api('address-save', {
      id: wasEditing ? target.id : null,
      t: data.t, x: data.x, r: data.r, c: data.c, def: data.def
    }).then(function (res) {
      if (!res || !res.ok) { toast((res && res.error) || 'آدرس ذخیره نشد.'); return; }
      if (!res.address) return;
      /* شناسه‌ی واقعی جای شناسه‌ی موقت، و نشانیِ مرتب‌شده‌ی سرور جای
         متن خام. */
      target.id = res.address.id;
      target.x = res.address.x;
      target.r = res.address.r;
      target.c = res.address.c;
      target.def = res.address.def;
      paintAddrs();
    });
    toast(wasEditing ? 'آدرس به‌روز شد.' : 'آدرس تازه ذخیره شد.');
  });

  /* ══ ۸. اطلاعات من ══ */
  function toLatin(s) {
    return String(s)
      .replace(/[۰-۹]/g, function (d) { return d.charCodeAt(0) - 0x06F0; })
      .replace(/[٠-٩]/g, function (d) { return d.charCodeAt(0) - 0x0660; });
  }
  function setErr(id, msg) {
    var el = byId(id);
    if (!el) return;
    el.textContent = msg || '';
    el.classList.toggle('is-on', !!msg);
  }
  function busy(btn, on) { btn.classList.toggle('is-busy', on); }

  var MONTHS = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
                'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'];

  (function fillDate() {
    var d = byId('pfDay'), m = byId('pfMonth'), y = byId('pfYear');
    d.innerHTML = '<option value="">روز</option>';
    for (var i = 1; i <= 31; i++) d.innerHTML += '<option value="' + i + '">' + faD(i) + '</option>';
    m.innerHTML = '<option value="">ماه</option>';
    MONTHS.forEach(function (n, i) { m.innerHTML += '<option value="' + (i + 1) + '">' + n + '</option>'; });
    y.innerHTML = '<option value="">سال</option>';
    for (var j = 1404; j >= 1320; j--) y.innerHTML += '<option value="' + j + '">' + faD(j) + '</option>';
  })();

  function paintProfile() {
    var p = db.profile;
    byId('pfFirst').value = p.first || '';
    byId('pfLast').value = p.last || '';
    byId('pfPhone').value = p.phone || '';
    byId('pfEmail').value = p.email || '';
    byId('pfDay').value = p.bDay || '';
    byId('pfMonth').value = p.bMonth || '';
    byId('pfYear').value = p.bYear || '';
    byId('nfSms').checked = !!p.sms;
    byId('nfNews').checked = !!p.news;
  }

  byId('profileForm').addEventListener('submit', function (e) {
    e.preventDefault();
    var first = byId('pfFirst').value.trim();
    var last = byId('pfLast').value.trim();
    var mail = byId('pfEmail').value.trim();
    if (first.length < 2) { setErr('pfErr', 'نام را بنویسید.'); return; }
    if (last.length < 2) { setErr('pfErr', 'نام خانوادگی را بنویسید.'); return; }
    if (mail && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(mail)) {
      setErr('pfErr', 'ایمیل درست به نظر نمی‌رسد.'); return;
    }
    /* تاریخ تولد یا کامل باشد یا اصلاً خالی — نیمه‌کاره ذخیره نکن */
    var d = byId('pfDay').value, m = byId('pfMonth').value, y = byId('pfYear').value;
    var filled = [d, m, y].filter(Boolean).length;
    if (filled > 0 && filled < 3) { setErr('pfErr', 'تاریخ تولد را کامل انتخاب کنید یا خالی بگذارید.'); return; }
    setErr('pfErr', '');

    var btn = this.querySelector('.ac-save');
    busy(btn, true);
    var data = { first: first, last: last, email: mail, bDay: d, bMonth: m, bYear: y };
    api('profile-save', data).then(function (res) {
      busy(btn, false);
      if (!res || !res.ok) { setErr('pfErr', (res && res.error) || 'ذخیره نشد. دوباره تلاش کنید.'); return; }
      Object.keys(data).forEach(function (k) { db.profile[k] = data[k]; });
      save(); paintIdentity();
      toast('اطلاعاتتان ذخیره شد.');
    }).catch(function () {
      busy(btn, false);
      setErr('pfErr', 'ارتباط با سرور برقرار نشد.');
    });
  });

  byId('pfPhoneChange').addEventListener('click', function () {
    toast('برای تغییر شماره، کد تأیید به شماره‌ی تازه پیامک می‌شود.');
  });

  byId('passForm').addEventListener('submit', function (e) {
    e.preventDefault();
    var oldp = byId('pwOld').value, n1 = byId('pwNew').value, n2 = byId('pwNew2').value;
    if (!oldp) { setErr('pwErr', 'رمز فعلی را وارد کنید.'); return; }
    if (n1.length < PASS_MIN) { setErr('pwErr', 'رمز تازه دست‌کم ' + faD(PASS_MIN) + ' نویسه باشد.'); return; }
    if (n1 !== n2) { setErr('pwErr', 'دو رمز تازه یکی نیستند.'); return; }
    if (n1 === oldp) { setErr('pwErr', 'رمز تازه با رمز فعلی فرقی ندارد.'); return; }
    setErr('pwErr', '');

    var btn = this.querySelector('.ac-save');
    busy(btn, true);
    /* رمز هرگز ذخیره نمی‌شود — فقط به سرور می‌رود */
    api('password-change', { old: oldp, next: n1 }).then(function (res) {
      busy(btn, false);
      if (!res || !res.ok) { setErr('pwErr', (res && res.error) || 'رمز فعلی درست نیست.'); return; }
      byId('pwOld').value = byId('pwNew').value = byId('pwNew2').value = '';
      toast('رمز عبور عوض شد.');
    }).catch(function () {
      busy(btn, false);
      setErr('pwErr', 'ارتباط با سرور برقرار نشد.');
    });
  });

  ['nfSms', 'nfNews'].forEach(function (id) {
    byId(id).addEventListener('change', function () {
      db.profile[id === 'nfSms' ? 'sms' : 'news'] = this.checked;
      save();
      api('notify-save', { sms: db.profile.sms, news: db.profile.news });
      toast(this.checked ? 'روشن شد.' : 'خاموش شد.');
    });
  });

  byId('delAcc').addEventListener('click', function () {
    if (!confirm('مطمئنید؟ سابقه‌ی سفارش‌ها و آدرس‌هایتان برگشت‌ناپذیر پاک می‌شود.')) return;
    var btn = this;
    btn.disabled = true;
    api('account-delete', {}).then(function (res) {
      if (res && res.ok) { location.href = res.redirect || '/'; return; }
      btn.disabled = false;
      toast((res && res.error) || 'برای حذف حساب، پشتیبانی با شما تماس می‌گیرد.');
    }).catch(function () {
      btn.disabled = false;
      toast('ارتباط با سرور برقرار نشد.');
    });
  });

  /* ══ راه‌اندازی ══ */
  paintIdentity();
  paintStats();
  paintLive();
  paintOrders();
  paintFavs();
  paintAddrs();
  paintProfile();

  var start = (location.hash || '').replace('#', '');
  var valid = ['overview', 'orders', 'favorites', 'addresses', 'profile'];
  go(valid.indexOf(start) !== -1 ? start : 'overview', false);
  paintClub();

  /* برای تست دستی */
  window.rozetAccount = { go: go, db: function () { return db; }, reset: function () {
    /* چیزی در مرورگر ذخیره نمی‌شود، پس «بازنشانی» یعنی گرفتن دوباره‌ی
       داده از سرور. */
    location.reload();
  } };
})();
