/* ═══════════════════════════════════════════════════════════════════════════
   رُزِت — سبد خرید مشترک
   ───────────────────────────────────────────────────────────────────────────
   نسخه‌ی جنگو. سبد در دیتابیس است، نه در مرورگر.

   رابط بیرونی همان چیزی است که سه صفحه‌ی سایت از قبل صدا می‌زنند:
   load() یک آرایه می‌دهد و save(items) آن را ذخیره می‌کند. برای همین
   هیچ‌کدام از آن صفحه‌ها بازنویسی نشده‌اند.

   داخلش اما فرق کرده:
     • load() از آینه‌ی حافظه می‌خواند که سرور با json_script پر کرده،
       چون سه صفحه آن را همگام و پیش از هر چیز صدا می‌زنند.
     • save() کل سبد را به سرور می‌فرستد و سرور بازش می‌سازد. یک اکشنِ
       idempotent به‌جای چهار اکشنِ افزودن/کم‌کردن/حذف — هیچ حالت
       ناهمگامی نمی‌ماند.
     • قیمت از پاسخ سرور می‌آید، نه از چیزی که فرستاده‌ایم. اگر مدیر
       قیمت را عوض کرده باشد، همان لحظه اصلاح می‌شود.
   ═══════════════════════════════════════════════════════════════════════════ */
window.RozetCart = (function () {
  'use strict';

  var BRIDGE = window.ROZET || {};

  /* آینه‌ی حافظه‌ای. منبع حقیقت دیتابیس است؛ این فقط آخرین نسخه‌ای است
     که از سرور گرفته‌ایم تا load() بتواند همگام جواب بدهد. */
  var items = (function () {
    var tag = document.getElementById('cart-data');
    if (!tag) return [];
    try { return JSON.parse(tag.textContent) || []; } catch (e) { return []; }
  })();

  var pending = null;   /* آخرین سبدی که منتظر ارسال است */
  var flying = false;   /* درخواستی در راه است */
  var timer = null;     /* جمع‌کننده‌ی فراخوانی‌های پشت‌سرهم */

  function norm(list) {
    if (!Array.isArray(list)) return [];
    return list.filter(function (i) { return i && (i.id != null); }).map(function (i) {
      return {
        id: i.id,
        name: String(i.name || ''),
        meta: i.meta ? String(i.meta) : '',
        price: Math.max(0, Number(i.price) || 0),
        img: i.img || '',
        qty: Math.max(1, Math.min(99, parseInt(i.qty, 10) || 1)),
        size: i.size != null ? i.size : null,
        flavor: i.flavor != null ? i.flavor : null,
        addons: Array.isArray(i.addons) ? i.addons.slice() : [],
        plaque: i.plaque ? String(i.plaque) : ''
      };
    });
  }

  /* سرور فقط «چه محصولی، کدام گزینه، چندتا» را لازم دارد. نام و قیمت و
     تصویر را خودش از دیتابیس می‌خواند و برمی‌گرداند. */
  function forServer(list) {
    return list.map(function (i) {
      return {
        id: i.id, qty: i.qty, size: i.size,
        flavor: i.flavor, addons: i.addons, plaque: i.plaque
      };
    });
  }

  /* چند تابعِ رنگ‌آمیزی پشت سر هم save() را صدا می‌زنند و هر کدام یک
     درخواست می‌شد. چون هر ارسال جایگزینیِ کامل است، فقط آخری معنی
     دارد — پس یک لحظه صبر می‌کنیم تا همه‌شان یکی شوند. */
  function queue() {
    if (timer) return;
    timer = setTimeout(function () { timer = null; send(); }, 60);
  }

  function send() {
    if (timer) { clearTimeout(timer); timer = null; }
    if (flying || pending === null || !BRIDGE.cartApi) return;
    var payload = pending;
    pending = null;
    flying = true;

    fetch(BRIDGE.cartApi, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': BRIDGE.csrf || '' },
      /* اگر کاربر همان لحظه صفحه را ترک کند، مرورگر درخواست را نیمه‌کاره
         رها نمی‌کند. برخلاف sendBeacon، هدر CSRF هم همراهش می‌رود. */
      keepalive: true,
      body: JSON.stringify({ action: 'replace', items: forServer(payload) })
    }).then(function (r) {
      return r.json().catch(function () { return null; });
    }).then(function (res) {
      flying = false;
      if (res && res.ok) {
        items = norm(res.items);
        /* اگر بین رفت و برگشت باز هم تغییری آمده، همان تازه‌تر می‌ماند */
        if (pending === null) notify();
      }
      send();
    }).catch(function () {
      flying = false;
      send();
    });
  }

  /* صفحه‌هایی که سبد را نشان می‌دهند می‌توانند گوش بدهند تا وقتی سرور
     قیمت یا ردیفی را اصلاح کرد، دوباره بکشند. */
  function notify() {
    try {
      document.dispatchEvent(new CustomEvent('rozet:cart', { detail: items.slice() }));
    } catch (e) {}
  }

  function load() { return norm(items); }

  function save(list) {
    items = norm(list);
    pending = items;
    queue();
    return items;
  }

  function clear() {
    items = [];
    pending = [];
    send();   /* خالی‌کردن صبر نمی‌کند */
  }

  /* ترک صفحه، ارسالِ معلق را جلو می‌اندازد. */
  window.addEventListener('pagehide', send);

  function count() {
    return items.reduce(function (s, i) { return s + i.qty; }, 0);
  }

  function total() {
    return items.reduce(function (s, i) { return s + i.price * i.qty; }, 0);
  }

  /* کلید یکتای هر ردیف: یک محصول با گزینه‌های متفاوت، ردیف جداست */
  function keyOf(i) { return String(i.id) + '|' + (i.meta || ''); }

  return {
    load: load, save: save, clear: clear,
    count: count, total: total, keyOf: keyOf
  };
})();
