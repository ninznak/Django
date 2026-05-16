/**
 * Mobile hero spotlight: slides, arrows inside canvas, swipe.
 */
(function () {
    "use strict";

    const root = document.querySelector("[data-hero-spotlight]");
    if (!root) return;

    const track = root.querySelector("[data-hero-spotlight-track]");
    const slideCount = root.querySelectorAll(".hero-mobile-spotlight-slide").length;
    if (!track || slideCount < 2) return;

    let index = 0;
    let touchStartX = 0;
    let touchStartY = 0;

    function goTo(next) {
        index = ((next % slideCount) + slideCount) % slideCount;
        var offset = "-" + index * 100 + "%";
        track.style.transform = "translate3d(" + offset + ", 0, 0)";
        track.style.webkitTransform = "translate3d(" + offset + ", 0, 0)";
        root.querySelectorAll("[data-hero-spotlight-dot]").forEach(function (dot, i) {
            const active = i === index;
            dot.classList.toggle("is-active", active);
            dot.setAttribute("aria-selected", active ? "true" : "false");
        });
    }

    root.querySelector("[data-hero-spotlight-prev]")?.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        goTo(index - 1);
    });

    root.querySelector("[data-hero-spotlight-next]")?.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        goTo(index + 1);
    });

    root.querySelectorAll("[data-hero-spotlight-dot]").forEach(function (dot) {
        dot.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            goTo(parseInt(dot.getAttribute("data-hero-spotlight-dot"), 10) || 0);
        });
    });

    root.addEventListener(
        "touchstart",
        function (e) {
            if (!e.touches.length) return;
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
        },
        { passive: true }
    );

    root.addEventListener(
        "touchend",
        function (e) {
            if (!e.changedTouches.length) return;
            const dx = e.changedTouches[0].clientX - touchStartX;
            const dy = e.changedTouches[0].clientY - touchStartY;
            if (Math.abs(dx) < 40 || Math.abs(dx) < Math.abs(dy)) return;
            goTo(dx < 0 ? index + 1 : index - 1);
        },
        { passive: true }
    );
})();
