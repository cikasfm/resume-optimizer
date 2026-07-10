#!/usr/bin/env python3
"""
Generate a beautifully styled DOCX from markdown source, matching
the layout, spacing, and design of the PDF/Print stylesheet.
"""
import argparse
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import docx
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from config_loader import get_path, get_output_filename

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = get_path('resume_source')
DEFAULT_OUTDIR = get_path('build_dir')
DEFAULT_OUTDIR.mkdir(parents=True, exist_ok=True)
DEFAULT_OUT = DEFAULT_OUTDIR / get_output_filename('baseline_docx')

MARKDOWN_INLINE_RE = re.compile(r'(\*\*|__)(.+?)\1|(\*|_)(.+?)\3')
MARKDOWN_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')


def parse_markdown_inline(text):
    """Parse inline markdown for bold and italic formatting."""
    segments = []
    last_end = 0

    for match in MARKDOWN_INLINE_RE.finditer(text):
        if match.start() > last_end:
            segments.append((text[last_end:match.start()], False, False))

        if match.group(1):
            segments.append((match.group(2), True, False))
        else:
            segments.append((match.group(4), False, True))

        last_end = match.end()

    if last_end < len(text):
        segments.append((text[last_end:], False, False))

    return segments


def add_hyperlink(paragraph, text, url, color_hex="2B6CB0", underline=True):
    """Adds a clickable hyperlink to a paragraph."""
    part = paragraph.part
    r_id = part.relate_to(url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)

    # Create the w:hyperlink node
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)

    # Create a w:r node
    new_run = OxmlElement('w:r')

    # Create a new w:rPr node
    rPr = OxmlElement('w:rPr')

    # Add color
    c = OxmlElement('w:color')
    c.set(qn('w:val'), color_hex)
    rPr.append(c)

    # Add underline
    if underline:
        u = OxmlElement('w:u')
        u.set(qn('w:val'), 'single')
        rPr.append(u)

    new_run.append(rPr)

    # Add text
    text_node = OxmlElement('w:t')
    text_node.text = text
    new_run.append(text_node)

    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    
    return hyperlink


def add_basic_runs(paragraph, text):
    """Adds bold/italic runs to a paragraph."""
    for segment, bold, italic in parse_markdown_inline(text):
        if segment:
            run = paragraph.add_run(segment)
            run.bold = bold
            run.italic = italic


def add_formatted_runs(paragraph, text):
    """Parses text for links and basic inline styles and adds them to paragraph."""
    last_end = 0
    for match in MARKDOWN_LINK_RE.finditer(text):
        if match.start() > last_end:
            add_basic_runs(paragraph, text[last_end:match.start()])
        
        link_text = match.group(1)
        link_url = match.group(2)
        add_hyperlink(paragraph, link_text, link_url)
        last_end = match.end()
        
    if last_end < len(text):
        add_basic_runs(paragraph, text[last_end:])


def add_p_border_bottom(paragraph, color_hex="1A365D", size_pt=6, space_pt=4):
    """Adds a horizontal bottom border line to a paragraph."""
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = pPr.find(qn('w:pBdr'))
    if pBdr is None:
        pBdr = OxmlElement('w:pBdr')
        pPr.append(pBdr)
    
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), str(size_pt))
    bottom.set(qn('w:space'), str(space_pt))
    bottom.set(qn('w:color'), color_hex)
    pBdr.append(bottom)


