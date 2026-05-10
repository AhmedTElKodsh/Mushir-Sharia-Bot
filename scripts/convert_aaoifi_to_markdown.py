"""
Convert AAOIFI PDF standards to markdown with Sharia compliance metadata
"""
import os
import re
from pathlib import Path
from datetime import datetime
import PyPDF2


def extract_title_from_first_page(pdf_path):
    """Extract title from the first page of PDF"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            if len(pdf_reader.pages) > 0:
                first_page = pdf_reader.pages[0]
                text = first_page.extract_text()
                
                # Get first non-empty line as title
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                if lines:
                    # Clean up the title
                    title = lines[0]
                    # Remove common prefixes
                    title = re.sub(r'^(AAOIFI|Shari[\'\']?ah Standard|Standard No\.?)\s*:?\s*', '', title, flags=re.IGNORECASE)
                    return title.strip()
    except Exception as e:
        print(f"Error extracting title from {pdf_path}: {e}")
    return None


def extract_full_text(pdf_path):
    """Extract all text from PDF"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text_content = []
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                if page_text.strip():
                    text_content.append(f"## Page {page_num}\n\n{page_text}\n")
            
            return '\n'.join(text_content)
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return ""


def sanitize_filename(title):
    """Convert title to valid filename"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', title)
    # Replace spaces and special chars with underscores
    filename = re.sub(r'\s+', '_', filename)
    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)
    # Limit length
    filename = filename[:200]
    return filename.strip('_')


def create_markdown_with_metadata(pdf_path, output_dir):
    """Convert PDF to markdown with Sharia compliance metadata"""
    
    # Extract information
    filename = Path(pdf_path).stem
    standard_match = re.match(r'Standard_(\d+)_(AR|EN)', filename)
    
    if not standard_match:
        print(f"Skipping {filename} - doesn't match expected pattern")
        return None
    
    standard_number = standard_match.group(1)
    language = "Arabic" if standard_match.group(2) == "AR" else "English"
    language_code = standard_match.group(2).lower()
    
    print(f"Processing Standard {standard_number} ({language})...")
    
    # Extract title and content
    title = extract_title_from_first_page(pdf_path)
    if not title:
        title = f"AAOIFI Shari'ah Standard No. {standard_number}"
    
    content = extract_full_text(pdf_path)
    
    # Create sanitized filename
    safe_title = sanitize_filename(title)
    output_filename = f"AAOIFI_Standard_{standard_number}_{language_code}_{safe_title}.md"
    output_path = output_dir / output_filename
    
    # Create metadata
    metadata = f"""---
# Sharia Compliance Metadata
document_type: "AAOIFI Shari'ah Standard"
standard_number: {standard_number}
title: "{title}"
language: "{language}"
language_code: "{language_code}"
source: "AAOIFI (Accounting and Auditing Organization for Islamic Financial Institutions)"
source_file: "{filename}.pdf"
category: "Islamic Finance Standards"
subcategory: "Shari'ah Standards"
compliance_domain: "Islamic Banking and Finance"
authority: "AAOIFI"
status: "Published"
extracted_date: "{datetime.now().strftime('%Y-%m-%d')}"
format: "markdown"
original_format: "pdf"

# Classification
topics:
  - Islamic Finance
  - Shari'ah Compliance
  - AAOIFI Standards
  - Islamic Banking

# Usage
intended_use: "Reference for Shari'ah compliance in Islamic financial transactions"
target_audience: 
  - Islamic Finance Professionals
  - Shari'ah Scholars
  - Compliance Officers
  - Financial Institutions

# Document Properties
has_arabic_version: true
has_english_version: true
paired_document: "Standard_{standard_number}_{'EN' if language_code == 'ar' else 'AR'}"
---

# {title}

**AAOIFI Shari'ah Standard No. {standard_number}**

---

{content}

---

## Document Information

- **Standard Number**: {standard_number}
- **Language**: {language}
- **Source**: AAOIFI
- **Extracted**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Original File**: `{filename}.pdf`
"""
    
    # Write markdown file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(metadata)
        print(f"✓ Created: {output_filename}")
        return output_path
    except Exception as e:
        print(f"✗ Error creating {output_filename}: {e}")
        return None


def main():
    # Paths
    base_dir = Path(__file__).parent.parent
    input_dir = base_dir / "data" / "raw" / "aaoifi_standards"
    output_dir = base_dir / "gemini-gem-prototype" / "knowledge-base"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all PDF files
    pdf_files = sorted(input_dir.glob("Standard_*.pdf"))
    
    print(f"Found {len(pdf_files)} PDF files to convert")
    print(f"Output directory: {output_dir}")
    print("-" * 60)
    
    # Convert each PDF
    success_count = 0
    for pdf_path in pdf_files:
        result = create_markdown_with_metadata(pdf_path, output_dir)
        if result:
            success_count += 1
    
    print("-" * 60)
    print(f"Conversion complete: {success_count}/{len(pdf_files)} files converted successfully")
    
    # Create index file
    create_index_file(output_dir)


def create_index_file(output_dir):
    """Create an index file listing all converted standards"""
    
    md_files = sorted(output_dir.glob("AAOIFI_Standard_*.md"))
    
    # Group by standard number
    standards = {}
    for md_file in md_files:
        match = re.search(r'Standard_(\d+)_(ar|en)', md_file.stem)
        if match:
            std_num = int(match.group(1))
            lang = match.group(2)
            if std_num not in standards:
                standards[std_num] = {}
            standards[std_num][lang] = md_file.name
    
    # Create index content
    index_content = f"""# AAOIFI Shari'ah Standards - Knowledge Base Index

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This knowledge base contains {len(standards)} AAOIFI Shari'ah Standards in both Arabic and English.

## About AAOIFI

The Accounting and Auditing Organization for Islamic Financial Institutions (AAOIFI) is an international organization that prepares accounting, auditing, governance, ethics and Shari'ah standards for Islamic financial institutions.

## Standards List

"""
    
    for std_num in sorted(standards.keys()):
        index_content += f"\n### Standard {std_num:02d}\n\n"
        if 'en' in standards[std_num]:
            index_content += f"- 🇬🇧 English: [{standards[std_num]['en']}](./{standards[std_num]['en']})\n"
        if 'ar' in standards[std_num]:
            index_content += f"- 🇸🇦 Arabic: [{standards[std_num]['ar']}](./{standards[std_num]['ar']})\n"
    
    index_content += f"""

## Metadata Structure

Each markdown file includes comprehensive Sharia compliance metadata:

- **Document Type**: AAOIFI Shari'ah Standard
- **Standard Number**: Unique identifier
- **Title**: Extracted from first page
- **Language**: Arabic or English
- **Source**: AAOIFI
- **Category**: Islamic Finance Standards
- **Topics**: Relevant classification tags
- **Intended Use**: Reference for Shari'ah compliance
- **Target Audience**: Islamic finance professionals, scholars, compliance officers

## Usage

These documents are intended for:
- Reference in Shari'ah compliance assessments
- Training and education in Islamic finance
- Development of Islamic financial products
- Compliance verification and auditing

---

*Total Standards: {len(standards)}*  
*Total Documents: {len(md_files)}*
"""
    
    index_path = output_dir / "INDEX.md"
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    print(f"✓ Created index file: INDEX.md")


if __name__ == "__main__":
    main()
