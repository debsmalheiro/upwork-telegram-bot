"""Cliente da API GraphQL oficial do Upwork.

Docs: https://www.upwork.com/developer/documentation/graphql/api/docs/index.html
Se o schema do Upwork mudar, ajuste apenas SEARCH_QUERY e parse_job().
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx

from .models import Job

TOKEN_URL = "https://www.upwork.com/api/v3/oauth2/token"
GRAPHQL_URL = "https://api.upwork.com/graphql"

SEARCH_QUERY = """
query SearchJobs($filter: MarketplaceJobPostingsSearchFilter, $sort: [MarketplaceJobPostingSearchSortAttribute]) {
  marketplaceJobPostingsSearch(
    marketPlaceJobFilter: $filter
    searchType: USER_JOBS_SEARCH
    sortAttributes: $sort
  ) {
    edges {
      node {
        id
        ciphertext
        title
        description
        createdDateTime
        publishedDateTime
        experienceLevel
        amount { rawValue currency }
        hourlyBudgetMin { rawValue }
        hourlyBudgetMax { rawValue }
        skills { name prettyName }
        occupations { category { prefLabel } }
        client {
          totalHires
          verificationStatus
          location { country }
          totalSpent { rawValue }
        }
      }
    }
  }
}
"""


class UpworkAuthError(RuntimeError):
    pass


def refresh_access_token(
    client_id: str, client_secret: str, refresh_token: str, http: Optional[httpx.Client] = None
) -> Dict[str, str]:
    """Troca o refresh token por um access token. O Upwork devolve um NOVO refresh token."""
    http = http or httpx.Client(timeout=30)
    resp = http.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    if resp.status_code != 200:
        raise UpworkAuthError(f"Falha ao renovar token ({resp.status_code}): {resp.text[:300]}")
    data = resp.json()
    new_refresh = data.get("refresh_token") or refresh_token
    _persist_refresh_token(new_refresh, refresh_token)
    return {"access_token": data["access_token"], "refresh_token": new_refresh}


def _persist_refresh_token(new_token: str, old_token: str) -> None:
    """No GitHub Actions, grava o novo refresh token num arquivo para o workflow salvar no secret."""
    path = os.environ.get("UPWORK_NEW_REFRESH_TOKEN_FILE")
    if path and new_token != old_token:
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::add-mask::{new_token}")
        with open(path, "w") as f:
            f.write(new_token)


def _num(obj: Any) -> Optional[float]:
    if not isinstance(obj, dict) or obj.get("rawValue") in (None, ""):
        return None
    try:
        return float(obj["rawValue"])
    except (TypeError, ValueError):
        return None


def parse_job(node: Dict[str, Any]) -> Job:
    client = node.get("client") or {}
    hourly_min = _num(node.get("hourlyBudgetMin"))
    hourly_max = _num(node.get("hourlyBudgetMax"))
    fixed = _num(node.get("amount"))
    if hourly_min or hourly_max:
        job_type = "HOURLY"
    elif fixed:
        job_type = "FIXED"
    else:
        job_type = None
    occupations = node.get("occupations") or {}
    category = ((occupations.get("category") or {}).get("prefLabel")) if isinstance(occupations, dict) else None
    cipher = node.get("ciphertext") or node.get("id")
    return Job(
        id=str(node.get("id") or cipher),
        title=(node.get("title") or "").strip(),
        url=f"https://www.upwork.com/jobs/{cipher}",
        description=(node.get("description") or "").strip(),
        job_type=job_type,
        fixed_budget=fixed if job_type == "FIXED" else None,
        hourly_min=hourly_min,
        hourly_max=hourly_max,
        currency=((node.get("amount") or {}).get("currency") or "USD"),
        experience_level=node.get("experienceLevel"),
        skills=[s.get("prettyName") or s.get("name") for s in (node.get("skills") or []) if s],
        category=category,
        client_country=((client.get("location") or {}).get("country")),
        client_payment_verified=(client.get("verificationStatus") == "VERIFIED"),
        client_total_spent=_num(client.get("totalSpent")),
        client_total_hires=client.get("totalHires"),
        published_at=node.get("publishedDateTime") or node.get("createdDateTime"),
    )


def build_search_expression(keywords: List[str]) -> str:
    parts = [f'"{k}"' if " " in k else k for k in keywords]
    return " OR ".join(parts)


def search_jobs(
    access_token: str, keywords: List[str], limit: int = 50, http: Optional[httpx.Client] = None
) -> List[Job]:
    http = http or httpx.Client(timeout=30)
    variables = {
        "filter": {
            "searchExpression_eq": build_search_expression(keywords),
            "pagination_eq": {"first": limit, "after": "0"},
        },
        "sort": [{"field": "RECENCY"}],
    }
    resp = http.post(
        GRAPHQL_URL,
        json={"query": SEARCH_QUERY, "variables": variables},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if resp.status_code == 401:
        raise UpworkAuthError("Access token rejeitado pela API do Upwork (401)")
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("errors"):
        raise RuntimeError(f"Erro GraphQL do Upwork: {payload['errors']}")
    edges = ((payload.get("data") or {}).get("marketplaceJobPostingsSearch") or {}).get("edges") or []
    return [parse_job(e["node"]) for e in edges if e.get("node")]
