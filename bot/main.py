"""Ponto de entrada: python -m bot.main [--dry-run]"""
from __future__ import annotations

import argparse
import html
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

from . import upwork
from .filters import Profile, matches
from .models import Job
from .state import SeenState
from .telegram import TelegramClient, format_job

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_profiles(path: Path) -> List[Profile]:
    data = yaml.safe_load(path.read_text()) or {}
    profiles = [Profile.from_dict(p) for p in data.get("profiles", [])]
    if not profiles:
        raise ValueError(f"Nenhum perfil definido em {path}")
    return profiles


def collect_matches(access_token: str, profiles: List[Profile]) -> List[Tuple[Job, List[str]]]:
    """Busca vagas de cada perfil e agrupa: uma vaga que casa com vários perfis recebe várias tags."""
    by_id: Dict[str, Tuple[Job, List[str]]] = {}
    for p in profiles:
        for job in upwork.search_jobs(access_token, p.keywords):
            if matches(job, p):
                entry = by_id.setdefault(job.id, (job, []))
                if p.tag not in entry[1]:
                    entry[1].append(p.tag)
    # Mais antigas primeiro, para o chat ficar em ordem cronológica
    return sorted(by_id.values(), key=lambda t: t[0].published_at or "")


def env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"Variável de ambiente ausente: {name}")
    return v


def run(dry_run: bool, config: Path, state_path: Path) -> int:
    profiles = load_profiles(config)
    state = SeenState(state_path)

    tg = None if dry_run else TelegramClient(env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID"))
    try:
        tokens = upwork.refresh_access_token(
            env("UPWORK_CLIENT_ID"), env("UPWORK_CLIENT_SECRET"), env("UPWORK_REFRESH_TOKEN")
        )
        found = collect_matches(tokens["access_token"], profiles)
    except Exception as exc:  # avisa no Telegram e falha o job
        if tg:
            tg.send(f"🚨 <b>Erro no bot do Upwork</b>\n<code>{html.escape(str(exc))[:800]}</code>")
        raise

    new = [(j, tags) for j, tags in found if j.id not in state]
    print(f"{len(found)} vagas casaram com os filtros, {len(new)} novas")

    if dry_run:
        for job, tags in new:
            print("-" * 60 + "\n" + format_job(job, tags))
        return 0

    if not state.initialized:
        # Primeira execução: só registra as vagas existentes, sem inundar o chat.
        state.add_many(j.id for j, _ in found)
        state.initialized = True
        state.save()
        tg.send(f"🤖 Bot ativo! Monitorando {len(profiles)} perfil(is): " + ", ".join(p.tag for p in profiles))
        print("Primeira execução: estado inicializado sem enviar vagas.")
        return 0

    for job, tags in new:
        tg.send(format_job(job, tags))
        state.add_many([job.id])
        state.save()  # salva a cada envio para não repetir se falhar no meio
        time.sleep(1)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Avisa no Telegram sobre novas vagas do Upwork")
    ap.add_argument("--dry-run", action="store_true", help="imprime as vagas em vez de enviar e não salva o estado")
    ap.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    ap.add_argument("--state", type=Path, default=ROOT / "state" / "seen.json")
    args = ap.parse_args()
    load_dotenv(ROOT / ".env")
    return run(args.dry_run, args.config, args.state)


if __name__ == "__main__":
    sys.exit(main())
