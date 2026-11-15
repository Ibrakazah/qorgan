"""Record the 3-minute backup demo video and screenshots with Playwright.

    make demo            # in one terminal (server on :8000)
    python3 scripts/record_demo.py [--base http://localhost:8000] [--fast]

Writes docs/media/qorgan_demo.webm (+ .mp4 if ffmpeg is available) and docs/media/shot_*.png.
Follows docs/submission/DEMO_SCRIPT.md; captions are injected into the page so the video
is understandable without narration. --fast shortens pauses (for a quick smoke run).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

MEDIA = Path(__file__).resolve().parents[1] / "docs" / "media"

CAPTION_JS = """
(text) => {
  let el = document.getElementById('__cap');
  if (!el) {
    el = document.createElement('div'); el.id = '__cap';
    el.style.cssText = 'position:fixed;left:50%;bottom:22px;transform:translateX(-50%);z-index:99;' +
      'background:rgba(10,20,16,.88);color:#fff;font:600 20px/1.35 -apple-system,Segoe UI,Roboto,sans-serif;' +
      'padding:12px 20px;border-radius:12px;max-width:1100px;text-align:center;box-shadow:0 6px 24px rgba(0,0,0,.3)';
    document.body.appendChild(el);
  }
  el.textContent = text; el.style.display = text ? 'block' : 'none';
}
"""


class Demo:
    def __init__(self, page: Page, fast: bool) -> None:
        self.page, self.fast = page, fast
        self.t0 = time.monotonic()

    def cap(self, text: str) -> None:
        self.page.evaluate(CAPTION_JS, text)

    def until(self, second: float) -> None:
        """Hold until `second` of the script timeline (keeps the video in sync with DEMO_SCRIPT.md)."""
        if self.fast:
            self.page.wait_for_timeout(600)
            return
        left = second - (time.monotonic() - self.t0)
        if left > 0:
            self.page.wait_for_timeout(int(left * 1000))

    def shot(self, name: str, element: str | None = None) -> None:
        """Clean screenshot (caption hidden) of the page or of one element."""
        self.page.evaluate(
            "() => { const c = document.getElementById('__cap'); if (c) c.style.visibility = 'hidden';"
            " document.querySelector('.top').style.position = 'static'; }"
        )
        target = self.page.locator(element).first if element else self.page
        target.screenshot(path=str(MEDIA / f"shot_{name}.png"))
        self.page.evaluate(
            "() => { const c = document.getElementById('__cap'); if (c) c.style.visibility = '';"
            " document.querySelector('.top').style.position = ''; }"
        )


def run(base: str, fast: bool, stills: bool = False) -> None:
    MEDIA.mkdir(parents=True, exist_ok=True)
    video = (
        {}
        if stills
        else {"record_video_dir": str(MEDIA / "_raw"), "record_video_size": {"width": 1600, "height": 1000}}
    )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 1600, "height": 1000},
            device_scale_factor=2 if stills else 1,
            locale="ru-RU",
            color_scheme="light",
            **video,  # type: ignore[arg-type]
        )
        page = ctx.new_page()
        page.request.post(f"{base}/api/demo/reset")
        page.goto(base)
        page.wait_for_selector("[data-sc]")
        d = Demo(page, fast)

        d.cap("Qorgan: клиент · доверенное лицо · аналитик банка. Данные синтетические.")
        d.until(12)
        d.shot("overview")

        page.click('[data-sc="normal"]')
        d.cap("1. Обычный перевод внуку 15 000 ₸ — знакомый получатель, звонка нет")
        d.until(20)
        page.click("#sendBtn")
        page.wait_for_selector("text=Перевод выполнен")
        d.cap("Проходит сразу. Честного клиента Qorgan не трогает.")
        d.shot("normal")
        d.until(40)

        page.click('[data-sc="fake_security"]')
        d.cap("2. Мошенник держит Сауле на видеосвязи со ВТОРОГО телефона — приложение звонка не видит")
        d.until(50)
        page.click("#sendBtn")
        page.wait_for_selector("text=Остановитесь на минуту")
        d.cap("Но риск 75/100: сумма в 39 раз больше обычной, а получатель похож на дроп — 43 отправителя за сутки")
        d.shot("safety_check")
        d.until(70)

        page.click("#fillBtn")
        d.cap("Клиент своими словами объясняет, зачем переводит")
        d.until(80)
        page.click("#answerBtn")
        page.wait_for_selector("text=Перевод задержан")
        d.cap(
            "ИИ узнал схему «служба безопасности банка». Перевод задержан — и задержался бы, даже если бы она соврала"
        )
        d.shot("held")
        d.shot("client_held", 'section[aria-label="Приложение клиента"] .phone')
        d.shot("trusted_alert", 'section[aria-label="Доверенное лицо"] .phone')
        d.until(95)

        page.click('[data-r="scam"]')
        d.cap("Дочь Айгерим получила уведомление и ответила: «Это мошенники»")
        d.until(115)
        d.shot("trusted")

        page.locator(".analyst").scroll_into_view_if_needed()
        d.cap("Аналитик видит готовый кейс: из чего сложился балл, ответ клиента, вердикт ИИ")
        d.until(135)
        d.shot("analyst")
        d.shot("analyst_case", "#detail")
        d.cap("Получатель — типичный дроп: счёт 5 дней, 43 отправителя за сутки, 97% денег сразу выведено")
        d.until(155)

        page.click('[data-dec="reject"]')
        page.wait_for_selector("text=Деньги остались у вас")
        page.evaluate("window.scrollTo(0, 0)")
        d.cap("Перевод отклонён, получатель — в стоп-лист и Антифрод-центр. 850 000 ₸ остались у Сауле")
        d.until(170)
        d.shot("rejected")
        d.cap("Обычный перевод — ноль трения. Обман — остановлен. Это Qorgan.")
        d.until(180)

        video_path = Path(page.video.path()) if page.video and not stills else None
        ctx.close()
        browser.close()

    if video_path and video_path.exists():
        webm = MEDIA / "qorgan_demo.webm"
        shutil.move(str(video_path), webm)
        shutil.rmtree(MEDIA / "_raw", ignore_errors=True)
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            subprocess.run(
                [ffmpeg, "-y", "-loglevel", "error", "-i", str(webm), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                 "-crf", "26", "-movflags", "+faststart", str(MEDIA / "qorgan_demo.mp4")],
                check=True,
            )  # fmt: skip
        print(f"video: {webm}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--stills", action="store_true", help="only screenshots (2x), no video; implies --fast")
    args = ap.parse_args()
    run(args.base, args.fast or args.stills, args.stills)
