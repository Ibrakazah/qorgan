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


def decide_after_check(score: int, verdict: ScamScriptOutput, mule_pattern: bool = False) -> tuple[AfterCheck, str]:
    """Outcome of the safety check. Returns (decision, human-readable reason).

    A coached client can lie in the answer («маме на лекарства»), so the answer may only add
    suspicion: a mule recipient or a very high score is held whatever the client says.
    """
    if verdict.script != "none" and verdict.confidence >= SCRIPT_CONFIDENCE_TO_HOLD:
        return "hold", "В ответе клиента распознан сценарий мошенничества"
    if mule_pattern:
        return "hold", "Получатель похож на дроп: перевод проверяет специалист при любом ответе клиента"
    if score >= HOLD_FROM:
        return "hold", f"Балл риска {score} ≥ {HOLD_FROM}: нужна проверка человеком даже без явного сценария"
    return "proceed_with_confirmation", "Сценарий не распознан, риск умеренный: клиент подтверждает перевод сам"
