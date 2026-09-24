/* ═══════════════════════════════════════════════════════════════════════════
   رُزِت — موتور صفحه‌ی ورود و ثبت‌نام
   ───────────────────────────────────────────────────────────────────────────
   ماژول ۱ : سوییچ تم
   ماژول ۲ : جابه‌جایی ورود / ثبت‌نام
   ماژول ۳ : ابزار ورودی (رقم فارسی، اعتبارسنجی، خطا)
   ماژول ۴ : نمایش رمز و سنجه‌ی قدرت
   ماژول ۵ : ارسال فرم‌ها
   ماژول ۶ : کد شش‌رقمی پیامکی
   ماژول ۷ : صفحه‌ی پایان
   ماژول ۸ : ذرات شکر قاب تصویری

   تمپلیت است: فرم‌ها اعتبارسنجی می‌شوند و مسیر کامل را نشان می‌دهند،
   ولی جایی ذخیره نمی‌شوند. هیچ رمزی در مرورگر نگه داشته نمی‌شود.
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
        setTimeout(apply, 260);   /* شبکه‌ی ایمنی اگر ترنزیشن اجرا نشد */
      } else { apply(); }
    });
  })();

  /* ══ ۳. ابزار ورودی ══ */

  /* کاربر ممکن است با کیبورد فارسی رقم بزند؛ همه به لاتین تبدیل می‌شوند */
  function toLatin(s) {
    return String(s)
      .replace(/[۰-۹]/g, function (d) { return d.charCodeAt(0) - 0x06F0; })
      .replace(/[٠-٩]/g, function (d) { return d.charCodeAt(0) - 0x0660; });
  }
  function digitsOnly(s) { return toLatin(s).replace(/\D/g, ''); }
  function faDigits(s) {
    return String(s).replace(/\d/g, function (d) { return String.fromCharCode(0x06F0 + (+d)); });
  }
  function validPhone(s) { return /^09\d{9}$/.test(digitsOnly(s)); }

  function setErr(id, msg) {
    var el = byId(id);
    if (!el) return;
    el.textContent = msg || '';
    el.classList.toggle('is-on', !!msg);
  }
  function clearErrs(form) {
    form.querySelectorAll('.au-err').forEach(function (e) {
      e.textContent = ''; e.classList.remove('is-on');
    });
  }

  /* شماره‌ها فقط رقم بپذیرند و در جا لاتین شوند */
  ['siPhone', 'suPhone'].forEach(function (id) {
    var el = byId(id);
    if (!el) return;
    el.addEventListener('input', function () {
      var v = digitsOnly(el.value).slice(0, 11);
      if (v !== el.value) el.value = v;
    });
  });

  /* ══ ۲. جابه‌جایی ورود / ثبت‌نام ══ */
  var tabs = document.querySelector('.au-tabs');
  var panes = {
    signin: byId('paneSignin'),
    signup: byId('paneSignup'),
    done: byId('paneDone')
  };
  var COPY = {
    signin: { t: 'خوش آمدید', s: 'برای ثبت سفارش و دیدن سابقه‌ی خریدتان وارد شوید.' },
    signup: { t: 'حساب تازه', s: 'یک بار ثبت‌نام کنید؛ دفعه‌ی بعد فقط انتخاب می‌کنید.' },
    done:   { t: '', s: '' }
  };

  function show(name) {
    Object.keys(panes).forEach(function (k) {
      if (!panes[k]) return;
      panes[k].hidden = (k !== name);
      panes[k].classList.toggle('is-on', k === name);
    });
    /* سوییچ و سربرگ فقط در دو حالت اول معنی دارند */
    var chrome = (name === 'signin' || name === 'signup');
    if (tabs) tabs.hidden = !chrome;
    byId('authSub').hidden = (name === 'done');
    byId('authHeading').hidden = (name === 'done');
    if (COPY[name] && COPY[name].t) {
      byId('authHeading').textContent = COPY[name].t;
      byId('authSub').textContent = COPY[name].s;
    }
    document.querySelector('.au-eyebrow').hidden = (name === 'done');

    if (chrome) {
      tabs.setAttribute('data-on', name);
      tabs.querySelectorAll('.au-tab').forEach(function (b) {
        var on = b.getAttribute('data-tab') === name;
        b.classList.toggle('is-on', on);
        b.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      var first = panes[name].querySelector('input:not([type=checkbox])');
      if (first && window.innerWidth > 980) first.focus();
    }
  }

  if (tabs) {
    tabs.setAttribute('data-on', 'signin');
    tabs.querySelectorAll('.au-tab').forEach(function (b) {
      b.addEventListener('click', function () { show(b.getAttribute('data-tab')); });
    });
  }

  /* ══ ۴. نمایش رمز و سنجه‌ی قدرت ══ */
  document.querySelectorAll('.au-eye').forEach(function (eye) {
    eye.addEventListener('click', function () {
      var input = byId(eye.getAttribute('data-eye'));
      if (!input) return;
      var open = input.type === 'password';
      input.type = open ? 'text' : 'password';
      eye.classList.toggle('is-open', open);
      eye.setAttribute('aria-label', open ? 'پنهان کردن رمز عبور' : 'نمایش رمز عبور');
      input.focus();
    });
  });

  /* امتیاز ساده: طول + تنوع نویسه‌ها. سخت‌گیری بیشتر کاربر را فراری می‌دهد */
  /* حداقل طول رمز از سرور (settings.PASSWORD_MIN_LENGTH) */
  var PASS_MIN = (window.ROZET && window.ROZET.passwordMin) || 6;
  function strength(pw) {
    if (!pw) return 0;
    var score = 0;
    if (pw.length >= PASS_MIN) score++;
    if (pw.length >= PASS_MIN + 4) score++;
    var kinds = 0;
    if (/[a-z]/.test(pw)) kinds++;
    if (/[A-Z]/.test(pw)) kinds++;
    if (/\d/.test(pw)) kinds++;
    if (/[^\w\s]/.test(pw)) kinds++;
    if (kinds >= 3) score++;
    return Math.min(3, score);
  }
  var suPass = byId('suPass');
  var meter = document.querySelector('.au-meter');
  var meterText = byId('suMeterText');
  if (suPass && meter) {
    var LABEL = ['قدرت رمز', 'ضعیف', 'متوسط', 'خوب'];
    suPass.addEventListener('input', function () {
      var lv = strength(suPass.value);
      meter.setAttribute('data-level', lv);
      meterText.textContent = LABEL[lv];
    });
  }

  /* ══ ۵. ارسال فرم‌ها ══ */

  /* تنها راه ارتباط با سرور. یک اندپوینت، تقسیم روی action — همان
     الگوی پنل کاربری. */
  var BRIDGE = window.ROZET || {};

  function sendToServer(action, payload) {
    var body = { action: action, next: BRIDGE.next || '' };
    Object.keys(payload || {}).forEach(function (k) { body[k] = payload[k]; });
    return fetch(BRIDGE.authApi, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': BRIDGE.csrf || '' },
      body: JSON.stringify(body)
    }).then(function (r) {
      /* پاسخ خطا هم بدنه‌ی JSON دارد و پیامش زیر همان ورودی می‌نشیند،
         پس روی status رد نمی‌شویم. */
      return r.json().catch(function () { return { ok: false }; });
    });
  }

  /* سرور می‌گوید پیام زیر کدام ورودی بنشیند. */
  var ERR_BOX = {
    signin: { phone: 'siPhoneErr', password: 'siPassErr' },
    signup: { name: 'suNameErr', phone: 'suPhoneErr', password: 'suPassErr' }
  };

  function showServerError(form, res, fallbackId) {
    var box = (ERR_BOX[form] || {})[res && res.field] || fallbackId;
    setErr(box, (res && res.error) || 'انجام نشد. دوباره تلاش کنید.');
  }

  function busy(btn, on) { btn.classList.toggle('is-busy', on); }

  var signin = byId('paneSignin');
  signin.addEventListener('submit', function (e) {
    e.preventDefault();
    clearErrs(signin);
    var phone = byId('siPhone').value, pass = byId('siPass').value;
    var bad = false;
    if (!validPhone(phone)) { setErr('siPhoneErr', 'شماره باید با ۰۹ شروع شود و ۱۱ رقم باشد.'); bad = true; }
    if (!pass) { setErr('siPassErr', 'رمز عبور را وارد کنید.'); bad = true; }
    if (bad) return;

    var btn = signin.querySelector('.au-submit');
    busy(btn, true);
    sendToServer('signin', {
      phone: digitsOnly(phone),
      password: pass,
      remember: byId('siRemember').checked
    }).then(function (res) {
      busy(btn, false);
      if (res && res.ok) finish('خوش برگشتید', 'وارد حساب رُزِت شدید.', res.redirect);
      else showServerError('signin', res, 'siPassErr');
    }).catch(function () {
      busy(btn, false);
      setErr('siPassErr', 'ارتباط با سرور برقرار نشد. دوباره تلاش کنید.');
    });
  });

  var signup = byId('paneSignup');
  signup.addEventListener('submit', function (e) {
    e.preventDefault();
    clearErrs(signup);
    var name = byId('suName').value.trim();
    var phone = byId('suPhone').value;
    var pass = byId('suPass').value;
    var bad = false;
    if (name.length < 3) { setErr('suNameErr', 'نام و نام خانوادگی را کامل بنویسید.'); bad = true; }
    if (!validPhone(phone)) { setErr('suPhoneErr', 'شماره باید با ۰۹ شروع شود و ۱۱ رقم باشد.'); bad = true; }
    if (pass.length < PASS_MIN) { setErr('suPassErr', 'رمز عبور دست‌کم ' + faDigits(PASS_MIN) + ' نویسه باشد.'); bad = true; }
    if (!byId('suTerms').checked) { setErr('suTermsErr', 'برای ساخت حساب باید شرایط را بپذیرید.'); bad = true; }
    if (bad) return;

    var btn = signup.querySelector('.au-submit');
    busy(btn, true);
    sendToServer('signup', {
      name: name,
      phone: digitsOnly(phone),
      password: pass,
      remember: true
    }).then(function (res) {
      busy(btn, false);
      /* بدون سامانه‌ی پیامکی مرحله‌ی تأیید شماره‌ای در کار نیست: حساب
         ساخته می‌شود و کاربر همان‌جا وارد است. */
      if (res && res.ok) {
        finish((res.name || name.split(/\s+/)[0]) + ' عزیز، خوش آمدید',
               'حساب رُزِت شما ساخته شد.', res.redirect);
      } else {
        showServerError('signup', res, 'suPhoneErr');
      }
    }).catch(function () {
      busy(btn, false);
      setErr('suPhoneErr', 'ارتباط با سرور برقرار نشد. دوباره تلاش کنید.');
    });
  });

  /* ══ ۶. صفحه‌ی پایان ══ */
  function finish(title, text, redirect) {
    byId('doneTitle').textContent = title;
    byId('doneText').textContent = text;
    /* دکمه به همان‌جایی می‌رود که کاربر پیش از ورود می‌خواست (next)،
       نه همیشه به پنل. */
    if (redirect) byId('doneGo').setAttribute('href', redirect);
    show('done');
    drawTick();
    /* چند لحظه تیک دیده شود، بعد خودکار برود. */
    setTimeout(function () { location.href = redirect || byId('doneGo').getAttribute('href'); }, 1400);
  }

  /* طول واقعی هر مسیر خوانده می‌شود تا خط دقیق کشیده شود، نه حدسی */
  function drawTick() {
    document.querySelectorAll('.au-done__circle, .au-done__tick').forEach(function (p) {
      var len = Math.ceil(p.getTotalLength());
      p.style.setProperty('--len', len);
      p.style.animation = 'none';
      void p.getBoundingClientRect();
      p.style.animation = '';
    });
  }

  /* ══ ۸. ذرات شکر ══ */
  (function motes() {
    var host = byId('auMotes');
    if (!host || reduced) return;
    var html = '';
    for (var i = 0; i < 14; i++) {
      html += '<span class="au-mote" style="' +
        'left:' + (Math.round(Math.random() * 92) + 4) + '%;' +
        'top:' + (Math.round(Math.random() * 60) + 35) + '%;' +
        'width:' + (2.6 + Math.random() * 2.4).toFixed(1) + 'px;' +
        'height:' + (2.6 + Math.random() * 2.4).toFixed(1) + 'px;' +
        '--mx:' + Math.round(Math.random() * 50 - 25) + 'px;' +
        'animation-duration:' + (9 + Math.random() * 9).toFixed(1) + 's;' +
        'animation-delay:-' + (Math.random() * 12).toFixed(1) + 's;"></span>';
    }
    host.innerHTML = html;
  })();

  /* اگر با ‎?mode=signup‎ آمده‌اید مستقیم روی ثبت‌نام باز شود */
  if (/[?&]mode=signup/.test(location.search)) show('signup');
})();
