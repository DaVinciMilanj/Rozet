/* ═══════════════════════════════════════════════════════════════════════════
   رُزِت — موتور صفحه جزئیات محصول
   ───────────────────────────────────────────────────────────────────────────
   ماژول ۱ : داده محصولات و گزینه‌ها
   ماژول ۲ : کمکی‌ها (اعداد فارسی، اعلان)
   ماژول ۳ : سوییچ تم (مستقل از main.js)
   ماژول ۴ : بارگذاری محصول از روی ?id= و پر کردن صفحه
   ماژول ۵ : گالری، بندانگشتی و لایت‌باکس
   ماژول ۶ : گزینه‌ها (اندازه، طعم، افزودنی، پلاک پیام) و محاسبه قیمت زنده
   ماژول ۷ : هرم طعم، مشخصات، آکاردئون، محصولات مرتبط
   ماژول ۷.۵: نظر مشتری‌ها (نمایشی — ذخیره نمی‌شود)
   ماژول ۸ : سبد خرید، علاقه‌مندی، نوار چسبان موبایل
   ماژول ۹ : ذرات شکر معلق (انیمیشن تکرارشونده)
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  /* داده از قالب جنگو می‌آید. اگر <script id="product-data"> در صفحه
     بود، همان مبناست؛ وگرنه آرایه‌های زیر کار می‌کنند تا تمپلیت ساکن
     مستقل بماند. بقیه‌ی فایل دست‌نخورده است. */
  var SEED = (function () {
    var el = document.getElementById('product-data');
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  })();

  /* سرور نشانی کامل تصویر را می‌دهد، پس پیشوند لازم نیست. */
  var IMG = SEED ? '' : '../assets/images/';
  /* نشانی فهرست محصولات از پل جنگو؛ در تمپلیت ساکن همان فایل کناری. */
  var LIST_URL = (window.ROZET && window.ROZET.productsUrl) || '../product-list/product-list.html';

  var CATEGORIES = SEED ? SEED.categories : {
    cakes:    'کیک',
    pastries: 'شیرینی تر و دسر',
    sweets:   'شیرینی سنتی',
    seasonal: 'مجموعه فصلی'
  };

  /* ══ ۱. داده ══ */
  var PRODUCTS = SEED ? SEED.products : [
    { id: 1, name: 'کیک رز ولوت', en: 'Rose Velvet', price: 380000, cat: 'cakes',
      img: 'cake-rose-velvet.webp', gallery: ['cake-rose-velvet.webp', 'cake-berry.webp', 'brand-story.webp'],
      notes: 'لایه‌های مخملی با گلاب کاشان، خامه وانیل بوربون و تمشک تازه. رویه‌اش را همان روز پخت تزیین می‌کنیم.',
      serves: '۶ تا ۸ نفر', badge: 'پرفروش‌ترین', rating: 4.8, reviews: 126, stock: true,
      pyramid: [{ n: 'گلاب کاشان', v: 90 }, { n: 'خامه وانیل', v: 72 }, { n: 'تمشک تازه', v: 58 }],
      ingredients: 'آرد گندم، تخم‌مرغ محلی، کره حیوانی، شکر، گلاب دوآتشه کاشان، خامه تازه، تمشک، رنگ طبیعی چغندر.',
      allergen: 'حاوی گلوتن، تخم‌مرغ و لبنیات.', keep: 'در یخچال نگهداری شود؛ تا ۴۸ ساعت پس از تحویل بهترین کیفیت را دارد.' },

    { id: 2, name: 'کیک پسته و زعفران', en: 'Pistachio & Saffron', price: 420000, cat: 'cakes',
      img: 'cake-pistachio.webp', gallery: ['cake-pistachio.webp', 'cake-saffron.webp', 'sweets-editorial.webp'],
      notes: 'زعفران نگین قائنات را شب قبل دم می‌کنیم و صبح با موس پسته رفسنجان لایه می‌گذاریم.',
      serves: '۸ تا ۱۰ نفر', badge: 'طعم سنتی', rating: 4.9, reviews: 208, stock: true,
      pyramid: [{ n: 'زعفران قائنات', v: 95 }, { n: 'پسته رفسنجان', v: 84 }, { n: 'هل سبز', v: 46 }],
      ingredients: 'آرد گندم، تخم‌مرغ، کره حیوانی، شکر، زعفران نگین، پسته رفسنجان، هل، خامه تازه.',
      allergen: 'حاوی گلوتن، تخم‌مرغ، لبنیات و آجیل.', keep: 'در یخچال نگهداری شود؛ نیم ساعت قبل از سرو بیرون بگذارید.' },

    { id: 3, name: 'کیک شکلات تلخ', en: 'Dark Chocolate 72%', price: 360000, cat: 'cakes',
      img: 'cake-chocolate.webp', gallery: ['cake-chocolate.webp', 'cake-truffle.webp', 'pastry-cookie.webp'],
      notes: 'شکلات تلخ ۷۲٪ با گاناش دولایه و کرانچ پرالین فندق. برای کسانی که شیرینیِ ملایم می‌خواهند.',
      serves: '۶ تا ۸ نفر', badge: '', rating: 4.7, reviews: 154, stock: true,
      pyramid: [{ n: 'شکلات تلخ ۷۲٪', v: 96 }, { n: 'گاناش', v: 78 }, { n: 'پرالین فندق', v: 62 }],
      ingredients: 'شکلات تلخ ۷۲٪، آرد، تخم‌مرغ، کره، شکر قهوه‌ای، خامه، فندق بوداده.',
      allergen: 'حاوی گلوتن، تخم‌مرغ، لبنیات و آجیل.', keep: 'در دمای خنک نگهداری شود.' },

    { id: 4, name: 'کیک زعفران و هل', en: 'Saffron & Cardamom', price: 390000, cat: 'cakes',
      img: 'cake-saffron.webp', gallery: ['cake-saffron.webp', 'cake-pistachio.webp', 'seasonal-editorial.webp'],
      notes: 'شهد زعفران روی لایه‌ها ریخته می‌شود و با خامه هل و خلال بادام تمام می‌شود.',
      serves: '۸ تا ۱۰ نفر', badge: 'مناسب مهمانی', rating: 4.6, reviews: 88, stock: true,
      pyramid: [{ n: 'زعفران دم‌کرده', v: 88 }, { n: 'خامه هل', v: 70 }, { n: 'خلال بادام', v: 52 }],
      ingredients: 'آرد، تخم‌مرغ، کره حیوانی، شکر، زعفران، هل، بادام، خامه تازه.',
      allergen: 'حاوی گلوتن، تخم‌مرغ، لبنیات و آجیل.', keep: 'در یخچال نگهداری شود.' },

    { id: 5, name: 'کیک هلو و توت', en: 'Peach & Berries', price: 340000, cat: 'cakes',
      img: 'cake-berry.webp', gallery: ['cake-berry.webp', 'cake-rose-velvet.webp', 'pastry-tart.webp'],
      notes: 'سبک و میوه‌ای؛ هلوی تازه و تمشک با خامه وانیل کم‌شیرین. انتخاب خوبی برای روزهای گرم.',
      serves: '۶ تا ۸ نفر', badge: 'سبک و میوه‌ای', rating: 4.5, reviews: 72, stock: true,
      pyramid: [{ n: 'هلوی تازه', v: 84 }, { n: 'تمشک', v: 66 }, { n: 'خامه وانیل', v: 55 }],
      ingredients: 'آرد، تخم‌مرغ، کره، شکر، هلوی تازه، تمشک، خامه، وانیل.',
      allergen: 'حاوی گلوتن، تخم‌مرغ و لبنیات. بدون آجیل.', keep: 'در یخچال؛ همان روز مصرف شود بهتر است.' },

    { id: 6, name: 'کیک شکلات و گلاب', en: 'Chocolate & Rose', price: 450000, cat: 'cakes',
      img: 'cake-truffle.webp', gallery: ['cake-truffle.webp', 'cake-chocolate.webp', 'brand-story.webp'],
      notes: 'کاکائوی تلخ با ترافل شکلاتی و عطر ملایم گلبرگ رز. ترکیبی که کمتر جایی می‌بینید.',
      serves: '۸ تا ۱۰ نفر', badge: 'ویژه', rating: 4.9, reviews: 97, stock: true,
      pyramid: [{ n: 'کاکائوی تلخ', v: 92 }, { n: 'ترافل شکلاتی', v: 80 }, { n: 'گلبرگ رز', v: 44 }],
      ingredients: 'کاکائو، شکلات، آرد، تخم‌مرغ، کره، شکر، خامه، گلاب و گلبرگ رز خوراکی.',
      allergen: 'حاوی گلوتن، تخم‌مرغ و لبنیات.', keep: 'در یخچال نگهداری شود.' },

    { id: 9, name: 'ماکارون پسته و گل سرخ', en: 'Macaron Pistache & Rose', price: 190000, cat: 'pastries',
      img: 'pastry-macaron.webp', gallery: ['pastry-macaron.webp', 'pastry-cupcake.webp', 'pastry-cookie.webp'],
      notes: 'پوسته‌ی نازک بادامی با فیلینگ پسته دوآتیشه و گلاب کاشان. در جعبه ۶ عددی.',
      serves: 'پک ۶ عددی', badge: 'پرفروش', rating: 4.8, reviews: 143, stock: true,
      pyramid: [{ n: 'پسته دوآتیشه', v: 90 }, { n: 'گلاب کاشان', v: 68 }, { n: 'بادام', v: 60 }],
      ingredients: 'پودر بادام، سفیده تخم‌مرغ، شکر، پسته، گلاب، کره.',
      allergen: 'حاوی تخم‌مرغ، لبنیات و آجیل. بدون گلوتن.', keep: 'در یخچال؛ ۲۰ دقیقه قبل از سرو بیرون بگذارید.' },

    { id: 17, name: 'باکس فصلی انار و شاه‌بلوط', en: 'Autumn Box', price: 520000, cat: 'seasonal',
      img: 'seasonal-editorial.webp', gallery: ['seasonal-editorial.webp', 'sweets-editorial.webp', 'brand-story.webp'],
      notes: 'انار یزد، پوره شاه‌بلوط کاراملی و شکلات تلخ ۶۶٪ در جعبه‌ای که فقط همین چند ماه از سال هست.',
      serves: 'جعبه ۱۲ عددی', badge: 'تیراژ محدود', rating: 5.0, reviews: 61, stock: true,
      pyramid: [{ n: 'انار یزد', v: 86 }, { n: 'شاه‌بلوط', v: 74 }, { n: 'شکلات ۶۶٪', v: 64 }],
      ingredients: 'انار تازه، شاه‌بلوط، شکلات تلخ ۶۶٪، شکر، کره، هل.',
      allergen: 'حاوی لبنیات و آجیل.', keep: 'در جای خنک و خشک، دور از نور مستقیم.' }
  ];

  /* گزینه‌های خرید — ضریب قیمت روی قیمت پایه اعمال می‌شود */
  var SIZES = SEED ? SEED.sizes : [
    { id: 's', label: 'کوچک', sub: '۴ تا ۶ نفر', mult: 0.78 },
    { id: 'm', label: 'متوسط', sub: '۶ تا ۸ نفر', mult: 1 },
    { id: 'l', label: 'بزرگ', sub: '۱۰ تا ۱۴ نفر', mult: 1.42 }
  ];
  var FLAVORS = SEED ? SEED.flavors : [
    { id: 'vanilla', label: 'خامه وانیل', add: 0 },
    { id: 'ganache', label: 'گاناش شکلاتی', add: 25000 },
    { id: 'pistachio', label: 'موس پسته', add: 45000 },
    { id: 'fruit', label: 'کرم میوه فصل', add: 20000 }
  ];
  var ADDONS = SEED ? SEED.addons : [
    { id: 'giftbox', label: 'جعبه کادویی مخملین', price: 45000 },
    { id: 'candles', label: 'شمع و فندک', price: 15000 },
    { id: 'card', label: 'کارت دست‌نویس', price: 12000 },
    { id: 'cooler', label: 'جعبه عایق حرارتی برای ارسال', price: 30000 }
  ];

  /* نظرهای نمایشی — همان نقشی که PRODUCTS دارد: تا وقتی بک‌اند وصل
     نشده، صفحه باید پر و واقعی به نظر برسد. */
  var REVIEWS = SEED ? SEED.reviews : [
    { name: 'مریم ک.', rating: 5, date: '۱۴۰۴/۰۶/۰۲',
      text: 'برای تولد مادرم گرفتم و واقعاً همان چیزی بود که در عکس دیدم. بوی گلابش تند نبود و همه دوست داشتند.' },
    { name: 'سینا ر.', rating: 5, date: '۱۴۰۴/۰۵/۲۸',
      text: 'خامه‌اش سبک بود و اصلاً زیادی شیرین نبود. جعبه هم سالم رسید.' },
    { name: 'نگار الف.', rating: 4, date: '۱۴۰۴/۰۵/۱۹',
      text: 'طعمش عالی بود، فقط کاش اندازه‌ی بزرگ‌تر هم داشت. تحویل سر وقت انجام شد.' },
    { name: 'امیر ح.', rating: 5, date: '۱۴۰۴/۰۵/۱۱',
      text: 'سومین باری است که سفارش می‌دهم. کیفیتش هر بار یکسان بوده و همین مهم است.' },
    { name: 'الهام ص.', rating: 4, date: '۱۴۰۴/۰۴/۳۰',
      text: 'تزیین رویش خیلی تمیز بود. برای مهمانی کوچک کاملاً کافی است.' }
  ];

  /* ══ ۲. کمکی‌ها ══ */
  var fa = function (n) { return Number(Math.round(n)).toLocaleString('fa-IR'); };

  /* fa() گرد می‌کند — برای قیمت درست است ولی امتیاز ۴٫۸ را ۵
     نشان می‌داد. خروجی این خودش جداکننده‌ی فارسی (٫) می‌گذارد. */
  var fa1 = function (n) {
    return Number(n).toLocaleString('fa-IR',
      { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  };
  var byId = function (i) { return document.getElementById(i); };

  var toastTimer;
  function toast(msg, icon) {
    var old = document.querySelector('.pd-toast');
    if (old) old.remove();
    clearTimeout(toastTimer);
    var el = document.createElement('div');
    el.className = 'pd-toast';
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
      var r = btn.getBoundingClientRect();
      root.style.setProperty('--rozet-tt-x', (r.left + r.width / 2) + 'px');
      root.style.setProperty('--rozet-tt-y', (r.top + r.height / 2) + 'px');
      btn.classList.remove('is-switching'); void btn.offsetWidth; btn.classList.add('is-switching');
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
        setTimeout(apply, 260);
      } else { apply(); }
    });
  })();

  /* ══ ۴. بارگذاری محصول ══ */
  /* روی جنگو، آدرس صفحه /product/<slug>/ است و سرور خودش می‌داند کدام
     محصول را بدهد؛ ?id= فقط برای تمپلیت ساکن مانده است. */
  var params = new URLSearchParams(location.search);
  var wantId = parseInt(params.get('id'), 10);
  var product = SEED ? SEED.product
    : (PRODUCTS.filter(function (p) { return p.id === wantId; })[0] || PRODUCTS[0]);

  /* وضعیت انتخاب‌ها */
  /* شناسه‌های پیش‌فرض از دیتابیس می‌آیند؛ 'م' و 'vanilla' فقط
     برای تمپلیت ساکن‌اند. */
  var DEF = (SEED && SEED.defaults) || {};
  var sel = {
    size: DEF.size || (SEED && SIZES[0] ? SIZES[0].id : 'm'),
    flavor: DEF.flavor || (SEED && FLAVORS[0] ? FLAVORS[0].id : 'vanilla'),
    addons: [], qty: 1, plaque: ''
  };
  var liked = false;

  function unitPrice() {
    var size = SIZES.filter(function (s) { return s.id === sel.size; })[0] || SIZES[1];
    var fl = FLAVORS.filter(function (f) { return f.id === sel.flavor; })[0] || FLAVORS[0];
    var add = sel.addons.reduce(function (s, id) {
      var a = ADDONS.filter(function (x) { return x.id === id; })[0];
      return s + (a ? a.price : 0);
    }, 0);
    /* مدل اختلاف قیمت را نگه می‌دارد نه ضریب — با ضریب، گِردکردن در
       هر صفحه فرق می‌کند و مبلغ کارت با مبلغ درگاه یکی نمی‌شود.
       شاخه‌ی mult برای تمپلیت ساکن مانده و همان نتیجه را می‌دهد. */
    var sizeAdd = (size && size.add !== undefined)
      ? size.add
      : Math.round(product.price * ((size ? size.mult : 1) - 1));
    /* در تمپلیت ساکن همیشه سه اندازه و چهار طعم بود. روی دیتابیس
       ممکن است محصولی هیچ‌کدام را نداشته باشد — آن‌وقت fl می‌شود undefined. */
    return product.price + sizeAdd + (fl ? fl.add : 0) + add;
  }
  function totalPrice() { return unitPrice() * sel.qty; }

  function stars(rating) {
    var out = '';
    for (var i = 1; i <= 5; i++) {
      var full = i <= Math.round(rating);
      out += '<svg viewBox="0 0 24 24" fill="' + (full ? 'currentColor' : 'none') +
        '" stroke="currentColor" stroke-width="1.5"><path d="M12 2.5l2.9 5.9 6.5.95-4.7 4.6 1.1 6.45L12 17.35 6.2 20.4l1.1-6.45-4.7-4.6 6.5-.95z"/></svg>';
    }
    return out;
  }

  function fillProduct() {
    /* عنوان سئوی صفحه را سرور ساخته (apps/common/seo.py)؛ جاوااسکریپت فقط
       در حالت تمپلیت ساکن که سروری نیست عنوان می‌گذارد. */
    if (!SEED) document.title = product.name + ' — رُزِت';
    byId('crumbName').textContent = product.name;
    byId('crumbCat').textContent = CATEGORIES[product.cat] || product.cat;
    byId('crumbCat').href = LIST_URL + '?cat=' + encodeURIComponent(product.cat);

    byId('pdCat').textContent = CATEGORIES[product.cat] || product.cat;
    byId('pdName').textContent = product.name;
    byId('pdEn').textContent = product.en;
    byId('pdNotes').textContent = product.notes;
    byId('mainBadge').textContent = product.badge || '';
    byId('sizeHint').textContent = '· پایه: ' + product.serves;

    byId('pdRating').innerHTML =
      '<span class="pd-rating__stars" aria-hidden="true">' + stars(product.rating) + '</span>' +
      '<span class="pd-rating__n">' + fa1(product.rating) + ' از ۵ · ' + fa(product.reviews) + ' نظر</span>';

    var stock = byId('pdStock');
    stock.textContent = product.stock ? 'موجود · آماده‌سازی ۴۸ ساعته' : 'فعلاً موجود نیست';
    stock.classList.toggle('is-out', !product.stock);

    byId('barName').textContent = product.name;

    byId('assureList').innerHTML = [
      ['M20 6 9 17l-5-5', 'پخت روز سفارش، بدون مواد آماده'],
      ['M12 2 4 6v6c0 5 3.4 8.6 8 10 4.6-1.4 8-5 8-10V6z', 'بسته‌بندی ایمن و عایق برای ارسال'],
      ['M3 12h18M12 3v18', 'امکان تغییر سفارش تا ۲۴ ساعت قبل']
    ].map(function (r) {
      return '<li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="' + r[0] + '"/></svg>' + r[1] + '</li>';
    }).join('');
  }

  /* ══ ۵. گالری ══ */
  var mainImage = byId('mainImage');

  function buildGallery() {
    var list = product.gallery && product.gallery.length ? product.gallery : [product.img];
    mainImage.src = IMG + list[0];
    mainImage.alt = product.name;
    byId('thumbs').innerHTML = list.map(function (src, i) {
      return '<button class="pd-thumb" type="button" role="tab" data-src="' + src + '" ' +
        'aria-selected="' + (i === 0) + '" aria-label="تصویر ' + fa(i + 1) + '">' +
        '<img src="' + IMG + src + '" alt="" loading="lazy"></button>';
    }).join('');
  }

  byId('thumbs').addEventListener('click', function (e) {
    var b = e.target.closest('.pd-thumb');
    if (!b) return;
    document.querySelectorAll('.pd-thumb').forEach(function (x) { x.setAttribute('aria-selected', String(x === b)); });
    /* تعویض نرم تصویر */
    mainImage.classList.add('is-swapping');
    setTimeout(function () {
      mainImage.src = IMG + b.getAttribute('data-src');
      mainImage.classList.remove('is-swapping');
    }, 180);
  });

  var lightbox = byId('lightbox');
  byId('zoomBtn').addEventListener('click', function () {
    byId('lbImage').src = mainImage.src;
    byId('lbImage').alt = product.name;
    lightbox.hidden = false;
    document.body.style.overflow = 'hidden';
    byId('lbClose').focus();
  });
  function closeLightbox() {
    lightbox.hidden = true;
    document.body.style.overflow = '';
    byId('zoomBtn').focus();
  }
  byId('lbClose').addEventListener('click', closeLightbox);
  lightbox.addEventListener('click', function (e) { if (e.target === lightbox) closeLightbox(); });

  /* ══ ۶. گزینه‌ها ══ */
  var CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>';

  function buildOptions() {
    byId('sizeChoices').innerHTML = SIZES.map(function (s) {
      return '<button class="pd-choice" type="button" data-size="' + s.id + '" aria-pressed="' + (s.id === sel.size) + '">' +
        '<span class="pd-choice__main">' + s.label + '</span>' +
        '<span class="pd-choice__sub">' + s.sub + '</span></button>';
    }).join('');

    byId('flavorChoices').innerHTML = FLAVORS.map(function (f) {
      return '<button class="pd-choice" type="button" data-flavor="' + f.id + '" aria-pressed="' + (f.id === sel.flavor) + '">' +
        '<span class="pd-choice__main">' + f.label + '</span>' +
        (f.add ? '<span class="pd-choice__sub">+ ' + fa(f.add) + ' تومان</span>' : '<span class="pd-choice__sub">بدون هزینه</span>') +
        '</button>';
    }).join('');

    byId('addonList').innerHTML = ADDONS.map(function (a) {
      return '<label class="pd-addon">' +
        '<input type="checkbox" data-addon="' + a.id + '">' +
        '<span class="pd-addon__box" aria-hidden="true">' + CHECK + '</span>' +
        '<span class="pd-addon__label">' + a.label + '</span>' +
        '<span class="pd-addon__price">+ ' + fa(a.price) + '</span></label>';
    }).join('');
  }

  function refreshPrice() {
    byId('pdPrice').textContent = fa(unitPrice());
    byId('addTotal').textContent = sel.qty > 1 ? '· ' + fa(totalPrice()) + ' تومان' : '';
    byId('barPrice').textContent = fa(totalPrice()) + ' تومان';
    byId('qtyVal').textContent = fa(sel.qty);
  }

  document.addEventListener('click', function (e) {
    var s = e.target.closest('[data-size]');
    if (s) {
      sel.size = s.getAttribute('data-size');
      document.querySelectorAll('[data-size]').forEach(function (x) {
        x.setAttribute('aria-pressed', String(x === s));
      });
      refreshPrice();
      return;
    }
    var f = e.target.closest('[data-flavor]');
    if (f) {
      sel.flavor = f.getAttribute('data-flavor');
      document.querySelectorAll('[data-flavor]').forEach(function (x) {
        x.setAttribute('aria-pressed', String(x === f));
      });
      refreshPrice();
      return;
    }
  });

  document.addEventListener('change', function (e) {
    var cb = e.target.closest('[data-addon]');
    if (!cb) return;
    var id = cb.getAttribute('data-addon');
    var i = sel.addons.indexOf(id);
    if (cb.checked && i === -1) sel.addons.push(id);
    if (!cb.checked && i > -1) sel.addons.splice(i, 1);
    refreshPrice();
  });

  /* پلاک پیام با پیش‌نمایش زنده */
  var plaqueInput = byId('plaqueInput');
  plaqueInput.addEventListener('input', function () {
    sel.plaque = plaqueInput.value.trim();
    byId('plaqueCount').textContent = fa(plaqueInput.value.length) + '/۲۴';
    var prev = byId('plaquePreview');
    byId('plaqueText').textContent = sel.plaque;
    prev.hidden = !sel.plaque;
  });

  /* تعداد */
  function setQty(v) { sel.qty = Math.max(1, Math.min(20, v)); refreshPrice(); }
  byId('qtyMinus').addEventListener('click', function () { setQty(sel.qty - 1); });
  byId('qtyPlus').addEventListener('click', function () { setQty(sel.qty + 1); });

  /* ══ ۷. پنل‌ها ══ */
  function buildPyramid() {
    byId('pyramid').innerHTML = product.pyramid.map(function (n) {
      return '<div class="pd-note">' +
        '<div class="pd-note__row"><span class="pd-note__name">' + n.n + '</span>' +
        '<span class="pd-note__lvl">' + (n.v >= 80 ? 'غالب' : n.v >= 60 ? 'متوسط' : 'ملایم') + '</span></div>' +
        '<div class="pd-note__bar"><div class="pd-note__fill" data-v="' + n.v + '"></div></div></div>';
    }).join('');

    /* نوارها وقتی وارد دید می‌شوند پر می‌شوند */
    var fills = document.querySelectorAll('.pd-note__fill');
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          en.target.style.width = en.target.getAttribute('data-v') + '%';
          io.unobserve(en.target);
        });
      }, { threshold: 0.4 });
      fills.forEach(function (f) { io.observe(f); });
    } else {
      fills.forEach(function (f) { f.style.width = f.getAttribute('data-v') + '%'; });
    }
  }

  function buildSpecs() {
    /* سرور پرش کرده (مشخصات در HTML برای خزنده)؛ فقط تمپلیت ساکن می‌سازد. */
    if (SEED && byId('specs').children.length) return;
    byId('specs').innerHTML =
      '<dt>دسته</dt><dd>' + (CATEGORIES[product.cat] || product.cat) + '</dd>' +
      '<dt>اندازه پایه</dt><dd>' + product.serves + '</dd>' +
      '<dt>آماده‌سازی</dt><dd>۴۸ ساعت پس از ثبت سفارش</dd>' +
      '<dt>حساسیت‌ها</dt><dd>' + product.allergen + '</dd>' +
      '<dt>امتیاز</dt><dd>' + fa1(product.rating) + ' از ۵</dd>';
  }

  function buildAccordion() {
    /* متن این بخش در قالب جنگوست؛ اینجا فقط برای تمپلیت ساکن. */
    if (SEED && byId('accordion').children.length) return;
    var items = [
      { t: 'مواد اولیه', b: product.ingredients },
      { t: 'نگهداری و سرو', b: product.keep },
      { t: 'ارسال و تحویل', b: 'ارسال داخل مشهد با پیک اختصاصی و جعبه عایق انجام می‌شود. برای شهرستان‌ها فقط شیرینی‌های خشک و باکس‌های کادویی ارسال می‌شوند. زمان تحویل را هنگام ثبت سفارش انتخاب می‌کنید و تا ۲۴ ساعت قبل قابل تغییر است.' },
      { t: 'سفارش اختصاصی', b: 'اگر اندازه، طعم یا طرح دیگری می‌خواهید، از صفحه کیک سفارشی درخواست بدهید. طرح نهایی را قبل از پخت برایتان می‌فرستیم تا تأیید کنید.' }
    ];
    byId('accordion').innerHTML = items.map(function (it, i) {
      return '<div class="pd-acc" data-open="' + (i === 0) + '">' +
        '<h2><button class="pd-acc__head" type="button" aria-expanded="' + (i === 0) + '">' + it.t +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>' +
        '</button></h2>' +
        '<div class="pd-acc__body"><div><p class="pd-acc__inner">' + it.b + '</p></div></div></div>';
    }).join('');
  }

  byId('accordion').addEventListener('click', function (e) {
    var head = e.target.closest('.pd-acc__head');
    if (!head) return;
    var acc = head.closest('.pd-acc');
    var open = acc.getAttribute('data-open') === 'true';
    acc.setAttribute('data-open', String(!open));
    head.setAttribute('aria-expanded', String(!open));
  });

  function buildRelated() {
    var rel = PRODUCTS.filter(function (p) { return p.id !== product.id; });
    /* هم‌دسته‌ها اول */
    rel.sort(function (a, b) { return (b.cat === product.cat) - (a.cat === product.cat); });
    byId('related').innerHTML = rel.slice(0, 4).map(function (p) {
      return '<a class="pd-rel" href="' + (p.url || 'product-details.html?id=' + p.id) + '">' +
        '<div class="pd-rel__media"><img src="' + IMG + p.img + '" alt="' + p.name + '" loading="lazy"></div>' +
        '<div class="pd-rel__body">' +
        '<p class="pd-rel__name">' + p.name + '</p>' +
        '<p class="pd-rel__price">' + fa(p.price) + ' تومان</p>' +
        '</div></a>';
    }).join('');
  }


  /* ══ ۷.۵ نظر مشتری‌ها ══ */
  /* فعلاً نمایشی است: نظر تازه فقط بالای فهرست می‌نشیند و جایی ذخیره
     نمی‌شود. وقتی بک‌اند آمد، همین دو تابع به یک fetch وصل می‌شوند. */

  var revShown = 3;                       /* چند نظر از فهرست دیده می‌شود */
  var revRating = 0;                      /* امتیازی که کاربر انتخاب کرده */
  var revList = REVIEWS.slice();

  function revStar(value, filled) {
    return '<button class="pd-star" type="button" role="radio" data-v="' + value + '"' +
      ' aria-checked="' + (filled ? 'true' : 'false') + '"' +
      ' aria-label="' + fa(value) + ' ستاره">' +
      '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.5l2.9 5.9 6.5.95-4.7 4.6 1.1 6.45L12 17.35 6.2 20.4l1.1-6.45-4.7-4.6 6.5-.95z"/></svg>' +
      '</button>';
  }

  function buildReviews() {
    /* خلاصه بالای بخش */
    byId('revAvg').textContent = fa1(product.rating);
    byId('revStars').innerHTML = stars(product.rating);
    byId('revCount').textContent = 'از ۵ · ' + fa(product.reviews) + ' نظر';

    /* ستاره‌چین فرم — از ۵ به ۱، چون ردیف در CSS برعکس شده است */
    var picker = byId('revPicker');
    var html = '';
    for (var v = 5; v >= 1; v--) html += revStar(v, false);
    picker.innerHTML = html;

    renderReviews();
  }

  /* نظرها را کاربران می‌نویسند، پس هر چه از آن‌ها می‌آید پیش از
     نشستن در innerHTML خنثی می‌شود؛ وگرنه یک نظرِ تأییدشده با تگ
     <script> برای هر بازدیدکننده اجرا می‌شد. */
  function escHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function renderReviews() {
    byId('revList').innerHTML = revList.slice(0, revShown).map(function (r) {
      return '<li class="pd-rev' + (r.fresh ? ' is-new' : '') + '">' +
        '<span class="pd-rev__avatar" aria-hidden="true">' + escHtml(r.name.charAt(0)) + '</span>' +
        '<div>' +
        '<div class="pd-rev__head">' +
        '<span class="pd-rev__name">' + escHtml(r.name) + '</span>' +
        '<span class="pd-rev__stars" aria-label="' + fa(r.rating) + ' از ۵">' + stars(r.rating) + '</span>' +
        '<span class="pd-rev__date">' + escHtml(r.date) + '</span>' +
        '</div>' +
        (r.text ? '<p class="pd-rev__text">' + escHtml(r.text) + '</p>' : '') +
        '</div></li>';
    }).join('');

    var more = byId('revMore');
    more.hidden = revShown >= revList.length;
    more.textContent = 'نظرهای بیشتر (' + fa(revList.length - revShown) + ')';
  }

  byId('revPicker').addEventListener('click', function (e) {
    var btn = e.target.closest('.pd-star');
    if (!btn) return;
    revRating = Number(btn.dataset.v);
    this.dataset.value = revRating;
    Array.prototype.forEach.call(this.children, function (b) {
      b.setAttribute('aria-checked', String(Number(b.dataset.v) === revRating));
    });
  });

  byId('revText').addEventListener('input', function () {
    byId('revLeft').textContent = fa(300 - this.value.length);
  });

  /* نظر به سرور می‌رود و «در انتظار تأیید» ذخیره می‌شود. مهمان به صفحه‌ی
     ورود فرستاده می‌شود؛ متنی که نوشته در فرم می‌ماند تا برگردد. */
  var revBusy = false;
  byId('revForm').addEventListener('submit', function (e) {
    e.preventDefault();
    if (!revRating) { toast('اول ستاره‌ها را انتخاب کنید.'); return; }
    if (revBusy) return;
    var form = this;
    var bridge = window.ROZET || {};
    revBusy = true;
    fetch(bridge.reviewApi, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': bridge.csrf || '' },
      body: JSON.stringify({ product: product.id, rating: revRating,
                             text: byId('revText').value.trim() })
    }).then(function (r) {
      return r.json().catch(function () { return { ok: false }; });
    }).then(function (res) {
      revBusy = false;
      if (res && res.ok) { addOwnReview(form); return; }
      toast((res && res.error) || 'نظر ثبت نشد؛ دوباره امتحان کنید.');
      if (res && res.auth === false && res.login) {
        setTimeout(function () { location.href = res.login; }, 900);
      }
    }).catch(function () {
      revBusy = false;
      toast('ارتباط با سرور برقرار نشد.');
    });
  });

  function addOwnReview(form) {
    /* با دو رقم، تا هم‌شکل بقیه‌ی تاریخ‌های فهرست باشد. */
    var today = new Date().toLocaleDateString('fa-IR',
      { year: 'numeric', month: '2-digit', day: '2-digit' });
    revList.unshift({
      name: 'شما', rating: revRating, date: today,
      text: byId('revText').value.trim(), fresh: true
    });
    revShown++;
    renderReviews();

    form.reset();
    revRating = 0;
    byId('revPicker').dataset.value = '';
    byId('revLeft').textContent = '۳۰۰';
    Array.prototype.forEach.call(byId('revPicker').children, function (b) {
      b.setAttribute('aria-checked', 'false');
    });
    toast('نظرتان ثبت شد. پس از تأیید نمایش داده می‌شود.');
  }

  byId('revMore').addEventListener('click', function () {
    revShown = revList.length;
    renderReviews();
  });

  /* ══ ۸. سبد خرید ══ */
  var cart = RozetCart.load();   /* سبد مشترک بین صفحه‌ها */
  var cartDrawer = document.querySelector('.cart-drawer');
  var cartOverlay = document.querySelector('.cart-overlay');

  function openCart() {
    cartDrawer.classList.add('is-open'); cartOverlay.classList.add('is-open');
    cartDrawer.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }
  function closeCart() {
    cartDrawer.classList.remove('is-open'); cartOverlay.classList.remove('is-open');
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

    countEl.textContent = fa(cart.reduce(function (s, i) { return s + i.qty; }, 0));
    countEl.classList.toggle('has-items', cart.length > 0);

    if (!cart.length) {
      if (empty) empty.style.display = 'flex';
      if (list) list.remove();
      subtotal.textContent = '۰ تومان';
      return;
    }
    if (empty) empty.style.display = 'none';
    if (!list) { list = document.createElement('div'); list.className = 'cart-items'; body.appendChild(list); }

    list.innerHTML = cart.map(function (i, idx) {
      return '<div class="cart-item">' +
        '<div class="cart-item-img"><img src="' + i.img + '" alt="' + i.name + '"></div>' +
        '<div class="cart-item-info">' +
        '<p class="cart-item-name">' + i.name + '</p>' +
        (i.meta ? '<p class="cart-item-price" style="opacity:.75">' + i.meta + '</p>' : '') +
        '<p class="cart-item-price">' + fa(i.price) + ' تومان</p>' +
        '<div class="cart-item-qty">' +
        '<button class="cart-qty-btn" type="button" data-cart="dec" data-idx="' + idx + '" aria-label="کاهش">−</button>' +
        '<span>' + fa(i.qty) + '</span>' +
        '<button class="cart-qty-btn" type="button" data-cart="inc" data-idx="' + idx + '" aria-label="افزایش">+</button>' +
        '</div></div></div>';
    }).join('');

    subtotal.textContent = fa(cart.reduce(function (s, i) { return s + i.price * i.qty; }, 0)) + ' تومان';
  }

  function addToCart() {
    if (!product.stock) return;
    var size = SIZES.filter(function (s) { return s.id === sel.size; })[0];
    var fl = FLAVORS.filter(function (f) { return f.id === sel.flavor; })[0];
    /* محصولی می‌تواند اصلاً اندازه یا طعم نداشته باشد — یک ماکارون
       فقط «پک ۶ عددی» است. بدون این بررسی، کلیک روی «افزودن به سبد»
       برای چنین محصولی TypeError می‌داد و هیچ اتفاقی نمی‌افتاد. */
    var bits = [];
    if (size) bits.push(size.label);
    if (fl) bits.push(fl.label);
    sel.addons.forEach(function (id) {
      var a = ADDONS.filter(function (x) { return x.id === id; })[0];
      if (a) bits.push(a.label);
    });
    if (sel.plaque) bits.push('پیام: «' + sel.plaque + '»');

    var meta = bits.join(' · ');
    var found = cart.filter(function (i) { return i.id === product.id && i.meta === meta; })[0];
    if (found) found.qty += sel.qty;
    else cart.push({
      id: product.id, name: product.name, meta: meta,
      price: unitPrice(), img: IMG + product.img, qty: sel.qty,
      /* گزینه‌ها با شناسه می‌روند، نه با برچسب: سرور باید بتواند
         اندازه و طعم و افزودنی را در دیتابیس پیدا کند تا قیمت را
         خودش حساب کند. meta فقط برای نمایش است. */
      size: sel.size, flavor: sel.flavor,
      addons: sel.addons.slice(), plaque: sel.plaque || ''
    });

    renderCart();
    toast('«' + product.name + '» به سبد خرید اضافه شد');
  }

  function flashAdd(btn) {
    var label = byId('addLabel');
    var orig = label.textContent;
    label.textContent = 'اضافه شد ✓';
    btn.classList.add('is-added');
    setTimeout(function () { label.textContent = orig; btn.classList.remove('is-added'); }, 1500);
  }

  byId('addBtn').addEventListener('click', function () { addToCart(); flashAdd(this); });
  byId('barAdd').addEventListener('click', function () { addToCart(); });


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

  /* حالت اولیه از دیتابیس؛ بدون این، محصولی که کاربر قبلاً نشان کرده
     با قلب خالی باز می‌شد و یک کلیک آن را پاک می‌کرد. */
  liked = !!(SEED && SEED.favorite);
  (function () {
    var btn = byId('wishBtn');
    btn.setAttribute('aria-pressed', String(liked));
  })();

  byId('wishBtn').addEventListener('click', function () {
    liked = !liked;
    this.setAttribute('aria-pressed', String(liked));
    this.classList.add('pop');
    var self = this;
    var was = liked;
    setTimeout(function () { self.classList.remove('pop'); }, 520);
    saveFavorite(product.id, was, function () {
      liked = !was;
      self.setAttribute('aria-pressed', String(liked));
      toast('برای ذخیره‌ی علاقه‌مندی‌ها وارد شوید.', '');
    });
    toast(liked ? 'به علاقه‌مندی‌ها اضافه شد' : 'از علاقه‌مندی‌ها حذف شد',
      '<svg width="17" height="17" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.3l-1.4-1.3C5.4 15.4 2 12.3 2 8.5 2 5.4 4.4 3 7.5 3c1.7 0 3.4.8 4.5 2.1C13.1 3.8 14.8 3 16.5 3 19.6 3 22 5.4 22 8.5c0 3.8-3.4 6.9-8.6 11.5L12 21.3z"/></svg>');
  });

  document.addEventListener('click', function (e) {
    if (e.target.closest('.cart-btn')) { openCart(); return; }
    if (e.target.closest('.cart-drawer-close') || e.target.closest('.cart-overlay')) { closeCart(); return; }
    var cq = e.target.closest('[data-cart]');
    if (cq) {
      var idx = +cq.getAttribute('data-idx');
      var item = cart[idx];
      if (!item) return;
      if (cq.getAttribute('data-cart') === 'inc') item.qty++;
      else { item.qty--; if (item.qty <= 0) cart.splice(idx, 1); }
      renderCart();
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (!lightbox.hidden) closeLightbox();
    else if (cartDrawer.classList.contains('is-open')) closeCart();
  });

  /* نوار چسبان موبایل — وقتی دکمه اصلی از دید خارج شد ظاهر می‌شود */
  var addBtn = byId('addBtn'), bar = byId('mobileBar');
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      var visible = entries[0].isIntersecting;
      bar.classList.toggle('is-visible', !visible);
      bar.setAttribute('aria-hidden', String(visible));
    }, { threshold: 0 }).observe(addBtn);
  }

  /* ══ ۹. ذرات شکر معلق ══ */
  (function motes() {
    var host = document.querySelector('.pd-motes');
    if (!host) return;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var N = 14;
    var html = '';
    for (var i = 0; i < N; i++) {
      var left = Math.round(Math.random() * 92) + 4;      /* درصد */
      var top = Math.round(Math.random() * 70) + 25;
      var dur = (7 + Math.random() * 7).toFixed(1);        /* ثانیه */
      var delay = (Math.random() * 9).toFixed(1);
      var drift = Math.round((Math.random() * 46) - 23);   /* پیکسل */
      var size = (3 + Math.random() * 2.5).toFixed(1);
      html += '<span class="pd-mote" style="' +
        'left:' + left + '%; top:' + top + '%;' +
        'width:' + size + 'px; height:' + size + 'px;' +
        '--mx:' + drift + 'px;' +
        'animation-duration:' + dur + 's; animation-delay:-' + delay + 's;"></span>';
    }
    host.innerHTML = html;
  })();

  /* ══ راه‌اندازی ══ */
  fillProduct();
  buildGallery();
  buildOptions();
  buildPyramid();
  buildSpecs();
  buildAccordion();
  buildReviews();
  buildRelated();
  refreshPrice();
  renderCart();

  window.rozetDetails = { product: product, sel: sel, unitPrice: unitPrice, totalPrice: totalPrice };
})();
