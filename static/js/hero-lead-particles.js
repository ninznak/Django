/**
 * Hero lead — particles drift right from the left accent bar through the subtitle.
 */
(function () {
    "use strict";

    function isIOSWebKit() {
        return document.documentElement.classList.contains("ios-webkit");
    }

    function init() {
        const wrap = document.querySelector(".hero-lead-wrap");
        if (!wrap) return;

        const canvas = wrap.querySelector(".hero-lead-particles");
        if (!canvas) return;

        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

        const ctx = canvas.getContext("2d", { alpha: true });
        if (!ctx) return;

        const TRAVEL_MULTIPLIER = 2;
        const iosBoost = isIOSWebKit();

        const particles = [];
        let width = 0;
        let height = 0;
        let wrapWidth = 0;
        let dpr = 1;
        let theme = "light";
        let rafId = 0;
        let lastSpawn = 0;

        function palette() {
            if (theme === "dark") {
                return {
                    core: [51, 109, 243],
                    accent: [246, 34, 189],
                };
            }
            return {
                core: [61, 122, 79],
                accent: [168, 201, 87],
            };
        }

        function resize() {
            const rect = wrap.getBoundingClientRect();
            dpr = Math.min(window.devicePixelRatio || 1, 2);
            wrapWidth = Math.max(1, Math.round(rect.width));
            width = wrapWidth * TRAVEL_MULTIPLIER;
            height = Math.max(1, Math.round(rect.height));
            if (height < 8 || wrapWidth < 8) return;

            canvas.width = Math.floor(width * dpr);
            canvas.height = Math.floor(height * dpr);
            canvas.style.width = width + "px";
            canvas.style.height = height + "px";
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        }

        function spawnParticle() {
            const pal = palette();
            const rgb = Math.random() < 0.38 ? pal.accent : pal.core;
            const band = height * 0.88;
            const yOffset = height * 0.06;

            particles.push({
                x: 0.5 + Math.random() * 2.5,
                y: yOffset + Math.random() * band,
                vx: 0.84 + Math.random() * 1.9,
                vy: (Math.random() - 0.5) * 0.22,
                r: (0.55 + Math.random() * 1.65) * (iosBoost ? 1.2 : 1),
                life: 0,
                maxLife: 160 + Math.random() * 240,
                rgb: rgb,
            });
        }

        function drawParticle(p) {
            const t = p.life / p.maxLife;
            let alpha = 1;
            if (t < 0.1) {
                alpha = t / 0.1;
            } else if (t > 0.72) {
                alpha = (1 - t) / 0.28;
            }
            alpha *= iosBoost ? 0.82 : 0.58;

            const [r, g, b] = p.rgb;
            const glowAlpha = alpha * (iosBoost ? 0.28 : 0.18);

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r * 2.4, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(" + r + "," + g + "," + b + "," + glowAlpha + ")";
            ctx.fill();

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(" + r + "," + g + "," + b + "," + alpha + ")";
            ctx.fill();
        }

        function tick(ts) {
            if (width < 8 || height < 8) {
                resize();
                rafId = window.requestAnimationFrame(tick);
                return;
            }

            if (!lastSpawn) lastSpawn = ts;
            if (ts - lastSpawn > 110) {
                spawnParticle();
                if (Math.random() < 0.5) spawnParticle();
                lastSpawn = ts;
            }

            ctx.clearRect(0, 0, width, height);

            for (let i = particles.length - 1; i >= 0; i--) {
                const p = particles[i];
                p.life += 1;
                p.x += p.vx;
                p.y += p.vy;
                p.vy += (Math.random() - 0.5) * 0.02;

                if (p.life >= p.maxLife || p.x > width + 10 || p.y < -6 || p.y > height + 6) {
                    particles.splice(i, 1);
                    continue;
                }

                drawParticle(p);
            }

            rafId = window.requestAnimationFrame(tick);
        }

        function start() {
            theme = document.documentElement.getAttribute("data-theme") || "light";
            resize();
            particles.length = 0;
            lastSpawn = 0;
            window.cancelAnimationFrame(rafId);
            rafId = window.requestAnimationFrame(tick);
        }

        if (typeof ResizeObserver !== "undefined") {
            const ro = new ResizeObserver(resize);
            ro.observe(wrap);
        } else {
            window.addEventListener("resize", resize, { passive: true });
        }

        const themeObserver = new MutationObserver(function () {
            const next = document.documentElement.getAttribute("data-theme") || "light";
            if (next !== theme) {
                theme = next;
                particles.length = 0;
            }
        });
        themeObserver.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ["data-theme"],
        });

        document.addEventListener("visibilitychange", function () {
            if (document.hidden) {
                window.cancelAnimationFrame(rafId);
            } else {
                resize();
                rafId = window.requestAnimationFrame(tick);
            }
        });

        window.addEventListener("load", resize, { passive: true });
        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(resize).catch(function () {});
        }

        start();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
