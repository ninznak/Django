/**
 * Lightweight UX helpers — remove script tag from base.html to roll back.
 */
(function () {
  'use strict';

  function buildRowAlignedWindows(totalItems, targetPerPage, rowLcm) {
    var windows = [];
    var from = 0;
    var total = Number(totalItems) || 0;
    var perPage = Number(targetPerPage) || 0;
    var lcm = Number(rowLcm) || 1;

    if (total <= 0 || perPage <= 0) return windows;

    while (from < total) {
      var remaining = total - from;
      if (remaining <= perPage) {
        windows.push({ from: from, to: total });
        break;
      }

      var size = perPage;
      var remainder = size % lcm;
      if (remainder !== 0) {
        var need = lcm - remainder;
        var availableFromNext = remaining - size;
        if (availableFromNext >= need) {
          // Fill incomplete row from the next page start.
          size += need;
        } else {
          // Not enough to fill: shift boundary back to previous full row.
          var down = size - remainder;
          if (down > 0 && (remaining - down) > 0) {
            size = down;
          }
        }
      }

      windows.push({ from: from, to: from + size });
      from += size;
    }

    return windows;
  }

  function renderNumberedPager(host, options) {
    if (!host || !options) return;

    var current = Number(options.current) || 1;
    var total = Number(options.total) || 1;
    var makeHref = options.makeHref;
    var onNavigate = options.onNavigate;

    host.innerHTML = '';
    if (!Number.isFinite(current) || !Number.isFinite(total) || total < 2) return;

    function addDots() {
      var dots = document.createElement('span');
      dots.className = 'shop-page-dots';
      dots.textContent = '...';
      host.appendChild(dots);
    }

    function addPage(p) {
      if (p === current) {
        var cur = document.createElement('span');
        cur.className = 'shop-page-current';
        cur.textContent = String(p);
        host.appendChild(cur);
        return;
      }

      if (typeof onNavigate === 'function') {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'shop-page-link';
        btn.textContent = String(p);
        btn.addEventListener('click', function () {
          onNavigate(p);
        });
        host.appendChild(btn);
        return;
      }

      var a = document.createElement('a');
      a.className = 'shop-page-link';
      a.href = typeof makeHref === 'function' ? makeHref(p) : ('?page=' + String(p));
      a.textContent = String(p);
      host.appendChild(a);
    }

    if (total <= 7) {
      for (var p = 1; p <= total; p += 1) addPage(p);
      return;
    }

    var start = Math.max(2, current - 1);
    var end = Math.min(total - 1, current + 1);
    if (current <= 3) {
      start = 2;
      end = 4;
    } else if (current >= total - 2) {
      start = total - 3;
      end = total - 1;
    }

    addPage(1);
    if (start > 2) addDots();
    for (var pp = start; pp <= end; pp += 1) addPage(pp);
    if (end < total - 1) addDots();
    addPage(total);
  }

  // Shared helpers for page templates (shop/free_models).
  window.PaginationUtils = {
    buildRowAlignedWindows: buildRowAlignedWindows,
    renderNumberedPager: renderNumberedPager
  };

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
