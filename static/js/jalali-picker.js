/* ═══════════════════════════════════════════════════════════════════════════
   رُزِت — تقویم شمسی
   ───────────────────────────────────────────────────────────────────────────
   <input type="date"> بومیِ مرورگر تقویم میلادی نشان می‌دهد. مشتری ایرانی
   «۷ مهر» را می‌شناسد، نه «September 29». این ماژول یک تقویم شمسی
   می‌سازد که کاربر با آن روز را انتخاب می‌کند، ولی مقدارِ ذخیره‌شده
   همان ISO میلادی می‌ماند — سرور و دیتابیس دست نمی‌خورند.

   کتابخانه‌ی بیرونی لازم نشد: الگوریتم تبدیل همان است که در
   apps/common/dates.py پایتونی نوشته شده و آزمون دارد.

   استفاده:
       RozetJalali.attach(input)     input.dataset.iso ← «2026-09-28»
                                     input.value       ← «دوشنبه ۷ مهر ۱۴۰۵»
   ═══════════════════════════════════════════════════════════════════════════ */
window.RozetJalali = (function () {
  'use strict';

  var MONTHS = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
                'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'];

  /* هفته‌ی ایرانی از شنبه شروع می‌شود؛ getDay() یکشنبه را صفر می‌گیرد. */
  var WEEK = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'];
  var WEEK_LONG = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه'];

  var G_DAYS = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];

  /* استایلِ ویجت همراه خودش می‌رود، نه در شیت مشترک.

     دلیلش یک باگ واقعی بود: مرورگر نسخه‌ی کهنه‌ی شیت مشترک را از کش
     می‌خواند، تقویم بدون استایل باز می‌شد و به‌جای پاپ‌آپ، فهرستی از
     اعداد وسط فرم پهن می‌شد. مارکاپ این ویجت را خودِ این فایل می‌سازد،
     پس استایلش هم با همین فایل می‌آید و هیچ‌وقت از آن جدا نمی‌افتد. */
  var STYLES = [
    '.jd { position: relative; }',
    '.jd__input { cursor: pointer; }',

    /* صریح، علاوه بر [hidden]: اگر روزی قاعده‌ای در صفحه display را
       روی این گره بنشاند، تقویمِ بسته نباید باز دیده شود. */
    '.jd__pop[hidden] { display: none !important; }',

    '.jd__pop {',
    '  position: absolute;',
    '  z-index: 40;',
    '  top: calc(100% + 0.45rem);',
    '  inset-inline-start: 0;',
    '  width: min(20rem, calc(100vw - 2rem));',
    '  padding: 0.85rem;',
    '  border: 1px solid var(--border-mid, rgba(255,255,255,0.18));',
    '  border-radius: 16px;',
    '  background: var(--bg, #171210);',
    '  box-shadow: 0 26px 52px -26px rgba(0, 0, 0, 0.55);',
    '}',

    '.jd__head {',
    '  display: flex; align-items: center; justify-content: space-between;',
    '  margin-bottom: 0.7rem;',
    '}',
    '.jd__title {',
    '  font-family: var(--font-heading, inherit);',
    '  font-size: var(--text-sm, 0.9rem);',
    '  color: var(--text, #e6dcd2);',
    '}',
    '.jd__nav {',
    '  width: 30px; height: 30px;',
    '  border: 1px solid var(--border, rgba(255,255,255,0.12));',
    '  border-radius: 9px; background: none;',
    '  color: var(--text-muted, #b9aa9d);',
    '  font-size: 1.1rem; line-height: 1; cursor: pointer;',
    '  transition: color 0.2s ease, border-color 0.2s ease;',
    '}',
    '.jd__nav:hover { color: var(--rosette, #c0405a); border-color: var(--rosette, #c0405a); }',

    '.jd__week, .jd__grid {',
    '  display: grid; grid-template-columns: repeat(7, 1fr); gap: 0.2rem;',
    '}',
    '.jd__week {',
    '  margin-bottom: 0.35rem; text-align: center;',
    '  font-family: var(--font, inherit);',
    '  font-size: var(--text-xs, 0.75rem);',
    '  color: var(--text-subtle, #8c7d72);',
    '}',

    '.jd__day {',
    '  aspect-ratio: 1;',
    '  border: 1px solid transparent; border-radius: 9px; background: none;',
    '  font-family: var(--font-num, var(--font, inherit));',
    '  font-size: var(--text-sm, 0.9rem);',
    '  color: var(--text, #e6dcd2);',
    '  cursor: pointer;',
    '  transition: background 0.2s ease, color 0.2s ease;',
    '}',
    '.jd__day:hover:not([disabled]) { background: rgba(255, 255, 255, 0.08); }',
    '.jd__day[disabled] {',
    '  color: var(--text-subtle, #8c7d72); opacity: 0.35; cursor: not-allowed;',
    '}',
    /* امروز فقط یک نشانه دارد؛ روزِ انتخاب‌شده پررنگ است. */
    '.jd__day.is-today { border-color: var(--border-mid, rgba(255,255,255,0.18)); }',
    '.jd__day.is-on {',
    '  background: var(--rosette, #c0405a);',
    '  border-color: var(--rosette, #c0405a);',
    '  color: var(--cream, #faf6f0);',
    '}'
  ].join(String.fromCharCode(10));

  function fa(n) {
    return String(n).replace(/\d/g, function (d) {
      return String.fromCharCode(0x06F0 + (+d));
    });
  }

  function isLeap(y) { return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0; }

  /* شماره‌ی روز از ابتدای ۱۶۰۰ میلادی — مبنای مشترک هر دو تقویم */
  function dayNumber(gy, gm, gd) {
    var off = gy - 1600;
    var days = 365 * off + Math.floor((off + 3) / 4)
             - Math.floor((off + 99) / 100) + Math.floor((off + 399) / 400);
    days += G_DAYS[gm - 1] + gd - 1;
    if (gm > 2 && isLeap(gy)) days += 1;
    return days;
  }

  function toJalali(date) {
    var days = dayNumber(date.getFullYear(), date.getMonth() + 1, date.getDate()) - 79;
    var cycles = Math.floor(days / 12053);
    days -= cycles * 12053;
    var jy = 979 + 33 * cycles + 4 * Math.floor(days / 1461);
    days %= 1461;
    if (days >= 366) {
      jy += Math.floor((days - 1) / 365);
      days = (days - 1) % 365;
    }
    if (days < 186) return { y: jy, m: 1 + Math.floor(days / 31), d: 1 + (days % 31) };
    days -= 186;
    return { y: jy, m: 7 + Math.floor(days / 30), d: 1 + (days % 30) };
  }

  /* معکوسِ دقیقِ toJalali — با همان مبنای «شماره‌ی روز از ۱۶۰۰».
     هر فرمول مستقلی می‌توانست یک روز با آن اختلاف پیدا کند؛ این یکی
     همان مسیر را برعکس می‌رود، پس نمی‌تواند. */
  function toGregorian(jy, jm, jd) {
    var years = jy - 979;
    var cycles = Math.floor(years / 33);
    var rest = years % 33;

    var days = cycles * 12053 + Math.floor(rest / 4) * 1461;
    var r = rest % 4;
    /* در هر گروه چهارساله، سال اول ۳۶۶ روز دارد و سه سال بعدی ۳۶۵. */
    if (r > 0) days += 366 + (r - 1) * 365;

    days += (jm <= 6) ? (jm - 1) * 31 : 186 + (jm - 7) * 30;
    days += jd - 1;

    /* ۷۹ روز فاصله‌ی ۱ فروردین ۹۷۹ تا ۱ ژانویه‌ی ۱۶۰۰ */
    var date = new Date(1600, 0, 1);
    date.setDate(date.getDate() + days + 79);
    return date;
  }

  function iso(date) {
    return date.getFullYear() + '-' +
      String(date.getMonth() + 1).padStart(2, '0') + '-' +
      String(date.getDate()).padStart(2, '0');
  }

  function sameDay(a, b) {
    return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth()
        && a.getDate() === b.getDate();
  }

  /* «دوشنبه ۷ مهر ۱۴۰۵» */
  function label(date) {
    var j = toJalali(date);
    return WEEK_LONG[(date.getDay() + 1) % 7] + ' ' + fa(j.d) + ' ' +
           MONTHS[j.m - 1] + ' ' + fa(j.y);
  }

  function daysInJalaliMonth(jy, jm) {
    if (jm <= 6) return 31;
    if (jm <= 11) return 30;
    /* اسفند: ۳۰ روز در سال کبیسه، وگرنه ۲۹. به‌جای فرمولِ کبیسه، از
       خودِ تبدیل می‌پرسیم — همان مرجعی که بقیه‌ی ماژول با آن کار
       می‌کند، پس نمی‌تواند با آن اختلاف پیدا کند. */
    var probe = toJalali(toGregorian(jy, 12, 30));
    return (probe.m === 12 && probe.d === 30) ? 30 : 29;
  }

  /* استایل همراه خودِ ویجت می‌رود، نه در شیت مشترک.

     دلیلش یک باگ واقعی بود: مرورگر نسخه‌ی کهنه‌ی شیت مشترک را از کش
     می‌خواند، تقویم بدون استایل باز می‌شد و به‌جای پاپ‌آپ، فهرستی از
     اعداد وسط فرم پهن می‌شد. مارکاپ این ویجت را خودِ این فایل می‌سازد،
     پس استایلش هم باید با همین فایل بیاید — آن‌وقت هیچ‌وقت از هم جدا
     نمی‌افتند. */
  var styled = false;

  function injectStyles() {
    if (styled || document.getElementById('jd-styles')) { styled = true; return; }
    styled = true;
    var tag = document.createElement('style');
    tag.id = 'jd-styles';
    tag.textContent = STYLES;
    document.head.appendChild(tag);
  }

  function attach(input, options) {
    injectStyles();
    options = options || {};
    var min = options.min ? new Date(options.min + 'T00:00:00') : null;
    var max = options.max ? new Date(options.max + 'T00:00:00') : null;
    var onPick = options.onPick || function () {};

    var wrap = document.createElement('div');
    wrap.className = 'jd';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    input.type = 'text';
    input.readOnly = true;
    input.autocomplete = 'off';
    input.dir = 'rtl';
    input.classList.add('jd__input');
    if (!input.placeholder) input.placeholder = 'انتخاب تاریخ';

    var pop = document.createElement('div');
    pop.className = 'jd__pop';
    pop.hidden = true;
    pop.setAttribute('role', 'dialog');
    pop.setAttribute('aria-label', 'انتخاب تاریخ');
    wrap.appendChild(pop);

    /* ماهی که الان نشان داده می‌شود؛ پیش‌فرض ماهِ حداقلِ مجاز */
    var view = toJalali(min && min > new Date() ? min : new Date());
    var picked = null;

    function cell(text, cls, attrs) {
      return '<button type="button" class="' + cls + '"' + (attrs || '') + '>' + text + '</button>';
    }

    function draw() {
      var first = toGregorian(view.y, view.m, 1);
      /* شنبه ستون اول: getDay() یکشنبه=۰ را به شنبه=۰ می‌چرخانیم */
      var lead = (first.getDay() + 1) % 7;
      var count = daysInJalaliMonth(view.y, view.m);
      var today = new Date();

      var html = '<div class="jd__head">' +
        cell('‹', 'jd__nav', ' data-move="-1" aria-label="ماه قبل"') +
        '<span class="jd__title">' + MONTHS[view.m - 1] + ' ' + fa(view.y) + '</span>' +
        cell('›', 'jd__nav', ' data-move="1" aria-label="ماه بعد"') +
        '</div><div class="jd__week">' +
        WEEK.map(function (w) { return '<span>' + w + '</span>'; }).join('') +
        '</div><div class="jd__grid">';

      for (var i = 0; i < lead; i++) html += '<span class="jd__empty"></span>';

      for (var d = 1; d <= count; d++) {
        var date = toGregorian(view.y, view.m, d);
        var dead = (min && date < min) || (max && date > max);
        var cls = 'jd__day';
        if (picked && sameDay(date, picked)) cls += ' is-on';
        if (sameDay(date, today)) cls += ' is-today';
        html += cell(fa(d), cls,
          ' data-iso="' + iso(date) + '"' + (dead ? ' disabled' : ''));
      }
      pop.innerHTML = html + '</div>';
    }

    function open() {
      if (picked) view = toJalali(picked);
      draw();
      pop.hidden = false;
      wrap.classList.add('is-open');
    }

    function close() {
      pop.hidden = true;
      wrap.classList.remove('is-open');
    }

    function set(date) {
      picked = date;
      input.dataset.iso = iso(date);
      input.value = label(date);
      input.classList.remove('is-invalid');
      onPick(input.dataset.iso);
      /* همان رویدادی که بقیه‌ی صفحه به آن گوش می‌دهد (پیش‌نویس، خطاها) */
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }

    input.addEventListener('click', function () {
      if (pop.hidden) open(); else close();
    });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); }
      if (e.key === 'Escape') close();
    });

    pop.addEventListener('click', function (e) {
      var nav = e.target.closest('[data-move]');
      if (nav) {
        view.m += +nav.getAttribute('data-move');
        if (view.m > 12) { view.m = 1; view.y++; }
        if (view.m < 1) { view.m = 12; view.y--; }
        draw();
        return;
      }
      var day = e.target.closest('[data-iso]');
      if (day && !day.disabled) {
        set(new Date(day.getAttribute('data-iso') + 'T00:00:00'));
        close();
      }
    });

    document.addEventListener('click', function (e) {
      if (!wrap.contains(e.target)) close();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') close();
    });

    return {
      set: function (isoText) {
        if (!isoText) return;
        set(new Date(isoText + 'T00:00:00'));
      },
      value: function () { return input.dataset.iso || ''; },
      clear: function () {
        picked = null;
        input.value = '';
        delete input.dataset.iso;
      }
    };
  }

  return { attach: attach, toJalali: toJalali, toGregorian: toGregorian,
           label: label, iso: iso, fa: fa };
})();
