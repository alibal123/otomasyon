"""TMDB'den film bilgisi + yazısız sahne kareleri (backdrop) indirir.

Girdi : derecefilm/stills/request.json
  {"ad": {"q": "Film adı", "year": 1999, "n": 4}}  ya da  {"ad": {"id": 123, "n": 4}}
  {"_upcoming_ad": {"upcoming": {"region": "TR", "from": "2026-11-05", "to": "2026-12-31"}}}
Çıktı : derecefilm/stills/<ad>_<i>.jpg  ve  derecefilm/stills/resolved.json (doğrulanmış künye bilgileri)
Token yalnızca TMDB_TOKEN ortam değişkeninden okunur.
"""
import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from derecefilm import tmdb  # noqa: E402

OUT = Path(__file__).parent / "stills"
REQ = OUT / "request.json"
RES = OUT / "resolved.json"


def info(mid: int) -> dict:
    d = tmdb.get(f"/movie/{mid}", append_to_response="credits,release_dates", language="tr-TR")
    tr_dates = []
    for r in d.get("release_dates", {}).get("results", []):
        if r["iso_3166_1"] == "TR":
            tr_dates = [x["release_date"][:10] for x in r["release_dates"]]
    crew = d.get("credits", {}).get("crew", [])
    return {
        "id": d["id"],
        "title_tr": d.get("title"),
        "original_title": d.get("original_title"),
        "release_date": d.get("release_date"),
        "tr_release": sorted(set(tr_dates)),
        "director": [c["name"] for c in crew if c.get("job") == "Director"],
        "cast": [c["name"] for c in d.get("credits", {}).get("cast", [])[:6]],
        "runtime": d.get("runtime"),
        "vote": round(d.get("vote_average") or 0, 1),
        "genres": [g["name"] for g in d.get("genres", [])],
        "overview": d.get("overview") or "",
        "status": d.get("status"),
    }


def backdrops(mid: int, n: int) -> list[str]:
    im = tmdb.get(f"/movie/{mid}/images", include_image_language="null", language="en")
    paths = [b["file_path"] for b in sorted(im.get("backdrops", []), key=lambda b: -(b.get("vote_average") or 0))
             if not b.get("iso_639_1")]
    return paths[:n]


def main() -> int:
    req = json.loads(REQ.read_text(encoding="utf-8"))
    res = json.loads(RES.read_text(encoding="utf-8")) if RES.exists() else {}
    for name, r in req.items():
        if name in res and "error" not in res[name]:
            continue
        try:
            if "discover" in r:
                found = []
                for page in (1, 2):
                    found += tmdb.get("/discover/movie", page=page, include_adult="false", **r["discover"])["results"]
                res[name] = [info(m["id"]) for m in found[:20]]
                print(name, len(res[name]), "film")
                continue
            if "upcoming" in r:
                u = r["upcoming"]
                found = []
                for page in (1, 2):
                    found += tmdb.get("/discover/movie", page=page, region=u["region"], with_release_type="2|3",
                                      sort_by="popularity.desc", include_adult="false",
                                      **{"release_date.gte": u["from"], "release_date.lte": u["to"]})["results"]
                res[name] = [info(m["id"]) for m in found[:20]]
                print(name, len(res[name]), "film")
                continue
            mid = r.get("id")
            if not mid:
                s = tmdb.get("/search/movie", query=r["q"], include_adult="false", **({"year": r["year"]} if r.get("year") else {}))
                if not s["results"]:
                    res[name] = {"error": "bulunamadı"}
                    continue
                mid = s["results"][0]["id"]
            meta = info(mid)
            files = []
            for i, p in enumerate(backdrops(mid, r.get("n", 4)), 1):
                out = OUT / f"{name}_{i}.jpg"
                if not out.exists():
                    out.write_bytes(requests.get(f"https://image.tmdb.org/t/p/w1280{p}", timeout=60).content)
                files.append(out.name)
            meta["files"] = files
            res[name] = meta
            print(name, mid, meta["title_tr"], meta["release_date"], len(files), "kare")
        except Exception as e:  # noqa: BLE001
            res[name] = {"error": str(e)[:200]}
            print("HATA", name, e)
    RES.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
