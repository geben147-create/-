/* ============================================================
   시네마틱 스크롤 — 지연 로딩 + 스크럽
   가이드 08-B / 08-C 를 그대로 구현.
   GSAP 이 없으면 스크럽은 자체 rAF 폴백으로 동작한다.
   ============================================================ */
(function () {
  'use strict';

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- 1. 지연 로딩: 화면에 들어올 때만 src 를 붙인다 ----------
     6개 영상을 동시에 받으면 첫 화면이 죽는다. */
  var lazy = document.querySelectorAll('video[data-src]');
  if (lazy.length) {
    if (reduced) {
      // 동작 줄이기: 아예 로드하지 않는다 (CSS 가 poster 배경으로 대체)
      lazy.forEach(function (v) { v.removeAttribute('data-src'); });
    } else if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          var v = e.target;
          if (e.isIntersecting) {
            if (!v.src && v.dataset.src) v.src = v.dataset.src;
            var p = v.play();
            if (p && p.catch) p.catch(function () {});   // 자동재생 거부돼도 조용히
          } else if (!v.hasAttribute('data-keep-playing')) {
            v.pause();                                    // 화면 밖이면 정지
          }
        });
      }, { rootMargin: '250px 0px', threshold: 0.05 });
      lazy.forEach(function (v) { io.observe(v); });
    } else {
      lazy.forEach(function (v) { v.src = v.dataset.src; });
    }
  }

  /* ---------- 2. 히어로: 자동재생이 막히면 조용히 포스터로 ---------- */
  var hero = document.querySelector('.hero__bg');
  if (hero && !reduced) {
    var hp = hero.play();
    if (hp && hp.catch) hp.catch(function () {});
  }

  /* ---------- 3. 스크럽 섹션 ----------
     스크롤 위치 → currentTime 직결. 핀은 sticky 로 건다
     (GSAP pin 은 조상에 transform 을 만들어 fixed 자식을 깨뜨리므로
      여기서는 position:sticky 로 핀하고 스크럽만 계산한다). */
  var scrubSection = document.querySelector('[data-scrub]');
  if (scrubSection && !reduced) {
    var video   = scrubSection.querySelector('.scrub__video');
    var stage   = scrubSection.querySelector('.scrub__stage');
    var bar     = scrubSection.querySelector('.scrub__progress i');
    var steps   = Array.prototype.slice.call(scrubSection.querySelectorAll('.step'));
    var duration = 0;
    var target = 0, current = 0, ticking = false;

    // sticky 로 핀 — 조상 transform 없이 화면에 고정된다
    stage.style.position = 'sticky';
    stage.style.top = '0';

    function onMeta() {
      duration = video.duration || 0;
      if (duration) loop();
    }
    if (video.readyState >= 1) onMeta();
    video.addEventListener('loadedmetadata', onMeta);

    function progress() {
      var rect = scrubSection.getBoundingClientRect();
      var total = scrubSection.offsetHeight - window.innerHeight;
      if (total <= 0) return 0;
      var p = (-rect.top) / total;
      return Math.max(0, Math.min(1, p));
    }

    function paint(p) {
      if (bar) bar.style.width = (p * 100).toFixed(2) + '%';
      if (steps.length) {
        var active = Math.min(steps.length - 1, Math.floor(p * steps.length + 0.0001));
        steps.forEach(function (s, i) { s.classList.toggle('is-on', i <= active && p > 0.02); });
      }
    }

    function loop() {
      target = progress() * duration;
      // scrub 관성 (가이드의 scrub:0.6 에 해당)
      current += (target - current) * 0.18;
      if (Math.abs(target - current) < 0.004) current = target;

      if (duration) {
        // 재생 중이면 seek 가 무시되므로 반드시 멈춘 상태로 조작
        if (!video.paused) video.pause();
        if (isFinite(current)) {
          try { video.currentTime = Math.max(0, Math.min(duration - 0.02, current)); } catch (e) {}
        }
      }
      paint(progress());
      requestAnimationFrame(loop);
    }

    // 스크럽 영상은 화면 밖에서도 seek 가능해야 하므로 즉시 로드
    if (video.dataset.src && !video.src) video.src = video.dataset.src;
    video.pause();
  }

  /* ---------- 4. 진입 페이드 ---------- */
  if ('IntersectionObserver' in window) {
    var revealables = document.querySelectorAll('[data-reveal]');
    if (revealables.length) {
      revealables.forEach(function (el) {
        if (reduced) { el.style.opacity = 1; el.style.transform = 'none'; return; }
        el.style.opacity = 0;
        el.style.transform = 'translateY(18px)';
        el.style.transition = 'opacity .7s cubic-bezier(.22,.61,.36,1), transform .7s cubic-bezier(.22,.61,.36,1)';
      });
      if (!reduced) {
        var ro = new IntersectionObserver(function (entries) {
          entries.forEach(function (e) {
            if (e.isIntersecting) {
              e.target.style.opacity = 1;
              e.target.style.transform = 'none';
              ro.unobserve(e.target);
            }
          });
        }, { rootMargin: '0px 0px -12% 0px', threshold: 0.08 });
        revealables.forEach(function (el) { ro.observe(el); });
      }
    }
  }
})();
