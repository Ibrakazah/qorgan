"""Render the HTML pitch deck (docs/submission/deck/index.html) to PDF and per-slide PNGs.

    python3 scripts/render_deck.py      (needs Playwright with Chromium; `make deck` runs it)

Outputs: docs/submission/Qorgan_pitch.pdf and docs/submission/deck/slides/slide_NN.png.
The PNGs feed scripts/build_deck.py, which packs them into Qorgan_pitch.pptx.
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "docs" / "submission" / "deck" / "index.html"
SLIDES = DECK.parent / "slides"
PDF = ROOT / "docs" / "submission" / "Qorgan_pitch.pdf"


def main() -> None:
    SLIDES.mkdir(parents=True, exist_ok=True)
    for old in SLIDES.glob("slide_*.png"):
        old.unlink()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page.goto(DECK.as_uri() + "?static")
        page.evaluate("document.fonts.ready")
        page.wait_for_load_state("networkidle")
        slides = page.locator(".slide")
        for i in range(slides.count()):
            slides.nth(i).screenshot(path=str(SLIDES / f"slide_{i + 1:02d}.png"))
        page.emulate_media(media="print")
        page.pdf(path=str(PDF), width="1920px", height="1080px", print_background=True, prefer_css_page_size=True)
        browser.close()
    print(f"slides: {len(list(SLIDES.glob('slide_*.png')))} → {SLIDES}\npdf: {PDF}")


if __name__ == "__main__":
    main()
