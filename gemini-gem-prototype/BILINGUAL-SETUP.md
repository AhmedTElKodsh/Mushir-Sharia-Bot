# Bilingual Setup Guide (English + Arabic)

## Overview

Your AAOIFI documents are available in both English and Arabic. This guide explains how to set up your Gemini Gem to handle both languages effectively.

## Language Matching Strategy

**User Query Language → AAOIFI Standard Language**

- User asks in **English** → Gem uses **English** version of standards
- User asks in **Arabic** → Gem uses **Arabic** version of standards

This is already configured in your `system-instructions.md`.

## File Organization

### Recommended Structure: Separate Language Folders

```
gemini-gem-prototype/
└── knowledge-base/
    ├── en/                                    # English standards
    │   ├── AAOIFI_FAS01_General-Presentation.md
    │   ├── AAOIFI_FAS02_Murabaha.md
    │   ├── AAOIFI_FAS03_Mudaraba.md
    │   └── [other standards...]
    └── ar/                                    # Arabic standards
        ├── AAOIFI_FAS01_العرض-العام.md
        ├── AAOIFI_FAS02_المرابحة.md
        ├── AAOIFI_FAS03_المضاربة.md
        └── [other standards...]
```

### Why Separate Folders?

✅ **Cleaner organization** - Easy to manage  
✅ **Better retrieval** - Gem selects appropriate language  
✅ **Smaller files** - Faster processing  
✅ **Independent testing** - Test each language separately  
✅ **Easier updates** - Update one language without affecting the other  

## Setup Steps

### Step 1: Organize Your Source PDFs

Create two folders for your source PDFs:

```
source-pdfs/
├── english/
│   ├── FAS01_EN.pdf
│   ├── FAS02_EN.pdf
│   ├── FAS03_EN.pdf
│   └── [other standards...]
└── arabic/
    ├── FAS01_AR.pdf
    ├── FAS02_AR.pdf
    ├── FAS03_AR.pdf
    └── [other standards...]
```

### Step 2: Create Language Directories

```bash
# Create English directory
mkdir gemini-gem-prototype\knowledge-base\en

# Create Arabic directory
mkdir gemini-gem-prototype\knowledge-base\ar
```

### Step 3: Convert English Standards

```bash
# Install dependencies (if not already done)
pip install -r gemini-gem-prototype/requirements.txt

# Convert English PDFs
python scripts/convert_pdf_to_markdown.py --input-dir "source-pdfs/english/" --output-dir "gemini-gem-prototype/knowledge-base/en/"
```

**Expected output:**
```
gemini-gem-prototype/knowledge-base/en/
├── AAOIFI_FAS01_General-Presentation-and-Disclosure.md
├── AAOIFI_FAS02_Murabaha-and-Murabaha-to-Purchase-Orderer.md
├── AAOIFI_FAS03_Mudaraba-Financing.md
└── [other standards...]
```

### Step 4: Convert Arabic Standards

```bash
# Convert Arabic PDFs
python scripts/convert_pdf_to_markdown.py --input-dir "source-pdfs/arabic/" --output-dir "gemini-gem-prototype/knowledge-base/ar/"
```

**Expected output:**
```
gemini-gem-prototype/knowledge-base/ar/
├── AAOIFI_FAS01_[Arabic-title].md
├── AAOIFI_FAS02_[Arabic-title].md
├── AAOIFI_FAS03_[Arabic-title].md
└── [other standards...]
```

**Note:** Arabic filenames can use Arabic characters or transliteration:
- Option A: `AAOIFI_FAS01_العرض-والإفصاح-العام.md`
- Option B: `AAOIFI_FAS01_Al-Ard-wal-Ifsah-al-Aam.md`

Choose what works best for your system.

### Step 5: Verify Conversions

**Check English files:**
- [ ] All section numbers preserved (3.1, 3.2, etc.)
- [ ] Text is readable
- [ ] No garbled characters
- [ ] File names follow convention

