from __future__ import annotations

import html
import time
from typing import List, Optional

import httpx

from .models import Job

API = "https://api.telegram.org/bot{token}/{method}"


def _fmt_money(v: Optional[float]) -> str:
    return f"${v:,.0f}" if v is not None else "?"


def format_job(job: Job, tags: List[str]) -> str:
    e = html.escape
    if job.job_type == "FIXED":
        budget = f"💰 Preço fixo: {_fmt_money(job.fixed_budget)}"
    elif job.job_type == "HOURLY":
        if job.hourly_min or job.hourly_max:
            budget = f"⏱ Por hora: {_fmt_money(job.hourly_min)}–{_fmt_money(job.hourly_max)}/h"
        else:
            budget = "⏱ Por hora (faixa não informada)"
    else:
        budget = "💰 Orçamento não informado"

    client_bits = []
    if job.client_country:
        client_bits.append(e(job.client_country))
    client_bits.append("✅ pagamento verificado" if job.client_payment_verified else "⚠️ pagamento não verificado")
    if job.client_total_spent is not None:
        client_bits.append(f"gastou {_fmt_money(job.client_total_spent)}")
    if job.client_total_hires is not None:
        client_bits.append(f"{job.client_total_hires} contratações")

    desc = job.description.replace("\n", " ")
    if len(desc) > 300:
        desc = desc[:300].rsplit(" ", 1)[0] + "…"

    lines = [
        " ".join(tags),
        f'<b><a href="{e(job.url, quote=True)}">{e(job.title)}</a></b>',
        budget,
    ]
    if job.experience_level:
        lines.append(f"🎯 Nível: {e(job.experience_level.title())}")
    lines.append("👤 Cliente: " + " · ".join(client_bits))
    if job.skills:
        lines.append("🛠 " + e(", ".join(job.skills[:8])))
    if desc:
        lines.append("")
        lines.append(e(desc))
    if job.published_at:
        lines.append("")
        lines.append(f"🕒 {e(job.published_at)}")
    return "\n".join(lines)


class TelegramClient:
    def __init__(self, token: str, chat_id: str, http: Optional[httpx.Client] = None):
        self.token = token
        self.chat_id = chat_id
        self.http = http or httpx.Client(timeout=30)

    def send(self, text: str, silent: bool = False, retries: int = 3) -> None:
        url = API.format(token=self.token, method="sendMessage")
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "disable_notification": silent,
        }
        for _ in range(retries):
            resp = self.http.post(url, json=payload)
            if resp.status_code == 429:
                wait = resp.json().get("parameters", {}).get("retry_after", 5)
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                raise RuntimeError(f"Telegram sendMessage falhou ({resp.status_code}): {resp.text[:300]}")
            return
        raise RuntimeError("Telegram: limite de envio excedido repetidamente")
