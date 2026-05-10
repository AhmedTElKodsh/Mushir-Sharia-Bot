# Test Questions Summary

## Overview

The test questions template now includes **20 comprehensive test questions** to validate your Gemini Gem prototype:

- **10 Core Questions** (Categories 1-4)
- **5 Custom English Questions**
- **5 Custom Arabic Questions**

## Question Breakdown

### Core Questions (10 Questions)

#### Category 1: Investment Screening (3 questions)
1. **Mixed Revenue Company** - 95% halal, 5% interest income
2. **Alcohol Producer** - Mixed halal/haram products
3. **REIT Investment** - Real estate investment trust

#### Category 2: Financing and Loans (3 questions)
4. **Conventional Car Loan** - Interest-based loan
5. **Murabaha Contract** - Islamic financing structure
6. **Credit Card Usage** - Paying before interest applies

#### Category 3: Business Transactions (2 questions)
7. **Partnership Structure** - Profit/loss distribution
8. **Late Payment Penalty** - Credit sales penalties

#### Category 4: Edge Cases (2 questions)
9. **Outside Scope - Zakat** - Testing scope recognition
10. **Ambiguous Query - Cryptocurrency** - Testing clarification
11. **Non-existent Standard** - Testing hallucination prevention

### Custom English Questions (5 Questions)

**EN-1: Islamic Insurance (Takaful)**
- Topic: Takaful vs conventional insurance
- Tests: Understanding of Takaful principles, AAOIFI citation

**EN-2: Sukuk Investment**
- Topic: Islamic bonds verification
- Tests: Sukuk structure knowledge, due diligence guidance

**EN-3: Profit Distribution in Partnership**
- Topic: Loss distribution in Musharaka
- Tests: Partnership rules, AAOIFI FAS-4 citation

**EN-4: Foreign Currency Trading (Forex)**
- Topic: Permissibility of currency trading
- Tests: Spot vs forward trading, speculation rules

**EN-5: Lease-to-Own (Ijara Muntahia Bittamleek)**
- Topic: Islamic lease-to-own structure
- Tests: Ijara conditions, identifying red flags

### Custom Arabic Questions (5 Questions)

**AR-1: التأمين الإسلامي (التكافل)**
- Arabic equivalent of EN-1
- Tests: Arabic language response, Arabic AAOIFI citation

**AR-2: الاستثمار في الصكوك**
- Arabic equivalent of EN-2
- Tests: Arabic language handling, content parity

**AR-3: توزيع الأرباح في الشراكة**
- Arabic equivalent of EN-3
- Tests: Arabic technical terminology, ruling consistency

**AR-4: تداول العملات الأجنبية (الفوركس)**
- Arabic equivalent of EN-4
- Tests: Arabic clarification questions, language matching

**AR-5: الإيجار المنتهي بالتمليك**
- Arabic equivalent of EN-5
- Tests: Arabic citation format, bilingual consistency

## Testing Strategy

### Phase 1: Core Questions (10 questions)
Test fundamental capabilities:
- Citation accuracy
- Clarification loop
- Scope recognition
- Hallucination prevention

**Target:** 5/10 accurate (50%)

### Phase 2: English Custom Questions (5 questions)
Test domain-specific knowledge:
- Takaful, Sukuk, Musharaka, Forex, Ijara
- More complex scenarios
- Deeper AAOIFI standard coverage

**Target:** 3/5 accurate (60%)

### Phase 3: Arabic Questions (5 questions)
Test bilingual functionality:
- Language matching
- Arabic citation format
- Content parity with English
- Arabic clarification questions

**Target:** 3/5 accurate (60%)

### Overall Target
**10/20 questions accurate (50%)**

## Success Metrics

### Overall Success Criteria
- ✅ 10+ out of 20 questions accurate
- ✅ Proper AAOIFI citations in both languages
- ✅ Clarifying questions when needed
- ✅ Admits limitations appropriately
- ✅ No hallucinations

### Language-Specific Criteria
- ✅ English questions: 8/15 accurate (53%)
- ✅ Arabic questions: 3/5 accurate (60%)
- ✅ Language matching: 5/5 correct (100%)

## Topics Covered

