#!/usr/bin/env python3
"""
Optimize a resume for a specific job posting and build Word/PDF outputs in one step.

Usage:
    python scripts/optimize_and_build.py <job_description_url> [--company COMPANY] [--verbose]

Example:
    python scripts/optimize_and_build.py https://example.com/jobs/software-engineer --company "Google"
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config_loader import get_path, get_output_filename
from optimize_resume import fetch_job_description, read_resume, call_ai_provider, save_outputs


def build_markdown_to_docx_pdf(source_md: Path, docx_path: Path, pdf_path: Path):
    """Build DOCX and PDF from a markdown source file."""
    source = str(source_md)

    # Build DOCX
    subprocess.run([sys.executable, str(Path(__file__).parent / "build_docx.py"), "--source", source, "--output", str(docx_path)], check=True)

    # Build PDF
    subprocess.run([sys.executable, str(Path(__file__).parent / "build_pdf.py"), "--source", source, "--output", str(pdf_path)], check=True)


def main():
    parser = argparse.ArgumentParser(description='Optimize resume and build Word/PDF outputs in one step')
    parser.add_argument('job_url', help='URL to the job description')
    parser.add_argument('--company', '-c', help='Company name for file naming', default=None)
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed error information')

    args = parser.parse_args()
    job_url = args.job_url
    company = args.company
    verbose = args.verbose

    print(f"\n🔍 Fetching job description from: {job_url}")
    job_description = fetch_job_description(job_url)
    print(f"✓ Fetched job description ({len(job_description)} characters)")

    print("📄 Loading current resume...")
    current_resume = read_resume()
    print(f"✓ Loaded resume ({len(current_resume)} characters)")

    print("🤖 Calling AI to optimize resume...")
    results = call_ai_provider(job_description, current_resume, verbose=verbose)
    print("✓ AI optimization complete")

    print("💾 Saving optimized markdown outputs...")
    resume_out, cover_letter_out, timestamp = save_outputs(
        results['optimized_resume'],
        results['cover_letter'],
        results['changelog'],
        job_url,
        company=company
    )

    build_dir = get_path('build_dir')
    if company:
        resume_docx = build_dir / get_output_filename('optimized_docx', company=company, timestamp=timestamp)
        resume_pdf = build_dir / get_output_filename('optimized_pdf', company=company, timestamp=timestamp)
        cover_docx = build_dir / get_output_filename('cover_letter_docx', company=company, timestamp=timestamp)
        cover_pdf = build_dir / get_output_filename('cover_letter_pdf', company=company, timestamp=timestamp)
    else:
        resume_docx = build_dir / get_output_filename('optimized_docx_fallback', timestamp=timestamp)
        resume_pdf = build_dir / get_output_filename('optimized_pdf_fallback', timestamp=timestamp)
        cover_docx = build_dir / get_output_filename('cover_letter_docx_fallback', timestamp=timestamp)
        cover_pdf = build_dir / get_output_filename('cover_letter_pdf_fallback', timestamp=timestamp)

    print("📦 Building optimized resume Word/PDF outputs...")
    build_markdown_to_docx_pdf(resume_out, resume_docx, resume_pdf)
    print("📦 Building cover letter Word/PDF outputs...")
    build_markdown_to_docx_pdf(cover_letter_out, cover_docx, cover_pdf)

    print("\n✅ One-step optimization complete!")
    print(f"  Resume Markdown: {resume_out}")
    print(f"  Resume DOCX: {resume_docx}")
    print(f"  Resume PDF: {resume_pdf}")
    print(f"  Cover Letter Markdown: {cover_letter_out}")
    print(f"  Cover Letter DOCX: {cover_docx}")
    print(f"  Cover Letter PDF: {cover_pdf}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
