"""Build the editable 5-minute pitch deck: docs/submission/Qorgan_pitch.pptx.

    make deck        (needs python-pptx from requirements-dev.txt; screenshots from `make record`)

Every element is a native PowerPoint shape, table or text box, so the team can edit it in
PowerPoint / Keynote / Google Slides. Slide order matches docs/submission/SPEECH.md.
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.slide import Slide
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "docs" / "media"
OUT = ROOT / "docs" / "submission" / "Qorgan_pitch.pptx"

BRAND = RGBColor(0x00, 0x87, 0x5A)
BRAND_SOFT = RGBColor(0xE3, 0xF4, 0xEC)
INK = RGBColor(0x14, 0x20, 0x1B)
MUTED = RGBColor(0x5D, 0x6B, 0x65)
LINE = RGBColor(0xDF, 0xE5, 0xE2)
DANGER = RGBColor(0xC6, 0x2F, 0x2F)
DANGER_SOFT = RGBColor(0xFD, 0xE9, 0xE8)
WARN = RGBColor(0xB2, 0x6A, 0x00)
WARN_SOFT = RGBColor(0xFF, 0xF3, 0xDD)
INFO_SOFT = RGBColor(0xE7, 0xEE, 0xFB)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Arial"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
W, H = prs.slide_width, prs.slide_height


def text(
    slide: Slide, x: float, y: float, w: float, h: float, body: str | list[str], *, size: int = 18,
    color: RGBColor = INK, bold: bool = False, align: PP_ALIGN = PP_ALIGN.LEFT, anchor: MSO_ANCHOR = MSO_ANCHOR.TOP,
    line: float = 1.15,
) -> None:  # fmt: skip
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    lines = [body] if isinstance(body, str) else body
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line
        run = p.add_run()
        run.text = ln
        run.font.name, run.font.size, run.font.bold, run.font.color.rgb = FONT, Pt(size), bold, color


def rect(
    slide: Slide, x: float, y: float, w: float, h: float, fill: RGBColor, *, line: RGBColor | None = None,
    rounded: bool = True,
) -> None:  # fmt: skip
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
    if rounded:
        shape.adjustments[0] = 0.08
    shape.shadow.inherit = False


def card(
    slide: Slide, x: float, y: float, w: float, h: float, title: str, body: str | list[str], *,
    fill: RGBColor = BRAND_SOFT, title_color: RGBColor = INK, size: int = 15,
) -> None:  # fmt: skip
    rect(slide, x, y, w, h, fill)
    text(slide, x + 0.25, y + 0.22, w - 0.5, 0.5, title, size=19, bold=True, color=title_color)
    text(slide, x + 0.25, y + 0.82, w - 0.5, h - 1.0, body, size=size, color=INK)


def header(slide: Slide, n: int, title: str, kicker: str = "") -> None:
    rect(slide, 0, 0, 13.333, 0.12, BRAND, rounded=False)
    if kicker:
        text(slide, 0.6, 0.42, 10, 0.35, kicker.upper(), size=12, bold=True, color=BRAND)
    text(slide, 0.6, 0.72, 12.1, 0.9, title, size=30, bold=True)
    text(slide, 12.2, 7.0, 0.6, 0.3, str(n), size=11, color=MUTED, align=PP_ALIGN.RIGHT)
    text(slide, 0.6, 7.0, 9, 0.3, "Qorgan · ITU HACKATHON-2026 · FINTECH CASE Банка ЦентрКредит", size=11, color=MUTED)


def picture(
    slide: Slide, name: str, x: float, y: float, w: float, crop: tuple[float, float, float, float] = (0, 0, 0, 0)
) -> None:
    path = MEDIA / f"shot_{name}.png"
    if not path.exists():
        rect(slide, x, y, w, w * 0.62, INFO_SOFT)
        text(slide, x, y + w * 0.28, w, 0.4, f"[скриншот {name}: запустите make record]", size=13, color=MUTED,
             align=PP_ALIGN.CENTER)  # fmt: skip
        return
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), width=Inches(w))
    left, top, right, bottom = crop
    pic.crop_left, pic.crop_top, pic.crop_right, pic.crop_bottom = left, top, right, bottom
    pic.width = Inches(w)
    ratio = (1 - top - bottom) / (1 - left - right) * (1000 / 1600)
    pic.height = Emu(int(Inches(w) * ratio))
    pic.line.color.rgb = LINE


def notes(slide: Slide, body: str) -> None:
    slide.notes_slide.notes_text_frame.text = body


# 1 — Title ------------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, 13.333, 7.5, BRAND, rounded=False)
shield = s.shapes.add_shape(MSO_SHAPE.PENTAGON, Inches(0.9), Inches(1.3), Inches(1.3), Inches(1.5))
shield.rotation = 90
shield.fill.solid()
shield.fill.fore_color.rgb = WHITE
shield.line.fill.background()
text(s, 0.9, 3.0, 11, 1.2, "Qorgan", size=66, bold=True, color=WHITE)
text(s, 0.9, 4.2, 11.5, 1.0, "Щит от переводов под диктовку мошенников", size=30, color=WHITE)
text(s, 0.9, 5.2, 11.5, 0.6, "«Қорған» — защита. Обычные переводы — без лишних вопросов.", size=18, color=BRAND_SOFT)
text(s, 0.9, 6.4, 11.5, 0.5, "ITU HACKATHON-2026 · FINTECH CASE Банка ЦентрКредит · Команда [название]", size=14,
     color=BRAND_SOFT)  # fmt: skip
notes(s, "0:00–0:19. Представить команду и проект в одной фразе.")

# 2 — Problem ----------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, 2, "Человек сам переводит деньги мошеннику — и антифрод этого не видит", "Проблема")
stats = [
    ("28,9 тыс.", "дел об интернет-мошенничестве в РК за 2025 год — рекорд, 23% всей преступности", "Kapital.kz, 21.08.2026"),
    ("№1", "схема — звонки и SMS «от имени банка»", "finprom.kz, янв.–июль 2026"),
    ("98%", "жертв сами передали деньги и данные; 45 млрд ₸ ушло мошенникам в 2024", "МВД РК, Finratings.kz, 06.02.2025"),
]  # fmt: skip
for i, (big, label, src) in enumerate(stats):
    x = 0.6 + i * 4.1
    rect(s, x, 2.0, 3.8, 3.9, BRAND_SOFT)
    text(s, x + 0.3, 2.3, 3.3, 1.2, big, size=54, bold=True, color=BRAND)
    text(s, x + 0.3, 3.6, 3.3, 1.6, label, size=18)
    text(s, x + 0.3, 5.35, 3.3, 0.4, src, size=11, color=MUTED)
text(s, 0.6, 6.2, 12, 0.6, "Вход настоящий, пароль не украден, подтверждает сам клиент → для классического антифрода это обычная операция.",
     size=16, color=MUTED)  # fmt: skip
notes(s, "0:19–0:55. Цифры — из docs/research/RESEARCH.md.")

# 3 — Why existing is not enough --------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, 3, "Существующие меры мошенники уже обходят", "Почему этого мало")
gaps = [
    (
        "Блок при звонке",
        "Требование регулятора (по данным СМИ). Обход: жертву держат на видеосвязи со второго телефона — приложение звонка не видит (АРРФР, авг. 2026).",
    ),
    ("Чёрный список АФЦ", "Дроп попадает в базу после жалоб — когда деньги уже ушли. Новые «серые» счета не видны."),
    (
        "Правило «блок / пропуск»",
        "Либо пропускает обман, либо тормозит честных клиентов. Нет объяснения ни клиенту, ни аналитику.",
    ),
]
for i, (t, b) in enumerate(gaps):
    card(s, 0.6 + i * 4.1, 1.9, 3.8, 4.4, t, b, fill=DANGER_SOFT, title_color=DANGER, size=17)
notes(s, "0:55–1:27.")

# 4 — Users ------------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, 4, "Три человека в одной истории", "Для кого")
users = [
    (
        "Сауле, 67 — клиент",
        ["Переводит под давлением «службы безопасности».", "Нужно: остановиться вовремя и понять, что это обман."],
    ),
    (
        "Айгерим — доверенное лицо",
        ["Дочь, назначена Сауле заранее, с согласия.", "Нужно: узнать сразу, без доступа к счёту."],
    ),
    (
        "Аналитик антифрода BCC",
        ["Разбирает подозрительные переводы.", "Нужно: за минуту понять, почему перевод опасен, и решить."],
    ),
]
for i, (t, b) in enumerate(users):
    card(s, 0.6 + i * 4.1, 1.9, 3.8, 4.0, t, b, size=17)
notes(s, "1:27–1:47.")

# 5 — Solution ---------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, 5, "Объяснимый балл риска выбирает уровень вмешательства", "Решение")
levels = [
    ("0–29", "Пропустить", "перевод сразу", BRAND_SOFT, BRAND),
    ("30–54", "Предупредить", "причины + подтверждение", WARN_SOFT, WARN),
    ("55–100", "Спросить", "«зачем переводите?» → ИИ", DANGER_SOFT, DANGER),
    ("сценарий / ≥80", "Задержать", "доверенное лицо + аналитик", DANGER, WHITE),
]
for i, (rng, name, what, fill, col) in enumerate(levels):
    y = 1.85 + i * 1.18
    rect(s, 0.6, y, 5.2, 1.0, fill)
    text(s, 0.85, y + 0.12, 1.6, 0.8, rng, size=15, bold=True, color=col, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 2.45, y + 0.1, 3.3, 0.45, name, size=20, bold=True, color=col)
    text(s, 2.45, y + 0.55, 3.3, 0.4, what, size=14, color=col if fill == DANGER else INK)
text(s, 0.6, 6.6, 5.4, 0.4, "Сигналы: звонок, удалённый доступ, сумма vs привычки, новый получатель, признаки дропа, «Телеком Антифрод»",
     size=11, color=MUTED)  # fmt: skip
picture(s, "analyst", 6.2, 1.85, 6.6, crop=(0.46, 0.07, 0.0, 0.33))
notes(s, "1:47–2:25. Справа — кейс аналитика: каждая причина балла с весом.")

# 6 — AI ----------------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, 6, "ИИ понимает ответ клиента — даже когда сигнала звонка нет", "ИИ там, где правила бессильны")
steps = [
    "Клиент своими словами (RU / KZ) отвечает: зачем перевод и кто попросил",
    "LLM → JSON по схеме: сценарий обмана, уверенность, признаки давления",
    "7 сценариев: служба безопасности, полиция, родственник в беде, инвестиции, предоплата, выигрыш/работа, давление",
    "Решает код политики: ИИ может только ужесточить. Выпустить перевод — только человек",
]
for i, st in enumerate(steps):
    y = 1.9 + i * 1.08
    rect(s, 0.6, y, 0.6, 0.6, BRAND)
    text(
        s,
        0.6,
        y,
        0.6,
        0.6,
        str(i + 1),
        size=20,
        bold=True,
        color=WHITE,
        align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    text(s, 1.4, y + 0.02, 5.2, 1.0, st, size=16)
rect(s, 0.6, 6.25, 6.1, 0.6, INFO_SOFT)
text(s, 0.8, 6.3, 5.8, 0.5, "Офлайн-эвристика на 63 синтетических ответах: accuracy 0,84 · macro-F1 0,85", size=13,
     anchor=MSO_ANCHOR.MIDDLE)  # fmt: skip
picture(s, "held", 7.0, 1.85, 5.8, crop=(0.0, 0.32, 0.53, 0.0))
notes(s, "2:25–2:55. Метрики — evals/reports; LLM-режим измеряется командой make eval с ключом.")

# 7 — Differentiation ---------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, 7, "Мы не первые в отдельных элементах — мы собираем их в один поток", "Отличие от аналогов")
cols = [
    "",
    "Блок при звонке (АРРФР)",
    "Kaspi «Доверенный контакт»",
    "ИИ-звонок НБРК (инициатива)",
    "BioCatch / Feedzai",
    "Qorgan",
]
rows = [
    ("Ловит обход «второй телефон»", "—", "—", "частично", "частично", "да: получатель + ответ"),
    ("Градуированное трение", "—", "—", "—", "да", "да: 4 уровня"),
    ("Оценка дропа до чёрного списка", "—", "—", "—", "да", "да"),
    ("Понимает ответ клиента", "—", "—", "голос", "—", "текст RU/KZ"),
    ("Объяснение для близких", "—", "нет данных", "—", "—", "да: схема обмана"),
    ("Кейс для аналитика / АФЦ", "—", "—", "—", "да", "да: причины + хронология"),
]
tbl = s.shapes.add_table(len(rows) + 1, len(cols), Inches(0.6), Inches(1.85), Inches(12.1), Inches(4.6)).table
widths = [2.9, 1.7, 1.8, 1.8, 1.6, 2.3]
for j, wdt in enumerate(widths):
    tbl.columns[j].width = Inches(wdt)
for i, row in enumerate([tuple(cols), *rows]):
    for j, val in enumerate(row):
        cell = tbl.cell(i, j)
        cell.text = val
        para = cell.text_frame.paragraphs[0]
        para.font.name, para.font.size = FONT, Pt(13 if i else 12)
        para.font.bold = i == 0 or j in (0, 5)
        para.font.color.rgb = WHITE if i == 0 else (BRAND if j == 5 else INK)
        cell.fill.solid()
        cell.fill.fore_color.rgb = BRAND if i == 0 else (BRAND_SOFT if j == 5 else WHITE)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
text(s, 0.6, 6.55, 12.1, 0.4, "По открытым источникам на 15.11.2026 (docs/research/RESEARCH.md). «—» = в публичных описаниях не найдено.",
     size=11, color=MUTED)  # fmt: skip
notes(
    s,
    "2:55–3:31. Не утверждаем, что аналогов нет. Т-Банк ловит мошенника в разговоре, но только с SIM своего оператора.",
)

# 8 — Tech --------------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, 8, "Работающий MVP, который встраивается в банк через API", "Техническая реализация")
arch = [
    ("Приложение / SDK", "сигналы сессии"),
    ("Qorgan API", "FastAPI · OpenAPI"),
    ("Движок риска", "причины + веса"),
    ("ИИ scam_script", "LLM → JSON · фолбэк"),
    ("Политика", "ИИ только ужесточает"),
    ("Кейсы и метрики", "SQLite → БД банка"),
]
for i, (t, sub) in enumerate(arch):
    x = 0.6 + (i % 3) * 2.45
    y = 1.9 + (i // 3) * 1.55
    rect(s, x, y, 2.25, 1.3, BRAND_SOFT if i != 3 else INFO_SOFT)
    text(s, x + 0.15, y + 0.18, 1.95, 0.5, t, size=16, bold=True)
    text(s, x + 0.15, y + 0.68, 1.95, 0.5, sub, size=12, color=MUTED)
facts = [
    "71 автотест · ruff · mypy --strict",
    "Работает без интернета: офлайн-эвристика, нет CDN",
    "Сквозной сценарий: клиент → доверенное лицо → аналитик",
    "Сброс демо одной кнопкой, видео-резерв 3:00",
]
text(s, 0.6, 5.2, 7.2, 1.6, ["• " + f for f in facts], size=15)
rect(s, 8.2, 1.9, 4.55, 4.75, WARN_SOFT)
text(s, 8.45, 2.1, 4.1, 0.5, "Честно: что симулировано", size=18, bold=True, color=WARN)
text(s, 8.45, 2.7, 4.1, 3.9, [
    "• клиенты, счета, получатели — синтетика",
    "• сигналы телефона — галочки в демо-панели",
    "• уведомление и передача в АФЦ — запись в системе",
    "• веса риска — экспертные, не обучены",
    "• LLM-режим не измерен без ключа",
], size=14)  # fmt: skip
notes(s, "3:31–4:01.")

# 9 — Value -------------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, 9, "Польза для клиентов и банка", "Экономика (оценка, не измерение)")
text(s, 0.6, 1.85, 12, 0.5, "Предотвращено = L × s × c × p", size=22, bold=True, color=BRAND)
text(s, 0.6, 2.45, 12, 0.9, "L = 35 млрд ₸ потерь в РК (МВД: 45 млрд в 2024, минус тренд 2026) · s = 10% доля BCC (допущение) · "
     "c = 50% через переводы в приложении (допущение) · p = доля остановленных (цель пилота)", size=13, color=MUTED)  # fmt: skip
for i, (p, val) in enumerate([("p = 10%", "175 млн ₸"), ("p = 25%", "437 млн ₸"), ("p = 40%", "700 млн ₸")]):
    x = 0.6 + i * 2.75
    rect(s, x, 3.5, 2.5, 1.7, BRAND_SOFT)
    text(s, x + 0.2, 3.65, 2.1, 0.4, p, size=14, color=MUTED)
    text(s, x + 0.2, 4.05, 2.1, 0.7, val, size=28, bold=True, color=BRAND)
    text(s, x + 0.2, 4.75, 2.1, 0.4, "в год · цель", size=12, color=MUTED)
card(s, 8.95, 3.5, 3.8, 1.7, "ИИ ≈ 43 000 ₸/мес", "30 млн переводов × 1% проверок × $0,000275", size=13, fill=INFO_SOFT)
text(s, 0.6, 5.55, 12, 1.2, [
    "Банку: меньше обязательных возмещений по переводам на «чёрных» получателей, меньше ручной работы аналитиков, готовые кейсы для АФЦ.",
    "Клиентам: деньги остаются у них, а обычные переводы не тормозятся.",
], size=15)  # fmt: skip
notes(s, "4:01–4:32. Формулы и допущения — docs/submission/ECONOMICS.md.")

# 10 — Next step --------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, 10, "Следующий шаг: проверить на данных BCC", "От MVP к пилоту")
road = [
    ("0. MVP", "сейчас", "сквозной сценарий, тесты, evals"),
    ("1. Офлайн-прогон", "1–2 мес.", "обезличенная история инцидентов BCC и АФЦ, калибровка весов"),
    ("2. Теневой режим", "1 мес.", "оцениваем живые переводы, не вмешиваемся"),
    ("3. Пилот", "2–3 мес.", "5–10% клиентов, A/B-контроль, friction ≤ 1% (цель)"),
]
for i, (t, when, what) in enumerate(road):
    x = 0.6 + i * 3.1
    rect(s, x, 1.95, 2.85, 2.6, BRAND_SOFT if i else BRAND)
    col = WHITE if i == 0 else INK
    text(s, x + 0.2, 2.15, 2.5, 0.5, t, size=19, bold=True, color=col)
    text(s, x + 0.2, 2.65, 2.5, 0.4, when, size=13, color=WHITE if i == 0 else MUTED)
    text(s, x + 0.2, 3.1, 2.5, 1.4, what, size=14, color=col)
rect(s, 0.6, 4.95, 12.1, 1.5, INFO_SOFT)
text(s, 0.85, 5.1, 11.6, 1.3, [
    "Просим: доступ к обезличенной истории инцидентов и ментора из антифрода BCC для офлайн-прогона.",
    "Встраивание — модулем через REST API в платёжный поток, а не отдельным приложением.",
], size=17)  # fmt: skip
notes(s, "4:32–5:00. Переход к живому демо (DEMO_SCRIPT.md).")

# 11 — Backup: demo screenshots -----------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, 11, "Резерв: демо в трёх кадрах", "Если живое демо недоступно")
for i, (name, crop) in enumerate([
    ("safety_check", (0.0, 0.3, 0.75, 0.0)),
    ("trusted", (0.24, 0.3, 0.52, 0.0)),
    ("rejected", (0.0, 0.3, 0.75, 0.0)),
]):  # fmt: skip
    picture(s, name, 0.6 + i * 4.15, 1.85, 3.8, crop=crop)
notes(s, "Полная запись — docs/media/qorgan_demo.mp4 (3:00).")

OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(OUT)
print(f"deck: {OUT} ({len(prs.slides)} slides)")
