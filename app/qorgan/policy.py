"""Decision policy: risk score + AI verdict → what happens to the money. Code decides, not the model.

Invariant: the AI verdict can only make a transfer *stricter*. A transfer that the score alone would
hold stays held whatever the model says; only a human (analyst) releases it.
"""

from __future__ import annotations

from typing import Final, Literal

from app.qorgan.risk import HOLD_FROM
from app.tasks.scam_script import ScamScriptOutput

AfterCheck = Literal["hold", "proceed_with_confirmation"]

SCRIPT_CONFIDENCE_TO_HOLD: Final = 0.6
COOLING_OFF_MINUTES: Final = 60


def decide_after_check(score: int, verdict: ScamScriptOutput) -> tuple[AfterCheck, str]:
    """Outcome of the safety check. Returns (decision, human-readable reason)."""
    if verdict.script != "none" and verdict.confidence >= SCRIPT_CONFIDENCE_TO_HOLD:
        return "hold", "В ответе клиента распознан сценарий мошенничества"
    if score >= HOLD_FROM:
        return "hold", f"Балл риска {score} ≥ {HOLD_FROM}: нужна проверка человеком даже без явного сценария"
    return "proceed_with_confirmation", "Сценарий не распознан, риск умеренный: клиент подтверждает перевод сам"
