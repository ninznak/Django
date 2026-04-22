import re

from django import template
from django.templatetags.static import static
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

_IMAGE_RE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)$")
_ORDERED_ITEM_RE = re.compile(r"^\d+\.\s+(?P<text>.+)$")

_INLINE_BOLD_RE = re.compile(r"\*\*(?P<body>\S(?:[^*]*\S)?)\*\*")
_INLINE_ITALIC_RE = re.compile(r"\*(?P<body>\S(?:[^*]*\S)?)\*")
_INLINE_LINK_RE = re.compile(r"(?<!!)\[(?P<label>[^\]]+)\]\((?P<url>[^)\s]+)\)")


def _resolve_image_path(raw_path: str) -> str:
    path = raw_path.strip()
    if not path:
        return ""
    if path.startswith(("http://", "https://", "/")):
        return path
    return static(path)


def _is_safe_url(url: str) -> bool:
    candidate = url.strip()
    if not candidate:
        return False
    lowered = candidate.lower()
    if lowered.startswith(("http://", "https://", "mailto:", "tel:")):
        return True
    if candidate.startswith(("/", "#", "./", "../")):
        return True
    # Relative path without scheme is safe; reject anything that looks like
    # an unknown scheme (e.g. "javascript:", "data:") to prevent XSS.
    head = candidate.split("/", 1)[0]
    return ":" not in head


def _apply_inline_markup(raw_text: str) -> str:
    """Escape HTML and apply inline markdown (bold, italic, links)."""
    text = escape(raw_text)

    text = _INLINE_BOLD_RE.sub(
        lambda m: f"<strong>{m.group('body')}</strong>", text
    )
    text = _INLINE_ITALIC_RE.sub(
        lambda m: f"<em>{m.group('body')}</em>", text
    )

    def _link_sub(match: "re.Match[str]") -> str:
        label = match.group("label")
        url = match.group("url")
        if not _is_safe_url(url):
            return match.group(0)
        return (
            f'<a href="{url}" class="text-[#3d7a4f] underline hover:no-underline" '
            f'rel="noopener noreferrer">{label}</a>'
        )

    text = _INLINE_LINK_RE.sub(_link_sub, text)
    return text


def _flush_paragraph(chunks: list[str], output: list[str]) -> None:
    if not chunks:
        return
    text = " ".join(chunks).strip()
    if text:
        body = _apply_inline_markup(text)
        output.append(
            f'<p class="text-gray-600 leading-relaxed mt-4">{body}</p>'
        )
    chunks.clear()


def _flush_list(
    items: list[str], list_type: str | None, output: list[str]
) -> None:
    if not items or list_type is None:
        return
    rendered_items = "".join(
        f"<li>{_apply_inline_markup(item)}</li>" for item in items
    )
    if list_type == "ol":
        tag = "ol"
        classes = (
            "list-decimal pl-6 text-gray-600 leading-relaxed mt-4 space-y-1"
        )
    else:
        tag = "ul"
        classes = (
            "list-disc pl-6 text-gray-600 leading-relaxed mt-4 space-y-1"
        )
    output.append(
        f'<{tag} class="{classes}">{rendered_items}</{tag}>'
    )
    items.clear()


@register.filter
def render_article_body(value):
    """Render simple article markup into styled HTML.

    Block-level syntax:
    - ``## Heading`` -> ``<h3>``
    - ``- item`` -> ``<ul><li>`` (unordered list)
    - ``1. item`` -> ``<ol><li>`` (ordered list; any positive integer works)
    - ``![Alt](path)`` on its own line -> inline image block
    - blank line separates paragraphs

    Inline syntax (works inside paragraphs, headings and list items):
    - ``**bold**`` -> ``<strong>``
    - ``*italic*`` -> ``<em>``
    - ``[label](url)`` -> ``<a>`` (only http/https/mailto/tel/relative URLs)

    All input is HTML-escaped first, so raw HTML never reaches the page.
    """
    text = str(value or "")
    lines = text.replace("\r\n", "\n").split("\n")

    output: list[str] = []
    paragraph_chunks: list[str] = []
    list_items: list[str] = []
    list_type: str | None = None

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            _flush_paragraph(paragraph_chunks, output)
            _flush_list(list_items, list_type, output)
            list_type = None
            continue

        image_match = _IMAGE_RE.match(line)
        if image_match:
            _flush_paragraph(paragraph_chunks, output)
            _flush_list(list_items, list_type, output)
            list_type = None
            alt = image_match.group("alt").strip()
            src = _resolve_image_path(image_match.group("path"))
            if src:
                output.append(
                    '<div class="mt-8 aspect-video rounded-3xl overflow-hidden">'
                    f'<img src="{escape(src)}" alt="{escape(alt)}" '
                    'class="w-full h-full object-cover" loading="lazy">'
                    "</div>"
                )
            continue

        if line.startswith("## "):
            _flush_paragraph(paragraph_chunks, output)
            _flush_list(list_items, list_type, output)
            list_type = None
            heading = _apply_inline_markup(line[3:].strip())
            output.append(
                '<h3 class="font-display text-2xl font-semibold mt-8 mb-4">'
                f"{heading}</h3>"
            )
            continue

        if line.startswith("- "):
            _flush_paragraph(paragraph_chunks, output)
            if list_type != "ul":
                _flush_list(list_items, list_type, output)
                list_type = "ul"
            list_items.append(line[2:].strip())
            continue

        ordered_match = _ORDERED_ITEM_RE.match(line)
        if ordered_match:
            _flush_paragraph(paragraph_chunks, output)
            if list_type != "ol":
                _flush_list(list_items, list_type, output)
                list_type = "ol"
            list_items.append(ordered_match.group("text").strip())
            continue

        _flush_list(list_items, list_type, output)
        list_type = None
        paragraph_chunks.append(line)

    _flush_paragraph(paragraph_chunks, output)
    _flush_list(list_items, list_type, output)

    return mark_safe("".join(output))
