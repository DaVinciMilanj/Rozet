/* ═══════════════════════════════════════════════════════════════════════════
   رُزِت — تعامل‌های صفحه‌ی ۴۰۴
   ───────────────────────────────────────────────────────────────────────────
   ۱. مُهر چرخان: فاصله‌ی حروف طوری تنظیم می‌شود که متن دقیقاً دور دایره را
      پر کند و جای درز نماند (طول متن به فونتِ بارشده بستگی دارد).
   ۲. کیک و رقم‌ها با حرکت ماوس کمی می‌چرخند و جابه‌جا می‌شوند.
   ۳. کلیک روی برشِ جامانده، آن را سر جایش برمی‌گرداند — و بعد دوباره
      بیرون می‌لغزد؛ چون صفحه هنوز پیدا نشده است.

   همه‌چیز اختیاری است: بدون این فایل صفحه کامل و خوانا می‌ماند. با
   «کاهش حرکت» سیستم‌عامل، ۲ و ۳ اجرا نمی‌شوند.
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hero = document.querySelector('.nf-hero');
  if (!hero) return;

  /* ══ ۱. مُهر ══ */
  function fitSeal() {
    var text = document.getElementById('nfSealText');
    var path = document.getElementById('nfSealPath');
    if (!text || !path || !text.getComputedTextLength) return;
    try {
      var chars = text.textContent.trim().length;
      var room = path.getTotalLength() - 2;
      text.style.letterSpacing = '0px';
      var natural = text.getComputedTextLength();
      if (natural > 0 && chars > 1) {
        text.style.letterSpacing = Math.max(0, (room - natural) / chars) + 'px';
      }
    } catch (e) { /* مرورگر قدیمی: همان فاصله‌ی پیش‌فرض CSS */ }
  }
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitSeal);
  else fitSeal();

  if (reduced) return;

  /* ══ ۲. حرکت با ماوس ══ */
  var fine = window.matchMedia && window.matchMedia('(pointer: fine)').matches;
  if (fine) {
    var raf = 0, nx = 0, ny = 0;
    hero.addEventListener('pointermove', function (e) {
      var r = hero.getBoundingClientRect();
      nx = ((e.clientX - r.left) / r.width - 0.5) * 2;     /* −۱ تا ۱ */
      ny = ((e.clientY - r.top) / r.height - 0.5) * 2;
      if (raf) return;
      raf = requestAnimationFrame(function () {
        raf = 0;
        hero.style.setProperty('--mx', nx.toFixed(3));
        hero.style.setProperty('--my', ny.toFixed(3));
      });
    });
    hero.addEventListener('pointerleave', function () {
      hero.style.setProperty('--mx', '0');
      hero.style.setProperty('--my', '0');
    });
  }

  /* ══ ۳. برگرداندن برش ══ */
  var slice = document.getElementById('nfSlice');
  if (!slice || !slice.animate || !slice.getAnimations) return;
  var busy = false;

  slice.addEventListener('click', function () {
    if (busy) return;
    busy = true;
    var floating = slice.getAnimations();
    var from = getComputedStyle(slice).transform;
    floating.forEach(function (a) { a.pause(); });

    var home = slice.animate(
      [{ transform: from }, { transform: 'translate(0px, 0px) rotate(0deg)' }],
      { duration: 650, easing: 'cubic-bezier(0.16, 1, 0.3, 1)', fill: 'forwards' });

    home.onfinish = function () {
      setTimeout(function () {
        var away = slice.animate(
          [{ transform: 'translate(0px, 0px) rotate(0deg)' }, { transform: from }],
          { duration: 900, easing: 'cubic-bezier(0.34, 1.56, 0.64, 1)', fill: 'forwards' });
        away.onfinish = function () {
          home.cancel();
          away.cancel();
          floating.forEach(function (a) { a.play(); });
          busy = false;
        };
      }, 1100);
    };
  });
})();
