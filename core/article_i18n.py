"""Client-side news article locale payloads (RU default, optional EN)."""

from __future__ import annotations

from django.utils.safestring import SafeString

from core.seo import NEWS_ARTICLE_SEO, get_seo, news_article_seo_overrides
from core.templatetags.article_extras import render_article_body


def article_has_english(article) -> bool:
    return bool((article.title_en or "").strip() and (article.content_en or "").strip())


def render_body_html(content: str) -> str:
    result = render_article_body(content)
    return str(result) if isinstance(result, SafeString) else result


def build_article_i18_payload(article) -> dict[str, dict[str, str]]:
    payload: dict[str, dict[str, str]] = {
        "ru": {
            "title": article.title,
            "excerpt": article.excerpt or "",
            "tag": article.tag or "Статья",
            "body_html": render_body_html(article.content),
        }
    }
    if article_has_english(article):
        payload["en"] = {
            "title": article.title_en,
            "excerpt": article.excerpt_en or "",
            "tag": article.tag_en or "Article",
            "body_html": render_body_html(article.content_en),
        }
    return payload


def build_article_seo_i18_payload(request, slug: str, article) -> dict[str, dict[str, str]] | None:
    if not article_has_english(article):
        return None

    ru_seo = get_seo(
        request, **news_article_seo_overrides(request, slug, article.title)
    )
    payload: dict[str, dict[str, str]] = {
        "ru": {
            "title": ru_seo["title"],
            "description": ru_seo["description"],
        }
    }

    entry = NEWS_ARTICLE_SEO.get(slug, {})
    en_entry = entry.get("en")
    if en_entry:
        payload["en"] = {
            "title": en_entry["title"],
            "description": en_entry["description"],
        }
    else:
        payload["en"] = {
            "title": f"{article.title_en} — KurilenkoArt | News: 3D, medals, bas-relief",
            "description": (
                article.excerpt_en
                or f"Article «{article.title_en}» — 3D modeling, medallic art, bas-relief, "
                "digital sculpture and AI. KurilenkoArt."
            ),
        }
    return payload
