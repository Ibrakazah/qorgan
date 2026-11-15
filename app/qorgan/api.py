"""REST API of the Qorgan demo: client app, trusted contact, antifraud analyst, demo controls."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.llm import get_llm
from app.qorgan import service
from app.qorgan.bank_sim import CLIENTS, RECIPIENTS, SCENARIOS
from app.qorgan.risk import TransferRequest

router = APIRouter(prefix="/api", tags=["Qorgan"])


class AnswerBody(BaseModel):
    answer: str = Field(min_length=1, max_length=1500)


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
async def create_transfer(req: TransferRequest) -> dict[str, Any]:
    result: dict[str, Any] = _guard(service.create_transfer, req)
    return result


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
        return await service.answer_safety_check(transfer_id, body.answer)
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
