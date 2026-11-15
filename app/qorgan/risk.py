"""Explainable transfer risk scoring.

A pure function: the same inputs always give the same score and the same list of reasons. Weights are
hand-set expert priors for the MVP (documented in docs/RISK_MODEL.md); in a pilot they are calibrated
on the bank's labelled history. Every point of the score is traceable to a named reason, which is what
an antifraud analyst and a regulator need.
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, Field

from app.qorgan.bank_sim import ClientProfile, RecipientProfile, SessionSignals

Level = Literal["allow", "warn", "safety_check"]
Group = Literal["session", "amount", "recipient", "history"]

WARN_FROM: Final = 30
CHECK_FROM: Final = 55
HOLD_FROM: Final = 80  # used by the policy: at this score a human must look even without a scam verdict


class Reason(BaseModel):
    code: str
    group: Group
    points: int
    text: str = Field(description="Объяснение по-русски для клиента и аналитика.")


class RiskAssessment(BaseModel):
    score: int = Field(ge=0, le=100)
    level: Level
    reasons: list[Reason]


class TransferRequest(BaseModel):
    client_id: str
    recipient_id: str
    amount: int = Field(gt=0, le=50_000_000, description="Сумма перевода, ₸.")
    purpose: str = Field(default="", max_length=200)
    session: SessionSignals = Field(default_factory=SessionSignals)


def _fmt(amount: float) -> str:
    return f"{round(amount):,}".replace(",", " ") + " ₸"


def assess(req: TransferRequest, client: ClientProfile, recipient: RecipientProfile) -> RiskAssessment:
    reasons: list[Reason] = []

    def add(code: str, group: Group, points: int, text: str) -> None:
        reasons.append(Reason(code=code, group=group, points=points, text=text))

    s = req.session
    # --- Session: the strongest social-engineering markers ------------------------------------
    if s.remote_access_app:
        add("remote_access", "session", 35, "На телефоне активно приложение удалённого доступа")
    if s.telecom_fraud_flag:
        add("telecom_flag", "session", 35, "Оператор связи: клиенту звонил номер с признаками мошенничества")
    if s.on_call:
        if s.caller_unknown:
            add("call_unknown", "session", 30, "Перевод во время звонка с номера не из контактов")
        else:
            add("call_known", "session", 10, "Перевод во время телефонного звонка")
        if s.call_minutes >= 10:
            add("long_call", "session", 5, f"Звонок длится {s.call_minutes} мин")
    if s.new_device_24h:
        add("new_device", "session", 10, "Вход с нового устройства за последние 24 ч")
    if s.local_hour < 6:
        add("night", "session", 5, "Нетипичное время — ночь")

    # --- Amount vs the client's own behaviour -------------------------------------------------
    if req.amount > max(client.max_transfer_90d, 3 * client.avg_transfer_90d):
        ratio = req.amount / max(client.avg_transfer_90d, 1)
        add(
            "amount_spike",
            "amount",
            15,
            f"Сумма в {ratio:.0f} раз больше обычного перевода ({_fmt(client.avg_transfer_90d)})",
        )
    share = req.amount / max(client.balance, 1)
    if share >= 0.6:
        add("drains_balance", "amount", 10, f"Переводится {share:.0%} всех средств на счёте")

    # --- Recipient: money-mule markers ----------------------------------------------------------
    prior = recipient.prior_transfers_from_client.get(req.client_id, 0)
    if recipient.in_antifraud_db:
        add("recipient_blacklisted", "recipient", 40, "Счёт получателя в базе мошеннических счетов")
    if prior == 0:
        add("new_recipient", "recipient", 10, "Первый перевод этому получателю")
    if recipient.account_age_days < 30:
        add("young_account", "recipient", 10, f"Счёт получателя открыт {recipient.account_age_days} дн. назад")
    if recipient.unique_senders_24h >= 10:
        add(
            "fan_in",
            "recipient",
            15,
            f"На счёт получателя за сутки перевели {recipient.unique_senders_24h} разных людей",
        )
    if recipient.cash_out_ratio_24h >= 0.8 and recipient.unique_senders_24h >= 3:
        add(
            "fast_cash_out",
            "recipient",
            10,
            f"Получатель сразу выводит деньги ({recipient.cash_out_ratio_24h:.0%} за сутки)",
        )

    # --- History: trust earned by repeated normal transfers --------------------------------------
    if prior >= 3 and not s.remote_access_app and not (s.on_call and s.caller_unknown):
        add("trusted_recipient", "history", -20, f"Клиент уже {prior} раз переводил этому получателю")

    score = max(0, min(100, sum(r.points for r in reasons)))
    level: Level = "allow" if score < WARN_FROM else "warn" if score < CHECK_FROM else "safety_check"
    reasons.sort(key=lambda r: -r.points)
    return RiskAssessment(score=score, level=level, reasons=reasons)
