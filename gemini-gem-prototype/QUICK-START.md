# Quick Start Guide - Gemini Gem Prototype

## 🎯 Goal
Test if AAOIFI standards + Gemini Gem can provide accurate Sharia compliance rulings **before** building the full RAG system.

## ⏱️ Time Estimate
- Setup: 1-2 hours
- Testing: 2-3 hours
- Total: 3-5 hours

## ✅ Prerequisites

Before you start, you need:

- [ ] AAOIFI standard PDFs (from https://aaoifi.com/accounting-standards-2/?lang=en)
- [ ] Google account (for Gemini Gems)
- [ ] Python 3.9+ installed (3.11+ recommended for better performance) (for PDF conversion script)
- [ ] 10-15 real test questions prepared

## 📋 Step-by-Step Checklist

### Phase 1: Prepare Your Standards (1-2 hours)

- [ ] **1.1** Collect AAOIFI PDF files
  - Download from AAOIFI website
  - Focus on most relevant standards first (FAS-1, FAS-2, FAS-21, etc.)
  - Aim for at least 5-10 standards

- [ ] **1.2** Install Python dependencies
  ```bash
  cd gemini-gem-prototype
  pip install -r requirements.txt
  ```

- [ ] **1.3** Convert PDFs to Markdown
  
  **Option A - Automated (Recommended):**
  ```bash
  # Convert all PDFs in a folder
  python ../scripts/convert_pdf_to_markdown.py --input-dir "path/to/pdfs/" --output-dir "knowledge-base/"
  ```
  
  **Option B - Online Tool:**
  - Go to https://cloudconvert.com/pdf-to-md
  - Upload PDF, download Markdown
  - Save to `knowledge-base/` folder
  
  **Option C - Manual:**
  - See `pdf-conversion-guide.md` for detailed instructions

- [ ] **1.4** Verify converted files
  - Check files are in `knowledge-base/` folder
  - Verify section numbers are preserved (3.1, 3.2, etc.)
  - Ensure text is readable (no garbled characters)
  - Confirm file names follow convention: `AAOIFI_FAS01_Topic.md`

### Phase 2: Create Your Gemini Gem (30 minutes)

- [ ] **2.1** Go to https://gemini.google.com/gems/create

- [ ] **2.2** Configure basic settings
  - **Name:** Sharia Compliance Advisor
  - **Description:** Analyzes financial operations against AAOIFI standards
  - **Model:** Gemini 1.5 Pro (recommended)

- [ ] **2.3** Add system instructions
  - Open `system-instructions.md`
  - Copy entire content
  - Paste into Gem's "Instructions" field

- [ ] **2.4** Upload knowledge base
  - Click "Add files" or "Upload knowledge"
  - Select all files from `knowledge-base/` folder
  - Wait for upload to complete (may take a few minutes)
  - Verify all files show as uploaded

- [ ] **2.5** Save your Gem
  - Click "Create" or "Save"
  - Note the Gem URL for future access

### Phase 3: Prepare Test Questions (30 minutes)

- [ ] **3.1** Open `test-questions-template.md`

- [ ] **3.2** Review pre-written questions
  - 10+ questions across 4 categories
  - Investment screening
  - Financing and loans
  - Business transactions
  - Edge cases

- [ ] **3.3** Add your own questions (optional)
  - Think of real user scenarios
  - Add to "Custom Questions" section
  - Define expected behavior for each

- [ ] **3.4** Prioritize questions
  - Mark which 10 questions to test first
  - Start with most common/important scenarios

### Phase 4: Test Your Gem (2-3 hours)

- [ ] **4.1** Test Question 1
  - Copy question from template
  - Paste into Gem chat
  - Evaluate response using criteria
  - Record results in template
  - Note: citations, clarifications, accuracy

- [ ] **4.2** Test Question 2
  - Repeat process
  - Compare with expected behavior

- [ ] **4.3** Test Questions 3-10
  - Continue testing all priority questions
  - Take notes on patterns (what works, what doesn't)

- [ ] **4.4** Test edge cases
  - Try questions outside scope
  - Test with non-existent standards (FAS-99)
  - Check for hallucinations

### Phase 5: Evaluate Results (30 minutes)

- [ ] **5.1** Calculate success rate
  - Count accurate answers with proper citations
  - Target: 5+ out of 10
  - Record in test template

- [ ] **5.2** Analyze patterns
  - Which standards were used most?
  - Which standards were never retrieved?
  - What types of questions worked well?
  - What types of questions failed?

- [ ] **5.3** Document findings
  - Fill out "Testing Summary" section in template
  - Note "What Worked Well"
  - Note "What Needs Improvement"
  - List "Next Steps"

- [ ] **5.4** Identify learnings for RAG system
  - Optimal chunk size insights
  - Metadata needs
  - Citation format preferences
  - Clarification patterns

### Phase 6: Iterate (if needed)

If success rate < 50%:

- [ ] **6.1** Improve system instructions
  - Add more examples
  - Clarify citation requirements
  - Strengthen anti-hallucination rules

- [ ] **6.2** Improve file formatting
  - Add more structure to Markdown files
  - Enhance section headers
  - Add table of contents

- [ ] **6.3** Re-test
  - Test same questions again
  - Compare results
  - Document improvements

## 🎉 Success Criteria

Your prototype is ready when:

✅ 5+ out of 10 questions get accurate answers  
✅ Gem cites specific AAOIFI standards (FAS-X, Section Y.Z)  
✅ Gem asks clarifying questions when needed  
✅ Gem admits when it can't find relevant standards  
✅ No hallucinations or fabricated citations  

## 📊 What to Measure

Track these metrics:

| Metric | Target | Actual |
|--------|--------|--------|
| Accurate answers | 5/10 (50%) | ___ |
| Proper citations | 8/10 (80%) | ___ |
| Clarifying questions asked | 3/10 (30%) | ___ |
| Admitted limitations | 2/10 (20%) | ___ |
| Hallucinations | 0/10 (0%) | ___ |

## 🚀 After Success

Once you hit success criteria:

1. **Document everything** in test template
2. **Share findings** with team
3. **Design RAG architecture** based on learnings
4. **Start full system build** using insights

## ⚠️ Common Pitfalls

**Pitfall 1:** PDFs don't convert cleanly
- **Solution:** Use manual conversion for critical standards

**Pitfall 2:** Gem doesn't cite sections
- **Solution:** Ensure section numbers are clear in Markdown files

**Pitfall 3:** Gem hallucinates
- **Solution:** Strengthen system instructions, test with fake standards

**Pitfall 4:** Files too large
- **Solution:** Split large standards into multiple files

**Pitfall 5:** Gem too slow
- **Solution:** Reduce number of uploaded files, focus on most relevant

## 📞 Need Help?

**Issue with PDF conversion?**
→ See `pdf-conversion-guide.md`

**Issue with system instructions?**
→ See `system-instructions.md`

**Issue with test questions?**
→ See `test-questions-template.md`

**Issue with overall approach?**
→ See main specs in `.kiro/specs/sharia-compliance-chatbot/`

## 🎯 Remember

This is a **prototype** to validate the approach. Don't aim for perfection—aim for learning!

**Key questions to answer:**
1. Can Gemini Gem retrieve relevant AAOIFI standards?
2. Can it cite them accurately?
3. Can it ask clarifying questions?
4. What's the optimal file structure?
5. What metadata would help?

Use these answers to design the full RAG system!

---

**Estimated Time:** 3-5 hours  
**Success Target:** 50% accuracy (5/10 questions)  
**Next Step:** Build full RAG system with learnings
