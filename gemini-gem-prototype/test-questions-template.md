# Gemini Gem Test Questions Template

## Purpose
This document contains test questions to validate the Gemini Gem prototype's ability to provide accurate, cited Sharia compliance rulings based on AAOIFI standards.

## Success Criteria
- **Target**: 5 out of 10 questions should receive accurate answers with proper AAOIFI citations
- **Quality Indicators**:
  - Gem cites specific AAOIFI standard numbers and sections
  - Gem asks clarifying questions when information is missing
  - Gem admits when it cannot find relevant standards
  - Gem does not hallucinate or fabricate standards
  - Gem provides clear compliance status (compliant/non-compliant/conditional)

## Test Question Categories

### Category 1: Investment Screening (Stock Market)
Questions about investing in publicly traded companies with mixed revenue sources.

**Question 1.1: Mixed Revenue Company**
```
I want to invest in a technology company that earns 95% of its revenue from software sales and 5% from interest on cash deposits. Is this investment permissible?
```

**Expected Behavior:**
- Should ask clarifying questions about investment timeframe, dividend purification willingness
- Should cite AAOIFI FAS-21 on Investment in Shares
- Should mention the 5% threshold for non-permissible revenue
- Should provide conditional compliance ruling with purification requirements

**Actual Result:**
- [ ] Asked clarifying questions: Yes / No
- [ ] Cited AAOIFI FAS-21: Yes / No
- [ ] Mentioned 5% threshold: Yes / No
- [ ] Provided purification guidance: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record any issues, hallucinations, or unexpected behaviors]

---

**Question 1.2: Alcohol Producer**
```
Can I buy shares in a beverage company that produces both soft drinks and alcoholic beverages?
```

**Expected Behavior:**
- Should ask about revenue breakdown between halal and haram products
- Should cite relevant AAOIFI standards on prohibited industries
- Should likely rule non-compliant if alcohol is a primary business line

**Actual Result:**
- [ ] Asked about revenue breakdown: Yes / No
- [ ] Cited relevant AAOIFI standard: Yes / No
- [ ] Provided clear ruling: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

**Question 1.3: REIT Investment**
```
I'm considering investing in a Real Estate Investment Trust (REIT). What should I know about Sharia compliance?
```

**Expected Behavior:**
- Should ask about the REIT's property types (commercial, residential, hotels, etc.)
- Should ask about financing structure (debt levels, interest-based loans)
- Should cite AAOIFI standards on real estate investment
- Should explain conditions for permissibility

**Actual Result:**
- [ ] Asked clarifying questions: Yes / No
- [ ] Cited AAOIFI standard: Yes / No
- [ ] Explained key compliance factors: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

### Category 2: Financing and Loans
Questions about various financing structures and loan arrangements.

**Question 2.1: Conventional Car Loan**
```
I need to buy a car and the bank is offering me a loan with 4% annual interest. Is this permissible?
```

**Expected Behavior:**
- Should clearly state this is non-compliant (riba/interest-based)
- Should cite AAOIFI standards on prohibited transactions
- Should suggest Sharia-compliant alternatives (Murabaha, Ijara)

**Actual Result:**
- [ ] Ruled non-compliant: Yes / No
- [ ] Cited AAOIFI standard: Yes / No
- [ ] Suggested alternatives: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

**Question 2.2: Murabaha Contract**
```
A bank is offering me a Murabaha contract to purchase a house. They will buy the house for $300,000 and sell it to me for $400,000 payable over 10 years. Is this Sharia compliant?
```

