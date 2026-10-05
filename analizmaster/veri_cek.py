"""Aşama 1 (Actions, hafta içi 19:30 İstanbul): gün sonu verisini çeker, metin yazarı için brief hazırlar.

Veri alınamazsa/hatalıysa brief YAZILMAZ ve hata verilir (taslak üretilmez).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import veri

BASE = Path(__file__).parent
TZ = ZoneInfo("Europe/Istanbul")

SISTEM = (
    "Sen Burak'ın X hesabı @analizmaster için günlük borsa taslağı yazan bir asistansın. "
    "Burak'ın yazım stilini ornek-yazilar/ klasöründeki örneklerden öğren ve taklit et (ton, cümle uzunluğu, kelime seçimi, emoji kullanımı). "
    "KESİN KURALLAR: (1) Yalnızca verilen sayıları kullan; hisse hakkında haber, bilanço, sebep, hedef fiyat UYDURMA — "
    "hareketin nedenini bilmiyorsan 'nedeni teyit edilmeli' de. (2) Al/sat/tut, hedef fiyat, 'kaçırma' gibi yatırım tavsiyesi "
    "ifadeleri KULLANMA. (3) Çıktı yalnızca geçerli JSON olsun."
)


def main() -> int:
    bugun = datetime.now(TZ).date()
    if bugun.weekday() >= 5:
        print("Hafta sonu, borsa kapalı; atlandı.")
        return 0
    try:
        d = veri.getir(bugun, min_ciro_tl=float(os.environ.get("MIN_CIRO_TL", 5_000_000)))
    except veri.DataError as e:
        print(f"::error title=analizmaster veri hatası::{e}")
        return 1

    ky = [s["kod"] for s in d["yukselen"]]
    kd = [s["kod"] for s in d["dusen"]]
    ozet = {
        "tarih": d["tarih"], "toplam_hisse": d["toplam"],
        "yukselen_sayisi": d["yukselen_sayisi"], "dusen_sayisi": d["dusen_sayisi"],
        "en_cok_yukselen": d["yukselen"], "en_cok_dusen": d["dusen"],
    }
    brief = {
        "date": d["tarih"],
        "sistem": SISTEM,
        "stil_klasoru": "ornek-yazilar",
        "veri": d,
        "istek": (
            f"Bugünün verisi: {json.dumps(ozet, ensure_ascii=False)}\n\n"
            'JSON şeması: {"giris":"2-3 cümle genel piyasa özeti (yükselen/düşen sayılarına dayan)",'
            '"yukselen_yorum":{"KOD":"1-2 cümle, yalnızca sayılara dayalı"},"dusen_yorum":{"KOD":"1-2 cümle"},'
            '"kapanis":"1-2 cümle kapanış","tweet":"En fazla 240 karakterlik tek tweet özeti"}\n'
            f"yukselen_yorum anahtarları tam olarak: {ky}; dusen_yorum anahtarları tam olarak: {kd}."
        ),
    }
    (BASE / "briefs").mkdir(exist_ok=True)
    yol = BASE / "briefs" / f"{d['tarih']}.json"
    yol.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Brief yazıldı: {yol}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
