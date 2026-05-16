/**
 * Swap news article RU/EN fields when the site language toggle changes.
 * Expects #article-i18-data JSON from news_article.html.
 */
(function () {
    "use strict";

    function parsePayload(id) {
        const el = document.getElementById(id);
        if (!el || !el.textContent) return null;
        try {
            let parsed = JSON.parse(el.textContent);
            // Guard against double-encoded JSON (legacy bug).
            if (typeof parsed === "string") {
                parsed = JSON.parse(parsed);
            }
            return parsed;
        } catch (e) {
            console.warn("article-i18n: invalid JSON", e);
            return null;
        }
    }

    function setMeta(name, content) {
        if (!content) return;
        const el = document.querySelector(`meta[name="${name}"]`);
        if (el) el.setAttribute("content", content);
    }

    function setPropertyMeta(property, content) {
        if (!content) return;
        const el = document.querySelector(`meta[property="${property}"]`);
        if (el) el.setAttribute("content", content);
    }

    function applyArticlePageI18n(lang) {
        const data = parsePayload("article-i18-data");
        if (!data) return;

        const locale = lang === "en" && data.en ? "en" : "ru";
        const block = data[locale];
        if (!block) return;

        const titleEl = document.querySelector("[data-article-field='title']");
        if (titleEl) titleEl.textContent = block.title;

        const tagEl = document.querySelector("[data-article-field='tag']");
        if (tagEl) tagEl.textContent = block.tag;

        const excerptEl = document.querySelector("[data-article-field='excerpt']");
        if (excerptEl) excerptEl.textContent = block.excerpt;

        const bodyEl = document.querySelector("[data-article-field='body']");
        if (bodyEl && block.body_html) bodyEl.innerHTML = block.body_html;

        const coverImg = document.querySelector("[data-article-field='cover']");
        if (coverImg && block.title) coverImg.setAttribute("alt", block.title);

        const seoData = parsePayload("article-seo-i18-data");
        if (seoData && seoData[locale]) {
            const seo = seoData[locale];
            document.title = seo.title;
            setMeta("description", seo.description);
            setPropertyMeta("og:title", seo.title);
            setPropertyMeta("og:description", seo.description);
            setMeta("twitter:title", seo.title);
            setMeta("twitter:description", seo.description);
        }
    }

    function applyArticleListI18n(lang) {
        document.querySelectorAll("[data-article-i18-title]").forEach((el) => {
            const ru = el.getAttribute("data-ru");
            const en = el.getAttribute("data-en");
            if (lang === "en" && en) {
                el.textContent = en;
            } else if (ru) {
                el.textContent = ru;
            }
        });
        document.querySelectorAll("[data-article-i18-excerpt]").forEach((el) => {
            const ru = el.getAttribute("data-ru");
            const en = el.getAttribute("data-en");
            if (lang === "en" && en) {
                el.textContent = en;
            } else if (ru) {
                el.textContent = ru;
            }
        });
        document.querySelectorAll("[data-article-i18-tag]").forEach((el) => {
            const ru = el.getAttribute("data-ru");
            const en = el.getAttribute("data-en");
            if (lang === "en" && en) {
                el.textContent = en;
            } else if (ru) {
                el.textContent = ru;
            }
        });
    }

    window.applyArticleI18n = function (lang) {
        applyArticlePageI18n(lang);
        applyArticleListI18n(lang);
    };
})();
