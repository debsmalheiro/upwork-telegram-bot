import json

import httpx
import pytest

from bot import main as bot_main
from bot import upwork
from bot.filters import Profile, matches
from bot.state import SeenState
from bot.telegram import TelegramClient, format_job


def node(i, **over):
    n = {
        "id": str(i),
        "ciphertext": f"~01abc{i}",
        "title": f"Python dev <{i}>",
        "description": "Need pandas & data analysis",
        "publishedDateTime": f"2026-11-01T10:0{i}:00Z",
        "experienceLevel": "INTERMEDIATE",
        "amount": {"rawValue": "500", "currency": "USD"},
        "hourlyBudgetMin": None,
        "hourlyBudgetMax": None,
        "skills": [{"name": "python", "prettyName": "Python"}],
        "occupations": {"category": {"prefLabel": "Data Science & Analytics"}},
        "client": {
            "totalHires": 3,
            "verificationStatus": "VERIFIED",
            "location": {"country": "United States"},
            "totalSpent": {"rawValue": "2500"},
        },
    }
    n.update(over)
    return n


PROFILE = Profile.from_dict(
    {
        "name": "Python Dados",
        "keywords": ["python"],
        "exclude_keywords": ["wordpress"],
        "min_fixed_budget": 300,
        "min_hourly_rate": 25,
        "client": {"payment_verified": True, "min_total_spent": 1000},
    }
)


def test_parse_fixed_job():
    job = upwork.parse_job(node(1))
    assert job.job_type == "FIXED"
    assert job.fixed_budget == 500
    assert job.url == "https://www.upwork.com/jobs/~01abc1"
    assert job.client_payment_verified and job.client_total_spent == 2500
    assert job.category == "Data Science & Analytics"


def test_parse_hourly_job():
    job = upwork.parse_job(node(2, amount=None, hourlyBudgetMin={"rawValue": "30"}, hourlyBudgetMax={"rawValue": "50"}))
    assert job.job_type == "HOURLY" and job.hourly_max == 50


@pytest.mark.parametrize(
    "over,expected",
    [
        ({}, True),
        ({"description": "WordPress site"}, False),
        ({"amount": {"rawValue": "100"}}, False),
        ({"amount": None, "hourlyBudgetMin": {"rawValue": "10"}, "hourlyBudgetMax": {"rawValue": "15"}}, False),
        ({"amount": None, "hourlyBudgetMin": {"rawValue": "20"}, "hourlyBudgetMax": {"rawValue": "40"}}, True),
        ({"client": {"verificationStatus": "UNVERIFIED", "totalSpent": {"rawValue": "5000"}}}, False),
        ({"client": {"verificationStatus": "VERIFIED", "totalSpent": {"rawValue": "50"}}}, False),
    ],
)
def test_filters(over, expected):
    assert matches(upwork.parse_job(node(1, **over)), PROFILE) is expected


def test_category_and_type_filters():
    p = Profile.from_dict({"name": "x", "keywords": ["a"], "categories": ["Web Development"], "job_type": "hourly"})
    assert not matches(upwork.parse_job(node(1)), p)
    p2 = Profile.from_dict({"name": "x", "keywords": ["a"], "job_type": "hourly"})
    assert not matches(upwork.parse_job(node(1)), p2)


def test_profile_tag():
    assert PROFILE.tag == "#PythonDados"


def test_format_escapes_html():
    msg = format_job(upwork.parse_job(node(1)), ["#PythonDados"])
    assert "&lt;1&gt;" in msg and "$500" in msg and "#PythonDados" in msg


def test_state_roundtrip_and_cap(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.state.MAX_IDS", 3)
    s = SeenState(tmp_path / "seen.json")
    s.add_many(["a", "b", "c", "d"])
    s.initialized = True
    s.save()
    s2 = SeenState(tmp_path / "seen.json")
    assert s2.initialized and "d" in s2 and "a" not in s2


@pytest.fixture
def fake_apis(monkeypatch):
    """Simula Upwork + Telegram via httpx.MockTransport."""
    sent = []
    jobs = {"nodes": [node(1), node(2)]}

    def handler(request: httpx.Request):
        if request.url.path.endswith("/oauth2/token"):
            return httpx.Response(200, json={"access_token": "AT", "refresh_token": "RT2"})
        if request.url.host == "api.upwork.com":
            return httpx.Response(
                200, json={"data": {"marketplaceJobPostingsSearch": {"edges": [{"node": n} for n in jobs["nodes"]]}}}
            )
        if request.url.host == "api.telegram.org":
            sent.append(json.loads(request.content)["text"])
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda *a, **k: real_client(transport=transport))
    monkeypatch.setattr(bot_main.time, "sleep", lambda s: None)
    for k in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "UPWORK_CLIENT_ID", "UPWORK_CLIENT_SECRET", "UPWORK_REFRESH_TOKEN"]:
        monkeypatch.setenv(k, "x")
    return sent, jobs


def test_end_to_end_first_run_then_only_new(tmp_path, fake_apis, monkeypatch):
    sent, jobs = fake_apis
    cfg = tmp_path / "config.yaml"
    cfg.write_text("profiles:\n  - name: Python Dados\n    keywords: [python]\n")
    state = tmp_path / "seen.json"
    token_file = tmp_path / "rt"
    monkeypatch.setenv("UPWORK_NEW_REFRESH_TOKEN_FILE", str(token_file))

    # 1ª execução: não envia vagas, só a mensagem de boas-vindas
    bot_main.run(False, cfg, state)
    assert len(sent) == 1 and "Bot ativo" in sent[0]
    assert token_file.read_text() == "RT2"

    # 2ª execução com uma vaga nova: envia só ela
    jobs["nodes"].append(node(3))
    bot_main.run(False, cfg, state)
    assert len(sent) == 2 and "~01abc3" in sent[1]

    # 3ª execução sem novidades: nada enviado
    bot_main.run(False, cfg, state)
    assert len(sent) == 2


def test_error_alert_sent(tmp_path, fake_apis, monkeypatch):
    sent, _ = fake_apis

    def boom(*a, **k):
        raise upwork.UpworkAuthError("token expirado")

    monkeypatch.setattr(upwork, "refresh_access_token", boom)
    cfg = tmp_path / "config.yaml"
    cfg.write_text("profiles:\n  - name: X\n    keywords: [python]\n")
    with pytest.raises(upwork.UpworkAuthError):
        bot_main.run(False, cfg, tmp_path / "seen.json")
    assert "Erro no bot" in sent[0] and "token expirado" in sent[0]
