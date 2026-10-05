# Görev: analizmaster günlük BIST metni (hafta içi 19:45 İstanbul)

Burak'ın X hesabı @analizmaster için günün BIST taslak metnini yaz. Sadece metin üretirsin; X'e hiçbir şey paylaşmazsın.

## Adımlar
1. `git pull` ile depoyu güncelle.
2. Bugünün tarihi (Europe/Istanbul) için `analizmaster/briefs/TARİH.json` var mı bak.
   - Yoksa: veri çekilememiştir (Actions zaten hata bildirimi açar). Hiçbir şey yazma, "brief yok, veri alınamadı" diye raporla ve bitir. Veri uydurma.
   - `analizmaster/metin/TARİH.json` zaten varsa tekrar yazma.
3. `ornek-yazilar/` içindeki `.md`/`.txt` dosyalarını (README hariç) oku ve Burak'ın yazım stilini (ton, cümle uzunluğu, kelime seçimi, emoji kullanımı) öğren.
   Klasör boşsa dur ve "ornek-yazilar/ boş, stil öğrenemem" diye raporla.
4. Brief'teki `sistem` kurallarına uy ve `istek` alanındaki JSON şemasına birebir uyan bir JSON yaz → `analizmaster/metin/TARİH.json`.
   - Yalnızca brief'teki rakamları kullan. Haber, bilanço, sebep, hedef fiyat uydurma; nedeni bilmiyorsan "nedeni teyit edilmeli" de.
   - Al/sat/tut, hedef fiyat, "kaçırma", "garanti" gibi yatırım tavsiyesi çağrışımlı ifadeler kullanma (doğrulama bunları reddeder).
   - `yukselen_yorum` ve `dusen_yorum` anahtarları brief'te belirtilen hisse kodlarıyla birebir aynı olmalı. `tweet` en fazla 240 karakter.
   - Çıktı yalnızca JSON nesnesi olsun.
5. JSON'un geçerli olduğunu doğrula, sonra yalnızca `analizmaster/metin/TARİH.json` dosyasını commit'le ve `main` dalına push'la
   (commit mesajı: `analizmaster: TARİH metni`). Push, taslağı birleştirip issue/e-posta bildirimi açan Actions'ı başlatır.

Secret/token isteme veya yazma.
