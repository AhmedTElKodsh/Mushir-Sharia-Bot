#!/usr/bin/env python3
"""
AAOIFI PDF to Markdown Converter

This script converts AAOIFI standard PDFs to clean Markdown format
optimized for Gemini Gem knowledge base.

Usage:
    # Convert single PDF
    python convert_pdf_to_markdown.py --input "path/to/FAS01.pdf" --output "output/"
    
    # Convert all PDFs in directory
    python convert_pdf_to_markdown.py --input-dir "pdfs/" --output-dir "output/"
    
    # With custom naming
    python convert_pdf_to_markdown.py --input "FAS01.pdf" --output "output/" --name "AAOIFI_FAS01_General-Presentation"

Requirements:
    pip install pymupdf markdown
"""

import argparse
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Optional, List, Dict, Union
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF not installed. Run: pip install pymupdf")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DocumentStructure:
    """Represents the detected structure of a document."""
    title: str
    sections: List[Dict[str, str]]
    subsections: List[Dict[str, str]]


class AAOIFIPDFConverter:
    """Converts AAOIFI PDF standards to Markdown format."""
    
    # Constants
    TITLE_DETECTION_LINES = 10
    MIN_HEADER_LENGTH = 5
    MAX_HEADER_LENGTH = 100
    SEPARATOR_WIDTH = 60
    PROGRESS_INTERVAL = 10
    MIN_TOKEN_COUNT = 50
    MAX_TOKEN_COUNT = 512
    
    # Compiled regex patterns
    SECTION_PATTERN = re.compile(r'^(\d+\.?\d*\.?\d*)\s+([A-Z][^\n]+)$')
    MAIN_SECTION_PATTERN = re.compile(r'^\d+\.\s+[A-Z]')
    SUBSECTION_PATTERN = re.compile(r'^\d+\.\d+\s+[A-Z]')
    SUB_SUBSECTION_PATTERN = re.compile(r'^\d+\.\d+\.\d+\s+[A-Z]')
    STANDARD_NUMBER_PATTERN = re.compile(r'FAS[-\s]?(\d+)', re.IGNORECASE)
    
    # Text cleaning patterns
    PAGE_NUMBER_PATTERN = re.compile(r'^\d+\s*$', re.MULTILINE)
    AAOIFI_HEADER_PATTERN = re.compile(r'^AAOIFI\s*$', re.MULTILINE)
    FAS_HEADER_PATTERN = re.compile(r'^Financial Accounting Standard.*$', re.MULTILINE)
    HYPHENATION_PATTERN = re.compile(r'(\w+)-\s*\n\s*(\w+)')
    EXCESSIVE_NEWLINES_PATTERN = re.compile(r'\n{3,}')
    EXCESSIVE_SPACES_PATTERN = re.compile(r' {2,}')
    MARKDOWN_EXCESSIVE_NEWLINES_PATTERN = re.compile(r'\n{4,}')
    
    def __init__(self, input_path: str, output_dir: str, custom_name: Optional[str] = None):
        self.input_path = Path(input_path)
        self.output_dir = Path(output_dir)
        self.custom_name = custom_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_text_from_pdf(self) -> str:
        """Extract text content from PDF file."""
        try:
            text_buffer = StringIO()
            
            with fitz.open(self.input_path) as doc:
                logger.info(f"Processing {len(doc)} pages...")
                
                for page_num, page in enumerate(doc, 1):
                    # Extract text with layout preservation
                    text = page.get_text("text")
                    
                    # Remove page numbers and headers/footers
                    text = self._remove_headers_footers(text)
                    
                    text_buffer.write(text)
                    text_buffer.write("\n\n")
                    
                    if page_num % self.PROGRESS_INTERVAL == 0:
                        logger.info(f"  Processed {page_num}/{len(doc)} pages...")
            
            full_text = text_buffer.getvalue()
            logger.info(f"✓ Extracted {len(full_text)} characters from PDF")
            
            return full_text
            
        except fitz.FileDataError as e:
            logger.error(f"Invalid or corrupted PDF file: {e}")
            return ""
        except IOError as e:
            logger.error(f"Error reading PDF file: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error extracting text from PDF: {e}")
            return ""
    
    def _remove_headers_footers(self, text: str) -> str:
        """Remove common headers, footers, and page numbers."""
        text = self.PAGE_NUMBER_PATTERN.sub('', text)
        text = self.AAOIFI_HEADER_PATTERN.sub('', text)
        text = self.FAS_HEADER_PATTERN.sub('', text)
        return text
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        # Fix broken hyphenation (word- \n word -> word)
        text = self.HYPHENATION_PATTERN.sub(r'\1\2', text)
        
        # Remove excessive whitespace
        text = self.EXCESSIVE_NEWLINES_PATTERN.sub('\n\n', text)
        text = self.EXCESSIVE_SPACES_PATTERN.sub(' ', text)
        
        # Fix common OCR errors (ligatures)
        text = text.replace('ﬁ', 'fi')
        text = text.replace('ﬂ', 'fl')
        
        return text.strip()
    
    def detect_structure(self, text: str) -> DocumentStructure:
        """Detect document structure (headers, sections, etc.)."""
        lines = text.split('\n')
        title = ''
        sections = []
        
        # Try to detect title (usually first few lines, all caps or title case)
        for line in lines[:self.TITLE_DETECTION_LINES]:
            if len(line) > 10 and (line.isupper() or line.istitle()):
                title = line.strip()
                break
        
        # Detect section headers
        for line in lines:
            match = self.SECTION_PATTERN.match(line.strip())
            if match:
                section_num, section_title = match.groups()
                sections.append({
                    'number': section_num,
                    'title': section_title.strip()
                })
        
        return DocumentStructure(
            title=title,
            sections=sections,
            subsections=[]  # Can be extended if needed
        )
    
    def convert_to_markdown(self, text: str) -> str:
        """Convert cleaned text to Markdown format."""
        lines = text.split('\n')
        markdown_lines = []
        
        # Detect and convert headers
        for line in lines:
            line = line.strip()
            
            if not line:
                markdown_lines.append('')
                continue
            
            # Main section headers (e.g., "1. Introduction", "2. Objective")
            if self.MAIN_SECTION_PATTERN.match(line):
                markdown_lines.append(f"\n## {line}\n")
            
            # Subsection headers (e.g., "1.1 Background", "2.3 Scope")
            elif self.SUBSECTION_PATTERN.match(line):
                markdown_lines.append(f"\n### {line}\n")
            
            # Sub-subsection headers (e.g., "1.1.1 Purpose")
            elif self.SUB_SUBSECTION_PATTERN.match(line):
                markdown_lines.append(f"\n#### {line}\n")
            
            # All caps lines (potential headers)
            elif line.isupper() and self.MIN_HEADER_LENGTH < len(line) < self.MAX_HEADER_LENGTH:
                markdown_lines.append(f"\n## {line.title()}\n")
            
            # Regular paragraph
            else:
                markdown_lines.append(line)
        
        markdown_text = '\n'.join(markdown_lines)
        
        # Clean up excessive newlines
        markdown_text = self.MARKDOWN_EXCESSIVE_NEWLINES_PATTERN.sub('\n\n', markdown_text)
        
        return markdown_text
    
    def add_metadata_header(self, markdown_text: str, structure: DocumentStructure) -> str:
        """Add metadata header to Markdown document."""
        title = structure.title or self.input_path.stem
        
        # Try to extract standard number from filename or title
        standard_match = self.STANDARD_NUMBER_PATTERN.search(title)
        standard_num = standard_match.group(1) if standard_match else "XX"
        
        header = f"""# AAOIFI FAS-{standard_num}: {title}

**Standard Number:** FAS-{standard_num}  
**Title:** {title}  
**Source:** https://aaoifi.com/accounting-standards-2/?lang=en  
**Converted:** {self._get_current_date()}  
**Format:** Markdown (converted from PDF)

---

## Table of Contents

"""
        
        # Add detected sections to TOC
        for section in structure.sections[:10]:
            section_title = section.get('title', 'Untitled Section')
            section_num = section.get('number', '')
            # Create anchor link
            anchor = section_title.lower().replace(' ', '-').replace('.', '')
            header += f"{section_num}. [{section_title}](#{anchor})\n"
        
        header += "\n---\n\n"
        
        return header + markdown_text
    
    def _get_current_date(self) -> str:
        """Get current date in YYYY-MM-DD format."""
        return datetime.now().strftime('%Y-%m-%d')
    
    def generate_output_filename(self) -> str:
        """Generate output filename following naming convention."""
        if self.custom_name:
            base_name = self.custom_name
        else:
            # Try to extract standard info from input filename
            base_name = self.input_path.stem
            
            # Clean up common patterns
            base_name = re.sub(r'[_\s]+', '_', base_name)
            base_name = re.sub(r'AAOIFI[_\s]*', 'AAOIFI_', base_name, flags=re.IGNORECASE)
            
            # Ensure it starts with AAOIFI_
            if not base_name.startswith('AAOIFI_'):
                base_name = f'AAOIFI_{base_name}'
        
        # Ensure .md extension
        if not base_name.endswith('.md'):
            base_name += '.md'
        
        return base_name
    
    def convert(self) -> Optional[Path]:
        """Main conversion process."""
        logger.info(f"\n{'='*self.SEPARATOR_WIDTH}")
        logger.info(f"Converting: {self.input_path.name}")
        logger.info(f"{'='*self.SEPARATOR_WIDTH}\n")
        
        # Step 1: Extract text from PDF
        logger.info("Step 1: Extracting text from PDF...")
        raw_text = self.extract_text_from_pdf()
        
        if not raw_text:
            logger.error("✗ Failed to extract text from PDF")
            return None
        
        # Step 2: Clean text
        logger.info("\nStep 2: Cleaning text...")
        cleaned_text = self.clean_text(raw_text)
        logger.info(f"✓ Cleaned text ({len(cleaned_text)} characters)")
        
        # Step 3: Detect structure
        logger.info("\nStep 3: Detecting document structure...")
        structure = self.detect_structure(cleaned_text)
        logger.info(f"✓ Detected {len(structure.sections)} sections")
        if structure.title:
            logger.info(f"  Title: {structure.title}")
        
        # Step 4: Convert to Markdown
        logger.info("\nStep 4: Converting to Markdown...")
        markdown_text = self.convert_to_markdown(cleaned_text)
        logger.info("✓ Converted to Markdown")
        
        # Step 5: Add metadata header
        logger.info("\nStep 5: Adding metadata header...")
        final_markdown = self.add_metadata_header(markdown_text, structure)
        logger.info("✓ Added metadata header")
        
        # Step 6: Save to file
        output_filename = self.generate_output_filename()
        output_path = self.output_dir / output_filename
        
        logger.info(f"\nStep 6: Saving to file...")
        logger.info(f"  Output: {output_path}")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_markdown)
            logger.info("✓ Saved successfully")
            logger.info(f"\n{'='*self.SEPARATOR_WIDTH}")
            logger.info(f"✓ Conversion complete: {output_path.name}")
            logger.info(f"{'='*self.SEPARATOR_WIDTH}\n")
            return output_path
        except IOError as e:
            logger.error(f"✗ Error saving file: {e}")
            return None


