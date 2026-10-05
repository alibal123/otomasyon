"""YEDEK yol: metni bulut görevi yerine Anthropic API ile yazar (ANTHROPIC_API_KEY gerekir).

Bulut kredisi bittiğinde ya da bulut görevi çalışmadığında elle/Actions'tan kullanılabilir:
  python -m common.metin_api derecefilm
  python -m common.metin_api analizmaster
Brief'i olup metni olmayan (bugün ve sonrası) günleri doldurur.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .llm import ask_json

ROOT = Path(__file__).resolve().parent.parent


def main(proje: str) -> int:
    base = ROOT / proje
    today = datetime.now(ZoneInfo("Europe/Istanbul")).date().isoformat()
    (base / "metin").mkdir(exist_ok=True)
    n = 0
    for bf in sorted((base / "briefs").glob("*.json")):
        out = base / "metin" / bf.name
        if bf.stem < today or out.exists():
            continue
        b = json.loads(bf.read_text(encoding="utf-8"))
        sistem = b["sistem"]
        stil = b.get("stil_klasoru")
        if stil:
            parcalar = [f.read_text(encoding="utf-8") for f in sorted((ROOT / stil).glob("*")) if f.suffix in (".md", ".txt") and f.name.lower() != "readme.md"]
            if not parcalar:
                print(f"::error title=Stil örneği yok::{stil}/ boş.")
                return 1
            sistem += "\n\n--- ÖRNEK YAZILAR ---\n" + "\n\n=====\n\n".join(parcalar)[:15000]
        out.write_text(json.dumps(ask_json(sistem, b["istek"]), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{bf.stem}: metin yazıldı.")
        n += 1
    print(f"{n} metin üretildi.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