### Islamic Finance Instruments
- Murabaha (cost-plus financing)
- Mudaraba (profit-sharing)
- Musharaka (partnership)
- Ijara (leasing)
- Sukuk (Islamic bonds)
- Takaful (Islamic insurance)

### Investment Types
- Stock market (mixed revenue companies)
- REITs (real estate)
- Forex (currency trading)
- Cryptocurrency (ambiguous case)

### Prohibited Elements
- Riba (interest)
- Gharar (excessive uncertainty)
- Maysir (gambling/speculation)
- Haram industries (alcohol, etc.)

### Business Transactions
- Partnership structures
- Profit/loss distribution
- Credit sales
- Late payment penalties

## AAOIFI Standards Tested

The questions are designed to test retrieval of these AAOIFI standards:

- **FAS-1**: General Presentation and Disclosure
- **FAS-2**: Murabaha and Murabaha to Purchase Orderer
- **FAS-3**: Mudaraba Financing
- **FAS-4**: Musharaka Financing
- **FAS-21**: Investment in Shares
- **Standards on Ijara**: Leasing
- **Standards on Sukuk**: Investment Certificates
- **Standards on Takaful**: Islamic Insurance

## Evaluation Criteria

For each question, evaluate:

### 1. Citation Quality (Weight: 30%)
- [ ] Cites specific AAOIFI standard number
- [ ] Includes section number
- [ ] Provides direct quotation
- [ ] Citation is accurate (not fabricated)

### 2. Clarification (Weight: 20%)
- [ ] Identifies missing information
- [ ] Asks specific questions
- [ ] Doesn't make assumptions

### 3. Accuracy (Weight: 30%)
- [ ] Ruling is correct
- [ ] Reasoning is sound
- [ ] Aligns with AAOIFI standards

### 4. Scope Recognition (Weight: 10%)
- [ ] Recognizes out-of-scope questions
- [ ] Admits limitations appropriately
- [ ] Doesn't overreach

### 5. Language Handling (Weight: 10%, Arabic only)
- [ ] Responds in correct language
- [ ] Uses appropriate language version of standards
- [ ] Maintains content parity

## Testing Workflow

### Step 1: Prepare
- [ ] Create Gemini Gem
- [ ] Upload English standards to `knowledge-base/en/`
- [ ] Upload Arabic standards to `knowledge-base/ar/`
- [ ] Add system instructions

### Step 2: Test Core Questions (1-2 hours)
- [ ] Test questions 1.1 - 4.3
- [ ] Record results in template
- [ ] Note patterns and issues

### Step 3: Test English Custom Questions (30 min)
- [ ] Test questions EN-1 to EN-5
- [ ] Record results
- [ ] Compare with core questions

### Step 4: Test Arabic Questions (30 min)
- [ ] Test questions AR-1 to AR-5
- [ ] Verify language matching
- [ ] Compare with English equivalents

### Step 5: Analyze Results (30 min)
- [ ] Calculate success rate
- [ ] Identify patterns
- [ ] Document learnings
- [ ] Plan improvements

## Expected Insights

### From Core Questions
- Which AAOIFI standards are most accessible?
- What types of queries work best?
- Where does clarification loop activate?
- What causes hallucinations?

### From English Custom Questions
- Coverage of advanced Islamic finance topics
- Depth of AAOIFI standard knowledge
- Handling of complex scenarios

### From Arabic Questions
- Bilingual functionality effectiveness
- Language matching accuracy
- Citation format in Arabic
- Content consistency across languages

## Next Steps After Testing

### If Success Rate ≥ 50%
1. Document what worked well
2. Identify most useful standards
3. Note optimal file structure
4. Design full RAG system based on learnings

### If Success Rate < 50%
1. Analyze failure patterns
2. Improve system instructions
3. Enhance file formatting
4. Re-test and iterate

## Quick Reference

**Total Questions:** 20
- Core: 10
- English Custom: 5
- Arabic Custom: 5

**Success Target:** 10/20 (50%)

**Time Estimate:** 3-4 hours total

**Key Topics:** Takaful, Sukuk, Murabaha, Musharaka, Ijara, Investment screening, Forex

**Languages:** English + Arabic (bilingual testing)

---

**Created:** 2026-05-07  
**Purpose:** Summary of test questions for Gemini Gem prototype  
**Total Questions:** 20 (10 core + 5 English + 5 Arabic)
