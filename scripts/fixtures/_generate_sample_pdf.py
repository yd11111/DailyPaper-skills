#!/usr/bin/env python3
"""Generate scripts/fixtures/sample.pdf — a 2-page PDF used by
test_pdf_tools.py. Run once; commit the resulting sample.pdf to git.

Requires: pip3 install --user reportlab

Page 1: text "Sample PDF for pdf_tools.py tests (spec #2)" + embedded
        large image (HuBERT_fig1.png) — guarantees pdfimages extracts
        an image >= 10 KB
Page 2: text "Page Two Only — this text is exclusive to page 2"
        (used by test_extract_text_first_n_pages: first_n_pages=1
        must NOT include this string)
"""

from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

HERE = Path(__file__).resolve().parent
OUT = HERE / "sample.pdf"
EMBED_IMG = Path(
    "/Users/xiangshu/DailyPaper/DailyPaper/assets/papers/figs/HuBERT_fig1.png"
)

def main():
    if not EMBED_IMG.exists():
        raise SystemExit(
            f"missing image to embed: {EMBED_IMG}\n"
            "pick another PNG and update EMBED_IMG above"
        )
    c = canvas.Canvas(str(OUT), pagesize=letter)
    # Page 1
    c.setFont("Helvetica", 14)
    c.drawString(72, 720, "Sample PDF for pdf_tools.py tests (spec #2)")
    c.drawString(72, 700, "This is page one. Used by test_extract_text_local.")
    # Embed the image, sized to ~400x500 pt; preserve aspect
    c.drawImage(
        str(EMBED_IMG), 72, 100, width=400, height=500,
        preserveAspectRatio=True, mask="auto",
    )
    c.showPage()
    # Page 2
    c.setFont("Helvetica", 14)
    c.drawString(72, 720, "Page Two Only — this text is exclusive to page 2")
    c.drawString(72, 700, "Used by test_extract_text_first_n_pages.")
    c.showPage()
    c.save()
    size = OUT.stat().st_size
    print(f"wrote {OUT} ({size} bytes)")

if __name__ == "__main__":
    main()
