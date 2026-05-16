"""English locale for the coin-minting overview article."""

from django.db import migrations

SLUG = "novinki-tekhnologii-chekanke-monet-2025-2026"

TITLE_EN = "Coin Minting Technology Trends: 2025–2026 Overview"

EXCERPT_EN = (
    "Laser-engraved dies, Britannia microtext, Smartminting® 4.0, Austrian niobium, "
    "and digital twins — a global trend roundup for medal artists and 3D sculptors."
)

TAG_EN = "Coins"

CONTENT_EN = """In 2025 and early 2026, the world's leading mints showed that modern coin striking is no longer just press and die, but a combination of laser engraving, micro-relief, new alloys, and digital authentication. Below is a summary of the main directions worth noting for medal artists and 3D sculptors.

![Minting illustration 2](images/news/16052026news.png)

## Laser engraving of dies

**The United States Mint** in 2025 released the first silver American Eagle with a laser privy mark — a stylized "sun ray" on the obverse. Lasers were previously used for serial numbers on die collars and proof surface frosting; now **the master die is created entirely by laser engraving**, yielding sharper fine detail: feathers, fabric folds, lettering.

For the artist this means: the design must contain **geometry that can actually be reproduced** — the laser won't "fix" a mushy relief, but it rewards clean forms.

## Microtext and visual security

**The Royal Mint (UK)** continues to develop the Britannia series as the benchmark for bullion coin security. Updated versions use:

- **microtext** DECUS ET TUTAMEN along the relief contour;
- **picosecond lasers** — marks fractions of a micron wide (hundreds of times thinner than a human hair);
- **latent image** (padlock / trident when tilted);
- **surface animation** — illusion of a "living" surface when the coin is turned.

The same techniques have been applied to **Britannia gold bars**: authenticity is checked visually, without special devices.

![Minting illustration 3](images/news/16052026news2.png)

## Smartminting® 4.0: relief up to 9 mm

**CIT / B.H. Mayer's** introduced **Smartminting® 4.0** (2024–2025): ultra-high relief of about **9 mm** while keeping proof-quality fields — roughly 50% higher than the previous generation. Example — the silver **Iron Knight** coin (Cook Islands): a knight in volumetric armor, elements "rising" toward the rim.

For bas-relief and medals this is an important reference: **height contrast** and silhouette readability are back in fashion; flat "slabs" on the premium market yield to sculptural solutions.

## Niobium, anodizing, and digital twin

**The Austrian Mint** develops the **silver + niobium** series (since 2003). The niobium core is colored by **anodic oxidation** — color is held in the metal volume, not paint.

- **2024 — "Edaphon"**: soil as an ecosystem, organisms in the silver ring and colored niobium.
- **2025 — "Digitalisation"**: analog and digital object pairs, microchip and AI motifs; for the first time in a limited set — a **digital twin of the coin** (blockchain / crypto stamp).

Niobium remains a rare material in striking: low density, bright interference colors, a separate process after the silver ring.

## High relief and reverse proof

**National Park Foundation** (USA) and partners issue **Saint-Gaudens Winged Liberty** silver medals in high relief with **reverse proof** — mirrored elements and matte fields swap roles vs. classic. **Royal Canadian Mint** in the Aztec Empire series combines ultra-high relief with **selective gilding**.

Trend: **two-sided volume** and combined finishes (proof + high relief + plating) in one mintage.

![Minting illustration 4](images/news/16052026news3.png)

## What this means for the medalist's practice

1. **Design for the tool** — laser and micro-relief need clean CAD/CAM data without mesh artifacts.
2. **Security as part of design** — microtext, variegated rim, latent elements are planned at the layout stage.
3. **Material ≠ decoration** — niobium, bimetal, selective plating dictate separate operations; the artist aligns composition with the technologist.
4. **Relief height** — Smartminting and high-relief presses again expand the usable Z-range; worth testing depth on wax/digital model before steel.

## Sources for further reading

- [US Mint — laser-engraved Silver Eagle 2025](https://www.usmint.gov/2025-laser-engraved-american-eagle-one-ounce-silver-proof-coin-25EALE.html)
- [Coin World — laser engraving on American Eagle](https://www.coinworld.com/news/us-coins/new-technology-brings-laser-engraving-on-american-eagle)
- [Royal Mint — visually secure Britannia](https://www.royalmint.com/aboutus/press-centre/the-royal-mint-unveil-the-worlds-most-visually-secure-bullion-coin/)
- [CoinsWeekly — Smartminting® 4.0 Iron Knight](https://new.coinsweekly.com/people-and-markets/cits-new-smartminting-4-0-iron-knight/)
- [Austrian Mint — niobium Digitalisation 2025](https://www.muenzeoesterreich.at/eng/collect/good-to-know/silver-niobium-coins)
- [Coin World — Austria niobium soil 2024](https://www.coinworld.com/news/world-coins/austria-s-annual-niobium-issue-celebrates-soil)

*Overview prepared from open publications of mints and trade press.*
"""


def seed_english(apps, schema_editor):
    NewsArticle = apps.get_model("core", "NewsArticle")
    NewsArticle.objects.filter(slug=SLUG).update(
        title_en=TITLE_EN,
        excerpt_en=EXCERPT_EN,
        content_en=CONTENT_EN,
        tag_en=TAG_EN,
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0020_newsarticle_english_fields"),
    ]

    operations = [
        migrations.RunPython(seed_english, noop),
    ]
