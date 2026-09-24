/* ═══════════════════════════════════════════════════════════════════════════
   رُزِت — موتور صفحه محصولات
   ───────────────────────────────────────────────────────────────────────────
   ماژول ۱ : داده محصولات و جدول دسته‌ها
   ماژول ۲ : ابزارهای کمکی (اعداد فارسی، دیبانس، اعلان)
   ماژول ۳ : سوییچ تم روشن/تیره (مستقل، بدون وابستگی به main.js)
   ماژول ۴ : وضعیت صفحه و همگام‌سازی با آدرس صفحه
   ماژول ۵ : ساخت فیلترها
   ماژول ۶ : فیلتر، جستجو، مرتب‌سازی
   ماژول ۷ : رندر کارت‌ها، اسکلت بارگذاری، نمایش بیشتر
   ماژول ۸ : تراشه‌های فیلتر فعال
   ماژول ۹ : سبد خرید و علاقه‌مندی‌ها
   ماژول ۱۰: نمایش سریع محصول (با تله فوکوس)
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ══ ۱. داده ══ */

  /* داده از قالب جنگو می‌آید. اگر <script id="catalog-data"> در صفحه بود،
     همان مبناست؛ وگرنه آرایه‌های زیر کار می‌کنند تا تمپلیت ساکن مستقل
     بماند. بقیه‌ی فایل هیچ تغییری نکرده — فیلتر، مرتب‌سازی، صفحه‌بندی،
     اسلایدر قیمت و نمای سریع همه همان‌اند. */
  var SEED = (function () {
    var el = document.getElementById('catalog-data');
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  })();

  /* سرور نشانی کامل تصویر را می‌دهد، پس پیشوند لازم نیست. */
  var IMG = SEED ? '' : '../assets/images/';

  var CATEGORIES = SEED ? SEED.categories : [
    { id: 'cakes',    label: 'کیک' },
    { id: 'pastries', label: 'شیرینی تر و دسر' },
    { id: 'sweets',   label: 'شیرینی سنتی' },
    { id: 'seasonal', label: 'مجموعه فصلی' }
  ];

  var OCCASIONS = SEED ? SEED.occasions : [
    { id: 'birthday',  label: 'تولد' },
    { id: 'wedding',   label: 'عروسی' },
    { id: 'gift',      label: 'هدیه' },
    { id: 'gathering', label: 'مهمانی' },
    { id: 'daily',     label: 'هر روز' }
  ];

  var FEATURES = SEED ? SEED.features : [
    { id: 'sameday',  label: 'آماده تحویل امروز' },
    { id: 'nut-free', label: 'بدون آجیل' },
    { id: 'eggless',  label: 'بدون تخم‌مرغ' },
    { id: 'giftbox',  label: 'همراه جعبه کادویی' }
  ];

  var PRODUCTS = SEED ? SEED.products : [
    { id: 1,  name: 'کیک رز ولوت', en: 'Rose Velvet', price: 380000, cat: 'cakes', img: 'cake-rose-velvet.webp',
      notes: 'گلاب کاشان · خامه وانیل · تمشک تازه', serves: '۶ تا ۸ نفر', badge: 'پرفروش‌ترین',
      occ: ['birthday', 'gift'], feat: ['sameday', 'giftbox'], pop: 98, added: 12, stock: true },
    { id: 2,  name: 'کیک پسته و زعفران', en: 'Pistachio & Saffron', price: 420000, cat: 'cakes', img: 'cake-pistachio.webp',
      notes: 'زعفران قائنات · پسته رفسنجان · هل', serves: '۸ تا ۱۰ نفر', badge: 'طعم سنتی',
      occ: ['gathering', 'gift'], feat: ['giftbox'], pop: 95, added: 9, stock: true },
    { id: 3,  name: 'کیک شکلات تلخ', en: 'Dark Chocolate 72%', price: 360000, cat: 'cakes', img: 'cake-chocolate.webp',
      notes: 'شکلات تلخ ۷۲٪ · گاناش شکلاتی · پرالین فندق', serves: '۶ تا ۸ نفر', badge: '',
      occ: ['birthday', 'daily'], feat: ['sameday'], pop: 90, added: 7, stock: true },
    { id: 4,  name: 'کیک زعفران و هل', en: 'Saffron & Cardamom', price: 390000, cat: 'cakes', img: 'cake-saffron.webp',
      notes: 'زعفران دم‌کرده · خامه هل · خلال بادام', serves: '۸ تا ۱۰ نفر', badge: 'مناسب مهمانی',
      occ: ['gathering', 'wedding'], feat: ['nut-free'], pop: 82, added: 5, stock: true },
    { id: 5,  name: 'کیک هلو و توت', en: 'Peach & Berries', price: 340000, cat: 'cakes', img: 'cake-berry.webp',
      notes: 'هلوی تازه · تمشک · خامه وانیل', serves: '۶ تا ۸ نفر', badge: 'سبک و میوه‌ای',
      occ: ['birthday', 'daily'], feat: ['sameday', 'nut-free', 'eggless'], pop: 76, added: 14, stock: true },
    { id: 6,  name: 'کیک شکلات و گلاب', en: 'Chocolate & Rose', price: 450000, cat: 'cakes', img: 'cake-truffle.webp',
      notes: 'کاکائوی تلخ · ترافل شکلاتی · گلبرگ رز', serves: '۸ تا ۱۰ نفر', badge: 'ویژه',
      occ: ['wedding', 'gift'], feat: ['giftbox'], pop: 88, added: 15, stock: true },
    { id: 7,  name: 'کیک چندطبقه سفارشی', en: 'Bespoke Tiered Cake', price: 1850000, cat: 'cakes', img: 'custom-cake.webp',
      notes: 'طراحی اختصاصی · انتخاب طعم لایه‌ها · تزیین دست‌ساز', serves: '۳۰ نفر به بالا', badge: 'سفارشی',
      occ: ['wedding'], feat: ['giftbox'], pop: 70, added: 16, stock: true },

    { id: 8,  name: 'مینی‌کیک وانیل و هل', en: 'Vanilla & Cardamom', price: 85000, cat: 'pastries', img: 'pastry-cupcake.webp',
      notes: 'پوست پرتقال · گاناش سفید', serves: 'تک‌نفره', badge: 'پخت روز',
      occ: ['daily', 'gathering'], feat: ['sameday'], pop: 92, added: 11, stock: true },
    { id: 9,  name: 'ماکارون پسته و گل سرخ', en: 'Macaron Pistache & Rose', price: 190000, cat: 'pastries', img: 'pastry-macaron.webp',
      notes: 'پسته دوآتیشه · گلاب کاشان · جعبه ۶ عددی', serves: 'پک ۶ عددی', badge: 'پرفروش',
      occ: ['gift', 'gathering'], feat: ['giftbox', 'eggless'], pop: 96, added: 13, stock: true },
    { id: 10, name: 'شیرینی خشک زعفرانی', en: 'Saffron Sablé', price: 145000, cat: 'pastries', img: 'pastry-cookie.webp',
      notes: 'کره تازه · زعفران سرگل · جعبه ۸ عددی', serves: 'پک ۸ عددی', badge: '',
      occ: ['gift', 'daily'], feat: ['sameday', 'giftbox', 'nut-free'], pop: 80, added: 6, stock: true },
    { id: 11, name: 'تارت انجیر و انار', en: 'Fig & Pomegranate', price: 110000, cat: 'pastries', img: 'pastry-tart.webp',
      notes: 'انجیر تازه · کرم بادام', serves: 'تک‌نفره', badge: 'فصلی',
      occ: ['daily'], feat: ['sameday'], pop: 74, added: 10, stock: false },

    { id: 12, name: 'سوهان زعفرانی', en: 'Saffron Sohan', price: 120000, cat: 'sweets', img: 'sweets-editorial.webp',
      notes: 'کره حیوانی · زعفران ممتاز', serves: 'جعبه ۴۵۰ گرمی', badge: '',
      occ: ['gift'], feat: ['giftbox', 'eggless'], pop: 85, added: 3, stock: true },
    { id: 13, name: 'گز انگبین اصفهان', en: 'Isfahan Gaz', price: 195000, cat: 'sweets', img: 'sweets-editorial.webp',
      notes: '۴۲٪ مغز پسته اعلا', serves: 'جعبه ۵۰۰ گرمی', badge: 'اصیل',
      occ: ['gift'], feat: ['giftbox', 'eggless'], pop: 87, added: 4, stock: true },
    { id: 14, name: 'قطاب سنتی یزد', en: 'Yazd Ghottab', price: 110000, cat: 'sweets', img: 'sweets-editorial.webp',
      notes: 'مغز گردو و بادام · هل سبز', serves: 'جعبه ۴۰۰ گرمی', badge: '',
      occ: ['daily', 'gift'], feat: ['eggless'], pop: 72, added: 2, stock: true },
    { id: 15, name: 'نان برنجی کرمانشاهی', en: 'Rice Cookies', price: 85000, cat: 'sweets', img: 'sweets-editorial.webp',
      notes: 'روغن کرمانشاهی اصل', serves: 'جعبه ۳۵۰ گرمی', badge: '',
      occ: ['daily'], feat: ['nut-free', 'eggless', 'sameday'], pop: 68, added: 1, stock: true },
    { id: 16, name: 'باقلوای استانبولی و ایرانی', en: 'Baklava Selection', price: 130000, cat: 'sweets', img: 'sweets-editorial.webp',
      notes: 'شهد عسل و زعفران', serves: 'جعبه ۴۵۰ گرمی', badge: '',
      occ: ['gift', 'gathering'], feat: ['giftbox'], pop: 79, added: 8, stock: true },

    { id: 17, name: 'باکس فصلی انار و شاه‌بلوط', en: 'Autumn Box', price: 520000, cat: 'seasonal', img: 'seasonal-editorial.webp',
      notes: 'انار یزد · شاه‌بلوط کاراملی · شکلات تلخ ۶۶٪', serves: 'جعبه ۱۲ عددی', badge: 'تیراژ محدود',
      occ: ['gift', 'gathering'], feat: ['giftbox'], pop: 93, added: 17, stock: true },
    { id: 18, name: 'باکس هدیه مینیاتور', en: 'Petite Gift Box', price: 290000, cat: 'seasonal', img: 'brand-story.webp',
      notes: 'ترکیبی از شیرینی‌های کوچک آتلیه', serves: 'جعبه ۹ عددی', badge: 'هدیه',
      occ: ['gift'], feat: ['giftbox', 'sameday'], pop: 84, added: 18, stock: true }
  ];

  var PAGE_SIZE = 8;

  /* ══ ۲. کمکی‌ها ══ */
  var fa = function (n) { return Number(n).toLocaleString('fa-IR'); };
  var byId = function (id) { return document.getElementById(id); };

  function debounce(fn, wait) {
    var t;
    return function () {
      var ctx = this, args = arguments;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(ctx, args); }, wait);
    };
  }

  /* حروف عربی/فارسی و اعداد را یکدست می‌کند تا جستجو به شکل نوشتن حساس نباشد */
  function normalize(s) {
    return String(s || '')
      .replace(/[يى]/g, 'ی')
      .replace(/ك/g, 'ک')
      .replace(/[‌‏‎]/g, ' ')
      .replace(/[ً-ْ]/g, '')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();
  }

  var toastTimer;
  function toast(msg, icon) {
    var old = document.querySelector('.pl-toast');
    if (old) old.remove();
    clearTimeout(toastTimer);
    var el = document.createElement('div');
    el.className = 'pl-toast';
    el.setAttribute('role', 'status');
    el.innerHTML = (icon || '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>') +
      '<span>' + msg + '</span>';
    document.body.appendChild(el);
    toastTimer = setTimeout(function () {
      el.classList.add('is-hiding');
      setTimeout(function () { el.remove(); }, 320);
    }, 2600);
  }

  /* ══ ۳. سوییچ تم ══ */
  (function themeSwitch() {
    var btn = document.querySelector('.theme-toggle');
    var lightLink = byId('theme-light');
    var darkLink = byId('theme-dark');
    if (!btn || !lightLink || !darkLink) return;
    var root = document.documentElement;

    function current() { return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light'; }

    function paint(theme) {
      var isDark = theme === 'dark';
      /* ترتیب مهم است: اول شیت مقصد فعال، بعد قبلی غیرفعال، تا هیچ فریمی بی‌استایل نماند */
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
      var r = btn.getBoundingClientRect();
      root.style.setProperty('--rozet-tt-x', (r.left + r.width / 2) + 'px');
      root.style.setProperty('--rozet-tt-y', (r.top + r.height / 2) + 'px');

      btn.classList.remove('is-switching');
      void btn.offsetWidth;
      btn.classList.add('is-switching');
      setTimeout(function () { btn.classList.remove('is-switching'); }, 700);

      var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      var done = false;
      function apply() { if (done) return; done = true; paint(next); }

      if (document.startViewTransition && !reduced) {
        try {
          var vt = document.startViewTransition(apply);
          /* هر سه وعده باید گرفته شوند؛ اگر کاربر سریع دوبار تم را عوض کند
             ترنزیشن قبلی abort می‌شود و rejection بی‌صاحب در کنسول می‌افتد. */
          ['ready', 'updateCallbackDone', 'finished'].forEach(function (k) {
            if (vt && vt[k] && vt[k].catch) vt[k].catch(function () {});
          });
        } catch (e) { apply(); }
        setTimeout(apply, 260); /* شبکه ایمنی اگر ترنزیشن اجرا نشد */
      } else { apply(); }
    });
  })();

  /* ══ ۴. وضعیت ══ */
  var PRICE_MIN = Math.min.apply(null, PRODUCTS.map(function (p) { return p.price; }));
  var PRICE_MAX = Math.max.apply(null, PRODUCTS.map(function (p) { return p.price; }));

  var state = {
    q: '', cats: [], occ: [], feat: [],
    min: PRICE_MIN, max: PRICE_MAX,
    sort: 'popular', view: 'grid', shown: PAGE_SIZE
  };

  function readURL() {
    var p = new URLSearchParams(location.search);
    if (p.get('q')) state.q = p.get('q');
    if (p.get('cat')) state.cats = p.get('cat').split(',').filter(Boolean);
    if (p.get('occ')) state.occ = p.get('occ').split(',').filter(Boolean);
    if (p.get('feat')) state.feat = p.get('feat').split(',').filter(Boolean);
    if (p.get('sort')) state.sort = p.get('sort');
    if (p.get('view')) state.view = p.get('view');
    var mn = parseInt(p.get('min'), 10), mx = parseInt(p.get('max'), 10);
    if (!isNaN(mn)) state.min = Math.max(PRICE_MIN, mn);
    if (!isNaN(mx)) state.max = Math.min(PRICE_MAX, mx);
  }

  function writeURL() {
    var p = new URLSearchParams();
    if (state.q) p.set('q', state.q);
    if (state.cats.length) p.set('cat', state.cats.join(','));
    if (state.occ.length) p.set('occ', state.occ.join(','));
    if (state.feat.length) p.set('feat', state.feat.join(','));
    if (state.sort !== 'popular') p.set('sort', state.sort);
    if (state.view !== 'grid') p.set('view', state.view);
    if (state.min > PRICE_MIN) p.set('min', state.min);
    if (state.max < PRICE_MAX) p.set('max', state.max);
    var qs = p.toString();
    history.replaceState(null, '', qs ? '?' + qs : location.pathname);
  }

  /* ══ ۵. ساخت فیلترها ══ */
  var CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>';

  function countFor(kind, id) {
    return PRODUCTS.filter(function (p) {
      if (kind === 'cat') return p.cat === id;
      if (kind === 'occ') return p.occ.indexOf(id) > -1;
      return p.feat.indexOf(id) > -1;
    }).length;
  }

  function optionRow(kind, item) {
    var checked = (kind === 'cat' ? state.cats : state.feat).indexOf(item.id) > -1;
    return '<label class="pl-opt">' +
      '<input type="checkbox" data-kind="' + kind + '" value="' + item.id + '"' + (checked ? ' checked' : '') + '>' +
      '<span class="pl-opt__box" aria-hidden="true">' + CHECK + '</span>' +
      '<span class="pl-opt__label">' + item.label + '</span>' +
      '<span class="pl-opt__n">' + fa(countFor(kind, item.id)) + '</span>' +
      '</label>';
  }

  function buildFilters() {
    byId('catGroup').innerHTML = CATEGORIES.map(function (c) { return optionRow('cat', c); }).join('');
    byId('featureGroup').innerHTML = FEATURES.map(function (f) { return optionRow('feat', f); }).join('');
    byId('occasionGroup').innerHTML = OCCASIONS.map(function (o) {
      var on = state.occ.indexOf(o.id) > -1;
      return '<button type="button" class="pl-tag" data-occ="' + o.id + '" aria-pressed="' + on + '">' + o.label + '</button>';
    }).join('');
  }

  /* ══ ۶. فیلتر و مرتب‌سازی ══ */
  function filtered() {
    var q = normalize(state.q);
    var list = PRODUCTS.filter(function (p) {
      if (state.cats.length && state.cats.indexOf(p.cat) === -1) return false;
      if (state.occ.length && !state.occ.some(function (o) { return p.occ.indexOf(o) > -1; })) return false;
      if (state.feat.length && !state.feat.every(function (f) { return p.feat.indexOf(f) > -1; })) return false;
      if (p.price < state.min || p.price > state.max) return false;
      if (q) {
        var hay = normalize(p.name + ' ' + p.en + ' ' + p.notes);
        if (hay.indexOf(q) === -1) return false;
      }
      return true;
    });

    var s = state.sort;
    list.sort(function (a, b) {
      if (s === 'price-asc') return a.price - b.price;
      if (s === 'price-desc') return b.price - a.price;
      if (s === 'new') return b.added - a.added;
      if (s === 'name') return a.name.localeCompare(b.name, 'fa');
      return b.pop - a.pop;
    });
    return list;
  }

  /* ══ ۷. رندر ══ */
  var grid = byId('productGrid');
  var emptyState = byId('emptyState');
  var loadMoreWrap = document.querySelector('.pl-more');
  /* نشان‌شده‌های همین کاربر از سرور می‌آیند تا قلب‌ها با حالت درست
     رندر شوند، نه همیشه خالی. */
  var wish = new Set((SEED && SEED.favorites) || []);

  /* ══ علاقه‌مندی روی سرور ══
     قلب تا پیش از این فقط یک کلاس CSS را عوض می‌کرد و با رفرش پاک
     می‌شد. حالا در جدول Favorite می‌نشیند و پنل کاربری همان را نشان
     می‌دهد.

     برای مهمان سرور ۴۰۱ می‌دهد و نشانی ورود را برمی‌گرداند؛ قلب به
     حالت قبل برمی‌گردد تا چیزی که ذخیره نشده، ذخیره‌شده به نظر نرسد. */
  function saveFavorite(id, on, revert) {
    var bridge = window.ROZET || {};
    if (!bridge.favoriteApi) return;
    fetch(bridge.favoriteApi, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': bridge.csrf || '' },
      body: JSON.stringify({ product: id, on: on })
    }).then(function (r) {
      return r.json().catch(function () { return { ok: false }; });
    }).then(function (res) {
      if (res && res.ok) return;
      if (revert) revert();
      if (res && res.auth === false && res.login) {
        setTimeout(function () { location.href = res.login; }, 900);
      }
    }).catch(function () { if (revert) revert(); });
  }


  function cardHTML(p) {
    var liked = wish.has(p.id);
    /* نشانی صفحه‌ی جزئیات روی خود کارت؛ کلیک روی هر جای کارت
       همین را باز می‌کند. */
    var href = p.url || ('../product-details/product-details.html?id=' + p.id);
    return '<article class="pl-card" data-id="' + p.id + '" data-url="' + href + '">' +
      '<div class="pl-card__media">' +
        '<img class="pl-card__img" src="' + IMG + p.img + '" alt="' + p.name + '" loading="lazy">' +
        (p.badge ? '<span class="pl-card__badge">' + p.badge + '</span>' : '') +
        '<button class="pl-card__wish' + (liked ? ' is-liked' : '') + '" type="button" data-wish="' + p.id + '" ' +
          'aria-pressed="' + liked + '" aria-label="افزودن ' + p.name + ' به علاقه‌مندی‌ها">' +
          '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21.2l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg>' +
        '</button>' +
        (p.stock ? '<button class="pl-card__quick" type="button" data-quick="' + p.id + '">نمایش سریع</button>'
                 : '<div class="pl-card__soldout">فعلاً موجود نیست</div>') +
      '</div>' +
      '<div class="pl-card__body">' +
        '<p class="pl-card__cat">' + catLabel(p.cat) + ' · ' + p.serves + '</p>' +
        '<h3 class="pl-card__name"><a href="' + href + '">' + p.name + '</a></h3>' +
        '<span class="pl-card__en">' + p.en + '</span>' +
        '<p class="pl-card__notes">' + p.notes + '</p>' +
        '<div class="pl-card__foot">' +
          '<span class="pl-card__price">' + fa(p.price) + ' <small>تومان</small></span>' +
          (p.stock
            ? '<button class="pl-card__add" type="button" data-add="' + p.id + '">افزودن به سبد</button>'
            : '<button class="pl-card__add" type="button" disabled>ناموجود</button>') +
        '</div>' +
      '</div>' +
    '</article>';
  }

  function catLabel(id) {
    var c = CATEGORIES.filter(function (x) { return x.id === id; })[0];
    return c ? c.label : id;
  }

  function skeleton(n) {
    var one = '<article class="pl-card pl-skeleton" aria-hidden="true">' +
      '<div class="pl-sk pl-sk--media"></div>' +
      '<div class="pl-card__body">' +
        '<div class="pl-sk pl-sk--line w45"></div>' +
        '<div class="pl-sk pl-sk--line w70"></div>' +
        '<div class="pl-sk pl-sk--line"></div>' +
        '<div class="pl-sk pl-sk--line w45"></div>' +
      '</div></article>';
    return new Array(n + 1).join(one);
  }

  var skelTimer;
  function render(useSkeleton) {
    var list = filtered();
    grid.setAttribute('data-view', state.view);

    function paint() {
      var slice = list.slice(0, state.shown);
      grid.innerHTML = slice.map(cardHTML).join('');
      /* انیمیشن ورود پلکانی */
      [].forEach.call(grid.children, function (el, i) {
        el.style.animationDelay = Math.min(i, 10) * 28 + 'ms';
      });

      emptyState.hidden = list.length !== 0;
      grid.hidden = list.length === 0;
      loadMoreWrap.hidden = list.length === 0;

      byId('resultCount').innerHTML = list.length
        ? '<b>' + fa(list.length) + '</b> محصول' + (state.q ? ' برای «' + escHtml(state.q) + '»' : '')
        : 'نتیجه‌ای یافت نشد';

      var more = list.length - slice.length;
      byId('loadMore').hidden = more <= 0;
      byId('moreHint').textContent = list.length
        ? (more > 0 ? fa(slice.length) + ' از ' + fa(list.length) + ' محصول' : 'همه محصولات نمایش داده شد')
        : '';
    }

    clearTimeout(skelTimer);
    if (useSkeleton) {
      grid.hidden = false;
      emptyState.hidden = true;
      grid.innerHTML = skeleton(Math.min(PAGE_SIZE, 6));
      skelTimer = setTimeout(paint, 260);
    } else {
      paint();
    }

    renderChips();
    updateFilterCount();
    writeURL();
  }

  /* ══ ۸. تراشه‌های فعال ══ */
  var X = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>';

  /* هر چیزی که از نشانی صفحه می‌آید (?q= و ?cat= …) ورودی کاربر است و
     پیش از innerHTML خنثی می‌شود؛ وگرنه لینکِ
     /products/?q=<img onerror=…> در مرورگرِ هر کسی که بازش کند اسکریپت
     اجرا می‌کرد. */
  function escHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function chip(label, kind, value) {
    label = escHtml(label); value = escHtml(value);
    return '<button class="pl-chip" type="button" data-chip="' + kind + '" data-value="' + value + '" ' +
      'aria-label="حذف فیلتر ' + label + '">' + label + X + '</button>';
  }

  function renderChips() {
    var out = [];
    state.cats.forEach(function (c) { out.push(chip(catLabel(c), 'cat', c)); });
    state.occ.forEach(function (o) {
      var m = OCCASIONS.filter(function (x) { return x.id === o; })[0];
      out.push(chip(m ? m.label : o, 'occ', o));
    });
    state.feat.forEach(function (f) {
      var m = FEATURES.filter(function (x) { return x.id === f; })[0];
      out.push(chip(m ? m.label : f, 'feat', f));
    });
    if (state.min > PRICE_MIN || state.max < PRICE_MAX) {
      out.push(chip('تا ' + fa(state.max) + ' تومان', 'price', 'x'));
    }
    if (state.q) out.push(chip('«' + state.q + '»', 'q', 'x'));
    byId('activeChips').innerHTML = out.join('');
  }

  function activeCount() {
    return state.cats.length + state.occ.length + state.feat.length +
      (state.min > PRICE_MIN || state.max < PRICE_MAX ? 1 : 0);
  }
  function updateFilterCount() {
    var n = activeCount(), el = byId('filterBtnCount');
    el.hidden = n === 0;
    el.textContent = fa(n);
  }

  /* ══ ۹. سبد خرید و علاقه‌مندی ══ */
  var cart = RozetCart.load();   /* سبد مشترک بین صفحه‌ها */
  var cartDrawer = document.querySelector('.cart-drawer');
  var cartOverlay = document.querySelector('.cart-overlay');

  function cartTotalCount() { return cart.reduce(function (s, i) { return s + i.qty; }, 0); }

  function openCart() {
    cartDrawer.classList.add('is-open');
    cartOverlay.classList.add('is-open');
    cartDrawer.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }
  function closeCart() {
    cartDrawer.classList.remove('is-open');
    cartOverlay.classList.remove('is-open');
    cartDrawer.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  function renderCart() {
    RozetCart.save(cart);   /* هر بازنویسی سبد، انبار را هم به‌روز می‌کند */
    var body = cartDrawer.querySelector('.cart-drawer-body');
    var empty = cartDrawer.querySelector('.cart-empty');
    var list = body.querySelector('.cart-items');
    var countEl = document.querySelector('.cart-count');
    var subtotal = document.querySelector('.cart-subtotal-amount');

    countEl.textContent = fa(cartTotalCount());
    countEl.classList.toggle('has-items', cart.length > 0);

    if (!cart.length) {
      if (empty) empty.style.display = 'flex';
      if (list) list.remove();
      subtotal.textContent = '۰ تومان';
      return;
    }
    if (empty) empty.style.display = 'none';
    if (!list) {
      list = document.createElement('div');
      list.className = 'cart-items';
      body.appendChild(list);
    }
    list.innerHTML = cart.map(function (i) {
      return '<div class="cart-item">' +
        '<div class="cart-item-img"><img src="' + i.img + '" alt="' + i.name + '"></div>' +
        '<div class="cart-item-info">' +
          '<p class="cart-item-name">' + i.name + '</p>' +
          '<p class="cart-item-price">' + fa(i.price) + ' تومان</p>' +
          '<div class="cart-item-qty">' +
            '<button class="cart-qty-btn" type="button" data-cart="dec" data-id="' + i.id + '" aria-label="کاهش">−</button>' +
            '<span>' + fa(i.qty) + '</span>' +
            '<button class="cart-qty-btn" type="button" data-cart="inc" data-id="' + i.id + '" aria-label="افزایش">+</button>' +
          '</div>' +
        '</div></div>';
    }).join('');

    var total = cart.reduce(function (s, i) { return s + i.price * i.qty; }, 0);
    subtotal.textContent = fa(total) + ' تومان';
  }

  function addToCart(id, qty) {
    var p = PRODUCTS.filter(function (x) { return x.id === id; })[0];
    if (!p || !p.stock) return;
    var found = cart.filter(function (i) { return i.id === id; })[0];
    if (found) found.qty += (qty || 1);
    else cart.push({ id: p.id, name: p.name, price: p.price, img: IMG + p.img,
                     qty: qty || 1, size: null, flavor: null, addons: [], plaque: '' });
    renderCart();
    toast('«' + p.name + '» به سبد خرید اضافه شد');
  }

  /* ══ ۱۰. نمایش سریع ══ */
  var modal = byId('quickView');
  var qvId = null, qvQty = 1, lastFocus = null;

  function openQuick(id) {
    var p = PRODUCTS.filter(function (x) { return x.id === id; })[0];
    if (!p) return;
    qvId = id; qvQty = 1;
    lastFocus = document.activeElement;

    byId('qvImage').src = IMG + p.img;
    byId('qvImage').alt = p.name;
    byId('qvBadge').textContent = p.badge || '';
    byId('qvName').textContent = p.name;
    byId('qvEn').textContent = p.en;
    byId('qvNotes').textContent = p.notes;
    byId('qvQty').textContent = fa(1);
    byId('qvPrice').textContent = fa(p.price);
    byId('qvSpecs').innerHTML =
      '<dt>دسته</dt><dd>' + catLabel(p.cat) + '</dd>' +
      '<dt>اندازه</dt><dd>' + p.serves + '</dd>' +
      '<dt>مناسبت</dt><dd>' + p.occ.map(function (o) {
        var m = OCCASIONS.filter(function (x) { return x.id === o; })[0];
        return m ? m.label : o;
      }).join('، ') + '</dd>' +
      '<dt>آماده‌سازی</dt><dd>' + (p.feat.indexOf('sameday') > -1 ? 'همین امروز' : '۴۸ ساعت قبل رزرو شود') + '</dd>';

    var full = byId('qvFull');
    if (full) full.href = p.url || ('../product-details/product-details.html?id=' + p.id);
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
    byId('qvAdd').focus();
  }

  function closeQuick() {
    modal.hidden = true;
    document.body.style.overflow = '';
    if (lastFocus) lastFocus.focus();
  }

  /* تله فوکوس: تب داخل پنل می‌چرخد و بیرون نمی‌رود */
  modal.addEventListener('keydown', function (e) {
    if (e.key !== 'Tab') return;
    var f = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });

  /* ══ رویدادها ══ */
  function setQty(v) {
    qvQty = Math.max(1, Math.min(20, v));
    byId('qvQty').textContent = fa(qvQty);
    var p = PRODUCTS.filter(function (x) { return x.id === qvId; })[0];
    if (p) byId('qvPrice').textContent = fa(p.price * qvQty);
  }

  byId('qvMinus').addEventListener('click', function () { setQty(qvQty - 1); });
  byId('qvPlus').addEventListener('click', function () { setQty(qvQty + 1); });
  /* لینک صفحه کامل محصول داخل پنل نمایش سریع */
  (function () {
    var host = byId('qvSpecs');
    if (!host || !host.parentNode) return;
    var a = document.createElement('a');
    a.className = 'pl-modal__full';
    a.id = 'qvFull';
    a.textContent = 'مشاهده صفحه کامل محصول';
    host.parentNode.insertBefore(a, host.nextSibling);
  })();

  byId('qvAdd').addEventListener('click', function () { addToCart(qvId, qvQty); closeQuick(); });

  document.addEventListener('click', function (e) {
    var t = e.target;

    if (t.closest('[data-close-modal]')) { closeQuick(); return; }

    var quick = t.closest('[data-quick]');
    if (quick) { openQuick(+quick.getAttribute('data-quick')); return; }

    var add = t.closest('[data-add]');
    if (add) {
      addToCart(+add.getAttribute('data-add'), 1);
      var orig = add.textContent;
      add.textContent = 'اضافه شد ✓';
      add.classList.add('is-added');
      setTimeout(function () { add.textContent = orig; add.classList.remove('is-added'); }, 1400);
      return;
    }

    var w = t.closest('[data-wish]');
    if (w) {
      var wid = +w.getAttribute('data-wish');
      var on = !wish.has(wid);
      var paint = function (state) {
        if (state) wish.add(wid); else wish.delete(wid);
        w.classList.toggle('is-liked', state);
        w.setAttribute('aria-pressed', String(state));
      };
      paint(on);
      w.classList.add('pop');
      setTimeout(function () { w.classList.remove('pop'); }, 520);
      saveFavorite(wid, on, function () {
        paint(!on);
        toast('برای ذخیره‌ی علاقه‌مندی‌ها وارد شوید.', '');
      });
      toast(on ? 'به علاقه‌مندی‌ها اضافه شد' : 'از علاقه‌مندی‌ها حذف شد',
        '<svg width="17" height="17" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.3l-1.4-1.3C5.4 15.4 2 12.3 2 8.5 2 5.4 4.4 3 7.5 3c1.7 0 3.4.8 4.5 2.1C13.1 3.8 14.8 3 16.5 3 19.6 3 22 5.4 22 8.5c0 3.8-3.4 6.9-8.6 11.5L12 21.3z"/></svg>');
      return;
    }

    var chipBtn = t.closest('[data-chip]');
    if (chipBtn) {
      var kind = chipBtn.getAttribute('data-chip'), val = chipBtn.getAttribute('data-value');
      if (kind === 'cat') state.cats = state.cats.filter(function (x) { return x !== val; });
      if (kind === 'occ') state.occ = state.occ.filter(function (x) { return x !== val; });
      if (kind === 'feat') state.feat = state.feat.filter(function (x) { return x !== val; });
      if (kind === 'price') { state.min = PRICE_MIN; state.max = PRICE_MAX; syncRange(); }
      if (kind === 'q') { state.q = ''; byId('searchInput').value = ''; byId('clearSearch').hidden = true; }
      state.shown = PAGE_SIZE;
      buildFilters();
      render(true);
      return;
    }

    /* کلیک روی خود کارت → صفحه‌ی جزئیات.

       عمداً آخرین شاخه است: همه‌ی دکمه‌های داخل کارت — نمایش
       سریع، افزودن به سبد، علاقه‌مندی — بالاتر return کرده‌اند، پس
       هیچ‌کدامشان به اینجا نمی‌رسد. لینک نام را هم خود مرورگر
       می‌برد، پس دو بار رفتن پیش نمی‌آید. */
    var openCard = t.closest('.pl-card');
    if (openCard && openCard.dataset.url && !t.closest('a, button')) {
      location.href = openCard.dataset.url;
      return;
    }

    var occBtn = t.closest('[data-occ]');
    if (occBtn) {
      var oid = occBtn.getAttribute('data-occ');
      var idx = state.occ.indexOf(oid);
      if (idx > -1) state.occ.splice(idx, 1); else state.occ.push(oid);
      occBtn.setAttribute('aria-pressed', String(idx === -1));
      state.shown = PAGE_SIZE;
      render(true);
      return;
    }

    var cartBtnEl = t.closest('.cart-btn');
    if (cartBtnEl) { openCart(); return; }
    if (t.closest('.cart-drawer-close') || t.closest('.cart-overlay')) { closeCart(); return; }

    var cq = t.closest('[data-cart]');
    if (cq) {
      var cid = +cq.getAttribute('data-id');
      var item = cart.filter(function (i) { return i.id === cid; })[0];
      if (!item) return;
      if (cq.getAttribute('data-cart') === 'inc') item.qty++;
      else { item.qty--; if (item.qty <= 0) cart = cart.filter(function (i) { return i.id !== cid; }); }
      renderCart();
      return;
    }
  });

  /* چک‌باکس‌های دسته و ویژگی */
  document.addEventListener('change', function (e) {
    var cb = e.target.closest('input[data-kind]');
    if (!cb) return;
    var kind = cb.getAttribute('data-kind'), val = cb.value;
    var arr = kind === 'cat' ? state.cats : state.feat;
    var i = arr.indexOf(val);
    if (cb.checked && i === -1) arr.push(val);
    if (!cb.checked && i > -1) arr.splice(i, 1);
    state.shown = PAGE_SIZE;
    render(true);
  });

  /* جستجو */
  var searchInput = byId('searchInput');
  var doSearch = debounce(function () {
    state.q = searchInput.value.trim();
    state.shown = PAGE_SIZE;
    render(true);
  }, 260);
  searchInput.addEventListener('input', function () {
    byId('clearSearch').hidden = !searchInput.value;
    doSearch();
  });
  byId('clearSearch').addEventListener('click', function () {
    searchInput.value = '';
    byId('clearSearch').hidden = true;
    state.q = '';
    state.shown = PAGE_SIZE;
    render(true);
    searchInput.focus();
  });

  /* مرتب‌سازی و نما */
  byId('sortSelect').addEventListener('change', function () {
    state.sort = this.value;
    render(false);
  });
  document.querySelectorAll('.pl-view__btn').forEach(function (b) {
    b.addEventListener('click', function () {
      state.view = b.getAttribute('data-view');
      document.querySelectorAll('.pl-view__btn').forEach(function (x) {
        var on = x === b;
        x.classList.toggle('is-active', on);
        x.setAttribute('aria-pressed', String(on));
      });
      render(false);
    });
  });

  /* محدوده قیمت — دو دستگیره که از هم رد نمی‌شوند */
  var rMin = byId('priceMin'), rMax = byId('priceMax');
  function syncRange() {
    var span = PRICE_MAX - PRICE_MIN;
    rMin.value = Math.round((state.min - PRICE_MIN) / span * 100);
    rMax.value = Math.round((state.max - PRICE_MIN) / span * 100);
    paintRange();
  }
  function paintRange() {
    var a = Math.min(+rMin.value, +rMax.value), b = Math.max(+rMin.value, +rMax.value);
    var fill = byId('rangeFill');
    /* صفحه RTL است: درصدها از سمت راست خوانده می‌شوند */
    fill.style.right = a + '%';
    fill.style.left = (100 - b) + '%';
    var span = PRICE_MAX - PRICE_MIN;
    state.min = Math.round(PRICE_MIN + span * a / 100);
    state.max = Math.round(PRICE_MIN + span * b / 100);
    byId('priceFrom').textContent = fa(state.min);
    byId('priceTo').textContent = fa(state.max);
  }
  [rMin, rMax].forEach(function (r) {
    r.addEventListener('input', function () { paintRange(); });
    r.addEventListener('change', function () { state.shown = PAGE_SIZE; render(true); });
  });

  /* آکاردئون گروه‌ها */
  document.querySelectorAll('.pl-group__toggle').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var sec = btn.closest('.pl-group');
      var open = sec.getAttribute('data-open') !== 'false';
      sec.setAttribute('data-open', String(!open));
      btn.setAttribute('aria-expanded', String(!open));
    });
  });

  /* کشوی فیلتر موبایل */
  var panel = byId('filterPanel'), scrim = byId('filterScrim');
  function openFilters() {
    panel.classList.add('is-open');
    scrim.hidden = false;
    byId('openFilters').setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
    byId('closeFilters').focus();
  }
  function closeFilters() {
    panel.classList.remove('is-open');
    scrim.hidden = true;
    byId('openFilters').setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  }
  byId('openFilters').addEventListener('click', openFilters);
  byId('closeFilters').addEventListener('click', closeFilters);
  byId('applyFilters').addEventListener('click', closeFilters);
  scrim.addEventListener('click', closeFilters);

  /* پاک کردن همه */
  function resetAll() {
    state.q = ''; state.cats = []; state.occ = []; state.feat = [];
    state.min = PRICE_MIN; state.max = PRICE_MAX; state.shown = PAGE_SIZE;
    searchInput.value = '';
    byId('clearSearch').hidden = true;
    syncRange();
    buildFilters();
    render(true);
    toast('فیلترها پاک شد');
  }
  byId('clearAll').addEventListener('click', resetAll);
  byId('emptyReset').addEventListener('click', resetAll);

  byId('loadMore').addEventListener('click', function () {
    state.shown += PAGE_SIZE;
    render(false);
  });

  /* Escape همه لایه‌ها را می‌بندد */
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (!modal.hidden) closeQuick();
    else if (panel.classList.contains('is-open')) closeFilters();
    else if (cartDrawer.classList.contains('is-open')) closeCart();
  });

  /* سایه نوار ابزار وقتی می‌چسبد */
  var toolbar = byId('toolbar');
  var headerH = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--header-h'), 10) || 76;
  window.addEventListener('scroll', function () {
    toolbar.classList.toggle('is-stuck', toolbar.getBoundingClientRect().top <= headerH + 1);
  }, { passive: true });

  /* ══ راه‌اندازی ══ */
  readURL();
  searchInput.value = state.q;
  byId('clearSearch').hidden = !state.q;
  byId('sortSelect').value = state.sort;
  document.querySelectorAll('.pl-view__btn').forEach(function (x) {
    var on = x.getAttribute('data-view') === state.view;
    x.classList.toggle('is-active', on);
    x.setAttribute('aria-pressed', String(on));
  });
  syncRange();
  buildFilters();
  renderCart();
  render(true);

  /* برای تست دستی در کنسول */
  window.rozetShop = { state: state, products: PRODUCTS, render: render };
})();
