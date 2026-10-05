"""Aşama 3 (Actions): metni yazılmış brief'leri görsele çevirip queue/ altına yazar.

Kullanım:
  python -m derecefilm.render_week            # metni gelenleri işler, eksikleri atlar
  python -m derecefilm.render_week --strict   # metni eksik gün varsa hata verir (kontrol çalışması)
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import content

ROOT = Path(__file__).parent
BRIEFS, METIN, QUEUE = ROOT / "briefs", ROOT / "metin", ROOT / "queue"
TZ = ZoneInfo("Europe/Istanbul")


def main(strict: bool) -> int:
    today = datetime.now(TZ).date().isoformat()
    failures, missing = [], []
    for bf in sorted(BRIEFS.glob("*.json")):
        day = bf.stem
        if day < today or (QUEUE / day / "post.json").exists():
            continue
        tf = METIN / f"{day}.json"
        if not tf.exists():
            missing.append(day)
            continue
        try:
            b = json.loads(bf.read_text(encoding="utf-8"))
            t = json.loads(tf.read_text(encoding="utf-8"))
            imgs, caption = content.render(b, t)
            out = QUEUE / day
            out.mkdir(parents=True, exist_ok=True)
            names = []
            for n, im in enumerate(imgs, 1):
                name = f"{n:02d}.jpg"
                im.convert("RGB").save(out / name, "JPEG", quality=92)
                names.append(name)
            (out / "post.json").write_text(
                json.dumps({"date": day, "kind": b["kind"], "caption": caption, "images": names, "status": "pending"},
                           ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"[{day}] {b['kind']}: {len(names)} görsel hazır.")
        except Exception as e:
            traceback.print_exc()
            print(f"::error title=Görsel üretim hatası ({day})::{e}")
            failures.append(f"{day}: {e}")

    if missing:
        msg = f"Metni henüz yazılmamış günler: {', '.join(missing)}"
        print(("::error title=Eksik metin::" if strict else "Not: ") + msg)
        if strict:
            failures.append(msg)
    if failures:
        print("\nSORUNLAR:\n" + "\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main("--strict" in sys.argv))
