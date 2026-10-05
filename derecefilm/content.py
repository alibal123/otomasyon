"""İçerik üretimi üç aşamalıdır:

1. brief()   — TMDB'den filmleri seçer, metin yazarı için bir "brief" hazırlar (LLM yok).
2. (metin)   — Metni Claude bulut görevi yazar (derecefilm/metin/TARİH.json) ya da yedek olarak API.
3. render()  — Doğrulanmış metni ve posterleri görsele çevirir.

Metin yazarı yalnızca brief içindeki verileri kullanır; veri dışı bilgi uydurmamalıdır.
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta

from . import designs as D
from . import tmdb

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
HAFTA_PLANI = ["list", "single", "doc", "quiz", "radar", "list", "single"]  # Pzt=0 ... Paz=6

LISTE_TURLERI = {
    53: "gerilim", 878: "bilim kurgu", 18: "dram", 35: "komedi", 80: "suç", 16: "animasyon",
    9648: "gizem", 10749: "romantik", 27: "korku", 12: "macera",
}

SISTEM = (
    "Sen 'derecefilm' adlı Türkçe film Instagram hesabının editörüsün. Samimi, bilgili, kısa cümlelerle yazarsın. "
    "KURALLAR: Yalnızca brief'teki verileri kullan; verilmeyen oyuncu, ödül, gişe, yönetmen ya da sahne bilgisi "
    "UYDURMA. Spoiler verme. En fazla 3 emoji kullan. İtalik/markdown kullanma. Çıktı yalnızca geçerli bir JSON nesnesi olsun."
)


def _tr_date(s: str) -> str:
    y, m, d = (int(x) for x in s.split("-"))
    return f"{d} {AYLAR[m - 1]}"


def _pick(rng: random.Random, used: set, n: int, min_votes: int, **extra) -> list[dict]:
    found, ids = [], set()
    for _ in range(8):
        for m in tmdb.discover(page=rng.randint(1, 12), **{"sort_by": "vote_average.desc", "vote_count.gte": min_votes, **extra}):
            if m["id"] not in used and m["id"] not in ids:
                found.append(m)
                ids.add(m["id"])
        if len(found) >= n * 3:
            break
    if len(found) < n:
        raise RuntimeError(f"TMDB'den yeterli yeni film bulunamadı (istenen {n}, bulunan {len(found)}).")
    rng.shuffle(found)
    return [tmdb.details(m["id"]) for m in found[:n]]


def _kisa(f: dict, *keys) -> dict:
    return {k: f[k] for k in keys}


# ------------------------------------------------------------------ 1) BRIEF
def brief(d: date, used: set) -> dict:
    kind = HAFTA_PLANI[d.weekday()]
    rng = random.Random(d.toordinal())
    b = {"date": d.isoformat(), "kind": kind, "sistem": SISTEM, "ekstra": {}}
    common_tail = '"etiketler":["en fazla 6, # olmadan"]'

    if kind == "list":
        gid = rng.choice(list(LISTE_TURLERI))
        films = _pick(rng, used, 5, 3000, with_genres=str(gid))
        veri = [_kisa(f, "id", "title", "year", "overview", "genres", "vote") for f in films]
        b["istek"] = (
            f"Tema: {LISTE_TURLERI[gid]} filmleri. Aşağıdaki 5 filmle bir liste gönderisi hazırla.\n"
            f"Filmler: {json.dumps(veri, ensure_ascii=False)}\n"
            'JSON: {"baslik":"<=55 karakter, sayı içeren çarpıcı liste başlığı","filmler":[{"id":int,"neden":"<=85 karakter"}],'
            f'"aciklama":"<=650 karakter, sonda bir soru",{common_tail}}}'
        )
    elif kind in ("single", "doc"):
        doc = kind == "doc"
        films = _pick(rng, used, 1, 400 if doc else 5000, **({"with_genres": "99"} if doc else {}))
        veri = _kisa(films[0], "title", "year", "overview", "tagline", "genres", "director", "cast", "runtime", "vote")
        b["istek"] = (
            f"{'BELGESEL' if doc else 'TEK FİLM'} gönderisi hazırla. Film verisi: {json.dumps(veri, ensure_ascii=False)}\n"
            'JSON: {"slogan":"<=70 karakter tek cümle","neden":"<=360 karakter, neden izlenmeli (spoilersiz)",'
            f'"aciklama":"<=650 karakter, sonda bir soru",{common_tail}}}'
        )
    elif kind == "quiz":
        films = _pick(rng, used, 3, 8000)
        titles = [f["title"] for f in films]
        order = list(range(3))
        rng.shuffle(order)
        shuffled = [titles[i] for i in order]
        b["ekstra"] = {"secenekler": shuffled, "dogru_index": order.index(0)}
        veri = _kisa(films[0], "title", "year", "overview", "tagline", "director", "cast", "genres")
        b["istek"] = (
            f"Quiz hazırla. Doğru cevap filmi: {json.dumps(veri, ensure_ascii=False)}\n"
            f"Seçenekler (sıra sabit, kodla belirlendi): {json.dumps(shuffled, ensure_ascii=False)}\n"
            "Soru, doğru filmi konusundan/oyuncularından/yönetmeninden ima etsin ama ASLA doğru filmin adını yazmasın "
            "(ne soruda ne açıklamada ne gönderi metninde cevap açığa çıkmasın).\n"
            'JSON: {"soru":"<=150 karakter","aciklama":"<=230 karakter, yalnızca verilen verilerle neden doğru",'
            f'"gonderi":"<=500 karakter, cevabı yorumlarda tahmin etmeye davet et, cevabı SÖYLEME",{common_tail}}}'
        )
        b["filmler"] = films  # tüm üçü kullanılmış sayılsın
        b["dogru_film"] = films[0]
        return b
    else:  # radar
        res = tmdb.discover(
            region="TR", with_release_type="2|3", sort_by="popularity.desc",
            **{"release_date.gte": d.isoformat(), "release_date.lte": (d + timedelta(days=45)).isoformat()},
        )
        res = [m for m in res if m["id"] not in used][:4]
        if len(res) < 3:
            raise RuntimeError(f"Radar için yeterli vizyon filmi yok (bulunan {len(res)}).")
        films = [tmdb.details(m["id"]) for m in res]
        for f, m in zip(films, res):
            f["release_date"] = m.get("release_date") or f["release_date"]
        veri = [_kisa(f, "id", "title", "release_date", "overview", "genres", "director") for f in films]
        b["istek"] = (
            f"RADAR gönderisi: önümüzdeki haftalarda Türkiye'de vizyona girecek filmler. Veri: {json.dumps(veri, ensure_ascii=False)}\n"
            'JSON: {"baslik":"<=50 karakter","filmler":[{"id":int,"not":"<=80 karakter, konuya dair spoilersiz not"}],'
            f'"aciklama":"<=600 karakter, sonda bir soru",{common_tail}}}'
        )
    b["filmler"] = films
    return b


# ------------------------------------------------------------------ 2) DOĞRULAMA
def _need(cond: bool, msg: str):
    if not cond:
        raise ValueError(msg)


def _str(t: dict, key: str, mx: int) -> str:
    v = t.get(key)
    _need(isinstance(v, str) and v.strip(), f"'{key}' eksik ya da boş.")
    _need(len(v) <= mx, f"'{key}' {len(v)} karakter, en fazla {mx} olmalı.")
    return v.strip()


def validate(b: dict, t: dict):
    """Metin brief'e uymuyorsa ValueError fırlatır."""
    kind = b["kind"]
    _need(isinstance(t.get("etiketler", []), list), "'etiketler' liste olmalı.")
    if kind == "list":
        _str(t, "baslik", 60)
        _str(t, "aciklama", 700)
        ids = {int(x["id"]): _str(x, "neden", 100) for x in t.get("filmler", [])}
        _need(set(ids) == {f["id"] for f in b["filmler"]}, "'filmler' kimlikleri brief ile eşleşmiyor.")
    elif kind in ("single", "doc"):
        _str(t, "slogan", 80)
        _str(t, "neden", 420)
        _str(t, "aciklama", 700)
    elif kind == "quiz":
        title = b["dogru_film"]["title"].lower()
        for k, mx in (("soru", 170), ("aciklama", 260), ("gonderi", 550)):
            _need(title not in _str(t, k, mx).lower(), f"'{k}' doğru cevabın adını içeriyor.")
    else:
        _str(t, "baslik", 55)
        _str(t, "aciklama", 650)
        ids = {int(x["id"]): _str(x, "not", 90) for x in t.get("filmler", [])}
        _need(set(ids) == {f["id"] for f in b["filmler"]}, "'filmler' kimlikleri brief ile eşleşmiyor.")


