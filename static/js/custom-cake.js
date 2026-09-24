/* ═══════════════════════════════════════════════════════════════════════════
   رُزِت — موتور فرم سفارش کیک اختصاصی
   ───────────────────────────────────────────────────────────────────────────
   ماژول ۱ : داده‌ها (شرایط، اندازه، طعم، فیلینگ، بافت)
   ماژول ۲ : کمکی‌ها
   ماژول ۳ : سوییچ تم
   ماژول ۴ : ساخت مراحل و ناوبری بین آن‌ها
   ماژول ۵ : اعتبارسنجی هر مرحله
   ماژول ۶ : آپلود تصویر (پیش‌نمایش سمت کاربر)
   ماژول ۷ : برآورد قیمت زنده
   ماژول ۸ : خلاصه سفارش و ثبت نهایی
   ماژول ۹ : ذخیره پیش‌نویس در مرورگر

   ⚠ این صفحه بک‌اند ندارد:
     • تصاویر فقط سمت کاربر پیش‌نمایش می‌شوند و جایی ارسال نمی‌شوند.
     • دکمه پرداخت درگاه واقعی صدا نمی‌زند و فقط شماره سفارش تولید می‌کند.
     برای واقعی‌شدن هر دو، به سرور نیاز است.
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ══ ۱. داده ══
     بندهای شرایط، اندازه‌ها، طعم‌ها، نرخ‌ها و قواعد تاریخ — همه از
     دیتابیس. هیچ‌کدام دیگر در این فایل ثابت نیستند: مدیر باید بتواند
     از پنل عوضشان کند، و قیمت هم باید همان باشد که سرور حساب می‌کند. */
  var SEED = (function () {
    var tag = document.getElementById('wizard-data');
    if (!tag) return null;
    try { return JSON.parse(tag.textContent); } catch (e) { return null; }
  })();

  if (!SEED) return;

  var BRIDGE = window.ROZET || {};
  var RULES = SEED.rules || {};
  var AUTH = SEED.auth || {};

  var TERMS = SEED.terms || [];
  var SIZES = SEED.sizes || [];
  var FLAVORS = SEED.flavors || [];
  var FILLINGS = SEED.fillings || [];
  var TEXTURES = SEED.coatings || [];
  var OCCASIONS = SEED.occasions || [];

  var DEPOSIT = (SEED.fees || {}).deposit || 0;
  var PRINT_FEE = (SEED.fees || {}).print || 0;
  var MIN_DAYS = RULES.minDays || 3;

  /* ══ ۲. کمکی‌ها ══ */
  var fa = function (n) { return Number(Math.round(n)).toLocaleString('fa-IR'); };
  var byId = function (i) { return document.getElementById(i); };
  var STEPS = ['شرایط', 'مشخصات', 'طرح', 'جزئیات', 'تأیید'];

  var state = {
    step: 1,
    agreed: false,
    mode: 'reference',
    files: [],          /* { name, size, dataUrl } — فقط سمت کاربر */
    size: null, flavor: null, filling: null, texture: null
  };

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

  /* ══ ۴. مراحل ══ */
  function buildStepBar() {
    byId('stepList').innerHTML = STEPS.map(function (label, i) {
      return '<li class="cc-steps__item" data-i="' + (i + 1) + '">' +
        '<span class="cc-steps__dot">' + fa(i + 1) + '</span>' +
        '<span class="cc-steps__label">' + label + '</span></li>';
    }).join('');
  }

  function paintStepBar() {
    document.querySelectorAll('.cc-steps__item').forEach(function (li) {
      var i = +li.getAttribute('data-i');
      li.classList.toggle('is-current', i === state.step);
      li.classList.toggle('is-done', i < state.step);
      if (i === state.step) li.querySelector('.cc-steps__dot').setAttribute('aria-current', 'step');
      else li.querySelector('.cc-steps__dot').removeAttribute('aria-current');
    });
    var done = Math.min(state.step - 1, STEPS.length - 1);
    byId('stepFill').style.width = (done / (STEPS.length - 1) * 100) + '%';
  }

  /* در اولین رندر نباید اسکرول کنیم؛ وگرنه کاربر روی صفحه‌ای فرود می‌آید
     که از سربرگ و تصویر رد شده است. فقط جابه‌جایی بین مراحل اسکرول می‌کند. */
  var firstPaint = true;

  function showStep(n) {
    state.step = n;
    document.querySelectorAll('.cc-step').forEach(function (s) {
      s.hidden = +s.getAttribute('data-step') !== n;
    });
    var isDone = n === 6;
    byId('stepBar').hidden = isDone;
    byId('wizardNav').hidden = isDone;
    byId('backBtn').hidden = n <= 1 || isDone;
    byId('nextBtn').textContent = n === 5 ? 'مرور نهایی انجام شد' : 'مرحله بعد';
    byId('nextBtn').hidden = n >= 5;
    if (!isDone) paintStepBar();
    if (n === 5) buildSummary();
    if (firstPaint) { firstPaint = false; return; }

    /* بعد از تعویض مرحله، فوکوس روی عنوان تا صفحه‌خوان بفهمد جا عوض شده */
    var head = document.querySelector('.cc-step:not([hidden]) .cc-step__title');
    if (head) { head.setAttribute('tabindex', '-1'); head.focus({ preventScroll: true }); }
    window.scrollTo({ top: byId('wizard').offsetTop - 120, behavior: 'smooth' });
  }

  /* ══ ۵. اعتبارسنجی ══ */
  function setError(id, msg) {
    var el = document.querySelector('.cc-error[data-for="' + id + '"]');
    var input = byId(id);
    if (input) input.classList.toggle('is-invalid', !!msg);
    if (!el) return;
    el.textContent = msg || '';
    el.hidden = !msg;
  }

  function normalizeDigits(s) {
    return String(s || '').replace(/[۰-۹]/g, function (d) { return '۰۱۲۳۴۵۶۷۸۹'.indexOf(d); })
                          .replace(/[٠-٩]/g, function (d) { return '٠١٢٣٤٥٦٧٨٩'.indexOf(d); });
  }

  function validate(step) {
    var ok = true;

    if (step === 1) {
      byId('termsError').hidden = state.agreed;
      return state.agreed;
    }

    if (step === 2) {
      [['fName', 'نام را وارد کنید'], ['fFamily', 'نام خانوادگی را وارد کنید'], ['fAddress', 'آدرس را وارد کنید']]
        .forEach(function (p) {
          var v = byId(p[0]).value.trim();
          if (!v) { setError(p[0], p[1]); ok = false; } else setError(p[0], '');
        });

      var phone = normalizeDigits(byId('fPhone').value).replace(/\D/g, '');
      if (!phone) { setError('fPhone', 'شماره تماس را وارد کنید'); ok = false; }
      else if (!/^09\d{9}$/.test(phone)) { setError('fPhone', 'شماره باید ۱۱ رقم و با ۰۹ شروع شود'); ok = false; }
      else { setError('fPhone', ''); byId('fPhone').value = phone; }
      return ok;
    }

    if (step === 3) {
      if (state.mode === 'print' && !state.files.length) {
        byId('fileError').textContent = 'برای چاپ روی کیک، عکس مورد نظرتان را آپلود کنید.';
        byId('fileError').hidden = false;
        return false;
      }
      byId('fileError').hidden = true;
      return true;
    }

    if (step === 4) {
      var d = dateISO();
      if (!d) { setError('fDate', 'تاریخ تحویل را انتخاب کنید'); ok = false; }
      else {
        var picked = new Date(d + 'T00:00:00');
        var min = new Date(); min.setHours(0, 0, 0, 0); min.setDate(min.getDate() + MIN_DAYS);
        if (picked < min) { setError('fDate', 'حداقل ' + fa(MIN_DAYS) + ' روز بعد از امروز را انتخاب کنید'); ok = false; }
        else setError('fDate', '');
      }
      [['size', 'sizeChoices', 'تعداد نفرات'], ['flavor', 'flavorChoices', 'طعم کیک'],
       ['filling', 'fillingChoices', 'فیلینگ'], ['texture', 'textureChoices', 'طعم روکش']]
        .forEach(function (p) {
          if (!state[p[0]]) {
            ok = false;
            var g = byId(p[1]);
            g.classList.add('is-missing');
            setTimeout(function () { g.classList.remove('is-missing'); }, 900);
          }
        });
      if (!ok && !byId('fDate').classList.contains('is-invalid')) {
        /* اگر فقط انتخاب‌ها ناقص بودند، پیام کلی بده */
        var box = byId('estimateBox');
        box.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      return ok;
    }
    return true;
  }

  /* ══ ۶. آپلود ══ */
  var MAX_FILES = RULES.maxImages || 4;
  var MAX_BYTES = RULES.maxBytes || 5 * 1024 * 1024;

  function renderPreviews() {
    byId('previews').innerHTML = state.files.map(function (f, i) {
      return '<div class="cc-preview">' +
        '<img src="' + f.dataUrl + '" alt="' + f.name + '">' +
        '<button type="button" class="cc-preview__del" data-del="' + i + '" aria-label="حذف تصویر">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>' +
        '</button></div>';
    }).join('');
  }

  function addFiles(list) {
    var err = byId('fileError');
    err.hidden = true;
    var arr = Array.prototype.slice.call(list);

    for (var i = 0; i < arr.length; i++) {
      var f = arr[i];
      if (state.files.length >= MAX_FILES) {
        err.textContent = 'حداکثر ' + fa(MAX_FILES) + ' تصویر می‌توانید اضافه کنید.';
        err.hidden = false; break;
      }
      if (!/^image\/(png|jpeg|webp)$/.test(f.type)) {
        err.textContent = 'فقط تصویر JPG، PNG یا WebP قابل قبول است.';
        err.hidden = false; continue;
      }
      if (f.size > MAX_BYTES) {
        err.textContent = '«' + f.name + '» بزرگ‌تر از ۵ مگابایت است.';
        err.hidden = false; continue;
      }
      (function (file) {
        var reader = new FileReader();
        reader.onload = function (e) {
          /* خودِ File هم نگه داشته می‌شود: پیش‌نمایش با dataUrl کشیده
             می‌شود ولی چیزی که به سرور می‌رود باید فایل واقعی باشد. */
          state.files.push({ name: file.name, size: file.size,
                             dataUrl: e.target.result, file: file });
          renderPreviews();
          saveDraft();
        };
        reader.readAsDataURL(file);
      })(f);
    }
  }

  var drop = byId('dropZone'), fileInput = byId('fileInput');
  drop.addEventListener('click', function () { fileInput.click(); });
  drop.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); }
  });
  fileInput.addEventListener('change', function () { addFiles(this.files); this.value = ''; });

  ['dragenter', 'dragover'].forEach(function (ev) {
    drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add('is-dragging'); });
  });
  ['dragleave', 'drop'].forEach(function (ev) {
    drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove('is-dragging'); });
  });
  drop.addEventListener('drop', function (e) {
    if (e.dataTransfer && e.dataTransfer.files) addFiles(e.dataTransfer.files);
  });

  byId('previews').addEventListener('click', function (e) {
    var b = e.target.closest('[data-del]');
    if (!b) return;
    state.files.splice(+b.getAttribute('data-del'), 1);
    renderPreviews();
    saveDraft();
  });

  /* حالت طرح */
  document.querySelectorAll('.cc-mode').forEach(function (m) {
    m.addEventListener('click', function () {
      state.mode = m.getAttribute('data-mode');
      document.querySelectorAll('.cc-mode').forEach(function (x) {
        var on = x === m;
        x.classList.toggle('is-selected', on);
        x.setAttribute('aria-checked', String(on));
      });
      byId('printGuide').hidden = state.mode !== 'print';
      byId('estimateValue') && refreshEstimate();
      saveDraft();
    });
  });

  /* ══ ۷. برآورد قیمت ══ */
  function buildChoices() {
    /* فقط زیرنویسِ توصیفی (مثل وزن) نمایش داده می‌شود؛ قیمت هرگز روی دکمه
       نمی‌آید تا انتخاب مشتری تحت تأثیر عدد قرار نگیرد. */
    function render(hostId, items, key) {
      byId(hostId).innerHTML = items.map(function (it) {
        return '<button type="button" class="cc-choice" data-key="' + key + '" data-id="' + it.id + '" ' +
          'aria-pressed="' + (state[key] === it.id) + '">' +
          '<span class="cc-choice__main">' + it.label + '</span>' +
          (it.sub ? '<span class="cc-choice__sub">' + it.sub + '</span>' : '') +
          '</button>';
      }).join('');
    }
    render('sizeChoices', SIZES, 'size');
    render('flavorChoices', FLAVORS, 'flavor');
    render('fillingChoices', FILLINGS, 'filling');
    render('textureChoices', TEXTURES, 'texture');
  }

  function pick(list, id) { return list.filter(function (x) { return x.id === id; })[0]; }

  function estimate() {
    var s = pick(SIZES, state.size);
    if (!s) return null;
    var total = s.base;
    var f = pick(FLAVORS, state.flavor);   if (f) total += f.add;
    var g = pick(FILLINGS, state.filling); if (g) total += g.add;
    var x = pick(TEXTURES, state.texture); if (x) total += x.add;
    if (state.mode === 'print') total += PRINT_FEE;
    return total;
  }

  function refreshEstimate() {
    var t = estimate();
    byId('estimateValue').textContent = t
      ? fa(t * 0.9) + ' تا ' + fa(t * 1.15) + ' تومان'
      : 'اول تعداد نفرات را انتخاب کنید';
  }

  document.addEventListener('click', function (e) {
    var c = e.target.closest('.cc-choice');
    if (!c) return;
    var key = c.getAttribute('data-key');
    state[key] = c.getAttribute('data-id');
    c.parentNode.querySelectorAll('.cc-choice').forEach(function (x) {
      x.setAttribute('aria-pressed', String(x === c));
    });
    refreshEstimate();
    saveDraft();
  });

  /* ══ ۸. خلاصه و ثبت ══ */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (m) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m];
    });
  }


  function row(dt, dd) {
    return '<div class="cc-sum__row"><dt>' + dt + '</dt><dd>' + esc(dd || '—') + '</dd></div>';
  }

  function buildSummary() {
    var s = pick(SIZES, state.size), f = pick(FLAVORS, state.flavor),
        g = pick(FILLINGS, state.filling), x = pick(TEXTURES, state.texture);
    var t = estimate();

    var thumbs = state.files.length
      ? '<div class="cc-sum__thumbs">' + state.files.map(function (fl) {
          return '<img src="' + fl.dataUrl + '" alt="' + esc(fl.name) + '">';
        }).join('') + '</div>'
      : '';

    byId('summary').innerHTML =
      '<div class="cc-sum">' +
        '<h3 class="cc-sum__title">مشخصات شما</h3>' +
        '<button type="button" class="cc-sum__edit" data-goto="2">ویرایش</button>' +
        '<dl class="cc-sum__body">' +
          row('نام', byId('fName').value + ' ' + byId('fFamily').value) +
          row('تماس', byId('fPhone').value + (byId('fPhone2').value ? ' / ' + byId('fPhone2').value : '')) +
          row('آدرس', byId('fAddress').value) +
        '</dl>' +
      '</div>' +

      '<div class="cc-sum">' +
        '<h3 class="cc-sum__title">طرح کیک</h3>' +
        '<button type="button" class="cc-sum__edit" data-goto="3">ویرایش</button>' +
        '<dl class="cc-sum__body">' +
          row('نوع', state.mode === 'print' ? 'چاپ عکس روی کیک' : 'ساخت بر اساس طرح نمونه') +
          row('تصاویر', state.files.length ? fa(state.files.length) + ' تصویر' : 'بدون تصویر') +
          row('توضیح', byId('fDesignNote').value) +
        '</dl>' + thumbs +
      '</div>' +

      '<div class="cc-sum">' +
        '<h3 class="cc-sum__title">جزئیات کیک</h3>' +
        '<button type="button" class="cc-sum__edit" data-goto="4">ویرایش</button>' +
        '<dl class="cc-sum__body">' +
          row('تاریخ تحویل', byId('fDate').value || '—') +
          row('مناسبت', occasionLabel()) +
          row('تعداد نفرات', s && (s.label + ' · ' + s.sub)) +
          row('طعم', f && f.label) +
          row('فیلینگ', g && g.label) +
          row('طعم روکش', x && x.label) +
          row('پیام روی کیک', byId('fMessage').value) +
          row('حساسیت', byId('fAllergy').value) +
          row('برآورد', t ? fa(t * 0.9) + ' تا ' + fa(t * 1.15) + ' تومان (غیرقطعی)' : '—') +
        '</dl>' +
      '</div>';
  }

  byId('summary').addEventListener('click', function (e) {
    var b = e.target.closest('[data-goto]');
    if (b) showStep(+b.getAttribute('data-goto'));
  });


  /* فهرست مناسبت‌ها از دیتابیس پر می‌شود تا مدل بتواند به رکورد واقعی
     وصل شود. گزینه‌های داخل HTML فقط وقتی می‌مانند که هنوز مناسبتی در
     دیتابیس ثبت نشده باشد. */
  (function fillOccasions() {
    if (!OCCASIONS.length) return;
    byId('fOccasion').innerHTML = OCCASIONS.map(function (o) {
      return '<option value="' + o.id + '">' + o.label + '</option>';
    }).join('');
  })();

  function occasionLabel() {
    var el = byId('fOccasion');
    return el.selectedOptions && el.selectedOptions[0]
      ? el.selectedOptions[0].textContent : el.value;
  }

  var sending = false;

  byId('submitBtn').addEventListener('click', function () {
    if (sending) return;

    /* ثبت نهایی فقط برای کاربر واردشده: این سفارش بیعانه می‌گیرد و
       مشتری باید بتواند وضعیتش را در پنل دنبال کند. */
    if (!AUTH['in']) {
      location.href = AUTH.url || '/auth/';
      return;
    }

    /* آخرین بازبینی همه‌ی مراحل قبل از ثبت */
    for (var i = 1; i <= 4; i++) {
      if (!validate(i)) { showStep(i); return; }
    }

    var btn = this;
    sending = true;
    btn.classList.add('is-busy');
    btn.disabled = true;

    /* multipart، نه JSON: تصویرهای طرح باید خودشان بروند. عددی هم
       فرستاده نمی‌شود — برآورد را سرور از روی دیتابیس می‌سازد. */
    var form = new FormData();
    form.append('payload', JSON.stringify({
      terms: state.agreed,
      termsVersion: SEED.termsVersion,
      name: byId('fName').value.trim(),
      family: byId('fFamily').value.trim(),
      phone: byId('fPhone').value.trim(),
      phone2: byId('fPhone2') ? byId('fPhone2').value.trim() : '',
      address: byId('fAddress') ? byId('fAddress').value.trim() : '',
      mode: state.mode,
      size: state.size,
      flavor: state.flavor,
      filling: state.filling,
      coating: state.texture,
      occasion: byId('fOccasion').value,
      tiers: byId('fTiers') ? byId('fTiers').value : 1,
      color: byId('fColor') ? byId('fColor').value.trim() : '',
      message: byId('fMessage').value.trim(),
      note: byId('fDesignNote').value.trim(),
      allergy: byId('fAllergy').value.trim(),
      date: dateISO()
    }));
    state.files.forEach(function (f) {
      if (f.file) form.append('images', f.file, f.name);
    });

    fetch(BRIDGE.wizardApi, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': BRIDGE.csrf || '' },
      body: form
    }).then(function (r) {
      return r.json().catch(function () { return { ok: false }; });
    }).then(function (res) {
      sending = false;
      btn.classList.remove('is-busy');
      btn.disabled = false;

      if (!res || !res.ok) {
        if (res && res.auth === false) { location.href = res.login || AUTH.url; return; }
        if (res && res.step) { showStep(res.step); }
        setSubmitError((res && res.error) || 'ثبت سفارش انجام نشد. دوباره تلاش کنید.');
        return;
      }

      /* وقتی درگاه بیعانه وصل شود، سرور نشانی‌اش را می‌فرستد. */
      if (res.redirect) { location.href = res.redirect; return; }

      byId('orderCode').textContent = res.code;

      /* وضعیت پیش‌پرداخت را سرور می‌گوید: پرداخت‌شده، در انتظار، یا
         اصلاً لازم نبوده. */
      var note = byId('depositNote');
      if (note) {
        var text = res.note || '';
        if (res.deposit && res.payment === 'paid') {
          text = 'پیش‌پرداخت ' + fa(res.deposit) + ' تومان پرداخت شد.'
               + (res.refId ? ' کد پیگیری: ' + res.refId : '');
        }
        note.textContent = text;
        note.hidden = !text;
      }
      try { localStorage.removeItem('rozet-custom-draft'); } catch (e) {}
      showStep(6);
    }).catch(function () {
      sending = false;
      btn.classList.remove('is-busy');
      btn.disabled = false;
      setSubmitError('ارتباط با سرور برقرار نشد.');
    });
  });

  function setSubmitError(message) {
    var box = byId('submitError');
    if (!box) { alert(message); return; }
    box.textContent = message;
    box.hidden = false;
  }

  byId('copyCode').addEventListener('click', function () {
    var code = byId('orderCode').textContent;
    var btn = this;
    function done() { btn.textContent = 'کپی شد ✓'; setTimeout(function () { btn.textContent = 'کپی'; }, 1600); }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(code).then(done).catch(function () { done(); });
    } else {
      var ta = document.createElement('textarea');
      ta.value = code; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } catch (e) {}
      ta.remove(); done();
    }
  });

  byId('newOrder').addEventListener('click', function () { location.reload(); });

  /* ══ ۹. پیش‌نویس ══ */
  var TEXT_FIELDS = ['fName', 'fFamily', 'fPhone', 'fPhone2', 'fAddress',
                     'fDesignNote', 'fDate', 'fOccasion', 'fMessage', 'fAllergy'];
  var saveTimer;

  function saveDraft() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      var data = { agreed: state.agreed, mode: state.mode, files: state.files,
                   size: state.size, flavor: state.flavor, filling: state.filling, texture: state.texture, fields: {} };
      TEXT_FIELDS.forEach(function (id) { var el = byId(id); if (el) data.fields[id] = el.value; });
      /* تاریخ دو بخش دارد: متن شمسیِ دیده‌شده و مقدار ISO. بدون این،
         پیش‌نویسِ بازیابی‌شده تاریخِ نمایشی داشت ولی مقدار واقعی نه. */
      data.dateISO = dateISO();
      try {
        localStorage.setItem('rozet-custom-draft', JSON.stringify(data));
        var note = byId('savedNote');
        note.hidden = false;
        clearTimeout(note._t);
        note._t = setTimeout(function () { note.hidden = true; }, 1800);
      } catch (e) { /* حافظه پر است یا مرورگر اجازه نمی‌دهد — بی‌صدا رد شو */ }
    }, 500);
  }

  function loadDraft() {
    var raw;
    try { raw = localStorage.getItem('rozet-custom-draft'); } catch (e) { return; }
    if (!raw) return;
    var d;
    try { d = JSON.parse(raw); } catch (e) { return; }

    state.agreed = !!d.agreed;
    state.mode = d.mode || 'reference';
    state.files = Array.isArray(d.files) ? d.files : [];
    ['size', 'flavor', 'filling', 'texture'].forEach(function (k) { if (d[k]) state[k] = d[k]; });
    if (d.fields) TEXT_FIELDS.forEach(function (id) {
      if (id === 'fDate') return;   /* تاریخ را تقویم برمی‌گرداند */
      var el = byId(id); if (el && d.fields[id] != null) el.value = d.fields[id];
    });
    if (d.dateISO && datePicker) datePicker.set(d.dateISO);
  }

  /* ══ راه‌اندازی ══ */
  /* شرایط فقط خوانده می‌شوند؛ تیک‌زدن تک‌تک بندها کار را بی‌جهت طولانی
     می‌کرد. یک تأیید در انتها کافی است. */
  function buildTerms() {
    byId('termsList').innerHTML = TERMS.map(function (t, i) {
      return '<div class="cc-term">' +
        '<span class="cc-term__num" aria-hidden="true">' + fa(i + 1) + '</span>' +
        '<div class="cc-term__body">' +
          '<p class="cc-term__title">' + t.title + '</p>' +
          '<p class="cc-term__text">' + t.text + '</p>' +
        '</div></div>';
    }).join('');
  }

  function syncTermsUI() {
    byId('agreeAll').checked = !!state.agreed;
  }

  document.addEventListener('change', function (e) {
    if (e.target.id === 'agreeAll') {
      state.agreed = e.target.checked;
      byId('termsError').hidden = true;
      saveDraft();
    }
  });

  /* شمارنده پیام و ذخیره خودکار فیلدها */
  byId('fMessage').addEventListener('input', function () {
    byId('msgCount').textContent = fa(this.value.length) + '/۳۰';
    saveDraft();
  });
  TEXT_FIELDS.forEach(function (id) {
    var el = byId(id);
    if (el) el.addEventListener('input', function () { setError(id, ''); saveDraft(); });
  });

  /* ══ تقویم شمسی ══
     تقویم بومی مرورگر میلادی است و مشتری «۷ مهر» را می‌شناسد نه
     «September 29». مقدارِ ذخیره‌شده همان ISO میلادی می‌ماند (در
     dataset.iso) تا قرارداد سرور دست نخورد؛ چیزی که در کادر دیده
     می‌شود تاریخ شمسی است. */
  var datePicker = null;

  function dateISO() {
    var el = byId('fDate');
    return (el && el.dataset.iso) || '';
  }

  (function setupDate() {
    var earliest = RULES.earliest;
    if (!earliest) {
      var min = new Date();
      min.setDate(min.getDate() + MIN_DAYS);
      earliest = min.toISOString().slice(0, 10);
    }
    /* یک سال جلوتر — همان سقفی که سرور هم می‌پذیرد. */
    var latest = new Date();
    latest.setFullYear(latest.getFullYear() + 1);

    datePicker = RozetJalali.attach(byId('fDate'), {
      min: earliest,
      max: RozetJalali.iso(latest)
    });

    byId('dateHint').textContent = 'حداقل ' + fa(MIN_DAYS) + ' روز بعد از امروز — یعنی از '
      + (RULES.earliestLabel || '') + ' به بعد.';
  })();

  byId('nextBtn').addEventListener('click', function () {
    if (!validate(state.step)) return;
    if (state.step < 5) showStep(state.step + 1);
  });
  byId('backBtn').addEventListener('click', function () {
    if (state.step > 1) showStep(state.step - 1);
  });

  byId('depositAmount').textContent = fa(DEPOSIT) + ' تومان';

  /* ذرات شکر معلق روی تصویر سربرگ */
  (function motes() {
    var host = document.querySelector('.cc-hero__motes');
    if (!host) return;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var html = '';
    for (var i = 0; i < 12; i++) {
      html += '<span class="cc-mote" style="' +
        'left:' + (Math.round(Math.random() * 90) + 5) + '%;' +
        'top:' + (Math.round(Math.random() * 68) + 26) + '%;' +
        'width:' + (3 + Math.random() * 2.4).toFixed(1) + 'px;' +
        'height:' + (3 + Math.random() * 2.4).toFixed(1) + 'px;' +
        '--mx:' + Math.round(Math.random() * 44 - 22) + 'px;' +
        'animation-duration:' + (7 + Math.random() * 7).toFixed(1) + 's;' +
        'animation-delay:-' + (Math.random() * 9).toFixed(1) + 's;"></span>';
    }
    host.innerHTML = html;
  })();

  buildStepBar();
  buildTerms();
  buildChoices();
  loadDraft();
  syncTermsUI();
  buildChoices();          /* دوباره، تا انتخاب‌های پیش‌نویس علامت بخورند */
  renderPreviews();
  byId('printGuide').hidden = state.mode !== 'print';
  document.querySelectorAll('.cc-mode').forEach(function (m) {
    var on = m.getAttribute('data-mode') === state.mode;
    m.classList.toggle('is-selected', on);
    m.setAttribute('aria-checked', String(on));
  });
  byId('msgCount').textContent = fa(byId('fMessage').value.length) + '/۳۰';
  refreshEstimate();
  showStep(1);

  window.rozetCustom = { state: state, estimate: estimate };
})();
