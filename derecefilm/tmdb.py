"""TMDB istemcisi. Token yalnızca TMDB_TOKEN ortam değişkeninden okunur."""
import os

import requests

BASE = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w780"


def get(path: str, **params) -> dict:
    token = os.environ.get("TMDB_TOKEN")
    if not token:
        raise RuntimeError("TMDB_TOKEN ortam değişkeni (GitHub Secret) tanımlı değil.")
    params.setdefault("language", "tr-TR")
    r = requests.get(
        f"{BASE}{path}",
        params=params,
        headers={"Authorization": f"Bearer {token}", "accept": "application/json"},
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"TMDB hatası {r.status_code} ({path}): {r.text[:300]}")
    return r.json()


def discover(page: int = 1, **params) -> list[dict]:
    res = get("/discover/movie", page=page, include_adult="false", **params)["results"]
    return [m for m in res if m.get("poster_path") and (m.get("overview") or "").strip()]


def details(movie_id: int) -> dict:
    d = get(f"/movie/{movie_id}", append_to_response="credits")
    director = next((c["name"] for c in d.get("credits", {}).get("crew", []) if c.get("job") == "Director"), None)
    cast = [c["name"] for c in d.get("credits", {}).get("cast", [])[:5]]
    return {
        "id": d["id"],
        "title": d.get("title") or d.get("original_title"),
        "original_title": d.get("original_title"),
        "year": (d.get("release_date") or "")[:4],
        "release_date": d.get("release_date"),
        "overview": d.get("overview") or "",
        "tagline": d.get("tagline") or "",
        "runtime": d.get("runtime"),
        "vote": round(d.get("vote_average") or 0, 1),
        "genres": [g["name"] for g in d.get("genres", [])],
        "director": director,
        "cast": cast,
        "poster_path": d.get("poster_path"),
    }


def poster_bytes(poster_path: str | None) -> bytes | None:
    if not poster_path:
        return None
    r = requests.get(IMG + poster_path, timeout=30)
    return r.content if r.ok else None
