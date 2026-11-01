from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import Job


@dataclass
class Profile:
    name: str
    keywords: List[str]
    exclude_keywords: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    job_type: str = "any"  # hourly | fixed | any
    min_fixed_budget: Optional[float] = None
    min_hourly_rate: Optional[float] = None
    client_payment_verified: bool = False
    client_min_total_spent: Optional[float] = None
    client_countries_exclude: List[str] = field(default_factory=list)

    @property
    def tag(self) -> str:
        return "#" + re.sub(r"[^0-9A-Za-zÀ-ÿ_]", "", self.name.title().replace(" ", ""))

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Profile":
        client = d.get("client") or {}
        if not d.get("name") or not d.get("keywords"):
            raise ValueError(f"Perfil inválido (name e keywords são obrigatórios): {d}")
        return cls(
            name=d["name"],
            keywords=list(d["keywords"]),
            exclude_keywords=list(d.get("exclude_keywords") or []),
            categories=list(d.get("categories") or []),
            job_type=(d.get("job_type") or "any").lower(),
            min_fixed_budget=d.get("min_fixed_budget"),
            min_hourly_rate=d.get("min_hourly_rate"),
            client_payment_verified=bool(client.get("payment_verified", False)),
            client_min_total_spent=client.get("min_total_spent"),
            client_countries_exclude=list(client.get("countries_exclude") or []),
        )


def matches(job: Job, p: Profile) -> bool:
    text = job.searchable_text
    if any(k.lower() in text for k in p.exclude_keywords):
        return False

    if p.categories:
        if not job.category or job.category.lower() not in {c.lower() for c in p.categories}:
            return False

    if p.job_type in ("hourly", "fixed") and job.job_type and job.job_type.lower() != p.job_type:
        return False

    if job.job_type == "FIXED" and p.min_fixed_budget is not None:
        if job.fixed_budget is None or job.fixed_budget < p.min_fixed_budget:
            return False

    if job.job_type == "HOURLY" and p.min_hourly_rate is not None:
        top = job.hourly_max or job.hourly_min
        # Vagas por hora sem faixa informada passam (muitos clientes não informam).
        if top is not None and top < p.min_hourly_rate:
            return False

    if p.client_payment_verified and not job.client_payment_verified:
        return False

    if p.client_min_total_spent is not None:
        if (job.client_total_spent or 0) < p.client_min_total_spent:
            return False

    if job.client_country and job.client_country.lower() in {c.lower() for c in p.client_countries_exclude}:
        return False

    return True
