"""Instagram Graph API ile resim / carousel yayını. Token yalnızca ortam değişkeninden okunur."""
from __future__ import annotations

import os
import time

import requests

VERSION = os.environ.get("GRAPH_VERSION", "v23.0")
BASE = f"https://graph.facebook.com/{VERSION}"


class IGError(RuntimeError):
    pass


def _creds() -> tuple[str, str]:
    uid, tok = os.environ.get("IG_USER_ID"), os.environ.get("IG_ACCESS_TOKEN")
    if not uid or not tok:
        raise IGError("IG_USER_ID ve/veya IG_ACCESS_TOKEN tanımlı değil (GitHub Secrets).")
    return uid, tok


def _call(method: str, path: str, **data) -> dict:
    _, tok = _creds()
    r = requests.request(method, f"{BASE}/{path}", data=data if method == "POST" else None,
                         params=data if method == "GET" else None,
                         headers={"Authorization": f"Bearer {tok}"}, timeout=60)
    try:
        body = r.json()
    except ValueError:
        body = {"raw": r.text[:300]}
    if not r.ok or "error" in body:
        raise IGError(f"Instagram API hatası ({method} {path}) HTTP {r.status_code}: {body.get('error', body)}")
    return body


def check_public(url: str):
    r = requests.get(url, timeout=30, stream=True)
    ctype = r.headers.get("content-type", "")
    if r.status_code != 200 or "jpeg" not in ctype:
        raise IGError(f"Görsel herkese açık değil ya da JPEG değil: {url} → HTTP {r.status_code} {ctype}. "
                      "Depo herkese açık (public) olmalı.")


def _wait(container: str, tries: int = 30):
    for _ in range(tries):
        st = _call("GET", container, fields="status_code,status").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise IGError(f"Konteyner işlenemedi: {container} durum={st}")
        time.sleep(4)
    raise IGError(f"Konteyner zaman aşımı: {container}")


def publish(image_urls: list[str], caption: str) -> str:
    uid, _ = _creds()
    for u in image_urls:
        check_public(u)
    if len(image_urls) == 1:
        cid = _call("POST", f"{uid}/media", image_url=image_urls[0], caption=caption)["id"]
    else:
        kids = []
        for u in image_urls:
            kid = _call("POST", f"{uid}/media", image_url=u, is_carousel_item="true")["id"]
            _wait(kid)
            kids.append(kid)
        cid = _call("POST", f"{uid}/media", media_type="CAROUSEL", children=",".join(kids), caption=caption)["id"]
    _wait(cid)
    return _call("POST", f"{uid}/media_publish", creation_id=cid)["id"]
