"""Yerel önizleme: API anahtarı gerektirmez, sahte verilerle tüm şablonları/paletleri çizer.

Kullanım:  python -m derecefilm.dev_preview  [çıktı_klasörü]
"""
import sys
from pathlib import Path

from . import designs as D


def main(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    posters = [None] * 4
    items = [{"title": f"Örnek Film Adı Biraz Uzun {i}", "year": 2000 + i, "blurb": "Kısa bir neden cümlesi burada yer alır, iki üç satıra yayılabilir.", "poster": None} for i in range(5)]
    for pi, p in enumerate(D.PALETTES):
        v = pi
        imgs = [
            D.cover(p, v, "LİSTE", "Bir oturuşta izlenecek 5 gerilim", posters, "5 film • kaydet", 1, 6),
            D.list_item(p, v, 1, items[0], 2, 6),
            D.single_cover(p, v, "TEK FİLM", "Örnek Film Adı", "Tek cümlelik bir slogan örneği buraya gelir.", None, 1, 2),
            D.single_detail(p, v, "Neden izlemeli?", "Spoilersiz, birkaç cümlelik bir neden metni. " * 4, ["Yönetmen: Ad Soyad", "TMDB puanı: 8.1", "Süre: 120 dk", "Yıl: 1999"], 2, 2),
            D.quiz_question(p, v, "Bir sığınakta yaşayan bir çocuğun hikayesini anlatan film hangisi?", ["Birinci seçenek", "İkinci seçenek biraz uzun bir film adı", "Üçüncü"], 1, 2),
            D.quiz_answer(p, v, "B", "İkinci seçenek", "Verilen verilere göre bu film doğru cevaptır çünkü konusu uyuşuyor.", None, 2, 2),
            D.radar_detail(p, v, "Önümüzdeki haftalarda vizyonda", [{"title": f"Vizyon Filmi {i}", "date": "14 Ekim", "blurb": "Spoilersiz kısa bir not.", "poster": None} for i in range(4)], 2, 2),
        ]
        for n, im in enumerate(imgs):
            im.convert("RGB").save(out / f"p{pi}_{n}.jpg", quality=90)
    print(f"{len(D.PALETTES) * 7} görsel yazıldı → {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "onizleme"))
