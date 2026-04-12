"""Display helpers for amounts stored in kopecks (1/100 RUB)."""

from __future__ import annotations

USD_TO_RUB_RATE = 80


def format_minor_as_rub(minor: int) -> str:
    """Format kopecks for display (space as thousands separator when whole rubles)."""
    if minor % 100 == 0:
        rub = minor // 100
        s = f"{rub:,}".replace(",", " ")
        return f"{s} ₽"
    rub = minor / 100.0
    return f"{rub:.2f} ₽"


def usd_whole_to_rub_kopecks(usd_whole: int) -> tuple[str, int]:
    """Convert a whole USD shelf price to display string and kopecks (RUB × 100)."""
    rub = int(usd_whole) * USD_TO_RUB_RATE
    kopecks = rub * 100
    return format_minor_as_rub(kopecks), kopecks