**Check Arabic files:**
- [ ] Arabic text displays correctly (not reversed or broken)
- [ ] Section numbers preserved (٣.١، ٣.٢ or 3.1, 3.2)
- [ ] Text is readable
- [ ] File names are valid

### Step 6: Upload to Gemini Gem

1. **Go to:** https://gemini.google.com/gems/create

2. **Add system instructions:**
   - Copy from `system-instructions.md`
   - Paste into "Instructions" field

3. **Upload English standards:**
   - Click "Add files"
   - Select all files from `knowledge-base/en/`
   - Wait for upload to complete

4. **Upload Arabic standards:**
   - Click "Add files" again
   - Select all files from `knowledge-base/ar/`
   - Wait for upload to complete

5. **Verify uploads:**
   - Check that both English and Arabic files appear in the knowledge base
   - Total files should be: (# of standards) × 2

6. **Save your Gem**

## Testing Bilingual Functionality

### Test 1: English Query

**Query:**
```
I want to invest in a company that earns 3% of its revenue from interest. Is this permissible?
```

**Expected:**
- Response in English
- Cites English version of AAOIFI FAS-21
- Example: "[AAOIFI FAS-21, Section 4.2.1]"

### Test 2: Arabic Query

**Query:**
```
أريد الاستثمار في شركة تحصل على 3٪ من إيراداتها من الفوائد. هل هذا جائز؟
```

**Expected:**
- Response in Arabic
- Cites Arabic version of AAOIFI FAS-21
- Example: "[معيار المحاسبة المالية رقم 21، القسم 4.2.1]"

### Test 3: Language Switching

**First query (English):**
```
What is Murabaha?
```

**Second query (Arabic):**
```
ما هي المرابحة؟
```

**Expected:**
- First response in English from English standards
- Second response in Arabic from Arabic standards
- Both should provide equivalent information

## File Naming Conventions

### English Files

Pattern: `AAOIFI_FAS[Number]_[Topic-Keywords].md`

Examples:
- `AAOIFI_FAS01_General-Presentation-and-Disclosure.md`
- `AAOIFI_FAS02_Murabaha-and-Murabaha-to-Purchase-Orderer.md`
- `AAOIFI_FAS21_Investment-in-Shares.md`

### Arabic Files

**Option A: Arabic Characters (Recommended if your system supports it)**

Pattern: `AAOIFI_FAS[Number]_[الموضوع-الكلمات-المفتاحية].md`

Examples:
- `AAOIFI_FAS01_العرض-والإفصاح-العام.md`
- `AAOIFI_FAS02_المرابحة-والمرابحة-للآمر-بالشراء.md`
- `AAOIFI_FAS21_الاستثمار-في-الأسهم.md`

**Option B: Transliteration (If Arabic filenames cause issues)**

Pattern: `AAOIFI_FAS[Number]_[Transliterated-Topic].md`

Examples:
- `AAOIFI_FAS01_Al-Ard-wal-Ifsah-al-Aam.md`
- `AAOIFI_FAS02_Al-Murabaha.md`
- `AAOIFI_FAS21_Al-Istithmar-fil-Ashum.md`

## Markdown Structure for Arabic Files

Arabic Markdown files should follow the same structure as English, but with Arabic content:

```markdown
# معيار المحاسبة المالية رقم 1: العرض والإفصاح العام في القوائم المالية

**رقم المعيار:** FAS-1  
**العنوان:** العرض والإفصاح العام في القوائم المالية للمصارف والمؤسسات المالية الإسلامية  
**المصدر:** https://aaoifi.com/accounting-standards-2/?lang=ar  
**تاريخ التحويل:** 2026-05-07  
**الصيغة:** Markdown (محول من PDF)

---

## جدول المحتويات

1. [المقدمة](#المقدمة)
2. [الهدف](#الهدف)
3. [النطاق](#النطاق)
4. [التعريفات](#التعريفات)

---

## 1. المقدمة

[المحتوى العربي هنا]

### 1.1 الخلفية

[المحتوى]

---

## 2. الهدف

[المحتوى العربي هنا]

---
```

## Common Issues and Solutions

### Issue 1: Arabic Text Appears Reversed or Broken

**Problem:** Arabic text displays incorrectly after conversion

**Solutions:**
1. Ensure your text editor supports RTL (right-to-left) text
2. Use UTF-8 encoding when saving files
3. Try a different PDF conversion tool
4. Manually copy-paste text from PDF and format in Markdown

### Issue 2: Gem Responds in Wrong Language

**Problem:** User asks in Arabic but Gem responds in English

**Solutions:**
1. Verify Arabic files were uploaded successfully
2. Check that Arabic text in files is readable
3. Test with a simple Arabic query first
4. Review system instructions to ensure language matching is clear

### Issue 3: Mixed Language Responses

**Problem:** Gem mixes English and Arabic in responses

**Solutions:**
1. Strengthen language matching instruction in system prompt
2. Add explicit examples of language-specific responses
3. Ensure file organization clearly separates languages

### Issue 4: Arabic Filenames Don't Work

**Problem:** System doesn't accept Arabic characters in filenames

**Solutions:**
1. Use transliteration instead (Option B above)
2. Use English filenames with language prefix: `AAOIFI_FAS01_AR_General.md`
3. Keep Arabic content but use English filenames

## Quality Checks

Before finalizing your setup:

### English Standards
- [ ] All files converted successfully
- [ ] Section numbers preserved
- [ ] Text is readable
- [ ] Citations are clear
- [ ] File names follow convention

### Arabic Standards
- [ ] All files converted successfully
- [ ] Arabic text displays correctly
- [ ] Section numbers preserved (Arabic or English numerals)
- [ ] Text is readable (RTL display works)
- [ ] Citations are clear
- [ ] File names are valid

### Gemini Gem
- [ ] Both language sets uploaded
- [ ] System instructions include language matching
- [ ] Test queries work in both languages
- [ ] Citations appear in correct language
- [ ] No mixed-language responses

## Testing Checklist

Use this checklist to verify bilingual functionality:

### English Tests
- [ ] Simple question in English → English response
- [ ] Complex question in English → English response with citations
- [ ] Clarification needed → Clarifying questions in English
- [ ] Out of scope → Limitation message in English

### Arabic Tests
- [ ] Simple question in Arabic → Arabic response
- [ ] Complex question in Arabic → Arabic response with citations
- [ ] Clarification needed → Clarifying questions in Arabic
- [ ] Out of scope → Limitation message in Arabic

### Cross-Language Tests
- [ ] Switch from English to Arabic mid-conversation
- [ ] Switch from Arabic to English mid-conversation
- [ ] Same question in both languages → Equivalent answers

## Maintenance

### Updating Standards

When AAOIFI releases updated standards:

1. **Download both versions** (English and Arabic)
2. **Convert both versions** to Markdown
3. **Replace old files** in respective folders
4. **Re-upload to Gem**
5. **Test in both languages**

### Adding New Standards

When adding new standards:

1. **Ensure you have both language versions**
2. **Convert both to Markdown**
3. **Add to appropriate folders** (en/ and ar/)
4. **Upload both to Gem**
5. **Update test questions** to include new standard

## Best Practices

✅ **Always maintain both languages** - Don't let one lag behind  
✅ **Test both languages equally** - Ensure parity in quality  
✅ **Use consistent naming** - Makes management easier  
✅ **Keep folder structure clean** - Separate languages clearly  
✅ **Document language-specific issues** - Track what works and what doesn't  
✅ **Version control both sets** - Keep them synchronized  

## Summary

**File Structure:**
```
knowledge-base/
├── en/  (English AAOIFI standards)
└── ar/  (Arabic AAOIFI standards)
```

**Language Matching:**
- English query → English standards
- Arabic query → Arabic standards

**Testing:**
- Test both languages independently
- Test language switching
- Verify citation accuracy in both languages

**Success Criteria:**
- Both languages work equally well
- No mixed-language responses
- Citations appear in correct language
- Equivalent accuracy in both languages

---

**Created:** 2026-05-07  
**Purpose:** Guide for setting up bilingual Gemini Gem prototype  
**Languages:** English + Arabic
