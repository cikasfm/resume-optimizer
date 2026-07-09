#!/usr/bin/env python3
"""
Convert docs/resume.md to docs/resume.dox (Doxygen format).
This allows you to edit only the markdown file and auto-generate the Doxygen file.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import re
from config_loader import get_path, load_config

ROOT = Path(__file__).resolve().parents[1]
SRC = get_path('resume_source')
OUT = get_path('resume_dox')

def convert_md_to_dox(md_content):
    """Convert markdown content to Doxygen format."""
    lines = md_content.splitlines()
    output = []
    
    # Load config to get name
    config = load_config()
    raw_name = config.get('name', 'Resume')
    display_name = raw_name.replace('_', ' ')
    
    # Doxygen header
    output.append("/*!")
    output.append(f"@page resume {display_name} — Resume")
    output.append("")
    
    # Process first heading as header
    header_processed = False
    i = 0
    
    while i < len(lines):
        line = lines[i].rstrip()
        
        # Skip empty lines at the start
        if not line and not output:
            i += 1
            continue
        
        # First # heading becomes the @htmlonly header
        if not header_processed and line.startswith("# "):
            name = line[2:].strip()
            # Get the next non-empty line for contact info (skip empty lines)
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].strip() and not lines[j].strip().startswith("#"):
                contact = lines[j].strip()
                output.append("@htmlonly")
                output.append(f"<p><strong>{name}</strong><br/>")
                output.append(f"{contact}</p>")
                output.append("@endhtmlonly")
                output.append("")
                i = j + 1
                header_processed = True
                continue
            else:
                output.append("@htmlonly")
                output.append(f"<p><strong>{name}</strong></p>")
                output.append("@endhtmlonly")
                output.append("")
                i += 1
                header_processed = True
                continue
        
        # ## headings become @section
        if line.startswith("## "):
            section_name = line[3:].strip()
            # Create a section ID from the name (lowercase, replace spaces/special chars with underscores)
            section_id = re.sub(r'[^a-zA-Z0-9]+', '_', section_name.lower()).strip('_')
            output.append(f"@section {section_id} {section_name}")
            output.append("")
            i += 1
            continue
        
        # ### headings become @subsection
        if line.startswith("### "):
            subsection_name = line[4:].strip()
            subsection_id = re.sub(r'[^a-zA-Z0-9]+', '_', subsection_name.lower()).strip('_')
            output.append(f"@subsection {subsection_id} {subsection_name}")
            output.append("")
            i += 1
            continue
        
        # #### headings become @subsubsection
        if line.startswith("#### "):
            subsubsection_name = line[5:].strip()
            subsubsection_id = re.sub(r'[^a-zA-Z0-9]+', '_', subsubsection_name.lower()).strip('_')
            output.append(f"@subsubsection {subsubsection_id} {subsubsection_name}")
            output.append("")
            i += 1
            continue
        
        # Italic text (*text*) becomes @paragraph
        if line.strip().startswith("*") and line.strip().endswith("*") and not line.strip().startswith("-"):
            para_text = line.strip().strip("*").strip()
            para_id = re.sub(r'[^a-zA-Z0-9]+', '_', para_text.lower()[:30]).strip('_')
            output.append(f"@paragraph {para_id}")
            output.append(para_text)
            output.append("")
            i += 1
            continue
        
        # Bullet points stay as bullet points
        if line.lstrip().startswith("- "):
            output.append(line)
            i += 1
            continue
        
        # Empty lines
        if not line:
            output.append("")
            i += 1
            continue
        
        # Regular paragraphs
        output.append(line)
        i += 1
    
    # Close the Doxygen comment
    output.append("*/")
    
    return "\n".join(output)

def main():
    """Main function to convert resume.md to resume.dox."""
    if not SRC.exists():
        print(f"Error: {SRC} not found")
        return 1
    
    md_content = SRC.read_text(encoding="utf-8")
    dox_content = convert_md_to_dox(md_content)
    
    OUT.write_text(dox_content, encoding="utf-8")
    print(f"Converted {SRC} -> {OUT}")
    return 0

if __name__ == "__main__":
    exit(main())
