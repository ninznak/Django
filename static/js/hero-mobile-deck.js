/**
 * Hero mobile stack: tap / swipe / indicators. Rollback: remove script tag + HERO_MOBILE_STACK_ENABLED=0.
 */
(function () {
  const deck = document.getElementById("heroMobileDeck");
  if (!deck) return;

  const cards = Array.from(deck.querySelectorAll(".hero-m-card"));
  const indicators = Array.from(
    document.querySelectorAll("[data-hero-mobile-indicator]")
  );
  const openLink = document.getElementById("heroMobileDeckLink");
  const prevBtn = document.querySelector("[data-hero-mobile-prev]");
  const nextBtn = document.querySelector("[data-hero-mobile-next]");
  if (cards.length < 1) return;

  const total = cards.length;
  let current = 1;
  let startX = 0;
  let deltaX = 0;
  let dragging = false;
  const SWIPE_THRESHOLD = 56;

  function applyStack() {
    cards.forEach(function (card, i) {
      card.classList.remove("is-active", "is-behind-1", "is-behind-2");
      const rel = (i - current + total) % total;
      if (rel === 0) card.classList.add("is-active");
      else if (rel === 1) card.classList.add("is-behind-1");
      else if (rel === 2) card.classList.add("is-behind-2");
    });
    indicators.forEach(function (btn, i) {
      btn.classList.toggle("is-active", i === current);
      btn.setAttribute("aria-selected", i === current ? "true" : "false");
    });
    const front = cards[current];
    if (openLink && front) {
      openLink.setAttribute("href", front.getAttribute("data-href") || "#");
    }
  }

  function goTo(idx) {
    current = ((idx % total) + total) % total;
    applyStack();
  }

  function next() {
    goTo(current + 1);
  }

  function prev() {
    goTo(current - 1);
  }

  function resetInlineTransforms() {
    cards.forEach(function (card) {
      card.style.transform = "";
    });
  }

  deck.addEventListener("click", function (e) {
    if (e.target.closest("#heroMobileDeckLink")) return;
    if (e.target.closest("[data-hero-mobile-indicator]")) return;
    if (e.target.closest("[data-hero-mobile-prev], [data-hero-mobile-next]")) return;
    next();
  });

  if (prevBtn) {
    prevBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      prev();
    });
  }
  if (nextBtn) {
    nextBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      next();
    });
  }

  deck.addEventListener("keydown", function (e) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      next();
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      next();
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      prev();
    }
  });

  indicators.forEach(function (btn, i) {
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      goTo(i);
    });
  });

  deck.addEventListener(
    "touchstart",
    function (e) {
      if (e.touches.length !== 1) return;
      dragging = true;
      startX = e.touches[0].clientX;
      deltaX = 0;
    },
    { passive: true }
  );

  deck.addEventListener(
    "touchmove",
    function (e) {
      if (!dragging || e.touches.length !== 1) return;
      deltaX = e.touches[0].clientX - startX;
      const active = cards[current];
      if (active) {
        active.style.transform =
          "translateX(calc(-50% + " + deltaX * 0.35 + "px)) rotate(" + deltaX * 0.02 + "deg)";
      }
    },
    { passive: true }
  );

  deck.addEventListener(
    "touchend",
    function () {
      if (!dragging) return;
      dragging = false;
      if (deltaX > SWIPE_THRESHOLD) prev();
      else if (deltaX < -SWIPE_THRESHOLD) next();
      deltaX = 0;
      resetInlineTransforms();
    },
    { passive: true }
  );

  applyStack();
})();
