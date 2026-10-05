"""Aşama 3 (Actions): brief'teki rakamlar + yazılmış metinden markdown taslağı birleştirir.

Tablolar koddan gelir (modelin rakam yazmasına gerek yok). X'e ASLA paylaşım yapmaz.

  python -m analizmaster.taslak            # metni gelmiş brief'leri birleştirir
  python -m analizmaster.taslak --kontrol  # bugünün brief'i var ama taslağı yoksa hata verir
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import veri

ROOT = Path(__file__).resolve().parent.parent
BASE = Path(__file__).parent
TZ = ZoneInfo("Europe/Istanbul")
UYARI = "> ⚠️ Yatırım tavsiyesi değildir. Bu metin yalnızca bilgilendirme amaçlı bir taslaktır; alım-satım önerisi içermez."
YASAK = re.compile(r"\b(hedef fiyat|alın|satın alın|satın al|alım fırsatı|kaçırma|kaçırmayın|garanti)\b", re.I)


def tablo(satirlar: list[dict]) -> str:
    out = ["| # | Hisse | Kapanış (TL) | Önceki (TL) | Değişim | Ciro (mn TL) |", "|---|---|---:|---:|---:|---:|"]
    for i, s in enumerate(satirlar, 1):
        out.append(f"| {i} | **{s['kod']}** | {s['kapanis']:.2f} | {s['onceki']:.2f} | %{s['degisim']:+.2f} | {s['ciro_mn']:.1f} |")
    return "\n".join(out)


def dogrula(d: dict, y: dict):
    ky, kd = [s["kod"] for s in d["yukselen"]], [s["kod"] for s in d["dusen"]]
    for k in ("giris", "kapanis", "tweet"):
        if not isinstance(y.get(k), str) or not y[k].strip():
            raise ValueError(f"'{k}' eksik.")
    if set(y.get("yukselen_yorum", {})) != set(ky) or set(y.get("dusen_yorum", {})) != set(kd):
        raise ValueError("Yorum anahtarları hisse kodlarıyla eşleşmiyor.")
    if len(y["tweet"]) > 240:
        raise ValueError("Tweet özeti 240 karakterden uzun.")
    tum = " ".join([y["giris"], y["kapanis"], y["tweet"], *y["yukselen_yorum"].values(), *y["dusen_yorum"].values()])
    bulunan = sorted({m.group(0).lower() for m in YASAK.finditer(tum)})
    if bulunan:
        raise ValueError(f"Yatırım tavsiyesi çağrışımlı ifade bulundu: {bulunan}. Metni gözden geçirip yeniden yazın.")


def birlestir(gun: str) -> Path:
    b = json.loads((BASE / "briefs" / f"{gun}.json").read_text(encoding="utf-8"))
    y = json.loads((BASE / "metin" / f"{gun}.json").read_text(encoding="utf-8"))
    d = b["veri"]
    dogrula(d, y)
    ky, kd = [s["kod"] for s in d["yukselen"]], [s["kod"] for s in d["dusen"]]
    md = [
        f"# BIST Gün Sonu Taslağı — {d['tarih']}", "",
        f"_Durum: **TASLAK** (otomatik üretildi, yayına hazır değil). Hesap: @analizmaster. Kaynak: EODHD gün sonu verisi. "
        f"Filtre: günlük cirosu ≥ {float(os.environ.get('MIN_CIRO_TL', 5_000_000)) / 1e6:.0f} mn TL._", "",
        y["giris"], "",
        "## 📈 En çok yükselenler", "", tablo(d["yukselen"]), "",
        *[f"- **{k}**: {y['yukselen_yorum'][k]}" for k in ky], "",
        "## 📉 En çok düşenler", "", tablo(d["dusen"]), "",
        *[f"- **{k}**: {y['dusen_yorum'][k]}" for k in kd], "",
        y["kapanis"], "",
        "## 🐦 Tweet özeti (taslak)", "", f"{y['tweet']}\n\nYatırım tavsiyesi değildir.", "",
    ]
    if d["dislanan"]:
        md += [f"> Veri notu: Günlük değişimi %{veri.MAX_GUNLUK_DEGISIM:.0f}'i aşan {', '.join(d['dislanan'])} sermaye işlemi/veri hatası şüphesiyle listeye alınmadı; elle kontrol edin.", ""]
    md += [UYARI, ""]
    (BASE / "taslaklar").mkdir(exist_ok=True)
    yol = BASE / "taslaklar" / f"{gun}.md"
    yol.write_text("\n".join(md), encoding="utf-8")
    return yol


def main(kontrol: bool) -> int:
    bugun = datetime.now(TZ).date().isoformat()
    yeni, sorun = [], []
    for bf in sorted((BASE / "briefs").glob("*.json")):
        gun = bf.stem
        if (BASE / "taslaklar" / f"{gun}.md").exists():
            continue
        if not (BASE / "metin" / bf.name).exists():
            if kontrol and gun == bugun:
                sorun.append(f"{gun}: brief var ama metin yazılmamış, taslak üretilemedi")
            continue
        try:
            yol = birlestir(gun)
            yeni.append((gun, yol))
            print(f"Taslak yazıldı: {yol}")
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            print(f"::error title=Taslak hatası ({gun})::{e}")
            sorun.append(f"{gun}: {e}")

    if os.environ.get("GITHUB_OUTPUT") and yeni:
        gun, yol = yeni[-1]
        with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
            fh.write(f"yol={yol.relative_to(ROOT)}\ntarih={gun}\n")
    if sorun:
        print("::error title=Taslak sorunu::" + "; ".join(sorun))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main("--kontrol" in sys.argv))
