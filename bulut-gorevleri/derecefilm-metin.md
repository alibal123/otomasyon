# Görev: derecefilm haftalık metinleri (Pazar 11:00 İstanbul)

Bu depoda `derecefilm/briefs/` altında sonraki haftanın her günü için bir brief dosyası (`TARİH.json`) var.
Metni henüz yazılmamış olanlar için `derecefilm/metin/TARİH.json` dosyasını sen yaz.

## Adımlar
1. `git pull` ile depoyu güncelle.
2. `derecefilm/briefs/*.json` dosyalarından, tarihi bugün veya sonrası olan ve `derecefilm/metin/` altında aynı adlı dosyası OLMAYANları bul.
3. Her biri için brief içindeki `sistem` kurallarına uy ve `istek` alanındaki JSON şemasına birebir uyan bir JSON yaz.
   Çıktı dosyası: `derecefilm/metin/<aynı dosya adı>` (yalnızca JSON nesnesi; markdown çiti, açıklama yok).
4. Yazarken YALNIZCA brief'teki verileri kullan. Verilmeyen oyuncu, ödül, gişe, sahne bilgisi uydurma. Spoiler verme. İtalik/markdown kullanma.
   - Liste ve radar: `filmler[].id` değerleri brief'teki film `id`'leriyle birebir aynı olmalı.
   - Quiz: doğru filmin adı soruda, açıklamada ve gönderi metninde GEÇMEMELİ.
   - Karakter sınırlarına uy; uzun yazarsan doğrulama reddeder.
5. Dosyaları doğrula: `python3 -c "import json,sys;[json.load(open(f)) for f in sys.argv[1:]]" derecefilm/metin/*.json`
6. Yalnızca `derecefilm/metin/` altındaki yeni dosyaları commit'le ve `main` dalına push'la (commit mesajı: `derecefilm: haftalık metinler`). Başka dosyaya dokunma.
   Push, GitHub Actions'taki görsel üretimini kendiliğinden başlatır.
7. Brief yoksa ya da bir şey ters giderse hiçbir şey uydurma; neyin eksik olduğunu kısaca raporla.

Instagram'a paylaşım yapma, secret/token isteme veya yazma.
