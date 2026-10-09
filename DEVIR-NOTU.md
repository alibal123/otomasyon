# Devir notu: Ali'nin otomasyonları ve yatırım sistemi

Son güncelleme: 9 Ekim 2026. Yeni bir sohbete bu dosyayı ver ve "bunu oku, buradan devam et" de.

> **Yeni sohbetteki Claude için:**
> - Bu dosya bir önceki sohbetin özetidir. Önce bunu oku.
> - Zamanlanmış görevleri `list_triggers` ile kontrol et.
> - Mac'teki dosyalara `mcp__remote-devices__*` araçlarıyla bak.
> - Hiçbir görevi yeniden oluşturma, hepsi zaten çalışıyor.
> - Değişiklik gerekirse `update_trigger` kullan.

## 1. Kullanıcı ve çalışma kuralları

- **Kim:** Ali. İlhan Şahin Kurs Merkezi'nde rehber öğretmen. @derecefilm Instagram film hesabını yönetiyor. **Mac** kullanıyor.
- **Dil ve talimatlar:** Her zaman Türkçe yazılır. Yalnızca Mac talimatı verilir.
- **Otomasyon beklentisi:** "Ben botu açarım, gerisi sende." Ali'nin komut yazması beklenmez; her şey otomatik olmalı.
- **Yatırım tavsiyesi:**
  - Kişisel yatırım tavsiyesi verilmez.
  - Sinyaller "kuralların mekanik çıktısı", seviyeler "kurallara göre", aralıklar "olası aralık" diye yazılır.
  - Her raporun sonunda "yatırım tavsiyesi değildir" uyarısı bulunur.
- **Güvenlik:**
  - API anahtarları sohbete yapıştırılmaz ve yazdırılmaz.
  - GitHub secrets ve IG_TOKEN'a dokunulmaz.
  - Dosya silinmez.
- **Gerçek hesaplar:**
  - Alpaca'da yalnızca **deneme (paper) hesabı** kullanılır.
  - Ali'nin gerçek portföyünde **ARKG**, **MRVL** ve **DY** var (8 Ekim ekran görüntüsü; DY en büyük pozisyon). Midas'ı kullanıyor, ama Midas'ın API'si yok.

## 2. Zamanlanmış görevler (bulutta çalışır; Mac kapalı olsa da çalışır, aksi belirtilmedikçe)

