"""Rode UMA vez localmente para obter o refresh token inicial do Upwork.

    python scripts/get_upwork_token.py

Pré-requisito: UPWORK_CLIENT_ID e UPWORK_CLIENT_SECRET no .env (ou no ambiente) e
UPWORK_REDIRECT_URI igual ao "Callback URL" cadastrado na chave da API.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot.main import ROOT, load_dotenv  # noqa: E402
from bot.upwork import TOKEN_URL  # noqa: E402

AUTH_URL = "https://www.upwork.com/ab/account-security/oauth2/authorize"


def main() -> None:
    load_dotenv(ROOT / ".env")
    client_id = os.environ["UPWORK_CLIENT_ID"]
    client_secret = os.environ["UPWORK_CLIENT_SECRET"]
    redirect_uri = os.environ.get("UPWORK_REDIRECT_URI", "https://localhost/callback")

    url = AUTH_URL + "?" + urlencode(
        {"response_type": "code", "client_id": client_id, "redirect_uri": redirect_uri}
    )
    print("1) Abra no navegador e autorize o app:\n\n   " + url + "\n")
    print("2) Você será redirecionada para uma URL (pode dar erro de página, tudo bem).")
    pasted = input("   Cole aqui a URL completa (ou só o code): ").strip()
    code = parse_qs(urlparse(pasted).query).get("code", [pasted])[0]

    resp = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        sys.exit(f"Erro {resp.status_code}: {resp.text}")
    data = resp.json()
    print("\n✅ Refresh token (salve no secret UPWORK_REFRESH_TOKEN e no seu .env):\n")
    print(data["refresh_token"])


if __name__ == "__main__":
    main()
