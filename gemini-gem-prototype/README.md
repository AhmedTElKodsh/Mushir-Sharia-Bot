# Gemini Gem Prototype - Sharia Compliance Advisor

## Overview

This is a **prototype** of the Sharia Compliance Chatbot using Google's Gemini Gem platform. The purpose is to validate the approach before building the full RAG pipeline with vector databases and chunking.

**Goal:** Test if a simple Gemini Gem with AAOIFI standards can provide accurate, cited compliance rulings.

**Success Metric:** 5 out of 10 test questions should receive accurate answers with proper AAOIFI citations.

## What is Gemini Gem?

Gemini Gem is Google's custom AI assistant platform (similar to OpenAI's Custom GPTs). You can:
- Upload knowledge base files (PDFs, Markdown, text)
- Provide custom instructions (system prompt)
- Share with others via link
- Test quickly without coding

**Access:** https://gemini.google.com/gems/create

## Directory Structure

```
gemini-gem-prototype/
├── README.md                          # This file
├── system-instructions.md             # Instructions for Gemini Gem
├── test-questions-template.md         # Test questions with evaluation criteria
├── pdf-conversion-guide.md            # Guide for converting PDFs to Markdown
└── knowledge-base/                    # Converted AAOIFI standards (Markdown)
    ├── AAOIFI_FAS01_[Topic].md
    ├── AAOIFI_FAS02_[Topic].md
    └── [other standards...]
```

## Important: Bilingual Support (English + Arabic)

Your AAOIFI documents are available in both English and Arabic. The system is configured to:
- Respond in **English** when user asks in English (using English standards)
- Respond in **Arabic** when user asks in Arabic (using Arabic standards)

**📖 See detailed bilingual setup guide:** `BILINGUAL-SETUP.md`

## Setup Steps

### Step 1: Prepare AAOIFI Standards

You need to convert your AAOIFI PDF standards to Markdown format for **both languages**.

**Option A: Use the AAOIFI Converter Script (Recommended - Automated)**

```bash
# Install dependencies
pip install PyPDF2

# Place your PDFs in data/raw/aaoifi_standards/ with naming: Standard_{number}_{AR|EN}.pdf
# Example: Standard_01_EN.pdf, Standard_01_AR.pdf, Standard_02_EN.pdf, etc.

# Run the converter (automatically processes all Standard_*.pdf files)
python scripts/convert_aaoifi_to_markdown.py
```

**This script automatically:**
- Detects standard number and language from filename
- Extracts title from first page
- Generates comprehensive Sharia compliance metadata
- Links bilingual document pairs (Arabic ↔ English)
- Creates an INDEX.md file with organized standards list
- Outputs to `gemini-gem-prototype/knowledge-base/`

**Input filename format:** `Standard_{number}_{AR|EN}.pdf`
- `Standard_01_EN.pdf` → English version of Standard 1
- `Standard_01_AR.pdf` → Arabic version of Standard 1

**Option B: Use the Generic PDF Converter**

```bash
# Install dependencies
pip install pymupdf

# Convert English PDFs
python scripts/convert_pdf_to_markdown.py --input-dir "path/to/english-pdfs/" --output-dir "knowledge-base/en/"

# Convert Arabic PDFs
python scripts/convert_pdf_to_markdown.py --input-dir "path/to/arabic-pdfs/" --output-dir "knowledge-base/ar/"
```

**Recommended folder structure:**
```
knowledge-base/
├── en/  (English standards)
└── ar/  (Arabic standards)
```

**Option B: Use the Generic PDF Converter**

```bash
# Install dependencies
pip install pymupdf

# Convert English PDFs
python scripts/convert_pdf_to_markdown.py --input-dir "path/to/english-pdfs/" --output-dir "knowledge-base/en/"

# Convert Arabic PDFs
python scripts/convert_pdf_to_markdown.py --input-dir "path/to/arabic-pdfs/" --output-dir "knowledge-base/ar/"
```

**Recommended folder structure:**
```
knowledge-base/
├── en/  (English standards)
└── ar/  (Arabic standards)
```

**Option C: Use Online Tools (Manual)**

1. Go to https://cloudconvert.com/pdf-to-md
2. Upload your AAOIFI PDF
3. Download the Markdown file
4. Clean up formatting (see `pdf-conversion-guide.md`)
5. Rename following convention: `AAOIFI_FAS01_Topic-Keywords.md`
6. Save to `knowledge-base/` folder

**Option D: Manual Conversion**

See detailed instructions in `pdf-conversion-guide.md`

### Step 2: Create Your Gemini Gem

1. **Go to Gemini Gems:** https://gemini.google.com/gems/create

2. **Name Your Gem:**
   - Name: "Sharia Compliance Advisor"
   - Description: "Analyzes financial operations against AAOIFI standards"

3. **Add Instructions:**
   - Copy the entire content from `system-instructions.md`
   - Paste into the "Instructions" field

4. **Upload Knowledge Base:**
   - Click "Add files" or "Upload knowledge"
   - Upload all Markdown files from `knowledge-base/` folder
   - Wait for processing to complete

5. **Configure Settings:**
   - Model: Gemini 1.5 Pro (recommended for accuracy)
   - Temperature: Low (for consistency)

6. **Save Your Gem**

### Step 3: Test Your Gem

1. **Open the test questions template:**
   - File: `test-questions-template.md`
   - Contains 10+ pre-written test questions

2. **Test each question:**
   - Copy a question from the template
   - Paste into your Gem's chat
   - Evaluate the response using the criteria in the template
   - Record results in the template

3. **Evaluate success:**
   - Target: 5/10 questions with accurate, cited answers
   - Track: Citation quality, clarification questions, hallucinations

### Step 4: Iterate and Improve

