"""BIST gün sonu verisi (EODHD 'eod-bulk-last-day' uç noktası, borsa kodu IS).

Veri alınamaz, bugüne ait değilse ya da bozuksa DataError fırlatılır; taslak üretilmez.
Anahtar yalnızca EODHD_API_KEY ortam değişkeninden okunur.
"""
from __future__ import annotations

import os
import re
from datetime import date

import requests

URL = "https://eodhd.com/api/eod-bulk-last-day/IS"
MAX_GUNLUK_DEGISIM = 11.0  # BIST'te günlük limit ~%10; üstü sermaye işlemi/veri hatası şüphesi


class DataError(RuntimeError):
    pass


def getir(bugun: date, min_ciro_tl: float = 5_000_000, adet: int = 5) -> dict:
    key = os.environ.get("EODHD_API_KEY")
    if not key:
        raise DataError("EODHD_API_KEY ortam değişkeni (GitHub Secret) tanımlı değil.")
    try:
        r = requests.get(URL, params={"api_token": key, "fmt": "json"}, timeout=60)
    except requests.RequestException as e:
        raise DataError(f"Veri kaynağına ulaşılamadı: {type(e).__name__}") from e
    if not r.ok:
        raise DataError(f"Veri kaynağı HTTP {r.status_code} döndürdü: {r.text[:200]}")
    try:
        rows = r.json()
    except ValueError as e:
        raise DataError("Veri kaynağı geçersiz JSON döndürdü.") from e
    if not isinstance(rows, list) or not rows:
        raise DataError("Veri kaynağı boş liste döndürdü.")

    tarih = max(str(x.get("date", "")) for x in rows)
    if tarih != bugun.isoformat():
        raise DataError(
            f"Beklenen tarih {bugun}, kaynaktaki son veri {tarih}. Resmî tatil ya da veri gecikmesi olabilir; "
            "veri uydurulmaz, taslak üretilmedi."
        )

    temiz, dislanan = [], []
    for x in rows:
        if x.get("date") != tarih or not re.fullmatch(r"[A-Z]{3,5}", str(x.get("code", ""))):
            continue
        try:
            kapanis, onceki, hacim = float(x["close"]), float(x["previousClose"]), float(x["volume"])
        except (KeyError, TypeError, ValueError):
            continue
        if kapanis <= 0 or onceki <= 0 or hacim <= 0 or kapanis * hacim < min_ciro_tl:
            continue
        degisim = (kapanis / onceki - 1) * 100
        if abs(degisim) > MAX_GUNLUK_DEGISIM:
            dislanan.append(x["code"])
            continue
        temiz.append({"kod": x["code"], "kapanis": kapanis, "onceki": onceki, "degisim": degisim, "ciro_mn": kapanis * hacim / 1e6})

    if len(temiz) < 2 * adet + 10:
        raise DataError(f"Filtre sonrası çok az hisse kaldı ({len(temiz)}); veri güvenilir görünmüyor.")
    temiz.sort(key=lambda s: s["degisim"], reverse=True)
    return {
        "tarih": tarih,
        "yukselen": temiz[:adet],
        "dusen": temiz[::-1][:adet],
        "toplam": len(temiz),
        "yukselen_sayisi": sum(s["degisim"] > 0 for s in temiz),
        "dusen_sayisi": sum(s["degisim"] < 0 for s in temiz),
        "dislanan": dislanan,
    }
