"""Transfer lifecycle: assess → (confirm | safety check → hold/confirm) → analyst decision.

Statuses
  executed               — money sent (directly, after confirmation, or released by the analyst)
  awaiting_confirmation  — warning shown, client must confirm or cancel
  awaiting_answer        — safety check: client must explain the transfer
  held                   — cooling-off: case in the analyst queue, trusted contact notified
  cancelled_by_client    — client stopped the transfer (counts as prevented if risk was flagged)
  rejected               — analyst rejected the transfer and flagged the recipient
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final, Literal

from pydantic import BaseModel, Field

from app.qorgan import store
from app.qorgan.bank_sim import CLIENTS, RECIPIENTS, SessionSignals, get_client, get_recipient
from app.qorgan.policy import COOLING_OFF_MINUTES, decide_after_check
from app.qorgan.risk import TransferRequest, assess
from app.tasks import get_task
from app.tasks.scam_script import CLIENT_ADVICE, SCRIPT_TITLES, ScamScriptInput, ScamScriptOutput

AnalystDecision = Literal["release", "reject", "false_positive"]
TrustedResponse = Literal["scam", "ok"]

OPEN_STATUSES: Final = ("awaiting_confirmation", "awaiting_answer", "held")


class FlowError(Exception):
    """Action not allowed in the transfer's current status (→ HTTP 409)."""


class NotFoundError(KeyError):
    """Unknown transfer / alert / client / recipient (→ HTTP 404)."""


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _event(doc: dict[str, Any], actor: str, text: str) -> None:
    doc.setdefault("timeline", []).append({"at": _iso(_now()), "actor": actor, "text": text})


def _load(transfer_id: str) -> dict[str, Any]:
    doc = store.get("transfers", transfer_id)
    if doc is None:
        raise NotFoundError(transfer_id)
    return doc


def _save(doc: dict[str, Any]) -> dict[str, Any]:
    store.put("transfers", doc["id"], doc["created_at"], doc)
    return doc


# --- create -------------------------------------------------------------------------------------


def create_transfer(req: TransferRequest) -> dict[str, Any]:
    if req.client_id not in CLIENTS:
        raise NotFoundError(req.client_id)
    if req.recipient_id not in RECIPIENTS:
        raise NotFoundError(req.recipient_id)
    client, recipient = get_client(req.client_id), get_recipient(req.recipient_id)
    if req.amount > client.balance:
        raise FlowError(f"Недостаточно средств: на счёте {client.balance} ₸")
    assessment = assess(req, client, recipient)
    status = {"allow": "executed", "warn": "awaiting_confirmation", "safety_check": "awaiting_answer"}[assessment.level]
    doc: dict[str, Any] = {
        "id": "T-" + uuid.uuid4().hex[:8].upper(),
        "created_at": _iso(_now()),
        "client_id": client.id,
        "client_name": client.name,
        "recipient_id": recipient.id,
        "recipient_name": recipient.display_name,
        "recipient_bank": recipient.bank,
        "amount": req.amount,
        "purpose": req.purpose,
        "session": req.session.model_dump(),
        "assessment": assessment.model_dump(),
        "status": status,
        "check": None,
        "alert_id": None,
        "trusted_response": None,
        "analyst": None,
        "synthetic_history": False,
        "timeline": [],
    }
    _event(doc, "система", f"Оценка риска: {assessment.score}/100 → {assessment.level}")
    if status == "executed":
        _event(doc, "система", "Перевод выполнен без дополнительных проверок")
    return _save(doc)


# --- client actions -----------------------------------------------------------------------------


def confirm(transfer_id: str) -> dict[str, Any]:
    doc = _load(transfer_id)
    if doc["status"] != "awaiting_confirmation":
        raise FlowError(f"Подтверждение недоступно в статусе {doc['status']}")
    doc["status"] = "executed"
    _event(doc, "клиент", "Клиент подтвердил перевод после предупреждения")
    return _save(doc)


def cancel(transfer_id: str) -> dict[str, Any]:
    doc = _load(transfer_id)
    if doc["status"] not in OPEN_STATUSES:
        raise FlowError(f"Отмена недоступна в статусе {doc['status']}")
    doc["status"] = "cancelled_by_client"
    _event(doc, "клиент", "Клиент отменил перевод")
    return _save(doc)


