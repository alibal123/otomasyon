"""Aşama 1 (Actions, Pazar 10:00 İstanbul): sonraki haftanın 7 günü için brief dosyaları üretir.

Çıktı: derecefilm/briefs/TARİH.json. Metni Claude bulut görevi yazar (bulut-gorevleri/derecefilm-metin.md).
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import content

ROOT = Path(__file__).parent
BRIEFS = ROOT / "briefs"
HISTORY = ROOT / "history.json"
TZ = ZoneInfo("Europe/Istanbul")


def main() -> int:
    today = datetime.now(TZ).date()
    start = today + timedelta(days=(7 - today.weekday()) % 7 or 7)  # sonraki Pazartesi
    hist = json.loads(HISTORY.read_text()) if HISTORY.exists() else {"used": []}
    used = set(hist["used"])
    BRIEFS.mkdir(exist_ok=True)
    failures = []
    print(f"Brief hazırlanan hafta: {start} → {start + timedelta(days=6)}")

    for i in range(7):
        d = start + timedelta(days=i)
        f = BRIEFS / f"{d.isoformat()}.json"
        if f.exists():
            print(f"[{d}] brief zaten var, atlandı.")
            continue
        try:
            b = content.brief(d, used)
            f.write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding="utf-8")
            used.update(x["id"] for x in b["filmler"])
            print(f"[{d}] {b['kind']}: brief hazır ({len(b['filmler'])} film).")
        except Exception as e:
            traceback.print_exc()
            print(f"::error title=Brief hatası ({d})::{e}")
            failures.append(f"{d}: {e}")

    hist["used"] = sorted(used)[-600:]
    HISTORY.write_text(json.dumps(hist, indent=2), encoding="utf-8")
    if failures:
        print("\nBAŞARISIZ GÜNLER:\n" + "\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
