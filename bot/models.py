from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Job:
    id: str
    title: str
    url: str
    description: str = ""
    job_type: Optional[str] = None  # "HOURLY" | "FIXED"
    fixed_budget: Optional[float] = None
    hourly_min: Optional[float] = None
    hourly_max: Optional[float] = None
    currency: str = "USD"
    experience_level: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    category: Optional[str] = None
    client_country: Optional[str] = None
    client_payment_verified: bool = False
    client_total_spent: Optional[float] = None
    client_total_hires: Optional[int] = None
    published_at: Optional[str] = None

    @property
    def searchable_text(self) -> str:
        return " ".join([self.title, self.description, " ".join(self.skills)]).lower()
