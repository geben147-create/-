/* ============================================================
   Cinematic Pipeline — runtime
   No external dependencies. No GSAP, no CDN, no build step.

   Three jobs:
     1. wire every [data-clip] <video> to the manifest in media/sources.js
     2. load section videos only when they scroll into view
     3. drive the pinned scrub section from scroll position
   ============================================================ */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var wrap = document.getElementById('scrubWrap');
  var scrubVideo = document.getElementById('scrubVideo');
  var bar = document.getElementById('scrubBar');
  var steps = [].slice.call(document.querySelectorAll('#scrubSteps li'));
  var scrubReady = false;

  var M = window.CLIP_SOURCES || { use: 'remote', clips: {} };
  var USE = M.use === 'local' ? 'local' : 'remote';

  function pick(slot) {
    if (!slot) return '';
    // fall back to whichever one exists, so a half-localised repo still runs
    return slot[USE] || slot.remote || slot.local || '';
  }

  /* ----------------------------------------------------------
     1 · wire the videos
     ---------------------------------------------------------- */
  var videos = [].slice.call(document.querySelectorAll('video[data-clip]'));

  videos.forEach(function (v) {
    var clip = M.clips[v.dataset.clip];
    if (!clip) return;

    // The render's own base colour, painted behind the video. If the network
    // never delivers a frame the section still looks intentional instead of
    // showing a black rectangle.
    if (clip.tint) v.style.background = clip.tint;

    var poster = pick(clip.poster);
    if (poster) v.setAttribute('poster', poster);

    // Same tint + poster on the reduced-motion still, which replaces the
    // video entirely when the OS asks for less movement.
    var still = document.querySelector('[data-poster="' + v.dataset.clip + '"]');
    if (still) {
      still.style.cssText =
        'position:absolute;inset:0;z-index:0;background-size:cover;' +
        'background-position:50% 46%;' +
        (clip.tint ? 'background-color:' + (clip.tintFlat || '#EFEFF4') + ';' : '');
      if (poster) still.style.backgroundImage = 'url("' + poster + '")';
    }
    // the small tile fallbacks are <img>, not divs
    var img = document.querySelector('img[data-poster-img="' + v.dataset.clip + '"]');
    if (img && poster) img.src = poster;

    if (reduceMotion) return;   // never attach a source, never autoplay

    var desktop = pick(clip.desktop);
    var mobile = pick(clip.mobile);
    var webm = pick(clip.webm);
    if (!desktop && !mobile) return;

    // <source media=...> is only honoured at parse time, so build the list
    // before anything triggers a load. Narrow source first — first match wins.
    function src(url, type, media) {
      var s = document.createElement('source');
      s.src = url;
      if (type) s.type = type;
      if (media) s.media = media;
      return s;
    }
    var frag = document.createDocumentFragment();
    if (mobile) frag.appendChild(src(mobile, 'video/mp4', '(max-width: 768px)'));
    if (webm) frag.appendChild(src(webm, 'video/webm'));
    if (desktop) frag.appendChild(src(desktop, 'video/mp4'));
    v.appendChild(frag);

    v.dataset.wired = '1';
    // The hero carries preload="metadata" and autoplay; everything else is
    // preload="none" and waits for the observer below.
    if (v.hasAttribute('autoplay')) {
      v.load();
      v.play().catch(function () {});   // a refused autoplay is not an error
    }
  });

  // Any still that has no video partner (or reduced motion) still needs showing
  if (reduceMotion) {
    [].slice.call(document.querySelectorAll('.stage__poster')).forEach(function (el) {
      el.style.display = 'block';
    });
  }

  /* ----------------------------------------------------------
     2 · load section video only when it comes into view
     ---------------------------------------------------------- */
  if (!reduceMotion && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        var v = e.target;
        if (v === scrubVideo) return;          // the scrub clip is driven by scroll
        if (e.isIntersecting) {
          if (v.dataset.wired && v.preload === 'none') {
            v.preload = 'auto';
            v.load();
          }
          v.play().catch(function () {});
        } else {
          v.pause();                            // off-screen: save battery and CPU
        }
      });
    }, { rootMargin: '200px 0px', threshold: 0.1 });

    videos.forEach(function (v) { if (!v.hasAttribute('autoplay')) io.observe(v); });
  }

  /* ----------------------------------------------------------
     3 · pinned scrub — native position:sticky, no library
     ---------------------------------------------------------- */
  if (scrubVideo) {
    scrubVideo.addEventListener('loadedmetadata', function () {
      scrubReady = !!(scrubVideo.duration && isFinite(scrubVideo.duration));
      tick();
    });
    // start fetching it a screen early — a scrub clip that is still buffering
    // reads as a frozen section
    if (!reduceMotion && 'IntersectionObserver' in window && wrap) {
      new IntersectionObserver(function (es, ob) {
        if (es[0].isIntersecting) {
          if (scrubVideo.dataset.wired) { scrubVideo.preload = 'auto'; scrubVideo.load(); }
          ob.disconnect();
        }
      }, { rootMargin: '100% 0px' }).observe(wrap);
    }
  }

  function progress() {
    if (!wrap) return 0;
    var span = wrap.offsetHeight - window.innerHeight;
    if (span <= 0) return 0;
    var p = -wrap.getBoundingClientRect().top / span;
    return p < 0 ? 0 : p > 1 ? 1 : p;
  }

  function tick() {
    if (!wrap) return;
    var p = progress();

    if (bar) bar.style.width = (p * 100).toFixed(2) + '%';

    for (var i = 0; i < steps.length; i++) {
      // each step lights up slightly before its share of the track
      steps[i].dataset.on = (p >= (i / steps.length) * 0.92) ? '1' : '0';
    }

    if (scrubReady && !reduceMotion) {
      // seeking is ignored while the element is playing
      if (!scrubVideo.paused) scrubVideo.pause();
      var t = p * Math.max(0, scrubVideo.duration - 0.05);
      if (Math.abs(scrubVideo.currentTime - t) > 0.03) {
        try { scrubVideo.currentTime = t; } catch (err) { /* seek not ready yet */ }
      }
    }
  }

  /* ----------------------------------------------------------
     4 · nav state + a single rAF-throttled scroll listener
     ---------------------------------------------------------- */
  var nav = document.getElementById('nav');
  var queued = false;

  function onScroll() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () {
      queued = false;
      if (nav) nav.dataset.stuck = window.scrollY > 12 ? 'true' : 'false';
      tick();
    });
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
  window.addEventListener('orientationchange', onScroll);
  onScroll();
})();
