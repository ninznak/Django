from django import template

from core.pricing import format_minor_as_rub

register = template.Library()


@register.filter
def rub_minor(value):
    try:
        return format_minor_as_rub(int(value))
    except (TypeError, ValueError):
        return value
