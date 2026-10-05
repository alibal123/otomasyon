"""Anthropic Messages API için küçük istemci. Anahtar yalnızca ortam değişkeninden okunur."""
import json
import os
import re

import requests

API_URL = "https://api.anthropic.com/v1/messages"


def ask(system: str, user: str, max_tokens: int = 2500) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY ortam değişkeni (GitHub Secret) tanımlı değil.")
    model = os.environ.get("LLM_MODEL", "claude-sonnet-5-5")
    r = requests.post(
        API_URL,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=120,
    )
    if not r.ok:
        raise RuntimeError(f"Anthropic API hatası {r.status_code}: {r.text[:500]}")
    return "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")


def ask_json(system: str, user: str, max_tokens: int = 2500) -> dict:
    text = ask(system, user, max_tokens)
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise RuntimeError(f"Model JSON döndürmedi: {text[:300]}")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Model JSON'u bozuk: {e}: {text[:300]}") from e
