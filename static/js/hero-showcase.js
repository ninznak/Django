/**
 * Hero showcase: cross-fade slides, auto-advance, dots, arrows, swipe.
 */
(function () {
    "use strict";

    const root = document.querySelector("[data-hero-showcase]");
    if (!root) return;

    const slides = Array.from(root.querySelectorAll("[data-hero-showcase-slide]"));
    const dots = Array.from(root.querySelectorAll("[data-hero-showcase-dot]"));
    if (slides.length < 2) return;

    const AUTO_MS = 6000;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let index = 0;
    let timer = null;
    let touchStartX = 0;
    let touchStartY = 0;

    function goTo(next, userInitiated) {
        index = ((next % slides.length) + slides.length) % slides.length;

        slides.forEach(function (slide, i) {
            const active = i === index;
            slide.classList.toggle("is-active", active);
            slide.setAttribute("aria-hidden", active ? "false" : "true");
            slide.setAttribute("tabindex", active ? "0" : "-1");
        });

        dots.forEach(function (dot, i) {
            const active = i === index;
            dot.classList.toggle("is-active", active);
            dot.setAttribute("aria-selected", active ? "true" : "false");
        });

        if (userInitiated) {
            restartAuto();
        }
    }

    function nextSlide(userInitiated) {
        goTo(index + 1, userInitiated);
    }

    function prevSlide(userInitiated) {
        goTo(index - 1, userInitiated);
    }

    function stopAuto() {
        if (timer) {
            clearInterval(timer);
            timer = null;
        }
    }

    function startAuto() {
        if (reducedMotion) return;
        stopAuto();
        timer = setInterval(function () {
            nextSlide(false);
        }, AUTO_MS);
    }

    function restartAuto() {
        stopAuto();
        startAuto();
    }

    root.querySelector("[data-hero-showcase-prev]")?.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        prevSlide(true);
    });

    root.querySelector("[data-hero-showcase-next]")?.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        nextSlide(true);
    });

    dots.forEach(function (dot) {
        dot.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            goTo(parseInt(dot.getAttribute("data-hero-showcase-dot"), 10) || 0, true);
        });
    });

    root.addEventListener("mouseenter", stopAuto);
    root.addEventListener("mouseleave", startAuto);
    root.addEventListener("focusin", stopAuto);
    root.addEventListener("focusout", function (e) {
        if (!root.contains(e.relatedTarget)) {
            startAuto();
        }
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
            if (Math.abs(dx) < 44 || Math.abs(dx) < Math.abs(dy)) return;
            if (dx < 0) {
                nextSlide(true);
            } else {
                prevSlide(true);
            }
        },
        { passive: true }
    );

    root.addEventListener("keydown", function (e) {
        if (e.key === "ArrowLeft") {
            e.preventDefault();
            prevSlide(true);
        } else if (e.key === "ArrowRight") {
            e.preventDefault();
            nextSlide(true);
        }
    });

    startAuto();
})();
