/* ═══════════════════════════════════════════════════════════════════════════
   رُزِت — موتور ورود پنل مدیریت
   ───────────────────────────────────────────────────────────────────────────
   ماژول ۱ : سوییچ تم
   ماژول ۲ : ابزار (رقم، خطا، حالت‌ها)
   ماژول ۳ : نام کاربری و رمز
   ماژول ۴ : کد دومرحله‌ای
   ماژول ۵ : ورود موفق

   این صفحه تمپلیت است: فرم هر ورودی را می‌پذیرد و می‌رود به تابلو.
   هیچ نام کاربری و رمزی در کد نیست و نباید گذاشته شود — جزئیات در
   admin/README.txt
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var MAX_TRIES = 5;               /* فقط پیام کاربری — قفل واقعی روی سرور */
  var BRIDGE = window.ROZET || {};
  /* مقصد پس از ورود را سرور می‌گوید (STAFF_HOME_URL)، نه این فایل. */
  var DASHBOARD = BRIDGE.next || '/admin/';

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
          ['ready', 'updateCallbackDone', 'finished'].forEach(function (k) {
            if (vt && vt[k] && vt[k].catch) vt[k].catch(function () {});
          });
        } catch (e) { apply(); }
        setTimeout(apply, 260);
      } else { apply(); }
    });
  })();

  /* ══ ۲. ابزار ══ */
  function toLatin(s) {
    return String(s)
      .replace(/[۰-۹]/g, function (d) { return d.charCodeAt(0) - 0x06F0; })
      .replace(/[٠-٩]/g, function (d) { return d.charCodeAt(0) - 0x0660; });
  }
  function digits(s) { return toLatin(s).replace(/\D/g, ''); }

  function setErr(id, msg) {
    var el = byId(id);
    if (!el) return;
    el.textContent = msg || '';
    el.classList.toggle('is-on', !!msg);
  }
  function busy(btn, on) { btn.classList.toggle('is-busy', on); }

  var card = byId('adCard');
  function shake() {
    if (reduced) return;
    card.classList.remove('is-wrong');
    void card.offsetWidth;               /* اجبار به بازپخش انیمیشن */
    card.classList.add('is-wrong');
    setTimeout(function () { card.classList.remove('is-wrong'); }, 500);
  }

  var panes = {
    creds: byId('paneCreds'),
    done: byId('paneDone')
  };
  var COPY = {
    creds: { t: 'ورود کارکنان', s: 'این بخش فقط برای تیم رُزِت است.' },
    otp:   { t: 'تأیید دومرحله‌ای', s: 'یک گام دیگر تا داشبورد.' },
    done:  { t: '', s: '' }
  };

  function show(name) {
    Object.keys(panes).forEach(function (k) {
      panes[k].hidden = (k !== name);
      panes[k].classList.toggle('is-on', k === name);
    });
    var isDone = (name === 'done');
    byId('adTitle').hidden = isDone;
    byId('adSub').hidden = isDone;
    document.querySelector('.ad-eyebrow').hidden = isDone;
    document.querySelector('.ad-foot').hidden = isDone;
    if (COPY[name] && COPY[name].t) {
      byId('adTitle').textContent = COPY[name].t;
      byId('adSub').textContent = COPY[name].s;
    }
  }

  /* تنها درِ ارتباط با سرور. اگر روزی تأیید دومرحله‌ای وصل شود، سرور
     ``twoFactor: true`` برمی‌گرداند و این فایل همان را می‌فهمد. */
  function verifyAdmin(step, payload) {
    var body = { action: step, next: BRIDGE.next || '' };
    Object.keys(payload || {}).forEach(function (k) { body[k] = payload[k]; });
    return fetch(BRIDGE.staffApi, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': BRIDGE.csrf || '' },
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.json().catch(function () { return { ok: false }; });
    });
  }

  /* ══ ۳. نام کاربری و رمز ══ */
  var tries = 0;
  var userEl = byId('adUser'), passEl = byId('adPass');

  /* هشدار Caps Lock — رایج‌ترین دلیل «رمزم درست است ولی قبول نمی‌کند» */
  function capsCheck(e) {
    var on = e.getModifierState && e.getModifierState('CapsLock');
    byId('adCaps').hidden = !on;
  }
  passEl.addEventListener('keydown', capsCheck);
  passEl.addEventListener('keyup', capsCheck);
  passEl.addEventListener('blur', function () { byId('adCaps').hidden = true; });

  byId('adEye').addEventListener('click', function () {
    var open = passEl.type === 'password';
    passEl.type = open ? 'text' : 'password';
    this.classList.toggle('is-open', open);
    this.setAttribute('aria-label', open ? 'پنهان کردن رمز عبور' : 'نمایش رمز عبور');
    passEl.focus();
  });

  byId('paneCreds').addEventListener('submit', function (e) {
    e.preventDefault();
    setErr('adUserErr', ''); setErr('adPassErr', '');

    var u = userEl.value.trim(), p = passEl.value;
    var bad = false;
    if (!u) { setErr('adUserErr', 'نام کاربری را وارد کنید.'); bad = true; }
    if (!p) { setErr('adPassErr', 'رمز عبور را وارد کنید.'); bad = true; }
    if (bad) { shake(); return; }

    var btn = byId('adSubmit');
    busy(btn, true);
    verifyAdmin('signin', { username: u, password: p }).then(function (res) {
      busy(btn, false);
      if (res && res.ok) {
        passEl.value = '';                 /* رمز را در DOM نگه ندار */
        if (res.twoFactor) {
          /* هنوز پنلی برای کد نداریم؛ وقتی TOTP وصل شود اینجا باز
             می‌شود. تا آن روز سرور هرگز twoFactor نمی‌فرستد. */
          setErr('adPassErr', 'تأیید دومرحله‌ای هنوز فعال نیست.');
          return;
        }
        finish(res.redirect);
        return;
      }
      tries++;
      shake();
      /* شمارنده فقط یادآوری است، نه قفل: قفل واقعی روی سرور نیست و
         این فایل نباید چیزی را وعده بدهد که پشتش نیست. */
      var left = MAX_TRIES - tries;
      var msg = (res && res.error) || 'نام کاربری یا رمز درست نیست.';
      if (left > 0) {
        msg += ' (' + left + ' تلاش دیگر تا هشدار)';
      } else {
        msg += ' هر تلاش ثبت می‌شود؛ اگر رمزتان را فراموش کرده‌اید با مدیر سیستم تماس بگیرید.';
      }
      setErr('adPassErr', msg);
    }).catch(function () {
      busy(btn, false);
      shake();
      setErr('adPassErr', 'ارتباط با سرور برقرار نشد.');
    });
  });

  /* ══ ۴. ورود موفق ══ */
  function finish(redirect) {
    if (redirect) DASHBOARD = redirect;
    show('done');
    /* طول واقعی مسیر خوانده می‌شود تا خط دقیق کشیده شود، نه حدسی */
    document.querySelectorAll('.ad-done__circle, .ad-done__tick').forEach(function (p) {
      p.style.setProperty('--len', Math.ceil(p.getTotalLength()));
    });
    setTimeout(function () { location.href = DASHBOARD; }, 1100);
  }

  /* ══ راه‌اندازی ══ */
  show('creds');
  userEl.focus();
})();