Based on test results:

**If Gem performs well (5+ accurate answers):**
- Document what worked
- Identify which standards are most useful
- Note optimal file structure
- Use learnings for full RAG system design

**If Gem struggles (<5 accurate answers):**
- Check if standards are properly formatted
- Verify citations are clear in source files
- Improve system instructions
- Consider splitting large files
- Add more structure to Markdown files

## Key Files Explained

### 1. system-instructions.md

This is the "system prompt" for your Gemini Gem. It tells the Gem:
- Its role (Sharia Compliance Advisor)
- How to cite AAOIFI standards
- When to ask clarifying questions
- How to structure responses
- What to do when uncertain

**You can customize this** based on your needs.

### 2. test-questions-template.md

Pre-written test questions organized by category:
- Investment screening (stocks, REITs)
- Financing and loans (Murabaha, conventional loans)
- Business transactions (partnerships, contracts)
- Edge cases (out of scope, ambiguous queries)

Each question includes:
- Expected behavior
- Evaluation criteria
- Space to record results

### 3. pdf-conversion-guide.md

Comprehensive guide for converting AAOIFI PDFs to Markdown:
- Three conversion methods (online tools, Python script, manual)
- File naming conventions
- Markdown structure template
- Post-conversion cleanup checklist
- Quality checks

### 4. knowledge-base/ folder

This is where you store your converted AAOIFI standards in Markdown format.

**File naming convention:**
```
AAOIFI_[Standard-Type][Number]_[Topic-Keywords].md
```

**Examples:**
- `AAOIFI_FAS01_General-Presentation-and-Disclosure.md`
- `AAOIFI_FAS02_Murabaha-and-Murabaha-to-Purchase-Orderer.md`
- `AAOIFI_FAS21_Investment-in-Shares.md`

## Testing Workflow

```
1. Prepare Standards
   ↓
2. Create Gem
   ↓
3. Upload Standards
   ↓
4. Test with Questions
   ↓
5. Evaluate Results
   ↓
6. Iterate (improve instructions/formatting)
   ↓
7. Document Learnings
   ↓
8. Use insights for full RAG system
```

## Success Criteria

Your prototype is successful if:

✅ **Accuracy:** 5+ out of 10 questions get accurate answers  
✅ **Citations:** Gem cites specific AAOIFI standard numbers and sections  
✅ **Clarification:** Gem asks questions when information is missing  
✅ **Honesty:** Gem admits when it can't find relevant standards  
✅ **No Hallucination:** Gem doesn't fabricate standards or citations

## Common Issues and Solutions

### Issue: Gem doesn't cite specific sections

**Solution:**
- Ensure your Markdown files have clear section numbers (3.1, 3.2, etc.)
- Add more structure to headers
- Emphasize citation requirements in system instructions

### Issue: Gem hallucinates standards

**Solution:**
- Strengthen the "never fabricate" instruction
- Add examples of proper citations
- Test with questions about non-existent standards (FAS-99)

### Issue: Gem doesn't ask clarifying questions

**Solution:**
- Add more examples of clarification in system instructions
- Test with intentionally vague questions
- Emphasize the importance of gathering complete information

### Issue: Gem is too verbose

**Solution:**
- Add "be concise" to system instructions
- Provide examples of ideal response length
- Adjust temperature setting (lower = more focused)

### Issue: Gem can't find relevant standards

**Solution:**
- Check if the standard is actually in your knowledge base
- Verify file was uploaded successfully
- Improve file formatting and structure
- Add more keywords to section headers

## What to Learn from This Prototype

Document these insights for the full RAG system:

### 1. Retrieval Patterns
- Which standards get used most frequently?
- What types of queries work well?
- What types of queries fail?

### 2. Chunk Size
- Are full standards too large?
- Would smaller sections work better?
- What's the optimal chunk size?

### 3. Metadata Needs
- What metadata would improve retrieval?
- How should standards be tagged?
- What filters would be useful?

### 4. Citation Quality
- How should citations be formatted?
- What level of detail is needed?
- How to ensure accuracy?

### 5. Clarification Loop
- What information is commonly missing?
- What clarifying questions work best?
- How many rounds of clarification are typical?

### 6. Edge Cases
- What questions are out of scope?
- How to handle ambiguous queries?
- When to admit uncertainty?

## Next Steps After Prototype

Once you've tested and learned from the prototype:

1. **Document findings** in test-questions-template.md
2. **Analyze patterns** (what worked, what didn't)
3. **Design RAG architecture** based on learnings
4. **Implement chunking strategy** informed by optimal chunk size
5. **Build metadata schema** based on retrieval patterns
6. **Develop clarification engine** using successful question patterns
7. **Create full system** following the spec in `.kiro/specs/`

## Resources

- **Gemini Gems:** https://gemini.google.com/gems/create
- **AAOIFI Standards:** https://aaoifi.com/accounting-standards-2/?lang=en
- **Markdown Guide:** https://www.markdownguide.org/
- **PDF to Markdown:** https://cloudconvert.com/pdf-to-md

## Questions?

If you encounter issues:
1. Check the `pdf-conversion-guide.md` for conversion problems
2. Review `system-instructions.md` for prompt improvements
3. Consult `test-questions-template.md` for evaluation criteria
4. Refer to main project specs in `.kiro/specs/sharia-compliance-chatbot/`

## Important Notes

⚠️ **This is a prototype** - Not production-ready  
⚠️ **Limited by Gemini Gem capabilities** - No custom retrieval logic  
⚠️ **Purpose is validation** - Test approach before full build  
⚠️ **Document everything** - Learnings inform full system design

---

**Created:** 2026-05-07  
**Project:** Sharia Compliance Chatbot  
**Phase:** MVP Validation (Pre-RAG)
