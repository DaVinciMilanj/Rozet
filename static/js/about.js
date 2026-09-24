/* ═══════════════════════════════════════════════════════════════════════════
   رُزِت — موتور صفحه درباره ما
   ───────────────────────────────────────────────────────────────────────────
   ماژول ۱ : سوییچ تم
   ماژول ۲ : ظهور کلمه‌به‌کلمه تیتر
   ماژول ۳ : ذرات شکر
   ماژول ۴ : تصویر خودکشیده SVG
   ماژول ۵ : شمارنده‌های بالارونده
   ماژول ۶ : خط زمانی پیش‌رونده
   ماژول ۷ : پارالاکس تصویر مغازه
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var byId = function (i) { return document.getElementById(i); };
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

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
      var r = btn.getBoundingClientRect();
      root.style.setProperty('--rozet-tt-x', (r.left + r.width / 2) + 'px');
      root.style.setProperty('--rozet-tt-y', (r.top + r.height / 2) + 'px');
      btn.classList.remove('is-switching'); void btn.offsetWidth; btn.classList.add('is-switching');
      setTimeout(function () { btn.classList.remove('is-switching'); }, 700);
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
        setTimeout(apply, 260);   /* شبکه ایمنی اگر ترنزیشن اجرا نشد */
      } else { apply(); }
    });
  })();

  /* ══ ۲. ظهور کلمه‌به‌کلمه ══
     هر کلمه در یک span بسته می‌شود تا با تأخیر پلکانی بالا بیاید.
     فاصله‌ها بیرون از span می‌مانند تا شکست خط طبیعی حفظ شود. */
  (function splitWords() {
    var el = document.querySelector('[data-split]');
    if (!el) return;
    var words = el.textContent.trim().split(/\s+/);
    el.textContent = '';
    words.forEach(function (w, i) {
      var wrap = document.createElement('span');
      wrap.className = 'ab-word';
      var inner = document.createElement('span');
      inner.textContent = w;
      inner.style.animationDelay = (0.08 + i * 0.07).toFixed(2) + 's';
      wrap.appendChild(inner);
      el.appendChild(wrap);
      if (i < words.length - 1) el.appendChild(document.createTextNode(' '));
    });
  })();

  /* ══ ۲.۵ نشان خانه (لوگو) ══
     فایل لوگو را در پوشه assets/logo بگذارید. لازم نیست نام دقیقی داشته باشد؛
     این ماژول چند نام و پسوند رایج را امتحان می‌کند و اولین فایلی را که واقعاً
     باز شود به کار می‌برد. تا وقتی هیچ فایلی پیدا نشود کادر پنهان می‌ماند تا
     بالای صفحه حفره‌ی خالی دیده نشود. */
  (function crestLogo() {
    var crest = document.querySelector('.ab-crest');
    var logo = document.querySelector('.ab-crest__logo');
    if (!crest || !logo) return;

    var EXT = ['webp', 'png', 'svg', 'jpg', 'jpeg'];
    var token = 0;   /* هر بار تعویض تم، جست‌وجوی قبلی باطل می‌شود */

    function candidates(theme) {
      var stems = ['rozet-mark-' + theme, 'logo-' + theme, 'rozet-' + theme,
                   'rozet-mark', 'logo', 'rozet'];
      var out = [];
      stems.forEach(function (s) {
        EXT.forEach(function (e) { out.push('../assets/logo/' + s + '.' + e); });
      });
      return out;
    }

    /* یکی‌یکی امتحان می‌کند تا اولین تصویری که لود شود پیدا شود */
    function resolve(list, mine, i) {
      i = i || 0;
      if (mine !== token) return;                 /* تم عوض شده — رها کن */
      if (i >= list.length) {
        crest.hidden = true;
        if (window.console) console.info('[رُزِت] فایل لوگو پیدا نشد. ' +
          'یک تصویر با نام rozet-mark-light یا rozet-mark-dark در assets/logo بگذارید.');
        return;
      }
      var probe = new Image();
      probe.onload = function () {
        if (mine !== token) return;
        logo.style.backgroundImage = 'url("' + list[i] + '")';
        crest.hidden = false;
      };
      probe.onerror = function () { resolve(list, mine, i + 1); };
      probe.src = list[i];
    }

    function check() {
      token++;
      var theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';

      /* روی جنگو نشانی دقیق فایل را داریم، پس حدس‌زدن لازم نیست.
         جست‌وجوی پایین فقط برای تمپلیت ساکن می‌ماند. */
      var crestUrls = (window.ROZET || {}).crest;
      if (crestUrls && crestUrls[theme]) {
        logo.style.backgroundImage = 'url("' + crestUrls[theme] + '")';
        crest.hidden = false;
        return;
      }

      resolve(candidates(theme), token);
    }

    check();
    /* بعد از تعویض تم، نسخه‌ی متناسب همان تم را دوباره پیدا کن */
    new MutationObserver(check).observe(document.documentElement,
      { attributes: true, attributeFilter: ['data-theme'] });
  })();

  /* ══ ۳. ذرات شکر ══ */
  (function motes() {
    var host = document.querySelector('.ab-hero__motes');
    if (!host || reduced) return;
    var html = '';
    for (var i = 0; i < 16; i++) {
      html += '<span class="ab-mote" style="' +
        'left:' + (Math.round(Math.random() * 94) + 3) + '%;' +
        'top:' + (Math.round(Math.random() * 70) + 25) + '%;' +
        'width:' + (3 + Math.random() * 2.6).toFixed(1) + 'px;' +
        'height:' + (3 + Math.random() * 2.6).toFixed(1) + 'px;' +
        '--mx:' + Math.round(Math.random() * 52 - 26) + 'px;' +
        'animation-duration:' + (8 + Math.random() * 8).toFixed(1) + 's;' +
        'animation-delay:-' + (Math.random() * 10).toFixed(1) + 's;"></span>';
    }
    host.innerHTML = html;
  })();

  /* ══ ۴. تصویر خودکشیده ══
     طول واقعی هر مسیر خوانده می‌شود تا dasharray دقیق باشد؛ حدس‌زدن عدد
     باعث می‌شود بعضی خط‌ها ناقص یا با تأخیر کشیده شوند. */
  (function selfDraw() {
    var svg = document.querySelector('.ab-draw');
    if (!svg) return;
    var paths = svg.querySelectorAll('.ab-draw__p');
    paths.forEach(function (p, i) {
      var len = Math.ceil(p.getTotalLength());
      p.style.setProperty('--len', len);
      p.style.setProperty('--d', (i * 0.18).toFixed(2) + 's');
    });
    if (reduced) { svg.classList.add('is-drawing'); return; }
    if (!('IntersectionObserver' in window)) { svg.classList.add('is-drawing'); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        svg.classList.add('is-drawing');
        io.unobserve(en.target);
      });
    }, { threshold: 0.35 });
    io.observe(svg);
  })();

  /* ══ ۵. معیارهای خانه — خط طلایی پیش‌رونده ══ */
  var list = byId('standards');
  var items = list ? list.querySelectorAll('.ab-item') : [];

  function updateStandards() {
    if (!list) return;
    var r = list.getBoundingClientRect();
    var mid = window.innerHeight * 0.62;
    /* چقدر از فهرست از خط میانی صفحه رد شده است */
    var passed = mid - r.top;
    var pct = Math.max(0, Math.min(100, (passed / r.height) * 100));
    list.style.setProperty('--progress', pct + '%');

    items.forEach(function (li) {
      li.classList.toggle('is-on', li.getBoundingClientRect().top < mid);
    });
  }

  /* ══ ۶. پارالاکس تصویر کافه ══ */
  var shop = byId('shopImage');

  function updateParallax() {
    if (!shop || reduced) return;
    var r = shop.getBoundingClientRect();
    if (r.bottom < 0 || r.top > window.innerHeight) return;
    var centre = r.top + r.height / 2 - window.innerHeight / 2;
    shop.style.setProperty('--par', (centre * -0.05).toFixed(1) + 'px');
  }

  var ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      updateStandards();
      updateParallax();
      ticking = false;
    });
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
  updateStandards();
  updateParallax();

  /* برای تست دستی — اجرای مستقیم بدون وابستگی به rAF */
  window.rozetAbout = { updateStandards: updateStandards, updateParallax: updateParallax };
})();
