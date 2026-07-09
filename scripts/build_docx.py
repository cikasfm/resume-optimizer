#!/usr/bin/env python3
"""
Generate DOCX from markdown source.
"""
import argparse
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from docx import Document
from config_loader import get_path, get_output_filename

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = get_path('resume_source')
DEFAULT_OUTDIR = get_path('build_dir')
DEFAULT_OUTDIR.mkdir(parents=True, exist_ok=True)
DEFAULT_OUT = DEFAULT_OUTDIR / get_output_filename('baseline_docx')

MARKDOWN_INLINE_RE = re.compile(r'(\*\*|__)(.+?)\1|(\*|_)(.+?)\3')


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


def add_formatted_runs(paragraph, text):
    for segment, bold, italic in parse_markdown_inline(text):
        if segment:
            run = paragraph.add_run(segment)
            run.bold = bold
            run.italic = italic


def build_docx(source_path, output_path):
    lines = source_path.read_text(encoding='utf-8').splitlines()
    doc = Document()

    for line in lines:
        line = line.rstrip()
        if not line:
            continue
        if line.startswith('# '):
            heading = doc.add_heading('', level=0)
            add_formatted_runs(heading, line[2:].strip())
        elif line.startswith('## '):
            heading = doc.add_heading('', level=1)
            add_formatted_runs(heading, line[3:].strip())
        elif line.startswith('### '):
            heading = doc.add_heading('', level=2)
            add_formatted_runs(heading, line[4:].strip())
        elif line.startswith('#### '):
            heading = doc.add_heading('', level=3)
            add_formatted_runs(heading, line[5:].strip())
        elif line.lstrip().startswith('- '):
            paragraph = doc.add_paragraph('', style='List Bullet')
            add_formatted_runs(paragraph, line.strip()[2:].strip())
        else:
            paragraph = doc.add_paragraph('')
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
