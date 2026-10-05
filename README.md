# derecefilm otomasyonu

Metinleri **Claude bulut görevleri** yazar (Claude hesabınızdaki "cloud session credits" kullanılır, API anahtarı gerekmez).
Zamana duyarlı ve deterministik her şey (veri çekme, görsel üretimi, 20:00 paylaşımı) GitHub Actions'ta kalır.

| Aşama | Nerede | Zaman (İstanbul) | UTC cron | Ne yapar |
|---|---|---|---|---|
| derecefilm-1-haftalik-brief | Actions | Pazar 10:00 | `0 7 * * 0` | 7 günün filmlerini TMDB'den seçer → `derecefilm/briefs/` |
| derecefilm-metin | **Bulut görevi** | Pazar 11:00 | — | Brief'lere metin yazar → `derecefilm/metin/` (push) |
| derecefilm-2-gorsel-uretimi | Actions | metin push'unda + Pazar 14:00 kontrol | `0 11 * * 0` | Metni doğrular, görselleri üretir → `derecefilm/queue/` |
| derecefilm-gunluk-paylasim | Actions | Her gün 20:00 | `30 16 * * *` (19:30'da başlar, 20:00'ı bekler) | O günün gönderisini Instagram'a paylaşır; telafi yok |

Türkiye yıl boyu UTC+3 olduğu için saat dönüşümü sabittir (20:00 TR = 17:00 UTC).
Bulut görevlerinin talimatları: `bulut-gorevleri/`. Bulut görevi çalışmazsa/kredi biterse yedek yol:
`ANTHROPIC_API_KEY` ekleyip `python -m common.metin_api derecefilm` ile aynı metinler API ile yazılır.

## Secrets (Settings → Secrets and variables → Actions)

| Secret | Kullanan | Nereden |
|---|---|---|
| `TMDB_TOKEN` | derecefilm | themoviedb.org → Ayarlar → API → "API Read Access Token" |
| `IG_USER_ID` | derecefilm | Instagram Business hesap kimliği (aşağıda) |
| `IG_ACCESS_TOKEN` | derecefilm | Süresiz Sayfa erişim jetonu (aşağıda) |
| `ANTHROPIC_API_KEY` | yalnızca yedek yol | console.anthropic.com (şimdilik gerekmez) |

Kodda hiçbir anahtar yoktur; hepsi ortam değişkeninden okunur. Bulut görevlerine hiçbir secret verilmez.

## Instagram ön koşulları

1. Instagram hesabı **Profesyonel** (Business veya Creator) olmalı: Ayarlar → Hesap türü ve araçlar.
2. Bir **Facebook Sayfası** oluşturun ve Instagram hesabını o sayfaya bağlayın (Sayfa → Ayarlar → Bağlı hesaplar).
3. developers.facebook.com → Uygulama oluştur (tür: Business). Ürün ekle: Instagram / Facebook Login for Business.
   İzinler: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`, `business_management`.
   Kendi hesabınıza yayın için uygulama "Geliştirme" modunda kalabilir (siz yönetici olursunuz); App Review gerekmez.
4. Graph API Explorer'dan kısa ömürlü kullanıcı jetonu alın, sonra uzun ömürlüye çevirin:
   `GET /oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=KISA_JETON`
5. Uzun ömürlü kullanıcı jetonuyla `GET /me/accounts` çağırın. Dönen sayfanın `access_token` değeri **süresiz** Sayfa jetonudur → `IG_ACCESS_TOKEN`.
6. `GET /{SAYFA_ID}?fields=instagram_business_account` → dönen `id` → `IG_USER_ID`.
7. Görseller JPEG ve **herkese açık URL**'de olmalı. Bu proje görselleri depoya işleyip `raw.githubusercontent.com` üzerinden verir; bu yüzden **depo public** olmalıdır.

## TikTok (@derecefilm)

Resmî Content Posting API var, ama uygulamanız TikTok denetiminden (≈2–6 hafta) geçmediği sürece paylaşımlar yalnızca
**özel (SELF_ONLY)** olur ve hesap özel olmalıdır. Bu yüzden otomatik TikTok paylaşımı bu pakete eklenmedi.
Seçenekler: (a) aynı görselleri TikTok'a fotoğraf modunda elle yüklemek; (b) Postiz'in barındırılan sürümü
(kendi denetlenmiş uygulamasını kullanır); (c) Postiz'i kendiniz barındırmak — bu durumda da kendi TikTok geliştirici
uygulamanızı denetletmeniz gerekir, barındırmak denetimi atlatmaz.

## Yerel önizleme (anahtarsız)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r derecefilm/requirements.txt
python -m derecefilm.dev_preview onizleme
```

## Notlar

- TMDB verisi/posterleri için TMDB şartları geçerlidir (atıf: "Bu ürün TMDB API'sini kullanır, TMDB tarafından onaylanmamıştır"); ticari kullanım için lisans gerekir.
- Instagram jeton/uygulama ayarları değişirse hata Actions logunda ve açılan issue'da görünür. Graph API sürümü `GRAPH_VERSION` ortam değişkeniyle değiştirilebilir (varsayılan `v23.0`).