| Görev | Zaman (İstanbul) | ID | Ne yapar |
|---|---|---|---|
| **ABD günlük analiz PDF'i** | Hafta içi 13:04 başlar, 13:30'da teslim | `trig_016rTEqHXKUTNs5bDngxHEdT` | `alibal123/otomasyon` deposundaki `bulut-gorevleri/abd-analiz.md` talimatını uygular (ayrıntı bölüm 3'te). Telefona bildirim ve e-posta gönderir. |
| **ABD fon günlük sinyal raporu** | Hafta içi 15:52 | `trig_01PhcKuJQHtbeAPgeZJ6xCkN` | Mac'teki botun saat 15:45'te ürettiği `gunluk_rapor.txt` dosyasını okur, haberleri ekler ve gönderir. **Mac'in açık olması gerekir.** |
| derecefilm 14:00 sinema haberi | Her gün 12:48 | `trig_015icUeYQ2EMCrV5etHHQ8AQ` | `alibal123/Ali` deposundaki NEWS_TASK.md'yi uygular. |
| derecefilm 19:30 uyarı + 20:00 paylaşım | Her gün 19:28 | `trig_01EJqhoww7ea9quJzRUSZ6wi` | `publish.yml` iş akışını tetikler ve paylaşımı doğrular. |
| derecefilm yorum cevapları | Her gün 22:13 | `trig_01GQfUaMhAtxAtKhhPigPNpU` | Cevap taslaklarını bildirim olarak gönderir. Ali "gönder" yazınca yayınlar. Mac'teki Claude tarayıcısı gerekir. |
| derecefilm haftalık içerik | Pazar 10:48 | `trig_01DPznLDFyw8EZ3UQk9YdDhX` | `alibal123/Ali` deposundaki WEEKLY_TASK.md'yi uygular. |
| derecefilm haftalık metin | Pazar 11:00 | `trig_019SjedHNfGMw1nNTEUM1W3p` | `otomasyon` deposundaki `bulut-gorevleri/derecefilm-metin.md`'yi uygular. |
| Ses klonlama / WhatsApp hatırlatmaları | 3 günde bir | `trig_011CEGj…`, `trig_01R5vdU…` | Ali "kapat" derse silinir. |

## 3. ABD günlük analiz PDF'i (13:30)

- **Kod:** `otomasyon` deposunda `abd-analiz/analiz.py`.
  - `python3 analiz.py hesapla` → göstergeler, seviyeler, olası aralıklar ve öz-kontrol.
  - `python3 analiz.py pdf` → PDF dosyası ve `tahminler/<tarih>.json`.
- **Görev talimatı:** `bulut-gorevleri/abd-analiz.md`. **İçerik şablonu:** `abd-analiz/ornek-icerik.json`.
- **Veri:** Bulut kabuğu finans sitelerine erişemez. Fiyatlar **WebFetch ile stockanalysis.com/…/history/** sayfalarından alınır. Yahoo ve stooq robots.txt nedeniyle kapalı.
- **Kapsam:**
  - Piyasa: SPY, QQQ.
  - Ayrıntılı hisseler: **MRVL, ARKG, DY**.
  - Fonlar: SMH, SOXX, AIQ, CIBR, ARKQ, ARKW, ARKF, BLOK, URA, GLD.
- **PDF içeriği:**
  - Dünkü tahminlerin öz-kontrolü.
  - Piyasa durumu ve senaryolar.
  - Her ayrıntılı hisse için üç grafik: geçmiş ve 1 haftalık koni, 1 gün, 1 hafta. Pivot, destek ve direnç seviyeleri.
  - Al-sat seviye tablosu, teknik görünüm, temel tablo, davranışsal sinyaller, riskler.
  - Fon tablosu ve grafikleri, kaynaklar.
- **Olası aralık yöntemi:** Son 20 günün oynaklığı σ ile hesaplanır. 1 gün için ±1σ (%68) ve ±2σ (%95). Hafta için σ√gün.
- **Öz-kontrol:** Her gün `tahminler/<tarih>.json` dosyası commit edilir. Ertesi gün gerçekleşen kapanışlarla karşılaştırılır.
- **Ali'nin kalıcı isteği (görev metninde):** Senaryolara bir "kalabalığa ters / manipülasyon ihtimali" senaryosu eklenir: stop avı, sahte kırılım, "haberi sat", short squeeze, opsiyon vadesi, ARK işlemleri, yönetici satışları. Kaynaksız suçlama yapılmaz.
- Ali bu raporda "sadece temel analiz yapma, derin araştır" dedi.

## 4. Mac'teki ABD fon botu (`~/Desktop/kisa-vade-bot`)

- **Aracı kurum:** Alpaca, **deneme hesabı**, sanal para.
- **Ayarlar (`abd_ayar.ini`):** `deneme_hesabi = evet`, `portfoy = otomatik`, `islem_basina_usd = 1000`, `en_fazla_acik_pozisyon = 8`, `takip = ARKG, MRVL` (DY henüz takip listesinde değil; Mac'e erişilince eklenmeli). Anahtarlar bu dosyada; yazdırılmaz.
- **Başlatma:** Masaüstünde `6-ABD-Bot-Baslat.command` dosyasına çift tıklanır. Bot ve panel birlikte açılır: http://localhost:8788. Terminal penceresi açık kalmalı ve **Mac uyumamalı.** Bot kod güncellemesinden sonra yeniden başlatılmalıdır (Ctrl+C, ardından çift tık).
- **Mantık:**
  - 37 ABD fonu ve MRVL için üç strateji test edilir: trend (EMA kesişimi), kırılım (20/55 gün zirvesi + SMA200), düşüşte alım (RSI2).
  - Test yöntemi: %60 eğitim, %20 doğrulama, %20 hiç görülmemiş son test. Üç dönemin hepsinde kâr eden fonlarda işlem yapılır.
  - Gün içi ölçekler (5 dk, 15 dk, 1 saat) de test edilir. Günlükten açıkça iyi değilse günlük ölçekte kalınır; şu an **günlük** ölçekte.
  - Günlük kararlar New York saatiyle 09:45'te (TR 16:45, Kasım'dan sonra 17:45) verilir. Her alımdan sonra Alpaca'ya zarar durdurma (stop) emri konur.
  - Testler her hafta borsa kapalıyken yenilenir.
- **Davranışsal katman (`davranis.py`):**
  - **VIX filtresi:** Test edilir; geçerse VIX yüksekken trend ve kırılım alımı yapılmaz.
  - **Bilanço/hacim sürprizi:** Test edilir; geçerse deneme hesabında 500 $'lık, en fazla 3 pozisyon açılır, en fazla 10–20 gün tutulur.
  - **Yalnızca taramada puan olarak:** yönetici alımları (openinsider), ARK'ın günlük işlemleri, Alpaca haber tonu, Reddit ilgisi (apewisdom).
  - Saat 15:45 raporunun "Davranışsal tarama · 5 isim" bölümü buradan gelir.
- **Rapor:** `abd_rapor.py`, hafta içi 15:45'te `gunluk_rapor.txt/.json/.html` dosyalarını üretir.
- **Diğer başlatıcılar:**
  - `8-Gunluk-Rapor.command`: raporu hemen üretir.
  - `9-Davranis-Test.command`: davranışsal testi hemen yapar.
  - `5-ABD-Kontrol.command`: bağlantıyı kontrol eder.
  - `ABD-Panel-Ac.command`: paneli açar.
- **Son bilinen pozisyonlar (deneme hesabı):** QQQ 1 adet @761,78 (stop 714,93); AIQ 14 adet @67,27 (stop 62,22).
- **Kripto botları** (`bot.py`, arbitraj): Geçmiş testte kârlı çıkmadı. **Kullanılmıyor.** MASAK kuralları ve komisyonlar nedeniyle arbitraj yapılabilir değil.

## 5. Ali'nin sorduğu ve cevaplanmış konular

- **Bot neye göre al diyor:** Yalnızca geçmiş fiyat hareketlerine (teknik analiz) bakıyor. Haberler sinyali değiştirmiyor, rapora bilgi olarak ekleniyor.
- **Davranışsal finans:** Ali piyasayı insanların etkilediğini düşünüyor. Bu yüzden davranışsal katman ve "kalabalığa ters" senaryolar eklendi.
- **Fed faiz artış dönemleri:**
  - 2022: Nakit, enerji, emtia ve dolar kazandı. Büyüme hisseleri, uzun tahvil ve kripto kaybetti.
  - 2023: Fed hâlâ artırırken Nasdaq +%43 yükseldi.
  - 16 Eylül 2026 artışından sonra: yarı iletkenler ve MRVL (+%25) yükseldi, altın düştü.
  - Mekanizma: Fiyat = kâr × çarpan. Kâr büyümesi faizin çarpandaki etkisini aşarsa hisse yine yükselir.
- **Bugünün piyasa bağlamı (Ekim 2026):**
  - Fed faizi %3,75–4,00. Aralık artışı ihtimali yaklaşık %85.
  - 10 yıllık faiz yaklaşık %5,3; Brent 100 $ üstü.
  - TÜFE 14 Ekim'de, TSMC bilançosu 15 Ekim'de. Çin'in nadir toprak elementi ihracat arası 10 Kasım'da bitiyor.

## 6. Önemli dosya ve depolar

- **GitHub `alibal123/otomasyon`:** `abd-analiz/` (PDF kodu ve tahmin kayıtları), `bulut-gorevleri/` (görev talimatları), derecefilm metinleri, bu not.
- **GitHub `alibal123/Ali`:** derecefilm Instagram gönderileri, `schedule.json`, render araçları, `publish.yml`.
- **Mac `~/Desktop/kisa-vade-bot`:** ABD botu, panel, raporlar, `ABD-KURULUM.md` kurulum notu.

## 7. Bilinen sınırlar ve dikkat edilecekler

- **Mac'e bağlı görevler:** 15:52 sinyal raporu ve derecefilm yorum cevapları ancak Mac açıkken ve Claude masaüstü uygulaması bağlıyken çalışır. Mac uyursa botun işlemleri de gecikir.
- **Bulut ortamının sınırları:** Yahoo, Alpaca ve Binance'e doğrudan erişemez. Mac'teki Claude kabuğu da (sandbox) erişemez; bunlara yalnızca botun kendisi erişebilir.
- **Kasım'da saat değişikliği:** ABD borsası TR saatiyle 17:30–24:00 olur. Bot New York saatine göre çalıştığı için bundan etkilenmez.
