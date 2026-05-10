# Bilingual Setup - Quick Reference

## ✅ Your Configuration

**AAOIFI Documents:** Available in both English and Arabic

**Language Matching Strategy:**
- User asks in **English** → Gem responds in **English** using English standards
- User asks in **Arabic** → Gem responds in **Arabic** using Arabic standards

## 📁 Folder Structure

```
gemini-gem-prototype/
└── knowledge-base/
    ├── en/                           # English AAOIFI standards
    │   ├── AAOIFI_FAS01_General-Presentation.md
    │   ├── AAOIFI_FAS02_Murabaha.md
    │   └── [other standards...]
    └── ar/                           # Arabic AAOIFI standards
        ├── AAOIFI_FAS01_العرض-العام.md
        ├── AAOIFI_FAS02_المرابحة.md
        └── [other standards...]
```

## 🚀 Quick Setup

### 1. Organize Source PDFs

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

### 2. Convert to Markdown

```bash
# English
python scripts/convert_pdf_to_markdown.py --input-dir "source-pdfs/english/" --output-dir "gemini-gem-prototype/knowledge-base/en/"

# Arabic
python scripts/convert_pdf_to_markdown.py --input-dir "source-pdfs/arabic/" --output-dir "gemini-gem-prototype/knowledge-base/ar/"
```

### 3. Upload to Gemini Gem

1. Go to https://gemini.google.com/gems/create
2. Add system instructions from `system-instructions.md`
3. Upload all files from `knowledge-base/en/`
4. Upload all files from `knowledge-base/ar/`
5. Save your Gem

## 🧪 Test Both Languages

### English Test
```
I want to invest in a company that earns 3% of its revenue from interest. Is this permissible?
```
**Expected:** English response with English AAOIFI citations

### Arabic Test
```
أريد الاستثمار في شركة تحصل على 3٪ من إيراداتها من الفوائد. هل هذا جائز؟
```
**Expected:** Arabic response with Arabic AAOIFI citations

## 📚 Documentation

- **Detailed setup:** `BILINGUAL-SETUP.md`
- **System instructions:** `system-instructions.md` (already configured for bilingual)
- **Test questions:** `test-questions-template.md` (includes Arabic test)
- **Conversion guide:** `pdf-conversion-guide.md` (includes bilingual section)

## ✅ What's Already Configured

✓ System instructions include language matching  
✓ Test template includes Arabic test question  
✓ Conversion guide explains bilingual setup  
✓ Folder structure supports both languages  

## 🎯 Success Criteria

Both languages should achieve:
- 5/10 questions accurate
- Proper citations in correct language
- Clarifying questions in correct language
- No mixed-language responses

---

**For full details, see:** `BILINGUAL-SETUP.md`