async def answer_safety_check(transfer_id: str, answer: str) -> dict[str, Any]:
    doc = _load(transfer_id)
    if doc["status"] != "awaiting_answer":
        raise FlowError(f"Проверка недоступна в статусе {doc['status']}")
    task = get_task("scam_script")
    payload = ScamScriptInput(
        answer=answer, transfer_purpose=doc["purpose"] or None, on_call=bool(doc["session"]["on_call"])
    )
    result = await task.run(payload)
    verdict: ScamScriptOutput = result.output
    decision, why = decide_after_check(doc["assessment"]["score"], verdict)
    doc["check"] = {
        "answer": answer,
        "verdict": verdict.model_dump(),
        "script_title": SCRIPT_TITLES[verdict.script],
        "advice": CLIENT_ADVICE[verdict.script],
        "source": result.meta.source,
        "decision": decision,
        "decision_reason": why,
    }
    _event(
        doc,
        "ИИ",
        f"Сценарий: {SCRIPT_TITLES[verdict.script]} (уверенность {verdict.confidence:.0%}, {result.meta.source})",
    )
    if decision == "hold":
        _hold(doc, why)
    else:
        doc["status"] = "awaiting_confirmation"
        _event(doc, "система", why)
    return _save(doc)


def _hold(doc: dict[str, Any], why: str) -> None:
    doc["status"] = "held"
    doc["hold_until"] = _iso(_now() + timedelta(minutes=COOLING_OFF_MINUTES))
    _event(doc, "система", f"Перевод задержан на {COOLING_OFF_MINUTES} мин: {why}. Кейс передан аналитику")
    client = get_client(doc["client_id"])
    if client.trusted_contact is not None:
        alert_id = "A-" + uuid.uuid4().hex[:8].upper()
        check = doc.get("check") or {}
        alert = {
            "id": alert_id,
            "created_at": _iso(_now()),
            "transfer_id": doc["id"],
            "client_id": client.id,
            "client_name": client.name,
            "contact": client.trusted_contact.model_dump(),
            "amount": doc["amount"],
            "recipient_name": doc["recipient_name"],
            "script_title": check.get("script_title"),
            "on_call": doc["session"]["on_call"],
            "status": "new",
            "responded_at": None,
        }
        store.put("alerts", alert_id, alert["created_at"], alert)
        doc["alert_id"] = alert_id
        tc = client.trusted_contact
        _event(doc, "система", f"Уведомление доверенному лицу: {tc.name} ({tc.relation})")


# --- trusted contact ----------------------------------------------------------------------------


def list_alerts(client_id: str | None = None) -> list[dict[str, Any]]:
    alerts = store.all_docs("alerts")
    return [a for a in alerts if client_id is None or a["client_id"] == client_id]


def respond_alert(alert_id: str, response: TrustedResponse) -> dict[str, Any]:
    alert = store.get("alerts", alert_id)
    if alert is None:
        raise NotFoundError(alert_id)
    if alert["status"] != "new":
        raise FlowError("На это уведомление уже ответили")
    alert["status"] = response
    alert["responded_at"] = _iso(_now())
    store.put("alerts", alert_id, alert["created_at"], alert)
    doc = _load(alert["transfer_id"])
    doc["trusted_response"] = response
    text = "считает, что это мошенники" if response == "scam" else "подтверждает, что перевод ожидаемый"
    _event(doc, "доверенное лицо", f"{alert['contact']['name']} {text}")
    _save(doc)
    return alert


# --- analyst ------------------------------------------------------------------------------------


def list_cases() -> list[dict[str, Any]]:
    """Every transfer that got friction, newest first; held ones first."""
    docs = [d for d in store.all_docs("transfers") if d["assessment"]["level"] != "allow"]  # newest first
    return sorted(docs, key=lambda d: d["status"] != "held")  # stable: held first, order kept


def analyst_decide(transfer_id: str, decision: AnalystDecision, note: str = "") -> dict[str, Any]:
    doc = _load(transfer_id)
    if doc["status"] != "held":
        raise FlowError(f"Решение аналитика недоступно в статусе {doc['status']}")
    doc["analyst"] = {"decision": decision, "note": note, "at": _iso(_now())}
    if decision == "reject":
        doc["status"] = "rejected"
        _event(doc, "аналитик", "Перевод отклонён, счёт получателя передан в стоп-лист и АФЦ (симуляция)")
    else:
        doc["status"] = "executed"
        label = "ложное срабатывание" if decision == "false_positive" else "проверено"
        _event(doc, "аналитик", f"Перевод выпущен ({label})")
    return _save(doc)


