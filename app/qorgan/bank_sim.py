"""BANK SIMULATOR — synthetic clients, recipients and demo scenarios. NOT real bank data.

Everything here stands in for systems Qorgan would read in production:
- `ClientProfile`   ← core banking / CRM of the bank (spending profile, trusted contact),
- `RecipientProfile` ← core banking for own clients + National Bank Antifraud Center (АФЦ НБРК)
                       exchange for accounts in other banks,
- `SessionSignals`  ← mobile app SDK (call state, remote-access apps, device change).
The pydantic models are the integration contract; only the data source is simulated.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, Field


class TrustedContact(BaseModel):
    name: str
    relation: str
    phone_masked: str


class ClientProfile(BaseModel):
    id: str
    name: str
    age: int
    city: str
    balance: int = Field(description="Остаток на счёте, ₸.")
    avg_transfer_90d: int = Field(description="Средний исходящий перевод за 90 дней, ₸.")
    max_transfer_90d: int = Field(description="Максимальный исходящий перевод за 90 дней, ₸.")
    trusted_contact: TrustedContact | None = None


class RecipientProfile(BaseModel):
    id: str
    display_name: str = Field(description="Маскированное имя получателя, как в приложении.")
    account_masked: str
    bank: str
    account_age_days: int
    unique_senders_24h: int = Field(description="Сколько разных людей перевели на счёт за 24 ч.")
    cash_out_ratio_24h: float = Field(ge=0, le=1, description="Доля входящих, ушедших со счёта за 24 ч.")
    in_antifraud_db: bool = Field(default=False, description="Счёт уже в базе АФЦ / стоп-листе банка.")
    prior_transfers_from_client: dict[str, int] = Field(
        default_factory=dict, description="client_id → сколько раз этот клиент уже переводил сюда."
    )


class SessionSignals(BaseModel):
    on_call: bool = Field(default=False, description="Во время перевода идёт телефонный звонок.")
    caller_unknown: bool = Field(default=False, description="Звонящего нет в контактах.")
    call_minutes: int = Field(default=0, ge=0, le=600)
    remote_access_app: bool = Field(default=False, description="Активно приложение удалённого доступа.")
    new_device_24h: bool = Field(default=False, description="Вход с нового устройства за последние 24 ч.")
    telecom_fraud_flag: bool = Field(
        default=False,
        description="Оператор связи сообщил о звонке с номера с признаками мошенничества "
        "(пилот НБРК «Телеком Антифрод»).",
    )
    local_hour: int = Field(default=14, ge=0, le=23)


class Scenario(BaseModel):
    id: str
    title: str
    story: str
    client_id: str
    recipient_id: str
    amount: int
    purpose: str
    session: SessionSignals
    suggested_answer: str | None = None


CLIENTS: Final[dict[str, ClientProfile]] = {
    c.id: c
    for c in (
        ClientProfile(
            id="saule", name="Сауле Ахметова", age=67, city="Тараз", balance=1_240_000,
            avg_transfer_90d=22_000, max_transfer_90d=60_000,
            trusted_contact=TrustedContact(name="Айгерим", relation="дочь", phone_masked="+7 701 *** ** 14"),
        ),
        ClientProfile(
            id="erlan", name="Ерлан Сапаров", age=34, city="Алматы", balance=640_000,
            avg_transfer_90d=48_000, max_transfer_90d=210_000,
            trusted_contact=None,
        ),
    )
}  # fmt: skip

RECIPIENTS: Final[dict[str, RecipientProfile]] = {
    r.id: r
    for r in (
        RecipientProfile(
            id="mom", display_name="Гульнар А. (мама)", account_masked="KZ** **** 4471", bank="Банк ЦентрКредит",
            account_age_days=3650, unique_senders_24h=1, cash_out_ratio_24h=0.1,
            prior_transfers_from_client={"saule": 0, "erlan": 0},
        ),
        RecipientProfile(
            id="grandson", display_name="Нурлан А. (внук)", account_masked="KZ** **** 9012", bank="Банк ЦентрКредит",
            account_age_days=1460, unique_senders_24h=2, cash_out_ratio_24h=0.2,
            prior_transfers_from_client={"saule": 14},
        ),
        RecipientProfile(
            id="landlord", display_name="Марат Т. (арендодатель)", account_masked="KZ** **** 3380",
            bank="Другой банк", account_age_days=2100, unique_senders_24h=1, cash_out_ratio_24h=0.0,
            prior_transfers_from_client={"erlan": 9},
        ),
        RecipientProfile(
            id="mule", display_name="Арман К.", account_masked="KZ** **** 0587", bank="Другой банк",
            account_age_days=5, unique_senders_24h=43, cash_out_ratio_24h=0.97,
        ),
        RecipientProfile(
            id="olx_seller", display_name="Данияр С.", account_masked="KZ** **** 7765", bank="Другой банк",
            account_age_days=19, unique_senders_24h=11, cash_out_ratio_24h=0.85,
        ),
        RecipientProfile(
            id="friend", display_name="Тимур Б.", account_masked="KZ** **** 2210", bank="Банк ЦентрКредит",
            account_age_days=900, unique_senders_24h=1, cash_out_ratio_24h=0.05,
        ),
    )
}  # fmt: skip

SCENARIOS: Final[tuple[Scenario, ...]] = (
    Scenario(
        id="normal",
        title="1. Обычный перевод внуку",
        story="Сауле, как обычно, отправляет внуку 15 000 ₸. Получатель знакомый, звонка нет.",
        client_id="saule", recipient_id="grandson", amount=15_000, purpose="Внуку на обед",
        session=SessionSignals(),
    ),
    Scenario(
        id="fake_security",
        title="2. «Служба безопасности» на второй телефон",
        story=(
            "Мошенники знают, что приложение блокирует перевод во время звонка, поэтому держат Сауле "
            "на видеосвязи в WhatsApp на втором телефоне. «Сотрудник службы безопасности» убеждает "
            "перевести 850 000 ₸ на «безопасный счёт». Сигнала звонка в банковском приложении нет."
        ),
        client_id="saule", recipient_id="mule", amount=850_000, purpose="Перевод собственных средств",
        session=SessionSignals(),
        suggested_answer=(
            "Позвонил сотрудник службы безопасности банка по видеосвязи, сказал что мой счёт пытаются взломать "
            "и на меня оформляют кредит. Надо срочно перевести деньги на безопасный счёт и никому не говорить."
        ),
    ),
    Scenario(
        id="call_active",
        title="3. Звонок + сигнал оператора",
        story=(
            "Тот же обман, но звонок идёт на этот же телефон, а оператор связи передал сигнал «Телеком Антифрод». "
            "Балл максимальный: перевод уходит на проверку даже без распознанного сценария."
        ),
        client_id="saule", recipient_id="mule", amount=850_000, purpose="Перевод собственных средств",
        session=SessionSignals(on_call=True, caller_unknown=True, call_minutes=25, telecom_fraud_flag=True),
        suggested_answer="Мне сказали перевести, я не знаю зачем, трубку не кладу",
    ),
    Scenario(
        id="olx",
        title="4. Предоплата продавцу с OLX",
        story="Ерлан покупает телефон на OLX. Продавец просит предоплату 250 000 ₸ на карту.",
        client_id="erlan", recipient_id="olx_seller", amount=250_000, purpose="Оплата за телефон",
        session=SessionSignals(),
        suggested_answer="Покупаю айфон на OLX, продавец просит предоплату, доставка завтра курьером",
    ),
    Scenario(
        id="rent",
        title="5. Аренда — крупно, но привычно",
        story="Ерлан, как каждый месяц, платит арендодателю 200 000 ₸.",
        client_id="erlan", recipient_id="landlord", amount=200_000, purpose="Аренда за декабрь",
        session=SessionSignals(),
    ),
)  # fmt: skip


def get_client(client_id: str) -> ClientProfile:
    return CLIENTS[client_id]


def get_recipient(recipient_id: str) -> RecipientProfile:
    return RECIPIENTS[recipient_id]
