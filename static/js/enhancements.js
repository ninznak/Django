/**
 * Lightweight UX helpers — remove script tag from base.html to roll back.
 */
(function () {
  'use strict';

  // Skip link: move focus into main for screen readers
  var skip = document.querySelector('.skip-to-content');
  var main = document.getElementById('main-content');
  if (skip && main) {
    skip.addEventListener('click', function () {
      main.setAttribute('tabindex', '-1');
      main.focus({ preventScroll: true });
    });
  }

  // Header shadow on scroll (throttled)
  var header = document.querySelector('.site-header');
  if (header) {
    var ticking = false;
    function onScroll() {
      if (!ticking) {
        window.requestAnimationFrame(function () {
          var y = window.scrollY || document.documentElement.scrollTop;
          header.classList.toggle('is-scrolled', y > 12);
          ticking = false;
        });
        ticking = true;
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }
})();
