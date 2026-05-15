"""One-off: extract translations from base.html into static/js/i18n/*.json."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "templates" / "core" / "base.html"
OUT = ROOT / "static" / "js" / "i18n"


def main() -> None:
    text = BASE.read_text(encoding="utf-8")
    m = re.search(
        r"const translations = (\{.*?\n        \});\s*\n\s*let currentLang",
        text,
        re.DOTALL,
    )
    if not m:
        raise SystemExit("translations block not found")
    raw = m.group(1)
    raw = re.sub(r"//.*?$", "", raw, flags=re.MULTILINE)
    raw = re.sub(
        r"(\n\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:",
        r'\1"\2":',
        raw,
    )
    data = json.loads(raw)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ru.json").write_text(
        json.dumps(data["ru"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (OUT / "en.json").write_text(
        json.dumps(data["en"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(data['ru'])} ru keys, {len(data['en'])} en keys")


if __name__ == "__main__":
    main()
