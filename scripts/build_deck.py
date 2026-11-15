"""Pack the rendered slides into docs/submission/Qorgan_pitch.pptx, with the speech as speaker notes.

    make deck     (= render_deck.py with Playwright, then this script with python-pptx)

The source of the deck is docs/submission/deck/index.html: edit text there and rebuild. The .pptx
is for organisers who need a PowerPoint file: each slide is a full-bleed image of the rendered
slide, and the speaker notes carry the matching part of docs/submission/SPEECH.md.
"""

from __future__ import annotations

import re
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

ROOT = Path(__file__).resolve().parents[1]
SLIDES = ROOT / "docs" / "submission" / "deck" / "slides"
SPEECH = ROOT / "docs" / "submission" / "SPEECH.md"
OUT = ROOT / "docs" / "submission" / "Qorgan_pitch.pptx"


def speech_by_slide() -> dict[int, str]:
    """`**[0:00–0:19] Слайд 1 — …**` blocks of SPEECH.md → {1: text}."""
    text = SPEECH.read_text(encoding="utf-8")
    notes: dict[int, str] = {}
    for m in re.finditer(r"\*\*\[([^\]]+)\] Слайд (\d+)[^*]*\*\*\n(.*?)(?=\n\*\*\[|\Z)", text, re.S):
        notes[int(m.group(2))] = f"[{m.group(1)}]\n{m.group(3).strip()}"
    return notes


def main() -> None:
    images = sorted(SLIDES.glob("slide_*.png"))
    if not images:
        raise SystemExit("Нет PNG слайдов: сначала python3 scripts/render_deck.py")
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    notes = speech_by_slide()
    for n, img in enumerate(images, 1):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.shapes.add_picture(str(img), 0, 0, width=prs.slide_width, height=prs.slide_height)
        slide.notes_slide.notes_text_frame.text = notes.get(n, "")
    prs.save(str(OUT))
    print(f"deck: {OUT} ({len(images)} slides, notes for {len(notes)})")


if __name__ == "__main__":
    main()
