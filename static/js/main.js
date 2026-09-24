/* ═══════════════════════════════════════════════════════════════════════════════════════
   موتور جاوااسکریپت اصلی وب‌سایت رُزِت (ROZET Main JavaScript Engine)
   معماری ماژولار، انیمیشن‌های سینمایی ۶۰ فریم و استانداردهای Awwwards
   ═══════════════════════════════════════════════════════════════════════════════════════
   فهرست ماژول‌های این اسکریپت:
   ماژول ۱: بارگذاری اولیه و آماده‌سازی صفحه (Page Initialization)
   ماژول ۲: موتور اسکرول فریم به فریم ویدیوی ۲۵۰ عکسی روی Canvas (Canvas Scrub Engine)
            - پیش‌بارگذاری هوشمند و پلکانی فریم‌ها (Progressive Preloader)
            - الگوریتم پیدا کردن نزدیک‌ترین فریم لود شده (Frame Fallback)
            - رندر Canvas با کیفیت رتینا و پوشش بهینه (Cover Fitting & Retina)
            - ترنزیشن و هماهنگی متون سکشن‌های ۱ و ۲ با اسکرول
            - حلقه فیزیک نرم‌کننده حرکات با فرمول لِرپ (Lerp Physics Loop)
   ماژول ۳: تشخیص موقعیت هدر و تغییر وضعیت شیشه‌ای (Header Adaptive Glass Theme)
   ماژول ۴: نشانگر ماوس اختصاصی لوکس (Custom Luxury Cursor with Lerp Follow)
   ماژول ۵: دکمه‌های مگنتی با کشش ملایم به سمت ماوس (Magnetic Buttons)
   ماژول ۶: سیستم اعلان‌های شناور گوشه صفحه (Toast Notification Engine)
   ماژول ۷: هسته تعاملات سبد خرید و علاقه‌مندی‌ها (Cart & Wishlist Engine)
            - افزودن مستقیم اثر با کلیک روی رزرو و تغییر متن دکمه به «رزرو شد ✓»
            - مدیریت علاقه‌مندی‌ها با انیمیشن جهش قلب (Wishlist Pop)
            - باز و بسته شدن سایدبار سبد خرید، شمارنده و محاسبه جمع کل
   ماژول ۸: مگامنوی آبشاری فروشگاه و ناوبری موبایل (Shop Dropdown & Mobile Menu)
   ماژول ۹: ناظر ورود المان‌ها به صفحه و افکت پارالاکس (Scroll Reveals & Parallax)
   ماژول ۱۰: اسکرول نرم برای لینک‌های داخلی و انکرها (Smooth Anchor Scroll)
   ═══════════════════════════════════════════════════════════════════════════════════════ */