def convert_single_pdf(input_path: str, output_dir: str, custom_name: Optional[str] = None):
    """Convert a single PDF file to Markdown."""
    converter = AAOIFIPDFConverter(input_path, output_dir, custom_name)
    return converter.convert()


def convert_directory(input_dir: str, output_dir: str):
    """Convert all PDF files in a directory to Markdown."""
    input_path = Path(input_dir)
    pdf_files = list(input_path.glob('*.pdf'))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return
    
    logger.info(f"\nFound {len(pdf_files)} PDF files to convert\n")
    
    successful = 0
    failed = 0
    
    for pdf_file in pdf_files:
        result = convert_single_pdf(str(pdf_file), output_dir)
        if result:
            successful += 1
        else:
            failed += 1
    
    logger.info(f"\n{'='*60}")
    logger.info("Batch Conversion Complete")
    logger.info(f"{'='*60}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total: {len(pdf_files)}")
    logger.info(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Convert AAOIFI PDF standards to Markdown format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert single PDF
  python convert_pdf_to_markdown.py --input FAS01.pdf --output output/
  
  # Convert with custom name
  python convert_pdf_to_markdown.py --input FAS01.pdf --output output/ --name AAOIFI_FAS01_General-Presentation
  
  # Convert all PDFs in directory
  python convert_pdf_to_markdown.py --input-dir pdfs/ --output-dir output/
        """
    )
    
    parser.add_argument('--input', type=str, help='Input PDF file path')
    parser.add_argument('--output', type=str, help='Output directory for single file conversion')
    parser.add_argument('--input-dir', type=str, help='Input directory containing PDF files')
    parser.add_argument('--output-dir', type=str, help='Output directory for batch conversion')
    parser.add_argument('--name', type=str, help='Custom output filename (without .md extension)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.input and args.input_dir:
        print("Error: Cannot specify both --input and --input-dir")
        sys.exit(1)
    
    if not args.input and not args.input_dir:
        print("Error: Must specify either --input or --input-dir")
        parser.print_help()
        sys.exit(1)
    
    # Single file conversion
    if args.input:
        if not args.output:
            print("Error: --output is required when using --input")
            sys.exit(1)
        
        if not os.path.exists(args.input):
            print(f"Error: Input file not found: {args.input}")
            sys.exit(1)
        
        result = convert_single_pdf(args.input, args.output, args.name)
        sys.exit(0 if result else 1)
    
    # Batch conversion
    if args.input_dir:
        if not args.output_dir:
            print("Error: --output-dir is required when using --input-dir")
            sys.exit(1)
        
        if not os.path.exists(args.input_dir):
            print(f"Error: Input directory not found: {args.input_dir}")
            sys.exit(1)
        
        convert_directory(args.input_dir, args.output_dir)
        sys.exit(0)


if __name__ == '__main__':
    main()
