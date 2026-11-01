"""Obtém o refresh token inicial do Upwork e grava no .env (sem exibi-lo).

    python scripts/get_upwork_token.py              # 1) mostra a URL de autorização
    python scripts/get_upwork_token.py "<URL>"      # 2) troca o code pelo token e salva no .env

Pré-requisito: UPWORK_CLIENT_ID e UPWORK_CLIENT_SECRET no .env. UPWORK_REDIRECT_URI deve ser
igual ao "Callback URL" da chave (padrão: https://localhost/callback).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot.main import ROOT, load_dotenv  # noqa: E402
from bot.upwork import TOKEN_URL  # noqa: E402

AUTH_URL = "https://www.upwork.com/ab/account-security/oauth2/authorize"
ENV_FILE = ROOT / ".env"


def save_to_env(key: str, value: str) -> None:
    text = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    line = f"{key}={value}"
    if re.search(rf"^{key}=.*$", text, flags=re.M):
        text = re.sub(rf"^{key}=.*$", lambda _: line, text, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    ENV_FILE.write_text(text)


def main() -> None:
    load_dotenv(ENV_FILE)
    client_id = os.environ["UPWORK_CLIENT_ID"]
    client_secret = os.environ["UPWORK_CLIENT_SECRET"]
    redirect_uri = os.environ.get("UPWORK_REDIRECT_URI", "https://localhost/callback")

    if len(sys.argv) < 2:
        url = AUTH_URL + "?" + urlencode(
            {"response_type": "code", "client_id": client_id, "redirect_uri": redirect_uri}
        )
        print("Abra no navegador e autorize o app:\n\n" + url + "\n")
        print("Depois rode de novo passando a URL para onde foi redirecionada:")
        print('  python scripts/get_upwork_token.py "<URL>"')
        return

    arg = sys.argv[1].strip()
    code = parse_qs(urlparse(arg).query).get("code", [arg])[0]
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
        sys.exit(f"Erro {resp.status_code}: {resp.text[:500]}")
    save_to_env("UPWORK_REFRESH_TOKEN", resp.json()["refresh_token"])
    print("✅ Refresh token salvo no .env (UPWORK_REFRESH_TOKEN).")


if __name__ == "__main__":
    main()