def get_transfer(transfer_id: str) -> dict[str, Any]:
    return _load(transfer_id)


# --- metrics ------------------------------------------------------------------------------------


class Metrics(BaseModel):
    transfers_total: int
    synthetic_history: int = Field(description="Сколько из них — синтетическая демо-история.")
    friction_rate: float = Field(description="Доля переводов, где было хоть какое-то вмешательство.")
    by_level: dict[str, int]
    by_status: dict[str, int]
    open_cases: int
    prevented_count: int
    prevented_amount: int = Field(
        description="Сумма отклонённых аналитиком и отменённых клиентом рискованных переводов, ₸."
    )
    false_positives: int
    scripts: dict[str, int]
    ai_sources: dict[str, int]
    trusted_responses: dict[str, int]


def metrics() -> Metrics:
    docs = store.all_docs("transfers")
    by_level: dict[str, int] = {}
    by_status: dict[str, int] = {}
    scripts: dict[str, int] = {}
    sources: dict[str, int] = {}
    trusted: dict[str, int] = {}
    prevented_count = prevented_amount = fp = 0
    for d in docs:
        level, status = d["assessment"]["level"], d["status"]
        by_level[level] = by_level.get(level, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
        if level != "allow" and status in ("rejected", "cancelled_by_client"):
            prevented_count += 1
            prevented_amount += d["amount"]
        if (d.get("analyst") or {}).get("decision") == "false_positive":
            fp += 1
        if d.get("check"):
            s = d["check"]["verdict"]["script"]
            scripts[s] = scripts.get(s, 0) + 1
            src = d["check"]["source"]
            sources[src] = sources.get(src, 0) + 1
        if d.get("trusted_response"):
            trusted[d["trusted_response"]] = trusted.get(d["trusted_response"], 0) + 1
    total = len(docs)
    friction = sum(v for k, v in by_level.items() if k != "allow")
    return Metrics(
        transfers_total=total,
        synthetic_history=sum(1 for d in docs if d.get("synthetic_history")),
        friction_rate=round(friction / total, 3) if total else 0.0,
        by_level=by_level,
        by_status=by_status,
        open_cases=by_status.get("held", 0),
        prevented_count=prevented_count,
        prevented_amount=prevented_amount,
        false_positives=fp,
        scripts=scripts,
        ai_sources=sources,
        trusted_responses=trusted,
    )


# --- demo ---------------------------------------------------------------------------------------

_HISTORY_ROUTES: Final = (
    ("saule", "grandson", 8_000, 25_000),
    ("saule", "mom", 10_000, 40_000),
    ("erlan", "landlord", 200_000, 200_000),
    ("erlan", "friend", 5_000, 60_000),
    ("erlan", "mom", 20_000, 80_000),
)


def reset_demo(history_size: int = 40, seed: int = 7) -> Metrics:
    """Wipe the DB and replay synthetic everyday transfers through the REAL risk engine.

    The history makes the friction-rate metric meaningful: it shows how often honest, everyday
    transfers would be bothered. It is synthetic and flagged as such in every record.
    """
    store.wipe()
    rng = random.Random(seed)
    start = _now() - timedelta(days=7)
    for i in range(history_size):
        client_id, recipient_id, lo, hi = rng.choice(_HISTORY_ROUTES)
        amount = rng.randrange(lo, hi + 1, 1_000)
        session = SessionSignals(
            on_call=rng.random() < 0.08,  # people do talk on the phone while paying family
            caller_unknown=False,
            local_hour=rng.choice([9, 12, 14, 18, 20, 22]),
        )
        req = TransferRequest(client_id=client_id, recipient_id=recipient_id, amount=amount, session=session)
        doc = create_transfer(req)
        doc["created_at"] = _iso(start + timedelta(hours=4 * i))
        doc["synthetic_history"] = True
        if doc["status"] != "executed":  # everyday transfers that got a warning: the client confirmed
            doc["status"] = "executed"
            _event(doc, "клиент", "Клиент подтвердил (синтетическая история)")
        store.put("transfers", doc["id"], doc["created_at"], doc)  # same id: overwrites, no duplicate
    return metrics()
