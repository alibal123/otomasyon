# Görev: ABD günlük analiz PDF'i (hafta içi 13:30 İstanbul)

Ali için Türkçe, grafikli bir PDF hazırla ve 13:30'a kadar gönder. Kod: `abd-analiz/analiz.py`. Biçim örneği:
`abd-analiz/ornek-icerik.json`. Bu dosyadaki adımları sırayla uygula. Yatırım tavsiyesi verme; seviyeler "kurallara
göre" ve "olası aralık" olarak yazılır. Bilmediğin bir sayıyı uydurma.

## 1. Fiyat verisi (yaklaşık 15 sembol)

Bu ortamın kabuğundan finans sitelerine erişim yok. Veriyi **WebFetch** ile al:

- Hisseler: `https://stockanalysis.com/stocks/<kucuk-harf-sembol>/history/` (MRVL, DY)
- Fonlar: `https://stockanalysis.com/etf/<kucuk-harf-sembol>/history/` (ARKG, SPY, QQQ, SMH, SOXX, AIQ, CIBR, ARKQ, ARKW, ARKF, BLOK, URA, GLD)
- WebFetch istemi: `Output the full daily price history table as CSV: date,open,high,low,close,volume. Every row shown, nothing else.`
- Çağrıları paralel yap. Her birini `abd-analiz/veri/<SEMBOL>.csv` olarak kaydet. Başlık satırı `date,open,high,low,close,volume`.
- Tarihler `YYYY-MM-DD` olsun. "Oct 7, 2026" gibi virgüllü tarihleri dönüştür, yoksa CSV sütunları kayar.
- Kontrol et:
  - Son satır bugünden önceki son işlem günü mü?
  - Satır sayısı yeterli mi? Detaylı hisseler için ≥ 50, fonlar için ≥ 25.
- Bir sayfa eski görünüyorsa (son tarih 2+ işlem günü geride):
  1. WebFetch'i bir kez daha dene.
  2. Olmazsa `https://stockanalysis.com/etf/<sembol>/` sayfasından son kapanışları alıp eksik günleri `tarih,c,c,c,c,0` olarak ekle.
  3. Bunu PDF'te fon notunda belirt.
- 13:30'da ABD borsası kapalıdır; bu yüzden gün içi (anlık) satır olmaz. `veri/anlik.json` dosyasını yazma.

## 2. Araştırma (derin, kaynaklı)

WebSearch (gerekirse `extended`) ve WebFetch ile son 24–48 saati tara. Her bilgi için kaynak URL'si topla.

- **Piyasa:**
  - Bir önceki kapanış: S&P 500, Nasdaq, Dow, Russell 2000.
  - Vadeli işlemler.
  - 10 ve 30 yıllık faiz, dolar endeksi (DXY), petrol, altın, Bitcoin, VIX.
  - Fed: son karar, tutanaklar, konuşmacılar, CME FedWatch olasılıkları.
  - Son makro veriler ve bu hafta açıklanacaklar.
  - Jeopolitik gelişmeler.
  - Stratejist görüşleri.
- **MRVL, ARKG, DY:**
  - Yeni haberler ve analist not/hedef değişiklikleri.
  - Yönetici alım ve satımları.
  - ARK'ın günlük işlemleri (ARKG için).
  - Bilanço tarihleri.
  - Önceki günkü hareketin nedeni.
- **Fon temaları:** yarı iletken, yapay zekâ, siber güvenlik, otonom teknoloji, fintek, blokzincir, uranyum, altın.
- **Takvim:** önümüzdeki 7 gün.

## 3. Hesapla ve öz-kontrol

```
cd abd-analiz && python3 analiz.py hesapla
```

- Çıktıdaki seviyeleri, aralıkları ve sinyalleri oku. `cikti/hesap.json` → `oz_kontrol` bölümüne de bak; burada önceki raporların aralıkları gerçekleşen kapanışlarla karşılaştırılır.
- `oz_kontrol_yorum` alanına 2–4 cümle yaz:
  - Dün verilen 1 günlük aralıkların tutup tutmadığı. Hangi sembol %68 aralığın içinde kaldı, hangisi dışına çıktı?
  - Dışına çıkanların nedeni (haber, veri).
  - Haftalık aralıkların şimdiye kadarki durumu.
  - Birikmiş tutma oranı (`ozet` alanından).

## 4. icerik.json'u yaz

`abd-analiz/icerik.json` dosyasını `ornek-icerik.json` ile aynı yapıda, bugünün verisi ve araştırmasıyla baştan yaz.

- Alanlar:
  - `tarih` (bugün)
  - `alt_baslik`
  - `ozet` (5–7 madde)
  - `oz_kontrol_yorum`
  - `piyasa` (paragraflar)
  - `piyasa_tablo`
  - `senaryolar` (Temel / Olumlu / Olumsuz)
  - `takvim`
  - `hisseler.MRVL|ARKG|DY`. Her biri `yon`, `al_sat`, `teknik`, `temel`, `davranis`, `senaryo` ve `risk` alanlarını içerir.
  - `fonlar_giris`, `fon_notlari`, `fonlar`
  - `kaynaklar` ([başlık, url] listesi)
- `al_sat` tablosu için seviyeleri `hesapla` çıktısından al:
  - Günlük ve haftalık pivotlar
  - Salınım destek ve dirençleri
  - 20 gün zirvesi ve 10 gün dibi
  - ATR ile kural zarar durdurma (giriş − 3×ATR)
  Her satıra mantığını yaz.
- `yon`:
  - `null` (yön beklentisi yok) ya da `"yukari"` / `"asagi"` yaz.
  - Yön yazacaksan gerekçesi `teknik` alanında olsun.
  - Bu alan öz-kontrolde yön isabet oranı olarak ölçülür. Kanıt zayıfsa `null` bırak.
- Dil:
  - Sade, Türkçe yaz. Sayılarda Türkçe ondalık virgül kullan.
  - Teknik terimleri ilk geçtiği yerde kısaca açıkla.
  - "Al/sat" yerine "kurala göre alım bölgesi", "direnç / kâr alma bölgesi" gibi ifadeler kullan.

## 5. PDF üret ve kontrol et

```
python3 analiz.py pdf
pdftoppm -r 55 -png cikti/ABD-Analiz-<tarih>.pdf cikti/s
```

Sayfa görsellerini Read ile gözden geçir. Taşan tablo, üst üste binen yazı ya da boş grafik varsa düzelt ve yeniden üret.

## 6. Kaydet (öz-kontrol hafızası)

`abd-analiz/tahminler/<tarih>.json` dosyası yarınki öz-kontrol için gereklidir. Bu dosyayı commit edip `main` dalına push et:

```
git pull --rebase
git add abd-analiz/tahminler
git commit -m "abd-analiz: <tarih> tahmin kaydı"
git push
```

`veri/`, `cikti/` ve `icerik.json` .gitignore'dadır. Başka dosyaya dokunma.

## 7. Gönder

1. SendUserMessage ile kısa bir özet gönder (telefonda okunur):
   - Başlık: "ABD analiz · <tarih>"
   - Özetin 4–6 maddesi.
   - Öz-kontrol tek satır (dünkü aralıkların kaç tanesi tuttu).
   - MRVL, ARKG ve DY için tek satır: son fiyat · 1 gün %68 aralığı · en yakın destek/direnç.
   - Son satır: "Yatırım tavsiyesi değildir."
2. SendUserFile ile PDF'i gönder (display: render).

Bir adım başarısız olursa (örneğin bir sembolün verisi gelmezse) o sembolü atla, PDF'te ve mesajda belirt, gerisini gönder.
