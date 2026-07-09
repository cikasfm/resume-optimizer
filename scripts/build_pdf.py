#!/usr/bin/env python3
"""
Generate a clean PDF from markdown source (headings + bullets + paragraphs).
Uses ReportLab Paragraph to properly support inline bold formatting (**).
"""
import sys
import re
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from config_loader import get_path, get_output_filename

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = get_path('resume_source')
DEFAULT_OUTDIR = get_path('build_dir')
DEFAULT_OUTDIR.mkdir(parents=True, exist_ok=True)
DEFAULT_OUT = DEFAULT_OUTDIR / get_output_filename('baseline_pdf')

LEFT = 0.75 * inch
RIGHT = 0.75 * inch
TOP = 0.75 * inch
BOTTOM = 0.75 * inch

H1, H2, H3, BODY = 16, 12, 11, 10
LEADING = 13

def md_to_html(text):
    """Convert markdown formatting to ReportLab XML tags."""
    # Escape HTML special characters
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Convert **bold** to <b>bold</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    return text

def build_pdf(source_path, output_path):
    lines = source_path.read_text(encoding="utf-8").splitlines()
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter
    maxw = width - LEFT - RIGHT
    y = height - TOP

    # Define styles
    style_h1 = ParagraphStyle('H1', fontName='Helvetica-Bold', fontSize=H1, leading=H1 + 4)
    style_h2 = ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=H2, leading=H2 + 4)
    style_h3 = ParagraphStyle('H3', fontName='Helvetica-Bold', fontSize=H3, leading=H3 + 2)
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=BODY, leading=LEADING)
    style_bullet = ParagraphStyle('Bullet', fontName='Helvetica', fontSize=BODY, leading=LEADING, leftIndent=12, firstLineIndent=-12)

    for raw in lines:
        line = raw.rstrip()
        if not line:
            y -= 6
            continue

        if line.startswith("# "):
            html_text = md_to_html(line[2:].strip())
            p = Paragraph(html_text, style_h1)
            w, h = p.wrap(maxw, height)
            if y - h < BOTTOM:
                c.showPage()
                y = height - TOP
            p.drawOn(c, LEFT, y - h)
            y -= (h + 4)
            continue

        if line.startswith("## "):
            html_text = md_to_html(line[3:].strip())
            p = Paragraph(html_text, style_h2)
            w, h = p.wrap(maxw, height)
            if y - h < BOTTOM:
                c.showPage()
                y = height - TOP
            p.drawOn(c, LEFT, y - h)
            y -= (h + 2)
            continue

        if line.startswith("### ") or line.startswith("#### "):
            txt = line.split(" ", 1)[1].strip()
            html_text = md_to_html(txt)
            p = Paragraph(html_text, style_h3)
            w, h = p.wrap(maxw, height)
            if y - h < BOTTOM:
                c.showPage()
                y = height - TOP
            p.drawOn(c, LEFT, y - h)
            y -= h
            continue

        if line.lstrip().startswith("- "):
            txt = line.strip()[2:].strip()
            html_text = "&bull; " + md_to_html(txt)
            p = Paragraph(html_text, style_bullet)
            w, h = p.wrap(maxw, height)
            if y - h < BOTTOM:
                c.showPage()
                y = height - TOP
            p.drawOn(c, LEFT, y - h)
            y -= h
            continue

        html_text = md_to_html(line)
        p = Paragraph(html_text, style_body)
        w, h = p.wrap(maxw, height)
        if y - h < BOTTOM:
            c.showPage()
            y = height - TOP
        p.drawOn(c, LEFT, y - h)
        y -= h

    c.save()
    print(f"Wrote {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Generate PDF from markdown source')
    parser.add_argument('--source', '-s', default=str(DEFAULT_SRC), help='Markdown source file')
    parser.add_argument('--output', '-o', default=str(DEFAULT_OUT), help='Output PDF file')

    args = parser.parse_args()
    source = Path(args.source).resolve()
    output = Path(args.output).resolve()

    if not source.exists():
        raise FileNotFoundError(f"Markdown source file not found: {source}")

    build_pdf(source, output)

if __name__ == "__main__":
    main()