**Expected Behavior:**
- Should ask clarifying questions about contract structure (ownership transfer timing, payment terms, penalties)
- Should cite AAOIFI FAS-2 on Murabaha
- Should explain conditions for valid Murabaha
- Should identify potential red flags (e.g., if bank doesn't take ownership first)

**Actual Result:**
- [ ] Asked about contract details: Yes / No
- [ ] Cited AAOIFI FAS-2: Yes / No
- [ ] Explained Murabaha conditions: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

**Question 2.3: Credit Card Usage**
```
Is it permissible to use a credit card if I always pay the full balance before interest charges apply?
```

**Expected Behavior:**
- Should ask about card terms (annual fees, late payment penalties, interest structure)
- Should cite relevant AAOIFI standards
- Should explain the difference between using credit facility vs. incurring interest

**Actual Result:**
- [ ] Asked clarifying questions: Yes / No
- [ ] Cited AAOIFI standard: Yes / No
- [ ] Explained key distinctions: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

### Category 3: Business Transactions
Questions about commercial contracts and business operations.

**Question 3.1: Partnership Structure**
```
I want to start a business with a partner where I provide 70% of the capital and they provide 30% plus all the management work. We'll split profits 50-50. Is this structure permissible?
```

**Expected Behavior:**
- Should identify this as a Mudaraba or Musharaka structure
- Should cite AAOIFI FAS-3 (Mudaraba) or FAS-4 (Musharaka)
- Should explain profit-sharing rules and loss-bearing principles
- Should validate if the proposed structure aligns with AAOIFI standards

**Actual Result:**
- [ ] Identified contract type: Yes / No
- [ ] Cited AAOIFI FAS-3 or FAS-4: Yes / No
- [ ] Explained profit/loss rules: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

**Question 3.2: Late Payment Penalty**
```
I'm drafting a contract for selling goods on credit. Can I include a clause that charges a penalty if the buyer pays late?
```

**Expected Behavior:**
- Should explain that conventional late payment penalties (interest-based) are not permissible
- Should cite relevant AAOIFI standards on credit sales
- Should suggest Sharia-compliant alternatives (charity penalties, actual damages)

**Actual Result:**
- [ ] Explained prohibition: Yes / No
- [ ] Cited AAOIFI standard: Yes / No
- [ ] Suggested alternatives: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

### Category 4: Edge Cases and Limitations
Questions designed to test the Gem's ability to handle uncertainty and scope limitations.

**Question 4.1: Outside Scope - Zakat**
```
How much Zakat do I need to pay on my savings account?
```

**Expected Behavior:**
- Should recognize this is outside AAOIFI FAS scope (this is a Sharia/fiqh question, not accounting)
- Should politely decline and suggest consulting a scholar
- Should NOT attempt to answer based on general knowledge

**Actual Result:**
- [ ] Recognized out of scope: Yes / No
- [ ] Declined appropriately: Yes / No
- [ ] Avoided hallucination: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

**Question 4.2: Ambiguous Query**
```
Is cryptocurrency halal?
```

**Expected Behavior:**
- Should ask clarifying questions (which cryptocurrency, what use case, trading vs. holding)
- Should acknowledge if AAOIFI standards don't specifically cover cryptocurrency
- Should explain what principles from AAOIFI standards might apply
- Should recommend consulting current scholarly opinions

**Actual Result:**
- [ ] Asked clarifying questions: Yes / No
- [ ] Acknowledged standard limitations: Yes / No
- [ ] Avoided definitive ruling without standards: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

**Question 4.3: Non-existent Standard**
```
What does AAOIFI FAS-99 say about blockchain technology?
```

**Expected Behavior:**
- Should state that FAS-99 doesn't exist or isn't in the knowledge base
- Should NOT fabricate content
- Should offer to help with actual AAOIFI standards

**Actual Result:**
- [ ] Acknowledged non-existence: Yes / No
- [ ] Avoided fabrication: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

## Custom Test Questions

### English Questions (5 Questions)

**Custom Question EN-1: Islamic Insurance (Takaful)**
```
I'm considering purchasing a Takaful insurance policy for my car. How is this different from conventional insurance, and what makes it Sharia compliant?
```

**Expected Behavior:**
- Should explain Takaful principles (mutual cooperation, risk-sharing)
- Should cite relevant AAOIFI standards on Takaful/insurance
- Should explain key differences from conventional insurance (no riba, no gharar, no maysir)
- Should mention conditions for Sharia compliance

**Actual Result:**
- [ ] Explained Takaful principles: Yes / No
- [ ] Cited AAOIFI standard: Yes / No
- [ ] Differentiated from conventional insurance: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

**Custom Question EN-2: Sukuk Investment**
```
I want to invest in a Sukuk (Islamic bond). The issuer says it's asset-backed and Sharia-compliant. What should I verify before investing?
```

**Expected Behavior:**
- Should ask about Sukuk structure type (Ijara, Mudaraba, Musharaka, etc.)
- Should cite AAOIFI standards on Sukuk/investment certificates
- Should explain key verification points (underlying assets, ownership rights, profit distribution)
- Should mention red flags to watch for

**Actual Result:**
- [ ] Asked about Sukuk structure: Yes / No
- [ ] Cited AAOIFI standard: Yes / No
- [ ] Explained verification points: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

**Custom Question EN-3: Profit Distribution in Partnership**
```
My business partner and I agreed to split profits 60-40, but we didn't specify how losses should be handled. What does Sharia law say about loss distribution in partnerships?
```

**Expected Behavior:**
- Should identify this as Musharaka (partnership) question
- Should cite AAOIFI FAS-4 on Musharaka
- Should explain that losses must be distributed according to capital contribution ratio
- Should clarify that profit distribution can differ from capital ratio, but loss distribution cannot

**Actual Result:**
- [ ] Identified as Musharaka: Yes / No
- [ ] Cited AAOIFI FAS-4: Yes / No
- [ ] Explained loss distribution rules: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

**Custom Question EN-4: Foreign Currency Trading (Forex)**
```
I'm interested in trading foreign currencies (Forex). Is this permissible in Islam, and are there any conditions I need to follow?
```

**Expected Behavior:**
- Should cite AAOIFI standards on currency exchange/trading
- Should explain conditions for permissible currency exchange (immediate exchange, no interest/riba)
- Should distinguish between spot trading (permissible) and forward/futures contracts (potentially problematic)
- Should mention the prohibition of speculation (maysir)

**Actual Result:**
- [ ] Cited AAOIFI standard: Yes / No
- [ ] Explained permissibility conditions: Yes / No
- [ ] Distinguished between trading types: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

**Custom Question EN-5: Lease-to-Own (Ijara Muntahia Bittamleek)**
```
A bank is offering me an Islamic lease-to-own arrangement (Ijara Muntahia Bittamleek) for a property. They will lease it to me for 15 years, and at the end, I can purchase it for $1. Is this structure Sharia compliant?
```

**Expected Behavior:**
- Should cite AAOIFI standards on Ijara (leasing)
- Should explain conditions for valid Ijara Muntahia Bittamleek
- Should identify potential issues (e.g., nominal purchase price, binding promise)
- Should ask clarifying questions about contract structure

**Actual Result:**
- [ ] Cited AAOIFI standard on Ijara: Yes / No
- [ ] Explained Ijara Muntahia Bittamleek conditions: Yes / No
- [ ] Identified potential issues: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

### Arabic Questions (5 Questions)

**Custom Question AR-1: التأمين الإسلامي (التكافل)**
```
أفكر في شراء بوليصة تأمين تكافلي لسيارتي. كيف يختلف هذا عن التأمين التقليدي، وما الذي يجعله متوافقاً مع الشريعة؟
```

**(Translation: I'm considering purchasing a Takaful insurance policy for my car. How is this different from conventional insurance, and what makes it Sharia compliant?)**

**Expected Behavior:**
- Should respond in Arabic
- Should cite Arabic version of AAOIFI standards on Takaful
- Should explain Takaful principles in Arabic
- Should provide same content as English equivalent (EN-1)

**Actual Result:**
- [ ] Responded in Arabic: Yes / No
- [ ] Cited Arabic AAOIFI standard: Yes / No
- [ ] Explained Takaful principles: Yes / No
- [ ] Content matches English equivalent: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations about Arabic language handling]

---

**Custom Question AR-2: الاستثمار في الصكوك**
```
أريد الاستثمار في صكوك إسلامية. يقول المُصدر إنها مدعومة بأصول ومتوافقة مع الشريعة. ما الذي يجب أن أتحقق منه قبل الاستثمار؟
```

**(Translation: I want to invest in Sukuk (Islamic bonds). The issuer says it's asset-backed and Sharia-compliant. What should I verify before investing?)**

**Expected Behavior:**
- Should respond in Arabic
- Should cite Arabic version of AAOIFI standards on Sukuk
- Should ask clarifying questions in Arabic
- Should provide same content as English equivalent (EN-2)

**Actual Result:**
- [ ] Responded in Arabic: Yes / No
- [ ] Cited Arabic AAOIFI standard: Yes / No
- [ ] Asked clarifying questions in Arabic: Yes / No
- [ ] Content matches English equivalent: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

**Custom Question AR-3: توزيع الأرباح في الشراكة**
```
اتفقت أنا وشريكي في العمل على تقسيم الأرباح بنسبة 60-40، لكننا لم نحدد كيفية التعامل مع الخسائر. ماذا تقول الشريعة الإسلامية عن توزيع الخسائر في الشراكات؟
```

**(Translation: My business partner and I agreed to split profits 60-40, but we didn't specify how losses should be handled. What does Sharia law say about loss distribution in partnerships?)**

**Expected Behavior:**
- Should respond in Arabic
- Should cite Arabic version of AAOIFI FAS-4 on Musharaka
- Should explain loss distribution rules in Arabic
- Should provide same content as English equivalent (EN-3)

**Actual Result:**
- [ ] Responded in Arabic: Yes / No
- [ ] Cited Arabic AAOIFI FAS-4: Yes / No
- [ ] Explained loss distribution rules: Yes / No
- [ ] Content matches English equivalent: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

**Custom Question AR-4: تداول العملات الأجنبية (الفوركس)**
```
أنا مهتم بتداول العملات الأجنبية (الفوركس). هل هذا جائز في الإسلام، وهل هناك أي شروط يجب أن أتبعها؟
```

**(Translation: I'm interested in trading foreign currencies (Forex). Is this permissible in Islam, and are there any conditions I need to follow?)**

**Expected Behavior:**
- Should respond in Arabic
- Should cite Arabic version of AAOIFI standards on currency exchange
- Should explain conditions in Arabic
- Should provide same content as English equivalent (EN-4)

**Actual Result:**
- [ ] Responded in Arabic: Yes / No
- [ ] Cited Arabic AAOIFI standard: Yes / No
- [ ] Explained permissibility conditions: Yes / No
- [ ] Content matches English equivalent: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

**Custom Question AR-5: الإيجار المنتهي بالتمليك**
```
يعرض علي البنك ترتيب إيجار إسلامي منتهي بالتمليك لعقار. سيؤجرونه لي لمدة 15 عاماً، وفي النهاية يمكنني شراؤه مقابل دولار واحد. هل هذا الهيكل متوافق مع الشريعة؟
```

**(Translation: A bank is offering me an Islamic lease-to-own arrangement (Ijara Muntahia Bittamleek) for a property. They will lease it to me for 15 years, and at the end, I can purchase it for $1. Is this structure Sharia compliant?)**

**Expected Behavior:**
- Should respond in Arabic
- Should cite Arabic version of AAOIFI standards on Ijara
- Should identify potential issues in Arabic
- Should provide same content as English equivalent (EN-5)

**Actual Result:**
- [ ] Responded in Arabic: Yes / No
- [ ] Cited Arabic AAOIFI standard on Ijara: Yes / No
- [ ] Identified potential issues: Yes / No
- [ ] Content matches English equivalent: Yes / No
- [ ] Overall accuracy: ⭐⭐⭐⭐⭐ (1-5 stars)

**Notes:**
[Record observations]

---

## Testing Summary

**Date Tested:** [YYYY-MM-DD]

**Overall Results:**
- Total questions tested: ____ / 20 (10 core + 5 English + 5 Arabic)
- Questions with accurate answers: ____ 
- Questions with proper citations: ____
- Questions where Gem asked clarifying questions: ____
- Questions where Gem admitted limitations: ____
- Questions with hallucinations/fabrications: ____

**Success Rate:** ____% (Target: 50%+ = 10/20 questions)

**Language-Specific Results:**
- English questions accurate: ____ / 15 (10 core + 5 custom)
- Arabic questions accurate: ____ / 5
- Language matching correct: ____ / 5 (Arabic responses in Arabic)

**Key Findings:**

### What Worked Well:
1. [Observation]
2. [Observation]
3. [Observation]

### What Needs Improvement:
1. [Issue and potential solution]
2. [Issue and potential solution]
3. [Issue and potential solution]

### Standards Most Frequently Used:
- [AAOIFI FAS-X]: Used in Y questions
- [AAOIFI FAS-X]: Used in Y questions

### Standards Never Retrieved:
- [List standards that were never cited despite being relevant]

### Hallucination Patterns:
- [Describe any patterns in fabricated content]

### Next Steps:
1. [Action item based on findings]
2. [Action item based on findings]
3. [Action item based on findings]

---

## Iteration Log

### Iteration 1 - [Date]
**Changes Made:**
- [What was changed in the Gem configuration or knowledge base]

**Results:**
- [Summary of test results]

**Learnings:**
- [What you learned from this iteration]

---

### Iteration 2 - [Date]
**Changes Made:**
- [What was changed]

**Results:**
- [Summary of test results]

**Learnings:**
- [What you learned]

---

## Migration to Full RAG System

### Insights for RAG Architecture:

**Optimal Chunk Size:**
- Based on testing, chunks should be approximately [X] tokens
- Rationale: [Why this size worked best]

**Metadata Schema:**
- Essential metadata fields identified: [List]
- Rationale: [Why these fields matter]

**Retrieval Patterns:**
- Users typically ask about: [Common topics]
- Standards most frequently needed: [List]
- Query types that need special handling: [List]

**Clarification Loop:**
- Common missing information: [List]
- Effective clarifying questions: [Examples]

**Citation Quality:**
- What makes a good citation: [Observations]
- How to improve citation accuracy: [Recommendations]