def build_docx(source_path, output_path):
    lines = source_path.read_text(encoding='utf-8').splitlines()
    doc = Document()

    # Set document margins (0.75 inch -> 54pt)
    for section in doc.sections:
        section.top_margin = Pt(54)
        section.bottom_margin = Pt(54)
        section.left_margin = Pt(54)
        section.right_margin = Pt(54)

    # Configure styles
    # Set Normal (body text)
    style_normal = doc.styles['Normal']
    font_normal = style_normal.font
    font_normal.name = 'Arial'
    font_normal.size = Pt(10.5)
    font_normal.color.rgb = RGBColor(0x33, 0x33, 0x33)
    style_normal.paragraph_format.space_after = Pt(4)
    style_normal.paragraph_format.line_spacing = 1.15

    # Set Heading 1
    style_h1 = doc.styles['Heading 1']
    font_h1 = style_h1.font
    font_h1.name = 'Arial'
    font_h1.size = Pt(20)
    font_h1.bold = True
    font_h1.color.rgb = RGBColor(0x1A, 0x36, 0x5D)
    style_h1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_h1.paragraph_format.space_after = Pt(6)

    # Set Heading 2
    style_h2 = doc.styles['Heading 2']
    font_h2 = style_h2.font
    font_h2.name = 'Arial'
    font_h2.size = Pt(12.5)
    font_h2.bold = True
    font_h2.color.rgb = RGBColor(0x1A, 0x36, 0x5D)
    style_h2.paragraph_format.space_before = Pt(18)
    style_h2.paragraph_format.space_after = Pt(6)

    # Set Heading 3
    style_h3 = doc.styles['Heading 3']
    font_h3 = style_h3.font
    font_h3.name = 'Arial'
    font_h3.size = Pt(11)
    font_h3.bold = True
    font_h3.color.rgb = RGBColor(0x2B, 0x6C, 0xB0)
    style_h3.paragraph_format.space_before = Pt(10)
    style_h3.paragraph_format.space_after = Pt(4)

    h2_count = 0
    is_first_paragraph_after_h1 = False

    for line in lines:
        line = line.rstrip()
        if not line:
            continue
            
        if line.startswith('# '):
            heading = doc.add_heading('', level=1)
            add_formatted_runs(heading, line[2:].strip())
            is_first_paragraph_after_h1 = True
        elif is_first_paragraph_after_h1:
            # Centered contact info with bottom border divider
            paragraph = doc.add_paragraph('')
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_after = Pt(12)
            add_p_border_bottom(paragraph, color_hex="CCCCCC", size_pt=6, space_pt=8)
            add_formatted_runs(paragraph, line.strip())
            is_first_paragraph_after_h1 = False
        elif line.startswith('## '):
            h2_count += 1
            text = line[3:].strip()
            heading = doc.add_heading('', level=2)
            if h2_count == 1:
                # Subtitle (Staff Software Engineer | ...) - no border
                add_formatted_runs(heading, text.upper())
            else:
                # Section heading (uppercase, bottom border)
                add_formatted_runs(heading, text.upper())
                add_p_border_bottom(heading, color_hex="1A365D", size_pt=8, space_pt=4)
        elif line.startswith('### '):
            heading = doc.add_heading('', level=3)
            add_formatted_runs(heading, line[4:].strip())
        elif line.startswith('#### '):
            heading = doc.add_heading('', level=4)
            add_formatted_runs(heading, line[5:].strip())
        elif line.lstrip().startswith('- '):
            paragraph = doc.add_paragraph('', style='List Bullet')
            paragraph.paragraph_format.space_after = Pt(3)
            add_formatted_runs(paragraph, line.strip()[2:].strip())
        else:
            paragraph = doc.add_paragraph('')
            paragraph.paragraph_format.space_after = Pt(4)
            add_formatted_runs(paragraph, line)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    print(f'Wrote {output_path}')


def main():
    parser = argparse.ArgumentParser(description='Generate DOCX from markdown source')
    parser.add_argument('--source', '-s', default=str(DEFAULT_SRC), help='Markdown source file')
    parser.add_argument('--output', '-o', default=str(DEFAULT_OUT), help='Output DOCX file')

    args = parser.parse_args()
    source = Path(args.source).resolve()
    output = Path(args.output).resolve()

    if not source.exists():
        raise FileNotFoundError(f'Markdown source file not found: {source}')

    build_docx(source, output)


if __name__ == '__main__':
    main()
