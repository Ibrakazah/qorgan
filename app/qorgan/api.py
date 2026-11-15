"""REST API of the Qorgan demo: client app, trusted contact, antifraud analyst, demo controls."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.llm import get_llm
from app.qorgan import service
from app.qorgan.bank_sim import CLIENTS, RECIPIENTS, SCENARIOS
from app.qorgan.risk import TransferRequest

router = APIRouter(prefix="/api", tags=["Qorgan"])


class AnswerBody(BaseModel):
    answer: str = Field(min_length=1, max_length=1500)
    someone_instructing: bool = Field(
        default=False, description="Ответ «да» на вопрос «Вам сейчас кто-то говорит, что нажимать?»"
    )

    @field_validator("answer")
    @classmethod
    def meaningful(cls, value: str) -> str:
        value = value.strip()
        if sum(ch.isalpha() for ch in value) < 2:
            raise ValueError("Напишите своими словами, зачем вы переводите деньги")
        return value


class DecisionBody(BaseModel):
    decision: service.AnalystDecision
    note: str = Field(default="", max_length=500)


class AlertResponseBody(BaseModel):
    response: service.TrustedResponse


def _guard(fn: Any, *args: Any) -> Any:
    try:
        return fn(*args)
    except service.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Не найдено: {exc.args[0]}") from None
    except service.FlowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.get("/demo/state")
async def demo_state() -> dict[str, Any]:
    return {
        "clients": [c.model_dump() for c in CLIENTS.values()],
        "recipients": [r.model_dump() for r in RECIPIENTS.values()],
        "scenarios": [s.model_dump() for s in SCENARIOS],
        "ai_mode": "mock" if get_llm().mock else "llm",
        "simulated": [
            "Данные клиентов и получателей — синтетика (BankSim)",
            "Сигналы телефона (звонок, удалённый доступ) задаются в демо-панели",
            "Уведомление доверенному лицу и передача в АФЦ — симуляция",
        ],
    }


@router.post("/demo/reset")
async def demo_reset() -> service.Metrics:
    return service.reset_demo()


@router.post("/transfers")
async def create_transfer(
    req: TransferRequest, idempotency_key: str | None = Header(default=None, max_length=100)
) -> dict[str, Any]:
    """Оценка перевода до исполнения. `Idempotency-Key`: повтор запроса вернёт тот же перевод."""
    result: dict[str, Any] = _guard(service.create_transfer, req, idempotency_key)
    return result


@router.get("/balances")
async def get_balances() -> dict[str, int]:
    return service.balances()


@router.get("/stoplist")
async def get_stoplist() -> list[str]:
    return service.stoplist()


@router.get("/transfers/{transfer_id}")
async def get_transfer(transfer_id: str) -> dict[str, Any]:
    result: dict[str, Any] = _guard(service.get_transfer, transfer_id)
    return result


@router.post("/transfers/{transfer_id}/confirm")
async def confirm(transfer_id: str) -> dict[str, Any]:
    result: dict[str, Any] = _guard(service.confirm, transfer_id)
    return result


@router.post("/transfers/{transfer_id}/cancel")
async def cancel(transfer_id: str) -> dict[str, Any]:
    result: dict[str, Any] = _guard(service.cancel, transfer_id)
    return result


@router.post("/transfers/{transfer_id}/answer")
async def answer(transfer_id: str, body: AnswerBody) -> dict[str, Any]:
    try:
        return await service.answer_safety_check(transfer_id, body.answer, body.someone_instructing)
    except service.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Не найдено: {exc.args[0]}") from None
    except service.FlowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.get("/cases")
async def cases() -> list[dict[str, Any]]:
    return service.list_cases()


@router.post("/cases/{transfer_id}/decision")
async def decide(transfer_id: str, body: DecisionBody) -> dict[str, Any]:
    result: dict[str, Any] = _guard(service.analyst_decide, transfer_id, body.decision, body.note)
    return result


@router.get("/alerts")
async def alerts(client_id: str | None = None) -> list[dict[str, Any]]:
    return service.list_alerts(client_id)


@router.post("/alerts/{alert_id}/respond")
async def respond(alert_id: str, body: AlertResponseBody) -> dict[str, Any]:
    result: dict[str, Any] = _guard(service.respond_alert, alert_id, body.response)
    return result


@router.get("/metrics")
async def get_metrics() -> service.Metrics:
    return service.metrics()