(function () {
  'use strict';

  var body = document.body;

  /* ─── Page Load ─── */
  window.addEventListener('load', function () {
    body.classList.add('loaded');
    updateCartCount();
  });

  /* ════════════════════════════════════════════════════════════════
     1. CANVAS 250-FRAME VIDEO SCRUB ENGINE
     Section 1 (Hero) ───▶ Section 2 (Brand Intro) ───▶ Page Flow
     ════════════════════════════════════════════════════════════════ */
  var FRAME_COUNT  = 250;
  /* مسیر از قالب می‌آید. {% static %} داخل فایل JS اجرا نمی‌شود،
     پس مسیر نسبی زیر روی جنگو به /assets/... می‌رسید و ۲۵۰ فریم ۴۰۴
     می‌دادند — هیرو سیاه می‌ماند. fallback برای این است که
     تمپلیت ساکن هم‌چنان مستقل کار کند. */
  var FRAME_PATH   = (window.ROZET && window.ROZET.framePath) || 'assets/frames/frame_';
  var FRAME_EXT    = '.webp';

  var container    = document.getElementById('scroll-frame-container');
  var canvas       = document.getElementById('scroll-frame-canvas');
  var ctx          = canvas ? canvas.getContext('2d', { alpha: false }) : null;
  var heroContent  = document.querySelector('.hero-content');
  var introOverlay = document.querySelector('.brand-intro-overlay');
  var overlayDark  = document.querySelector('.hero-overlay-dark');
  var scrollHint   = document.querySelector('.scroll-hint');
  var progressBar  = document.querySelector('.scroll-frame-progress');

  var frames       = new Array(FRAME_COUNT);
  var loadedFrames = {};
  var currentFrame = -1;
  var targetProgress = 0;
  var currentProgress = 0;
  var isScrubbing  = false;
  var dpr          = Math.min(window.devicePixelRatio || 1, 2);

  function padZero(n) {
    var s = String(n);
    while (s.length < 4) s = '0' + s;
    return s;
  }

  /* تابع بارگذاری تک‌فریم با ذخیره در حافظه کش (Cache) */
  function loadFrame(index, onComplete) {
    if (frames[index]) return;
    var img = new Image();
    img.src = FRAME_PATH + padZero(index + 1) + FRAME_EXT;
    img.onload = function () {
      frames[index] = img;
      loadedFrames[index] = true;
      if (onComplete) onComplete(index);
      /* If this is the active frame or nearest, redraw */
      if (currentFrame === index || currentFrame === -1) {
        drawFrame(index);
      }
    };
    img.onerror = function () {
      frames[index] = null;
    };
  }

  /* ── بارگذاری فریم‌ها: کم‌هزینه برای کسی که رد می‌شود، کامل برای کسی که می‌ماند ──
     drawFrame از getBestFrame استفاده می‌کند و اگر فریم دقیق نرسیده باشد نزدیک‌ترین
     را می‌کشد. پس لازم نیست هر ۲۵۰ فریم از اول دانلود شوند؛ می‌شود اول یک شبکه‌ی
     درشت گرفت و بقیه را فقط جایی که کاربر واقعاً هست پر کرد.

     بیشتر بازدیدکننده‌ها در چند ثانیه از هرو رد می‌شوند و هیچ‌وقت همه‌ی فریم‌ها را
     نمی‌بینند؛ دانلود کامل برای آن‌ها فقط هدررفت است. */
  var KEY_STEP  = 8;     /* شبکه‌ی درشت اولیه ≈ ۳۲ فریم */
  var NEAR_SPAN = 22;    /* شعاع پرکردن اطراف فریم فعلی */
  var fillTimer = null;
  var fillDone  = false;

  /* روی اینترنت کم‌سرعت یا حالت صرفه‌جویی داده، به همان شبکه‌ی درشت بسنده کن */
  function lowData() {
    var c = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (!c) return false;
    if (c.saveData) return true;
    return /(^|-)2g$/.test(c.effectiveType || '');
  }

  function loadKeyframes() {
    for (var i = KEY_STEP; i < FRAME_COUNT; i += KEY_STEP) loadFrame(i);
    loadFrame(FRAME_COUNT - 1);
  }

  /* فریم‌های نزدیک به جایی که کاربر هست، از نزدیک به دور */
  function fillAround(center) {
    if (fillDone || lowData()) return;
    var queued = 0;
    for (var d = 1; d <= NEAR_SPAN && queued < 10; d++) {
      var a = center - d, b = center + d;
      if (a >= 0 && !frames[a]) { loadFrame(a); queued++; }
      if (b < FRAME_COUNT && !frames[b]) { loadFrame(b); queued++; }
    }
    if (!queued) {
      /* اطراف پر شده؛ اگر کاربر مانده، بی‌سروصدا بقیه را هم بیاور */
      for (var k = 0; k < FRAME_COUNT; k++) {
        if (!frames[k]) { loadFrame(k); return; }
      }
      fillDone = true;
    }
  }

  function scheduleFill(center) {
    if (fillTimer || fillDone || lowData()) return;
    fillTimer = setTimeout(function () {
      fillTimer = null;
      fillAround(center);
    }, 90);
  }

  function initPreloader() {
    /* گام ۱ — فریم اول، بلافاصله: همین است که کاربر اول می‌بیند */
    loadFrame(0, function () {
      drawFrame(0);
      /* گام ۲ — شبکه‌ی درشت: از همین‌جا اسکراب روان است */
      loadKeyframes();
    });
    /* گام ۳ — بقیه، فقط وقتی کاربر واقعاً در هرو اسکرول می‌کند (در scrubLoop) */
  }

  /* الگوریتم یافتن بهترین فریم در دسترس در صورت بارگذاری نشدن فریم دقیق */
  function getBestFrame(idx) {
    if (frames[idx] && loadedFrames[idx] && frames[idx].naturalWidth > 0) {
      return frames[idx];
    }
    /* Search outward for nearest loaded frame */
    for (var offset = 1; offset < FRAME_COUNT; offset++) {
      var prev = idx - offset;
      if (prev >= 0 && frames[prev] && loadedFrames[prev] && frames[prev].naturalWidth > 0) {
        return frames[prev];
      }
      var next = idx + offset;
      if (next < FRAME_COUNT && frames[next] && loadedFrames[next] && frames[next].naturalWidth > 0) {
        return frames[next];
      }
    }
    return null;
  }

  /* ترسیم فریم روی Canvas با نسبت اندازه استاندارد Cover (پوشش کامل بدون دفرمه شدن) */
  function drawFrame(idx) {
    if (!ctx || !canvas) return;
    var img = getBestFrame(idx);
    if (!img) return;

    currentFrame = idx;

    var cw = canvas.width;
    var ch = canvas.height;
    var iw = img.naturalWidth;
    var ih = img.naturalHeight;
    var scale = Math.max(cw / iw, ch / ih);
    var dw = iw * scale;
    var dh = ih * scale;
    var dx = (cw - dw) / 2;
    var dy = (ch - dh) / 2;

    ctx.drawImage(img, dx, dy, dw, dh);
  }

  /* تنظیم اندازه Canvas متناسب با نمایشگر و پشتیبانی از تراکم پیکسل بالا (Retina) */
  function resizeCanvas() {
    if (!canvas) return;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width  = window.innerWidth * dpr;
    canvas.height = window.innerHeight * dpr;
    if (currentFrame >= 0) {
      drawFrame(currentFrame);
    }
  }

  /* محاسبه درصد اسکرول و انتقال نرم متون و لایه‌های سکشن ۱ و سکشن ۲ */
  function updateOverlays(progress) {
    /* 1. Section 1 (Hero): 0% to 35% */
    if (heroContent) {
      if (progress < 0.32) {
        var alpha = 1 - (progress / 0.32);
        heroContent.style.opacity = Math.max(0, alpha);
        heroContent.style.transform = 'translateY(' + (-progress * 60) + 'px)';
        heroContent.style.pointerEvents = 'auto';
      } else {
        heroContent.style.opacity = 0;
        heroContent.style.pointerEvents = 'none';
      }
    }

    /* 2. Scroll hint */
    if (scrollHint) {
      scrollHint.style.opacity = Math.max(0, 1 - progress * 9);
    }

    /* 3. Section 2 (Brand Intro): 38% to 92% */
    if (introOverlay) {
      if (progress >= 0.38 && progress < 0.90) {
        var introAlpha = 1;
        if (progress < 0.48) {
          introAlpha = (progress - 0.38) / 0.10;
        } else if (progress > 0.80) {
          introAlpha = Math.max(0, 1 - (progress - 0.80) / 0.10);
        }
        introOverlay.style.opacity = introAlpha;
        introOverlay.style.pointerEvents = introAlpha > 0.4 ? 'auto' : 'none';
        introOverlay.classList.add('is-visible');
      } else {
        introOverlay.style.opacity = 0;
        introOverlay.style.pointerEvents = 'none';
        introOverlay.classList.remove('is-visible');
      }
    }

    /* 4. Atmospheric darkening for text legibility in second half */
    if (overlayDark) {
      var darkAlpha = 0;
      if (progress > 0.25) {
        darkAlpha = Math.min(0.68, (progress - 0.25) * 0.95);
      }
      overlayDark.style.backgroundColor = 'rgba(10, 5, 2, ' + darkAlpha + ')';
    }

    /* 5. Top progress line */
    if (progressBar) {
      var inScrub = progress > 0.005 && progress < 0.995;
      progressBar.classList.toggle('is-visible', inScrub);
      progressBar.style.width = (progress * 100) + '%';
    }
  }

  /* حلقه محاسباتی فیزیک و نرم‌سازی اسکرول با فرمول لِرپ (Linear Interpolation) */
  function renderScrubLoop() {
    var diff = targetProgress - currentProgress;
    if (Math.abs(diff) > 0.0004) {
      currentProgress += diff * 0.14; /* Luxury fluid easing */
    } else {
      currentProgress = targetProgress;
    }

    var frameIdx = Math.min(FRAME_COUNT - 1, Math.max(0, Math.floor(currentProgress * (FRAME_COUNT - 1))));
    scheduleFill(frameIdx);
    if (frameIdx !== currentFrame) {
      drawFrame(frameIdx);
    }
    updateOverlays(currentProgress);

    if (Math.abs(diff) > 0.0004) {
      requestAnimationFrame(renderScrubLoop);
      isScrubbing = true;
    } else {
      isScrubbing = false;
    }
  }

  function onScroll() {
    if (!container) return;
    var rect  = container.getBoundingClientRect();
    var total = container.offsetHeight - window.innerHeight;
    var scrollY = Math.max(0, -rect.top);

    targetProgress = total > 0 ? Math.min(1, Math.max(0, scrollY / total)) : 0;

    /* پرکردن فریم‌ها به خودِ رویداد اسکرول هم وصل است، نه فقط به حلقه‌ی rAF:
       اگر مرورگر rAF را کند کند (تب پس‌زمینه، باتری کم، حرکت کم)، باز هم
       فریم‌های اطراف جایی که کاربر هست بارگذاری می‌شوند. */
    scheduleFill(Math.min(FRAME_COUNT - 1, Math.max(0,
      Math.round(targetProgress * (FRAME_COUNT - 1)))));

    if (!isScrubbing) {
      isScrubbing = true;
      requestAnimationFrame(renderScrubLoop);
    }

    /* Header mode check */
    updateHeaderMode(rect.bottom);
  }

  /* ════════════════════════════════════════════════════════════════
     2. DYNAMIC LUXURY HEADER (Dark Glass over Video, Light Glass over Content)
     ════════════════════════════════════════════════════════════════ */
  var header = document.querySelector('.site-header');

  function updateHeaderMode(containerBottom) {
    if (!header) return;
    var scrollY = window.pageYOffset;

    /* Inside the video container */
    if (containerBottom > 80) {
      header.classList.remove('scrolled-light');
      if (scrollY > 50) {
        header.classList.add('scrolled-dark');
      } else {
        header.classList.remove('scrolled-dark');
      }
    } else {
      /* Scrolled past the video container into cream sections */
      header.classList.remove('scrolled-dark');
      header.classList.add('scrolled-light');
    }
  }

  window.addEventListener('scroll', onScroll, { passive: true });

  if (container && canvas) {
    resizeCanvas();
    initPreloader();
    window.addEventListener('resize', function () {
      resizeCanvas();
      if (currentFrame >= 0) drawFrame(currentFrame);
    });
    onScroll();
  }

  /* ════════════════════════════════════════════════════════════════
   ماژول ۴: نشانگر ماوس اختصاصی لوکس (Custom Luxury Cursor)
   دارای نقطه مرکزی و حلقه شناور با افکت لِرپ و بزرگ شدن در هاور المان‌ها WITH SPRING PHYSICS
     ════════════════════════════════════════════════════════════════ */
  var cursor = document.querySelector('.custom-cursor');
  if (cursor) {
    var mouseX = window.innerWidth / 2;
    var mouseY = window.innerHeight / 2;
    var ringX  = mouseX;
    var ringY  = mouseY;
    var cursorActive = false;

    window.addEventListener('mousemove', function (e) {
      mouseX = e.clientX;
      mouseY = e.clientY;
      if (!cursorActive) {
        cursorActive = true;
        cursor.classList.remove('is-hidden');
      }
    });

    document.addEventListener('mouseleave', function () {
      cursor.classList.add('is-hidden');
      cursorActive = false;
    });

    function updateCursor() {
      ringX += (mouseX - ringX) * 0.18;
      ringY += (mouseY - ringY) * 0.18;
      cursor.style.transform = 'translate(' + mouseX + 'px, ' + mouseY + 'px)';
      var ring = cursor.querySelector('.cursor-ring');
      if (ring) {
        var dx = ringX - mouseX;
        var dy = ringY - mouseY;
        ring.style.transform = 'translate(calc(-50% + ' + dx + 'px), calc(-50% + ' + dy + 'px))';
      }
      requestAnimationFrame(updateCursor);
    }
    requestAnimationFrame(updateCursor);

    /* Hover detection */
    var hoverTargets = 'a, button, .product-card, .shop-trigger, .sweet-item, input';
    document.addEventListener('mouseover', function (e) {
      if (e.target.closest(hoverTargets)) {
        cursor.classList.add('is-hover');
      }
    });
    document.addEventListener('mouseout', function (e) {
      if (e.target.closest(hoverTargets)) {
        cursor.classList.remove('is-hover');
      }
    });
  }

      /* ════════════════════════════════════════════════════════════════
     4. QUIET LUXURY CARD INTERACTIONS (Pure, Dignified, Uncluttered)
     ════════════════════════════════════════════════════════════════ */
  var cards = document.querySelectorAll('.product-card');

  cards.forEach(function (card) {
    /* Smooth, dignified click interaction */
    card.addEventListener('click', function (e) {
      /* If clicked on wishlist, wishlist handler takes care of it */
      if (e.target.closest('.product-card__wishlist')) return;

      var nameEl  = card.querySelector('.product-card__name a');
      var priceEl = card.querySelector('.product-card__price');
      var imgEl   = card.querySelector('.product-card__image');

      var pName  = nameEl ? nameEl.textContent.trim() : 'کیک رُزِت';
      var pPrice = priceEl ? parseInt(priceEl.dataset.price || priceEl.textContent.replace(/[^0-9]/g, ''), 10) : 280000;
      var pImg   = imgEl ? imgEl.getAttribute('src') : '';

      /* If clicked on quick action button */
      var quickBtn = e.target.closest('.product-card__quick-btn');
      if (quickBtn) {
        /* در نسخه‌ی جنگو این دکمه یک لینک واقعی به صفحه‌ی جزئیات
           است؛ بگذار مرورگر ببرد. در تمپلیت ساکن <button> بود و
           کارش افزودن به سبد بود — همان رفتار حفظ می‌شود. */
        if (quickBtn.tagName === 'A' && quickBtn.getAttribute('href')) return;
        e.preventDefault();
        e.stopPropagation();
        addToCart(pName, pPrice, pImg, card && card.getAttribute('data-product'));
        showToast('«' + pName + '» به سبد خرید اضافه شد', '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>');
        return;
      }
    });
  });

  /* Magnetic subtle pull on luxury buttons */
  var magneticBtns = document.querySelectorAll('.btn-magnetic');
  /* دو نکته که قبلاً دکمه را از صفحه بیرون می‌برد و صفحه را افقی می‌کرد:
     ۱. getBoundingClientRect ترنسفورمِ فعلی را هم در خودش دارد، پس هر حرکت
        روی حرکت قبلی سوار می‌شد و دکمه پله‌پله دور می‌شد.
     ۲. هیچ سقفی نداشت. حالا از مرکزِ بدونِ ترنسفورم حساب می‌شود و کشش
        حداکثر ۱۰ پیکسل است. */
  var MAG_PULL = 0.22, MAG_MAX = 10;
  function magClamp(v) { return Math.max(-MAG_MAX, Math.min(MAG_MAX, v)); }

  magneticBtns.forEach(function (btn) {
    btn.addEventListener('mousemove', function (e) {
      var rect = btn.getBoundingClientRect();
      var dx = 0, dy = 0;
      try {
        var m = new DOMMatrixReadOnly(getComputedStyle(btn).transform);
        dx = m.m41; dy = m.m42;
      } catch (err) { /* مرورگر قدیمی: بدون تصحیح هم کار می‌کند */ }
      var cx = rect.left - dx + rect.width / 2;
      var cy = rect.top - dy + rect.height / 2;
      btn.style.transform = 'translate(' +
        magClamp((e.clientX - cx) * MAG_PULL).toFixed(1) + 'px, ' +
        magClamp((e.clientY - cy) * MAG_PULL).toFixed(1) + 'px)';
    });
    btn.addEventListener('mouseleave', function () {
      btn.style.transform = '';
    });
  });

  /* ════════════════════════════════════════════════════════════════
     5. TOAST NOTIFICATION ENGINE
     ════════════════════════════════════════════════════════════════ */
  var activeToast = null;
  function showToast(message, iconSvg) {
    if (activeToast) {
      activeToast.remove();
      activeToast = null;
    }
    var toast = document.createElement('div');
    toast.className = 'rozet-toast';
    toast.innerHTML = '<span class="rozet-toast-icon">' + (iconSvg || '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>') + '</span>'
      + '<span class="rozet-toast-text">' + message + '</span>';
    document.body.appendChild(toast);
    activeToast = toast;

    setTimeout(function () {
      if (toast.parentNode) {
        toast.classList.add('is-hiding');
        setTimeout(function () {
          if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 350);
      }
    }, 2800);
  }

  /* ════════════════════════════════════════════════════════════════
   ماژول ۷: هسته تعاملات سبد خرید و لیست علاقه‌مندی‌ها
   (Cart & Wishlist Interaction Engine)
     ════════════════════════════════════════════════════════════════ */

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

  /* ۱۶ پیکسل در هر دو حالت — تمپلیت قلب خالی را ۱۶ می‌کشید و این تابع
     پُرش را ۱۸، پس آیکن با هر کلیک یک پرش اندازه داشت. */
  var HEART_ON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>';
  var HEART_OFF = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>';

  function paintHeart(btn, on) {
    btn.classList.toggle('is-liked', on);
    btn.setAttribute('aria-pressed', String(on));
    btn.innerHTML = on ? HEART_ON : HEART_OFF;
  }

  document.addEventListener('click', function (e) {
    /* Wishlist Click */
    var wishBtn = e.target.closest('.product-card__wishlist');
    if (wishBtn) {
      e.preventDefault();
      e.stopPropagation();
      wishBtn.classList.add('pop');
      setTimeout(function () { wishBtn.classList.remove('pop'); }, 550);

      var isLiked = !wishBtn.classList.contains('is-liked');
      var card = wishBtn.closest('.product-card');
      var productName = card ? (card.querySelector('.product-card__name a') || {}).textContent || 'محصول' : 'محصول';

      paintHeart(wishBtn, isLiked);
      showToast(isLiked ? '«' + productName + '» به علاقه‌مندی‌ها افزوده شد' : 'از علاقه‌مندی‌ها حذف شد');

      var pid = card && card.getAttribute('data-product');
      if (pid) {
        saveFavorite(+pid, isLiked, function () {
          paintHeart(wishBtn, !isLiked);
          showToast('برای ذخیره‌ی علاقه‌مندی‌ها وارد شوید.');
        });
      }
      return;
    }

    /* Click on "رزرو اثر" or Order button */
    var orderBtn = e.target.closest('.product-card__order-btn, .product-card__order-link');
    if (orderBtn) {
      e.preventDefault();
      var pCard = orderBtn.closest('.product-card');
      if (pCard) {
        var nameEl  = pCard.querySelector('.product-card__name a') || pCard.querySelector('.product-card__name');
        var priceEl = pCard.querySelector('.product-card__price');
        var imgEl   = pCard.querySelector('.product-card__image');
        var pName   = nameEl ? nameEl.textContent.trim() : 'کیک رُزِت';
        var pPriceAttr = priceEl ? priceEl.dataset.price : null;
        var pPrice  = pPriceAttr ? parseInt(pPriceAttr, 10) : (parseInt((priceEl ? priceEl.textContent.replace(/[^0-9]/g, '') : '380000'), 10) || 380000);
        var pImg    = imgEl ? imgEl.getAttribute('src') : '';

        addToCart(pName, pPrice, pImg, pCard.getAttribute('data-product'));
        showToast('«' + pName + '» به سبد خرید اضافه شد', '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>');

        var origText = orderBtn.textContent;
        orderBtn.textContent = 'اضافه شد ✓';
        orderBtn.style.backgroundColor = '#C5A059';
        orderBtn.style.color = '#FFFFFF';
        orderBtn.style.borderColor = '#C5A059';
        setTimeout(function () {
          orderBtn.textContent = origText;
          orderBtn.style.backgroundColor = '';
          orderBtn.style.color = '';
          orderBtn.style.borderColor = '';
        }, 1400);
      }
      return;
    }
  });

  /* Cart State */
  var cart = RozetCart.load();   /* سبد مشترک بین صفحه‌ها */
  var cartBtns     = document.querySelectorAll('.cart-btn');
  var cartOverlay  = document.querySelector('.cart-overlay');
  var cartDrawer   = document.querySelector('.cart-drawer');
  var cartClose    = document.querySelector('.cart-drawer-close');
  var cartCountEl  = document.querySelector('.cart-count');
  var cartSubtotal = document.querySelector('.cart-subtotal-amount');

  function openCart() {
    if (!cartDrawer || !cartOverlay) return;
    cartOverlay.classList.add('is-open');
    cartDrawer.classList.add('is-open');
    body.style.overflow = 'hidden';
  }

  function closeCart() {
    if (!cartDrawer || !cartOverlay) return;
    cartOverlay.classList.remove('is-open');
    cartDrawer.classList.remove('is-open');
    body.style.overflow = '';
  }

  cartBtns.forEach(function (btn) { btn.addEventListener('click', openCart); });
  if (cartClose)   cartClose.addEventListener('click', closeCart);
  if (cartOverlay) cartOverlay.addEventListener('click', closeCart);

  /* سبد حالا بین صفحه‌ها مشترک است و ممکن است پُر وارد این صفحه شود؛
     پس یک بار در شروع کشیده می‌شود، نه فقط بعد از افزودن. */
  updateCartCount();
  renderCart();

  function updateCartCount() {
    var total = cart.reduce(function (s, i) { return s + i.qty; }, 0);
    if (cartCountEl) {
      /* ارقام فارسی — همان نشان در صفحه‌ی فهرست فارسی نوشته
         می‌شد و اینجا لاتین؛ یک نشان نباید دو جور دیده شود. */
      cartCountEl.textContent = total > 99 ? '۹۹+' : total.toLocaleString('fa-IR');
      cartCountEl.classList.toggle('has-items', total > 0);
    }
  }

  function formatPrice(n) {
    return n.toLocaleString('fa-IR') + ' تومان';
  }

  function renderCart() {
    RozetCart.save(cart);   /* هر بازنویسی سبد، انبار را هم به‌روز می‌کند */
    if (!cartDrawer) return;
    var cartBody  = cartDrawer.querySelector('.cart-drawer-body');
    var emptyEl   = cartDrawer.querySelector('.cart-empty');
    if (!cartBody) return;

    var existingList = cartBody.querySelector('.cart-items');

    if (cart.length === 0) {
      if (emptyEl) emptyEl.style.display = 'flex';
      if (existingList) existingList.remove();
      if (cartSubtotal) cartSubtotal.textContent = '۰ تومان';
      return;
    }

    if (emptyEl) emptyEl.style.display = 'none';

    if (!existingList) {
      existingList = document.createElement('div');
      existingList.className = 'cart-items';
      cartBody.appendChild(existingList);
    }

    var total = cart.reduce(function (s, i) { return s + i.price * i.qty; }, 0);
    if (cartSubtotal) cartSubtotal.textContent = formatPrice(total);

    existingList.innerHTML = cart.map(function (item) {
      return '<div class="cart-item">'
        + '<div class="cart-item-img"><img src="' + item.img + '" alt="' + item.name + '"></div>'
        + '<div class="cart-item-info">'
        + '<p class="cart-item-name">' + item.name + '</p>'
        + '<p class="cart-item-price">' + formatPrice(item.price) + '</p>'
        + '<div class="cart-item-qty">'
        + '<button class="cart-qty-btn" data-action="dec" data-name="' + item.name + '">−</button>'
        + '<span>' + item.qty + '</span>'
        + '<button class="cart-qty-btn" data-action="inc" data-name="' + item.name + '">+</button>'
        + '</div></div></div>';
    }).join('');

    existingList.querySelectorAll('.cart-qty-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var name   = btn.dataset.name;
        var action = btn.dataset.action;
        var item   = cart.find(function (i) { return i.name === name; });
        if (!item) return;
        if (action === 'inc') {
          item.qty++;
        } else {
          item.qty--;
          if (item.qty <= 0) {
            cart = cart.filter(function (i) { return i.name !== name; });
          }
        }
        updateCartCount();
        renderCart();
      });
    });
  }

  function addToCart(name, price, img, id) {
    /* شناسه از data-product کارت می‌آید. بدون آن سرور نمی‌داند کدام
       محصول است و ردیف را کنار می‌گذارد. */
    var pid = id ? parseInt(id, 10) : null;
    var item = cart.find(function (i) { return i.id === pid && !i.meta; });
    if (item) {
      item.qty++;
    } else {
      cart.push({ id: pid, name: name, price: price, img: img, qty: 1 });
    }
    updateCartCount();
    renderCart();

    if (cartCountEl) {
      cartCountEl.style.transform = 'scale(1.45)';
      setTimeout(function () { cartCountEl.style.transform = ''; }, 300);
    }
  }

  window.rozet = { addToCart: addToCart, showToast: showToast };

  /* ════════════════════════════════════════════════════════════════
   ماژول ۸: مگامنوی آبشاری فروشگاه و منوی ریسپانسیو موبایل
   (Shop Dropdown Mega-Menu & Mobile Nav Drawer)
     ════════════════════════════════════════════════════════════════ */
  var shopNavItem  = document.querySelector('.shop-nav-item');
  var shopTrigger  = document.querySelector('.shop-trigger');
  var shopDropdown = document.querySelector('.shop-dropdown');
  var dropdownTimer;

  function openDropdown() {
    clearTimeout(dropdownTimer);
    shopDropdown.classList.add('is-open');
    shopTrigger.setAttribute('aria-expanded', 'true');
  }

  function closeDropdown() {
    dropdownTimer = setTimeout(function () {
      shopDropdown.classList.remove('is-open');
      shopTrigger.setAttribute('aria-expanded', 'false');
    }, 220);
  }

  if (shopNavItem && shopDropdown) {
    shopNavItem.addEventListener('mouseenter', openDropdown);
    shopNavItem.addEventListener('mouseleave', closeDropdown);
    shopDropdown.addEventListener('mouseenter', function () { clearTimeout(dropdownTimer); });
    shopDropdown.addEventListener('mouseleave', closeDropdown);
    shopTrigger.addEventListener('click', function (e) {
      e.stopPropagation();
      shopDropdown.classList.contains('is-open') ? closeDropdown() : openDropdown();
    });
    document.addEventListener('click', function (e) {
      if (!shopNavItem.contains(e.target) && !shopDropdown.contains(e.target)) {
        shopDropdown.classList.remove('is-open');
      }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeDropdown();
    });
  }

  /* Mobile Nav */
  var menuToggle  = document.querySelector('.menu-toggle');
  var mobileNav   = document.querySelector('.mobile-nav');
  var mobileClose = document.querySelector('.mobile-nav-close');

  function openMobileMenu() {
    menuToggle.classList.add('is-open');
    mobileNav.classList.add('is-open');
    body.style.overflow = 'hidden';
  }
  function closeMobileMenu() {
    menuToggle.classList.remove('is-open');
    mobileNav.classList.remove('is-open');
    body.style.overflow = '';
  }

  if (menuToggle) menuToggle.addEventListener('click', function () {
    menuToggle.classList.contains('is-open') ? closeMobileMenu() : openMobileMenu();
  });
  if (mobileClose) mobileClose.addEventListener('click', closeMobileMenu);
  if (mobileNav) {
    mobileNav.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', closeMobileMenu);
    });
  }

  /* ════════════════════════════════════════════════════════════════
   ماژول ۹: سیستم ظهور نرم المان‌ها و افکت حرکتی پارالاکس
   (Intersection Observer Scroll Reveals & Parallax Engine)
     ════════════════════════════════════════════════════════════════ */
  var reveals = document.querySelectorAll('[data-reveal]');
  if ('IntersectionObserver' in window && reveals.length) {
    var revealObs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -50px 0px' });
    reveals.forEach(function (el) { revealObs.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add('revealed'); });
  }

  /* Image Curtain Wipe */
  var imgReveals = document.querySelectorAll('.img-reveal');
  if ('IntersectionObserver' in window && imgReveals.length) {
    var imgObs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) entry.target.classList.add('revealed');
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
    imgReveals.forEach(function (el) { imgObs.observe(el); });
  }

  /* Parallax Controller */
  var parallaxEls = document.querySelectorAll('[data-parallax]');
  if (parallaxEls.length) {
    var pRaf = false;
    function updateParallax() {
      parallaxEls.forEach(function (el) {
        var speed = parseFloat(el.dataset.parallax) || 0.08;
        var rect  = el.getBoundingClientRect();
        if (rect.bottom < 0 || rect.top > window.innerHeight) return;
        var center = rect.top + rect.height / 2 - window.innerHeight / 2;
        el.style.transform = 'translateY(' + (center * speed).toFixed(2) + 'px)';
      });
    }
    window.addEventListener('scroll', function () {
      if (!pRaf) {
        pRaf = true;
        requestAnimationFrame(function () {
          updateParallax();
          pRaf = false;
        });
      }
    }, { passive: true });
  }

  /* ════════════════════════════════════════════════════════════════
   ماژول ۹.۵: فیلتر محصولات و دسرهای انفرادی آتلیه (Pastry Category Filter)
     ════════════════════════════════════════════════════════════════ */
  var filterPills = document.querySelectorAll('.filter-pill');
  var pastryCards = document.querySelectorAll('.product-card--pastry');

  if (filterPills.length && pastryCards.length) {
    filterPills.forEach(function (pill) {
      pill.addEventListener('click', function () {
        var filter = pill.getAttribute('data-filter') || 'all';

        filterPills.forEach(function (p) {
          p.classList.remove('active');
          p.setAttribute('aria-selected', 'false');
        });
        pill.classList.add('active');
        pill.setAttribute('aria-selected', 'true');

        pastryCards.forEach(function (card) {
          var category = card.getAttribute('data-category');
          if (filter === 'all' || category === filter) {
            card.style.display = '';
            card.classList.add('revealed');
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
          } else {
            card.style.display = 'none';
          }
        });
      });
    });
  }

  /* ════════════════════════════════════════════════════════════════
   ماژول ۹.۶: سوییچ تم روشن / تیره (Theme Switcher)
   هر دو استایل‌شیت از قبل لود شده‌اند و تعویض فقط با disabled انجام
   می‌شود، پس آنی است. اگر مرورگر View Transitions را پشتیبانی کند،
   تم جدید به شکل یک دایره از خودِ دکمه به بیرون باز می‌شود.
     ════════════════════════════════════════════════════════════════ */
  var themeToggle = document.querySelector('.theme-toggle');
  var linkLight   = document.getElementById('theme-light');
  var linkDark    = document.getElementById('theme-dark');

  if (themeToggle && linkLight && linkDark) {
    var root = document.documentElement;

    function currentTheme() {
      return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    }

    function paintTheme(theme) {
      var isDark = theme === 'dark';
      /* ترتیب مهم است: اول شیت مقصد فعال، بعد شیت قبلی غیرفعال،
         تا در هیچ فریمی صفحه بدون استایل نماند. */
      if (isDark) {
        linkDark.disabled = false;
        linkLight.disabled = true;
      } else {
        linkLight.disabled = false;
        linkDark.disabled = true;
      }
      root.setAttribute('data-theme', theme);
      themeToggle.setAttribute('aria-checked', isDark ? 'true' : 'false');
      themeToggle.setAttribute('aria-label', isDark ? 'تغییر تم به روشن' : 'تغییر تم به تیره');
      try { localStorage.setItem('rozet-theme', theme); } catch (e) {}
    }

    /* وضعیت اولیه دکمه را با تمی که اسکریپت هد اعمال کرده هماهنگ می‌کند */
    paintTheme(currentTheme());

    themeToggle.addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark';

      /* مرکز پرده دایره‌ای را روی خود دکمه می‌نشانیم */
      var r = themeToggle.getBoundingClientRect();
      root.style.setProperty('--rozet-tt-x', (r.left + r.width / 2) + 'px');
      root.style.setProperty('--rozet-tt-y', (r.top + r.height / 2) + 'px');

      /* پرش فنری کاپ‌کیک */
      themeToggle.classList.remove('is-switching');
      void themeToggle.offsetWidth; /* ری‌استارت انیمیشن */
      themeToggle.classList.add('is-switching');
      setTimeout(function () { themeToggle.classList.remove('is-switching'); }, 700);

      var reduced = window.matchMedia &&
                    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

      /* تم فقط یک بار اعمال می‌شود، از هر مسیری که زودتر برسد */
      var done = false;
      function apply() {
        if (done) return;
        done = true;
        paintTheme(next);
      }

      if (document.startViewTransition && !reduced) {
        try {
          var vt = document.startViewTransition(apply);
          /* هر سه وعده باید گرفته شوند؛ اگر کاربر سریع دوبار تم را عوض کند
             ترنزیشن قبلی abort می‌شود و rejection بی‌صاحب در کنسول می‌افتد. */
          ['ready', 'updateCallbackDone', 'finished'].forEach(function (k) {
            if (vt && vt[k] && vt[k].catch) vt[k].catch(function () {});
          });
        } catch (e) {
          apply();
        }
        /* شبکه ایمنی: اگر مرورگر ترنزیشن را اجرا نکرد (تب پس‌زمینه،
           رندر متوقف‌شده یا پیاده‌سازی ناقص)، تم به‌هرحال عوض می‌شود. */
        setTimeout(apply, 260);
      } else {
        apply();
      }
    });
  }

  /* ماژول ۱۰: اسکرول نرم برای لینک‌های داخلی و انکرها (Smooth Anchor Scroll) */
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var id = a.getAttribute('href').slice(1);
      if (!id) return;
      var target = document.getElementById(id);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

})();