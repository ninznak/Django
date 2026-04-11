(function () {
  var API = '/api/cart/';

  function getCsrf() {
    var inp = document.querySelector('[name=csrfmiddlewaretoken]');
    if (inp && inp.value) return inp.value;
    var m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function formatMoney(cents) {
    return '$' + (cents / 100).toFixed(2);
  }

  function cartI18n() {
    return window.__CART_I18N__ || {};
  }

  async function apiPost(body) {
    var r = await fetch(API, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrf(),
      },
      credentials: 'same-origin',
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error('cart api');
    return r.json();
  }

  async function apiGet() {
    var r = await fetch(API, { credentials: 'same-origin' });
    if (!r.ok) throw new Error('cart get');
    return r.json();
  }

  function updateBadge(n) {
    var b = document.getElementById('cart-badge');
    if (!b) return;
    b.textContent = n > 99 ? '99+' : String(n);
    b.classList.toggle('hidden', n === 0);
  }

  function renderDrawer(data) {
    var root = document.getElementById('cart-drawer-lines');
    var footer = document.getElementById('cart-drawer-footer');
    var empty = document.getElementById('cart-empty');
    var clearBtn = document.getElementById('cart-clear');
    if (!root) return;
    var lines = data.lines || [];
    var t = cartI18n();
    if (lines.length === 0) {
      root.innerHTML = '';
      if (empty) empty.classList.remove('hidden');
      if (footer) footer.classList.add('hidden');
      if (clearBtn) clearBtn.classList.add('hidden');
      return;
    }
    if (empty) empty.classList.add('hidden');
    if (footer) footer.classList.remove('hidden');
    if (clearBtn) clearBtn.classList.remove('hidden');
    root.innerHTML = lines
      .map(function (line) {
        var p = line.product;
        return (
          '<li class="cart-line flex gap-3 border-b pb-4 last:border-0" style="border-color: var(--line)" data-pid="' +
          p.id +
          '" data-qty="' +
          line.qty +
          '">' +
          '<div class="h-16 w-20 flex-shrink-0 overflow-hidden rounded-xl border bg-white/50" style="border-color: var(--line)">' +
          '<img src="' +
          escapeHtml(p.img) +
          '" alt="' +
          escapeHtml(p.alt || '') +
          '" class="h-full w-full object-cover" loading="lazy" width="80" height="64"/>' +
          '</div>' +
          '<div class="min-w-0 flex-1">' +
          '<p class="font-display text-sm font-semibold line-clamp-2" style="color: var(--text)">' +
          escapeHtml(p.title) +
          '</p>' +
          '<p class="text-xs mt-0.5" style="color: var(--muted)">' +
          escapeHtml(p.price) +
          '</p>' +
          '<div class="mt-2 flex flex-wrap items-center gap-2">' +
          '<span class="text-[10px] uppercase tracking-wider" style="color: var(--muted)">' +
          escapeHtml(t.qty || 'Qty') +
          '</span>' +
          '<div class="flex items-center gap-1 rounded-lg border bg-white/50" style="border-color: var(--line)">' +
          '<button type="button" class="px-2 py-1 text-sm cart-qty hover:opacity-80" data-delta="-1">−</button>' +
          '<span class="min-w-[1.5rem] text-center text-sm font-medium">' +
          line.qty +
          '</span>' +
          '<button type="button" class="px-2 py-1 text-sm cart-qty hover:opacity-80" data-delta="1">+</button>' +
          '</div>' +
          '<button type="button" class="ml-auto text-xs cart-remove hover:underline" style="color: var(--muted)">' +
          escapeHtml(t.remove || 'Remove') +
          '</button>' +
          '</div></div></li>'
        );
      })
      .join('');
    var subEl = document.getElementById('cart-subtotal-val');
    if (subEl) subEl.textContent = formatMoney(data.subtotalCents);
  }

  function applyDrawerLabels() {
    var t = cartI18n();
    var el = document.getElementById('cart-drawer-title');
    if (el && t.title) el.textContent = t.title;
    el = document.getElementById('cart-empty');
    if (el && t.empty) el.textContent = t.empty;
    el = document.getElementById('cart-subtotal-label');
    if (el && t.subtotal) el.textContent = t.subtotal;
    el = document.getElementById('cart-checkout-hint');
    if (el && t.checkoutHint) el.textContent = t.checkoutHint;
    el = document.getElementById('cart-checkout-btn');
    if (el && t.checkout) el.textContent = t.checkout;
    el = document.getElementById('cart-clear');
    if (el && t.clear) el.textContent = t.clear;
    el = document.getElementById('cart-drawer-close');
    if (el) el.setAttribute('aria-label', t.close || 'Close');
    el = document.getElementById('cart-toggle');
    if (el) el.setAttribute('aria-label', t.navCart || 'Cart');
    el = document.getElementById('cart-drawer-backdrop');
    if (el && t.close) el.setAttribute('aria-label', t.close);
  }

  async function refresh() {
    var data = await apiGet();
    updateBadge(data.totalItems);
    renderDrawer(data);
    return data;
  }

  async function postAction(body) {
    var data = await apiPost(body);
    updateBadge(data.totalItems);
    renderDrawer(data);
    applyDrawerLabels();
    return data;
  }

  document.addEventListener('DOMContentLoaded', function () {
    var drawer = document.getElementById('cart-drawer');
    var backdrop = document.getElementById('cart-drawer-backdrop');
    var closeBtn = document.getElementById('cart-drawer-close');
    var clearBtn = document.getElementById('cart-clear');
    var openBtn = document.getElementById('cart-toggle');

    function openDrawer() {
      if (drawer) drawer.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
      refresh().catch(function () {});
    }

    function closeDrawer() {
      if (drawer) drawer.classList.add('hidden');
      document.body.style.overflow = '';
    }

    window.openCartDrawer = openDrawer;
    window.closeCartDrawer = closeDrawer;
    window.refreshCartBadge = function () {
      refresh().catch(function () {});
    };

    if (openBtn) openBtn.addEventListener('click', openDrawer);
    if (backdrop) backdrop.addEventListener('click', closeDrawer);
    if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeDrawer();
    });

    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        postAction({ action: 'clear' }).catch(function () {});
      });
    }

    var linesRoot = document.getElementById('cart-drawer-lines');
    if (linesRoot) {
      linesRoot.addEventListener('click', function (e) {
        var line = e.target.closest('.cart-line');
        if (!line) return;
        var pid = parseInt(line.getAttribute('data-pid'), 10);
        var cur = parseInt(line.getAttribute('data-qty'), 10);
        if (e.target.closest('.cart-qty')) {
          var btn = e.target.closest('.cart-qty');
          var delta = parseInt(btn.getAttribute('data-delta'), 10);
          postAction({ action: 'set', product_id: pid, qty: cur + delta }).catch(function () {});
          return;
        }
        if (e.target.closest('.cart-remove')) {
          postAction({ action: 'remove', product_id: pid }).catch(function () {});
        }
      });
    }

    document.querySelectorAll('[data-add-to-cart]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = parseInt(btn.getAttribute('data-product-id'), 10);
        if (!id) return;
        postAction({ action: 'add', product_id: id, qty: 1 })
          .then(function () {
            if (drawer) drawer.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
            applyDrawerLabels();
          })
          .catch(function () {});
      });
    });

    applyDrawerLabels();
    window.applyCartI18n = applyDrawerLabels;
    refresh().catch(function () {});
  });
})();