def _caption(text: str, tags: list) -> str:
    tags = [str(x).strip().lstrip("#").replace(" ", "") for x in tags][:8]
    tags = ["derecefilm", "film", *[x for x in tags if x and x.lower() not in ("derecefilm", "film")]]
    cap = text.strip() + "\n\n" + " ".join(f"#{x}" for x in tags)
    _need(len(cap) <= 2100, "Açıklama Instagram sınırını aşıyor.")
    return cap


# ------------------------------------------------------------------ 3) RENDER
def palette_for(d: date) -> tuple[dict, int]:
    """Ardışık günler hiçbir zaman aynı paleti/düzeni kullanmaz."""
    o = d.toordinal()
    return D.PALETTES[(o * 3) % len(D.PALETTES)], (o * 5) % 4


def render(b: dict, t: dict) -> tuple[list, str]:
    validate(b, t)
    d = date.fromisoformat(b["date"])
    p, v = palette_for(d)
    kind, films = b["kind"], b["filmler"]
    tags = t.get("etiketler", [])

    if kind == "list":
        neden = {int(x["id"]): x["neden"] for x in t["filmler"]}
        posters = [tmdb.poster_bytes(f["poster_path"]) for f in films]
        n = len(films) + 1
        imgs = [D.cover(p, v, "LİSTE", t["baslik"], posters, f"{len(films)} film • kaydet", 1, n)]
        for i, (f, pb) in enumerate(zip(films, posters), 1):
            imgs.append(D.list_item(p, v, i, {"title": f["title"], "year": f["year"], "blurb": neden[f["id"]], "poster": pb}, i + 1, n))
        return imgs, _caption(t["aciklama"], tags)

    if kind in ("single", "doc"):
        f = films[0]
        pb = tmdb.poster_bytes(f["poster_path"])
        facts = []
        if f["director"]:
            facts.append(f"Yönetmen: {f['director']}")
        if f["vote"]:
            facts.append(f"TMDB puanı: {f['vote']}")
        if f["runtime"]:
            facts.append(f"Süre: {f['runtime']} dk")
        if f["year"]:
            facts.append(f"Yıl: {f['year']}")
        imgs = [
            D.single_cover(p, v, "BELGESEL" if kind == "doc" else "TEK FİLM", f["title"], t["slogan"], pb, 1, 2),
            D.single_detail(p, v, "Neden izlemeli?", t["neden"], facts[:4], 2, 2),
        ]
        return imgs, _caption(t["aciklama"], tags)

    if kind == "quiz":
        opts, idx = b["ekstra"]["secenekler"], b["ekstra"]["dogru_index"]
        c = b["dogru_film"]
        imgs = [
            D.quiz_question(p, v, t["soru"], opts, 1, 2),
            D.quiz_answer(p, v, "ABC"[idx], c["title"], t["aciklama"], tmdb.poster_bytes(c["poster_path"]), 2, 2),
        ]
        return imgs, _caption(t["gonderi"], tags)

    notes = {int(x["id"]): x["not"] for x in t["filmler"]}
    posters = [tmdb.poster_bytes(f["poster_path"]) for f in films]
    items = [
        {"title": f["title"], "date": _tr_date(f["release_date"]), "blurb": notes[f["id"]], "poster": pb}
        for f, pb in zip(films, posters)
    ]
    imgs = [
        D.cover(p, v, "RADAR", t["baslik"], posters, "vizyon takvimi", 1, 2),
        D.radar_detail(p, v, t["baslik"], items, 2, 2),
    ]
    return imgs, _caption(t["aciklama"], tags)
