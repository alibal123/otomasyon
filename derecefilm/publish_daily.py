"""Günlük yayın: bugünün (İstanbul saatiyle) gönderisini 20:00'da Instagram'a paylaşır.

Telafi YOKTUR: bugünün gönderisi yoksa ya da çok geç kalındıysa hata verip çıkar.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import instagram

QUEUE = Path(__file__).parent / "queue"
TZ = ZoneInfo("Europe/Istanbul")
HEDEF_SAAT = 20
EN_GEC = timedelta(hours=2)  # 20:00'dan sonra bu kadar geçtiyse paylaşma, hata ver
EN_FAZLA_BEKLEME = timedelta(minutes=55)


def fail(msg: str) -> int:
    print(f"::error title=derecefilm paylaşım hatası::{msg}")
    return 1


def main() -> int:
    now = datetime.now(TZ)
    today = now.date()
    pdir = QUEUE / today.isoformat()
    pfile = pdir / "post.json"
    if not pfile.exists():
        return fail(f"{today} için hazırlanmış gönderi yok ({pfile}). Haftalık hazırlık çalışmamış olabilir. Telafi yapılmadı.")
    post = json.loads(pfile.read_text(encoding="utf-8"))
    if post["status"] == "published":
        print("Bu gönderi zaten paylaşılmış, atlandı.")
        return 0

    if post["status"] == "publishing":
        return fail("Önceki çalışma yarım kalmış (durum: publishing). Çift paylaşımı önlemek için durdu; "
                    "Instagram'ı kontrol edip post.json durumunu elle düzeltin.")

    target = now.replace(hour=HEDEF_SAAT, minute=0, second=0, microsecond=0)
    if now > target + EN_GEC:
        post["status"] = "missed"
        pfile.write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
        return fail(f"Çalışma çok geç başladı ({now:%H:%M}). Hedef 20:00 idi; telafi yapılmadı.")
    if now < target:
        wait = target - now
        if wait > EN_FAZLA_BEKLEME:
            return fail(f"20:00'a {wait} var; beklenenden çok erken çalıştı.")
        print(f"20:00'a kadar {int(wait.total_seconds())} sn bekleniyor...")
        time.sleep(wait.total_seconds())

    repo, branch = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_REF_NAME", "main")
    if not repo:
        return fail("GITHUB_REPOSITORY tanımlı değil (yalnızca GitHub Actions içinde çalışır).")
    base = f"https://raw.githubusercontent.com/{repo}/{branch}/derecefilm/queue/{today.isoformat()}"
    urls = [f"{base}/{n}" for n in post["images"]]

    post["status"] = "publishing"  # yarım kalırsa yeniden çalışınca çift paylaşım riskine karşı iz
    pfile.write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        media_id = instagram.publish(urls, post["caption"])
    except Exception as e:
        post["status"] = "failed"
        post["error"] = str(e)[:500]
        pfile.write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
        return fail(str(e))
    post["status"] = "published"
    post["media_id"] = media_id
    pfile.write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Paylaşıldı: {today} ({post['kind']}) media_id={media_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
