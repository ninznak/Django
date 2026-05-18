/**
 * Sync data-text for .hero-glitch (CSS ::before/::after) after i18n updates.
 * Rollback: remove script + HERO_TITLE_GLITCH_ENABLED=0
 */
(function (global) {
  function syncHeroTitleGlitch() {
    document.querySelectorAll("[data-hero-glitch]").forEach(function (el) {
      var text = (el.textContent || "").trim();
      if (!text) return;
      el.setAttribute("data-text", text);
      el.setAttribute("aria-label", text);
    });
  }

  global.syncHeroTitleGlitch = syncHeroTitleGlitch;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", syncHeroTitleGlitch);
  } else {
    syncHeroTitleGlitch();
  }
})(window);
