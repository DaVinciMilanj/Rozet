/* ═══════════════════════════════════════════════════════════════════════════
   رُزِت — داده‌ی مشترک پنل کارکنان
   ───────────────────────────────────────────────────────────────────────────
   جانشینِ admin/data/orders-data.js. همان واسط را بیرون می‌دهد
   (window.RozetOrders: STATE · PREV · STEPS · all · find · history · …) تا
   موتور تابلو و صفحه‌ی جزئیات دست‌نخورده بمانند؛ فقط منبع عوض شده:

     • سفارش‌ها از json_script «panel-data» می‌آیند، نه از یک آرایه‌ی ثابت.
     • تغییر وضعیت به سرور می‌رود (api) و پاسخِ سرور جای سفارش می‌نشیند.
     • caps می‌گوید این کاربر کدام دکمه‌ها را ببیند. سرور هم هر کار را
       دوباره می‌سنجد؛ پنهان‌کردن دکمه فقط برای شلوغ نبودن صفحه است.

   تاریخ‌ها میلادیِ ISO می‌آیند و فقط موقع نمایش شمسی می‌شوند.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (w) {
  'use strict';

  var el = document.getElementById('panel-data');
  var SEED = {};
  try { SEED = el ? JSON.parse(el.textContent) : {}; } catch (e) { SEED = {}; }
  var BRIDGE = w.ROZET || {};
  var URLS = SEED.urls || {};

  /* تصویرها نشانی کامل دارند (رسانه یا مسیر خصوصی کیک)؛ پیشوندی لازم نیست */
  var IMG = '';

  function midnight(d) { var x = new Date(d); x.setHours(0, 0, 0, 0); return x; }
  function iso(d) {
    var x = midnight(d);
    return x.getFullYear() + '-' + ('0' + (x.getMonth() + 1)).slice(-2) + '-' + ('0' + x.getDate()).slice(-2);
  }
  function day(offset) { var d = new Date(); d.setDate(d.getDate() + offset); return iso(d); }
  function fromIso(s) { var p = String(s).split('-'); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function daysFromToday(s) { return Math.round((midnight(fromIso(s)) - midnight(new Date())) / 86400000); }

  var STATE = {
    new:       { l: 'ثبت شده',           next: 'baking',    btn: 'شروع پخت' },
    baking:    { l: 'در حال آماده‌سازی', next: 'ready',     btn: 'آماده شد' },
    ready:     { l: 'آماده‌ی تحویل',     next: 'delivered', btn: 'تحویل داده شد' },
    delivered: { l: 'تحویل شده',         next: null,        btn: '' },
    canceled:  { l: 'لغو شده',           next: null,        btn: '' }
  };
  /* همان BACKWARD_TRANSITIONS سرور */
  var PREV = { baking: 'new', ready: 'baking', delivered: 'ready' };
  var STEPS = [
    { k: 'new',       l: 'ثبت سفارش' },
    { k: 'baking',    l: 'آماده‌سازی' },
    { k: 'ready',     l: 'آماده‌ی تحویل' },
    { k: 'delivered', l: 'تحویل' }
  ];

  var ORDERS = SEED.orders || (SEED.order ? [SEED.order] : []);

  function all() { return ORDERS; }
  function find(code) {
    return ORDERS.filter(function (o) { return o.code === code; })[0] || null;
  }
  /* تاریخچه‌ی واقعی از جدول OrderStatusHistory، با زمان و نام کسی که زد */
  function history(o) { return o.history || []; }

  /* سفارشِ تازه از سرور را جای نسخه‌ی قدیمی می‌گذارد (همان شیء، تا
     ارجاع‌های موجود در صفحه کهنه نشوند). */
  function replace(fresh) {
    if (!fresh) return null;
    var old = find(fresh.code);
    if (!old) { ORDERS.push(fresh); return fresh; }
    Object.keys(old).forEach(function (k) { if (!(k in fresh)) delete old[k]; });
    Object.keys(fresh).forEach(function (k) { old[k] = fresh[k]; });
    return old;
  }
  function setAll(list) {
    ORDERS.length = 0;
    (list || []).forEach(function (o) { ORDERS.push(o); });
  }

  function detailUrl(code) {
    return (URLS.detail || '').replace('CODE', encodeURIComponent(code));
  }

  /* ══ ارتباط با سرور ══
     نشست تمام‌شده (۴۰۱) یعنی برگشتن به صفحه‌ی ورود؛ بقیه‌ی خطاها همان
     پیام سرور را به صفحه می‌دهند. */
  function handle(r) {
    if (r.status === 401) {
      location.href = (URLS.login || '/staff/login/') + '?next=' + encodeURIComponent(location.pathname);
      return new Promise(function () {});
    }
    return r.json().catch(function () {
      return { ok: false, error: 'پاسخ سرور خوانا نبود؛ دوباره امتحان کنید.' };
    }).then(function (data) { data.status = r.status; return data; });
  }
  function offline() {
    return { ok: false, status: 0, error: 'ارتباط با سرور برقرار نشد.' };
  }

  function api(body) {
    return fetch(URLS.api, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': BRIDGE.csrf || '' },
      body: JSON.stringify(body)
    }).then(handle, offline);
  }
  function load(code) {
    var url = URLS.api + (code ? '?code=' + encodeURIComponent(code) : '');
    return fetch(url, { credentials: 'same-origin', cache: 'no-store' }).then(handle, offline);
  }

  w.RozetOrders = {
    IMG: IMG,
    STATE: STATE, PREV: PREV, STEPS: STEPS,
    all: all, find: find, history: history, replace: replace, setAll: setAll,
    day: day, iso: iso, fromIso: fromIso, daysFromToday: daysFromToday,
    caps: SEED.caps || {}, me: SEED.me || {}, urls: URLS,
    poll: Math.max(5, +SEED.poll || 20),
    unseen: SEED.unseen || [],
    code: SEED.code || '',
    detailUrl: detailUrl, api: api, load: load
  };
})(window);
