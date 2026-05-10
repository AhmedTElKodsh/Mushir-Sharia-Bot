# AAOIFI PDF to Markdown Conversion Guide

## Overview

This guide helps you convert AAOIFI standard PDFs into clean Markdown files optimized for Gemini Gem knowledge base.

## File Naming Convention

Use this pattern for all converted files:

```
AAOIFI_[Standard-Type][Number]_[Topic-Keywords].md
```

**Examples:**
- `AAOIFI_FAS01_General-Presentation-and-Disclosure.md`
- `AAOIFI_FAS02_Murabaha-and-Murabaha-to-Purchase-Orderer.md`
- `AAOIFI_FAS03_Mudaraba-Financing.md`
- `AAOIFI_FAS21_Investment-in-Shares.md`

**Standard Types:**
- `FAS` = Financial Accounting Standards
- `SS` = Sharia Standards (if you expand scope later)
- `GS` = Governance Standards (if you expand scope later)

## Conversion Methods

### Method 1: Online Conversion Tools (Easiest)

**Recommended Tools:**
1. **Adobe Acrobat Online** (https://www.adobe.com/acrobat/online/pdf-to-word.html)
   - Convert PDF → Word
   - Then Word → Markdown using Pandoc or manual formatting

2. **Zamzar** (https://www.zamzar.com/convert/pdf-to-md/)
   - Direct PDF → Markdown conversion
   - Free for files under 50MB

3. **CloudConvert** (https://cloudconvert.com/pdf-to-md)
   - Direct PDF → Markdown conversion
   - Good quality output

**Steps:**
1. Upload your AAOIFI PDF
2. Select Markdown as output format
3. Download converted file
4. Clean up formatting (see "Post-Conversion Cleanup" below)
5. Rename using naming convention

### Method 2: Python Script (Automated)

I'll create a Python script that converts PDFs to Markdown automatically.

**Requirements:**
- Python 3.9+ (minimum) / Python 3.11+ (recommended)
- Libraries: `pymupdf` (PyMuPDF), `markdown`

**Script location:** `scripts/convert_pdf_to_markdown.py`

**Usage:**
```bash
# Convert single PDF
python scripts/convert_pdf_to_markdown.py --input "path/to/AAOIFI_FAS01.pdf" --output "gemini-gem-prototype/knowledge-base/"

# Convert all PDFs in a folder
python scripts/convert_pdf_to_markdown.py --input-dir "path/to/pdfs/" --output-dir "gemini-gem-prototype/knowledge-base/"
```

### Method 3: Manual Conversion (Highest Quality)

For critical standards or when automated conversion fails:

1. **Copy text from PDF** (Ctrl+A, Ctrl+C in PDF reader)
2. **Paste into text editor** (VS Code, Notepad++)
3. **Add Markdown formatting manually:**
   - Headers: `#`, `##`, `###`
   - Lists: `-` or `1.`
   - Bold: `**text**`
   - Italic: `*text*`
   - Code/quotes: `` `text` `` or `> quote`

## Markdown Structure Template

Each converted AAOIFI standard should follow this structure:

```markdown
# AAOIFI FAS-[Number]: [Full Title]

**Standard Number:** FAS-[Number]  
**Title:** [Full Title]  
**Issued:** [Date]  
**Revised:** [Date if applicable]  
**Effective Date:** [Date]  
**Language:** [English/Arabic/Both]

---

## Table of Contents

1. [Introduction](#introduction)
2. [Objective](#objective)
3. [Scope](#scope)
4. [Definitions](#definitions)
5. [Recognition and Measurement](#recognition-and-measurement)
6. [Presentation and Disclosure](#presentation-and-disclosure)
7. [Effective Date](#effective-date)

---

## 1. Introduction

[Content from PDF]

### 1.1 Background

[Content]

### 1.2 Purpose

[Content]

---

## 2. Objective

[Content from PDF]

---

## 3. Scope

### 3.1 Application

[Content]

### 3.2 Exclusions

[Content]

---

## 4. Definitions

**Term 1:** Definition text here.

**Term 2:** Definition text here.

**Term 3:** Definition text here.

---

## 5. Recognition and Measurement

### 5.1 Recognition Criteria

[Content]

### 5.2 Measurement Principles

[Content]

### 5.3 Specific Provisions

#### 5.3.1 [Subsection Title]

[Content]

#### 5.3.2 [Subsection Title]

[Content]

---

## 6. Presentation and Disclosure

### 6.1 Financial Statement Presentation

[Content]

### 6.2 Disclosure Requirements

[Content]

---

## 7. Effective Date

[Content]

---

## Appendices

### Appendix A: [Title]

[Content]

### Appendix B: [Title]

[Content]

---

**Document Information:**
- **Source:** https://aaoifi.com/accounting-standards-2/?lang=en
- **Converted:** [Date]
- **Format:** Markdown
- **Original Format:** PDF
```

## Post-Conversion Cleanup Checklist

After converting, clean up the Markdown file:

### 1. Fix Headers
- [ ] Ensure proper header hierarchy (`#`, `##`, `###`)
- [ ] Remove duplicate headers
- [ ] Fix header numbering (1.1, 1.2, etc.)

### 2. Fix Lists
- [ ] Convert to proper Markdown lists (`-` or `1.`)
- [ ] Fix indentation for nested lists
- [ ] Remove extra line breaks in lists

### 3. Fix Tables
- [ ] Convert to Markdown table format:
```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
```

### 4. Remove Artifacts
- [ ] Remove page numbers
- [ ] Remove headers/footers
- [ ] Remove "AAOIFI" watermarks
- [ ] Remove extra whitespace
- [ ] Fix broken words (hy-phenation)

### 5. Preserve Structure
- [ ] Keep section numbers (3.1, 3.2, etc.)
- [ ] Preserve cross-references
- [ ] Keep footnotes and citations
- [ ] Maintain definition formatting

### 6. Add Metadata
- [ ] Add document header with standard info
- [ ] Add table of contents
- [ ] Add source URL
- [ ] Add conversion date

### 7. Validate Content
- [ ] Check that all sections are present
- [ ] Verify no content was lost
- [ ] Ensure readability
- [ ] Test that citations are clear

## Quality Check

Before uploading to Gemini Gem, verify:

1. **Completeness:** All sections from PDF are present
2. **Readability:** Text flows naturally, no broken formatting
3. **Structure:** Headers and sections are properly organized
4. **Citations:** Section numbers are preserved (e.g., "Section 4.2.1")
5. **Length:** File is not too large (keep under 100 pages per file)
6. **Naming:** File follows naming convention

## File Organization

Organize converted files in this structure:

```
gemini-gem-prototype/
├── knowledge-base/
│   ├── AAOIFI_FAS01_General-Presentation-and-Disclosure.md
│   ├── AAOIFI_FAS02_Murabaha-and-Murabaha-to-Purchase-Orderer.md
│   ├── AAOIFI_FAS03_Mudaraba-Financing.md
│   ├── AAOIFI_FAS04_Musharaka-Financing.md
│   ├── AAOIFI_FAS21_Investment-in-Shares.md
│   └── [other standards...]
├── system-instructions.md
├── test-questions-template.md
└── README.md
```

## Handling Large Standards (100+ pages)

If a standard is very large, split it at major section boundaries:

**Example: FAS-1 (if it were 150 pages)**
- `AAOIFI_FAS01_Part1_Introduction-and-Definitions.md`
- `AAOIFI_FAS01_Part2_Recognition-and-Measurement.md`
- `AAOIFI_FAS01_Part3_Disclosure-and-Presentation.md`

**Splitting Guidelines:**
- Split at major section boundaries (not mid-section)
- Each part should be 30-80 pages
- Include cross-references between parts
- Add "Part X of Y" to filename

## Language Considerations

### Your Case: Bilingual Standards (English + Arabic)

Since your AAOIFI documents are available in both English and Arabic, you have two options:

#### **Option 1: Separate Files (Recommended)**

Keep English and Arabic versions as separate files:

```
knowledge-base/
├── en/
│   ├── AAOIFI_FAS01_General-Presentation-and-Disclosure.md
│   ├── AAOIFI_FAS02_Murabaha-and-Murabaha-to-Purchase-Orderer.md
│   └── [other standards...]
└── ar/
    ├── AAOIFI_FAS01_العرض-والإفصاح-العام.md
    ├── AAOIFI_FAS02_المرابحة-والمرابحة-للآمر-بالشراء.md
    └── [other standards...]
```

**Advantages:**
- Cleaner file structure
- Easier to manage
- Gemini Gem can select appropriate language version
- Better for large documents

**File Naming:**
- English: `AAOIFI_FAS01_Topic-Keywords.md`
- Arabic: `AAOIFI_FAS01_الموضوع-الكلمات-المفتاحية.md`

#### **Option 2: Combined Files**

Keep both languages in the same file with clear markers:

```markdown
# AAOIFI FAS-1: General Presentation and Disclosure in the Financial Statements of Islamic Banks and Financial Institutions
# معيار المحاسبة المالية رقم 1: العرض والإفصاح العام في القوائم المالية للمصارف والمؤسسات المالية الإسلامية

---

## 1. Introduction / المقدمة

### English Version

[English text content]

### النسخة العربية

[Arabic text content]

---

## 2. Objective / الهدف

### English Version

[English text content]

### النسخة العربية

[Arabic text content]
```

**Advantages:**
- Single file per standard
- Easy to keep versions synchronized
- User sees both languages

**Disadvantages:**
- Larger file sizes
- May confuse retrieval if not structured well

### Recommendation for Your Prototype

**Use Option 1 (Separate Files)** because:
1. Your system instructions specify: "If user asks in English → Use English version"
2. Cleaner separation makes language selection easier
3. Smaller file sizes improve retrieval
4. Easier to test each language independently

### Conversion Workflow for Bilingual Standards

1. **Organize your PDFs:**
   ```
   source-pdfs/
   ├── english/
   │   ├── FAS01_EN.pdf
   │   ├── FAS02_EN.pdf
   │   └── [other standards...]
   └── arabic/
       ├── FAS01_AR.pdf
       ├── FAS02_AR.pdf
       └── [other standards...]
   ```

2. **Convert English versions:**
   ```bash
   python scripts/convert_pdf_to_markdown.py --input-dir "source-pdfs/english/" --output-dir "gemini-gem-prototype/knowledge-base/en/"
   ```

3. **Convert Arabic versions:**
   ```bash
   python scripts/convert_pdf_to_markdown.py --input-dir "source-pdfs/arabic/" --output-dir "gemini-gem-prototype/knowledge-base/ar/"
   ```

4. **Upload both to Gemini Gem:**
   - Upload all files from `knowledge-base/en/`
   - Upload all files from `knowledge-base/ar/`
   - Gemini will use the appropriate version based on query language

### Testing Both Languages

Add bilingual test questions to your test template:

**English Question:**
```
I want to invest in a company that earns 3% of its revenue from interest. Is this permissible?
```

**Arabic Question:**
```
أريد الاستثمار في شركة تحصل على 3٪ من إيراداتها من الفوائد. هل هذا جائز؟
```

Both should cite the same AAOIFI standard but in the appropriate language.

## Common Conversion Issues and Fixes

### Issue 1: Broken Tables
**Problem:** Tables don't convert properly  
**Fix:** Manually recreate as Markdown tables or use HTML tables

### Issue 2: Lost Formatting
**Problem:** Bold, italic, or special formatting is lost  
**Fix:** Manually add Markdown formatting (`**bold**`, `*italic*`)

### Issue 3: Garbled Text
**Problem:** Text is unreadable after conversion  
**Fix:** Use OCR tool (Adobe Acrobat, Tesseract) or manual retyping

### Issue 4: Missing Sections
**Problem:** Some pages didn't convert  
**Fix:** Compare with original PDF and add missing content manually

### Issue 5: Broken Cross-References
**Problem:** "See Section 3.2" links don't work  
**Fix:** Keep as plain text; Gemini Gem will understand contextually

## Next Steps After Conversion

1. **Upload to Gemini Gem:**
   - Go to https://gemini.google.com/gems/create
   - Upload all converted Markdown files
   - Add system instructions

2. **Test with Questions:**
   - Use test-questions-template.md
   - Verify Gem can cite specific sections
   - Check for hallucinations

3. **Iterate:**
   - If Gem struggles with certain standards, improve their formatting
   - If citations are unclear, add more structure
   - If retrieval fails, consider splitting large files

## Automation Script Coming Next

I'll create the Python conversion script in the next step. This will automate the PDF → Markdown conversion process.
