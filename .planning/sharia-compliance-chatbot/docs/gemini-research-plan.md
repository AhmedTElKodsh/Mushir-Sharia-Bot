# **Architectural Blueprint and Implementation Strategy for a Multilingual AAOIFI Sharia-Compliant Financial Chatbot**

## **Introduction and System Architecture Rationale**

The intersection of artificial intelligence and Islamic finance presents a unique confluence of technical and domain-specific challenges. The fundamental objective is the creation of an advanced Conversational AI system—a chatbot—capable of meticulously evaluating user-described financial operations, contracts, and services to determine their compliance with the Accounting and Auditing Organization for Islamic Financial Institutions (AAOIFI) Sharia Standards. Furthermore, this system must not merely offer a binary judgment of compliance or non-compliance; it must definitively ground its reasoning by retrieving and presenting the precise reference, including the specific number and title, of the corresponding AAOIFI regulatory file.  
Achieving this requires moving far beyond the capabilities of standard, general-purpose Large Language Models (LLMs). General LLMs are prone to hallucination, particularly in niche legal and theological domains, and lack the deterministic precision required for regulatory compliance checking. To fulfill the operational mandate, the architecture must be constructed upon a sophisticated Retrieval-Augmented Generation (RAG) pipeline, heavily integrated with an active Human-in-the-Loop (HITL) framework. This pipeline must navigate profound linguistic complexities, processing inputs that span English, classical Arabic, modern standard Arabic (MSA), regional colloquialisms, and code-switched combinations of these languages.  
The system must also possess a deep, programmatic understanding of common financial operations, contractual structures, and institutional services. It must intelligently map ambiguous user phrasing to canonical Islamic finance terminology—translating a user's vague description of a "profit-sharing lease" into the formal construct of *Ijarah Muntahia Bittamleek* or matching a "delayed payment sale" to *Murabahah*. When the user's description lacks the necessary regulatory parameters to make a definitive Sharia judgment, the system must deploy a Chain of Thought reasoning process to recognize this ambiguity. It must then suspend its compliance evaluation, generate highly targeted clarifying questions, and prompt the human user for the missing parameters.  
To realize this vision, the project architecture is sequentially divided into comprehensive phases encompassing corpus ingestion, linguistic normalization, multidimensional semantic retrieval, agentic reasoning, and stateful human interaction management. Each phase leverages state-of-the-art open-source methodologies and libraries, synthesizing them into a cohesive, production-ready blueprint.

## **The AAOIFI Corpus and the Necessity of Hierarchical Context**

The foundational knowledge base for this system comprises the AAOIFI Sharia Standards, which exist as highly structured, legalistic documents available in both English and Arabic. These documents dictate the permissibility of operations ranging from currency trading (Standard 1\) and guarantees (Standard 5\) to complex corporate transitions, such as the conversion of a conventional bank into an Islamic bank (Standard 6). Processing these documents downloaded as text files for ingestion into a vector database requires specialized chunking methodologies, as naive chunking algorithms utterly fail in legal and regulatory contexts.

### **The Failure of Naive Chunking in Legal Documentation**

In standard RAG architectures, document chunking typically relies on recursive character splitting, where a text is divided into uniform blocks of a fixed token length. For a general knowledge base, this is acceptable. However, legal documentation is inherently hierarchical. An AAOIFI standard consists of a title, scope, specific rulings, conditional clauses, and exceptions. If a naive chunking algorithm splits a document in the middle of a conditional list, the resulting chunk may contain a specific compliance rate or a minor ruling but lose all connection to the parent contract it modifies.  
For example, if a user asks about the penalties for a "Procrastinating Debtor," the system must retrieve information specifically from AAOIFI Standard 3\. If the chunk describing the penalty does not contain the metadata linking it to Standard 3, the RAG pipeline will retrieve isolated text, forcing the LLM to guess the reference, thereby violating the core objective of the system.

### **Structure-Aware Markdown Segmentation**

To preserve the semantic and hierarchical integrity of the AAOIFI standards, the corpus must be formatted into Markdown and processed using structure-aware chunking algorithms. Open-source repositories such as chunky (GiovanniPasq/chunky) and md2chunks (verloop/md2chunks) provide the necessary architectural frameworks for this task. The ingestion pipeline begins by utilizing Markdown's inherent heading hierarchy (represented by hashes, from \# to \#\#\#\#\#\#) to establish a logical Abstract Syntax Tree (AST) of the document.  
The chunky library allows for the bulk conversion of these documents while executing validation routines to ensure that Markdown formatting artifacts do not corrupt the text. More importantly, it facilitates chunk enrichment, utilizing a localized LLM pass to generate titles, summaries, and thematic keywords for every individual chunk before it enters the vector database. This enrichment ensures that a heavily localized sub-clause still contains a dense semantic representation of the broader standard it belongs to.  
Concurrently, methodologies found in md2chunks enforce context enrichment by injecting parent header information into all child chunks. If a specific Sharia ruling spans multiple paragraphs, the chunker maintains an overlap of approximately thirty-five percent between neighboring chunks, ensuring that the transition of context does not abruptly terminate at an artificial boundary. Advanced implementations of this methodology dynamically shift their internal strategies based on the content type, separating standard text from bulleted condition lists, thereby ensuring that logical units of Islamic jurisprudence remain perfectly intact within the vector space.

## **Navigating Linguistic Complexity and Arabic NLP Optimization**

Islamic finance operates across a vast linguistic spectrum. A financial operation might be queried by a user in London using entirely English terminology, or by a user in Cairo blending Egyptian colloquial Arabic with formal financial terms, or by a scholar in Riyadh utilizing classical Arabic jurisprudence terminology. The system must process these inputs uniformly, mapping disparate linguistic signals to the identical underlying semantic concept.

### **Morphological Disambiguation and Text Normalization**

The Arabic language is highly agglutinative, meaning that prefixes and suffixes are frequently attached to root words to modify their meaning, tense, and subject. Furthermore, Arabic text is often written without diacritics (the vowel marks known as Tashkeel), which introduces significant ambiguity, as a single undiacritized word can possess multiple entirely different meanings depending on the context.  
To construct a robust preprocessing pipeline, the architecture integrates the camel\_tools suite, developed by the CAMeL Lab at New York University Abu Dhabi. This comprehensive open-source Python toolkit provides targeted utilities for Arabic text normalization, tokenization, and morphological analysis. When an Arabic query enters the system, the pipeline first deploys the dediac\_ar function to strip any erratic or partial diacritics provided by the user, establishing a normalized baseline string.  
Following basic normalization, the text undergoes morphological disambiguation. The system utilizes either the Maximum Likelihood Estimation (MLE) disambiguator or the BERT-unfactored disambiguator provided by camel\_tools. This process critically analyzes the context of the sentence to determine the precise lemma and part-of-speech for each word. If a user describes a financial transaction involving the transfer of debt, the disambiguator isolates the root concept, allowing the subsequent mapping engine to identify it as *Hawalah* (AAOIFI Standard 7).

### **Managing Code-Switching and Arabizi**

A significant challenge in modern conversational interfaces is code-switching, where users seamlessly transition between languages within a single sentence. Furthermore, younger demographics may utilize "Arabizi," the Arabic chat alphabet that relies on Latin characters and numerals to represent Arabic phonetics. A rigid NLP pipeline will fail to comprehend a query formatted in Arabizi or a hybrid English-Arabic sentence.  
To counteract this, the preprocessing engine must incorporate specialized noise removal and normalization routines that target User-Generated Content (UGC). If Arabizi is detected, a transliteration module maps the Latin phonetics back to Arabic script. When code-switching occurs, the system does not attempt a direct, unified translation. Instead, it prepares the query for multi-route retrieval, ensuring that the English components and the Arabic components are preserved in their native semantic states before querying the vector database.

### **Leveraging Financial Banking Intent Datasets**

Understanding the words is only the first step; understanding the financial intent is the core objective. The linguistic pipeline is fortified by training on domain-specific datasets such as ArBanking77. This dataset contains approximately thirty-nine thousand parallel queries spanning MSA and four regional dialects, mapped precisely to seventy-seven distinct banking intents. By fine-tuning the intent detection module on ArBanking77, the chatbot gains the intrinsic ability to interpret a colloquial Levantine phrase regarding credit card fees and map it to the formal intent of inquiring about "Debit Card, Charge Card and Credit Card" operations (AAOIFI Standard 2). This ensures that the user's regional dialect does not act as a barrier to accurate Sharia compliance checking.

## **Cross-Lingual Embedding and Hybrid Search Architecture**

With the AAOIFI corpus meticulously chunked and the user's query linguistically normalized, the system requires a retrieval engine capable of bridging the gap between the query language and the document language. The AAOIFI standards exist in parallel English and Arabic texts, but relying on a direct match between the language of the query and the language of the document restricts the system's flexibility.

### **Vector Space Design and Multilingual Models**

The optimal architecture utilizes a unified multilingual vector database, such as Milvus or Vectara, which natively supports cross-lingual retrieval without requiring fragile third-party translation APIs at query time. The system relies on advanced multilingual embedding models, such as BGE-M3 or ArbEngVec, to project both the AAOIFI chunks and the user queries into a shared high-dimensional vector space.  
In this shared space, semantic meaning supersedes lexical structure. The mathematical representation of the English word "Endowment" is placed in immediate proximity to the Arabic word "وقف" (Waqf). Consequently, if an English-speaking user describes a charitable trust mechanism, the dense vector search will successfully retrieve the Arabic text for AAOIFI Standard 33 (Waqf) if the English text chunk is somehow occluded or less relevant. ArbEngVec, explicitly trained on over ninety-three million pairs of Arabic-English parallel sentences, provides unparalleled accuracy in maintaining cross-language Semantic Textual Similarity (STS) specifically for these operations.

### **Implementing the 10-Route Retrieval Strategy**

Relying solely on dense vector embeddings (semantic search) often leads to diminished precision when dealing with exact legal terminology or specific reference numbers. Conversely, relying solely on BM25 keyword search (lexical search) fails when the user employs synonyms. The solution is a robust Hybrid Search architecture that fuses both methodologies, dynamically routing queries based on linguistic characteristics.  
The retrieval orchestrator implements several distinct retrieval routes to maximize accuracy. When a standard, single-language query is received, the system utilizes the "Same-Language Hybrid" route. It executes a BM25 search equipped with Arabic stemming algorithms alongside a dense vector search. The results are merged, and a multilingual cross-encoder reranks the candidates to ensure precision.  
However, when a code-switched or highly colloquial query enters the system, the orchestrator triggers the "Code-Switch Route". It expands the single user input into multiple query variants: the original query, a formally translated query, a transliterated variant, and a keyword-only variant focusing purely on extracted financial entities. These variants search the vector database simultaneously. The resulting candidate lists are then fused using Reciprocal Rank Fusion (RRF), a mathematical technique that calculates a unified ranking based on the relative positions of documents across all lists, completely mitigating the risk of translation artifacts derailing the search.

### **Glossary Injection and Entity Recognition**

Islamic finance is deeply rooted in highly specific contractual entities. To ensure that unclear user words are accurately matched to the correct financial operation, the retrieval pipeline utilizes Entity-First Retrieval and Glossary Injection. An open-source Islamic finance ontology is constructed, serving as a comprehensive dictionary mapping common phrases, colloquialisms, and synonyms to their canonical AAOIFI equivalents.  
If a user vaguely describes a system where they "buy something now and the bank pays the seller, and I pay the bank back later with a known markup," the ontology recognizes the structural markers of this description. It injects the formal term "Murabahah" into the BM25 keyword search as a controlled expansion, applying a heavy algorithmic boost to documents containing that entity. This guarantees that the retrieval engine prioritizes AAOIFI Standard 8 over general discussions of debt. This deterministic mapping ensures that the LLM is fed the exact regulatory context required to evaluate the operation.

## **The Generative Engine: Agentic Reasoning and Sharia Compliance**

The retrieval engine provides the necessary legal context, but the synthesis of this context into a definitive ruling requires an advanced generative model. General-purpose LLMs lack the domain-specific rigor required for Sharia reasoning, often hallucinating permissibility based on conventional Western financial norms rather than strict AAOIFI parameters.

### **The SAHM Benchmark and Domain-Specific Adaptation**

To construct a reliable generative engine, the architecture relies heavily on the insights and models derived from the SAHM (Arabic Financial and Shari'ah-Compliant Reasoning) project. The SAHM initiative exposes a critical flaw in general AI: fluency in Arabic does not guarantee competence in financial reasoning. Models that perform well on general language tasks experience catastrophic degradation when subjected to Event-Cause QA and specific Sharia standard evaluation.  
To overcome this, the chatbot utilizes models explicitly fine-tuned for this domain, such as the SAHM-7B-Instruct or SAHM-ALLAM-7B models. These models demonstrate parameter efficiency that rivals models ten times their size because their instruction-tuning dataset comprises over fourteen thousand expert-verified instances drawn directly from AAOIFI standards, official fatwa archives, and Islamic finance regulatory material. By deploying a SAHM-adapted model as the core reasoning agent, the system ensures that the logic applied to the user's query aligns inherently with Islamic jurisprudence.

### **Chain of Thought for Compliance Evaluation**

When the system processes a user's description of a financial service, the SAHM-adapted agent executes a rigid Chain of Thought (CoT) prompting strategy. The agent is instructed not to output a final answer immediately. Instead, it must internally document its reasoning steps.  
First, the agent classifies the user's described service against the retrieved AAOIFI standards. Second, it extracts the mandatory conditions for permissibility explicitly stated in the retrieved chunk. Third, it cross-references every extracted condition against the details provided in the user's prompt. Finally, it formulates a structured response indicating whether the operation is compliant, non-compliant, or ambiguous, accompanied by the exact AAOIFI standard number and title (e.g., "Non-compliant per the conditions of SS (1) Trading in Currencies").

## **Active RAG and Clarifying Question Generation**

A critical vulnerability in any financial advisory chatbot is the handling of ambiguity. Users rarely provide a perfectly structured description of a financial contract in their initial prompt. They may omit crucial details, such as the exact sequence of possession in a commodity sale or the specific risk-sharing structure in an investment. If the agent attempts to force a compliance verdict based on incomplete information, it will produce a legally and theologically flawed ruling.

### **The STaR-GATE Methodology**

To address high levels of uncertainty, the architecture pivots from passive retrieval to Active RAG. When the agent's Chain of Thought process determines that a mandatory condition for compliance cannot be verified using the user's provided text, it halts the evaluation phase. The system then utilizes methodologies inspired by STaR-GATE (Teaching Language Models to Ask Clarifying Questions).  
STaR-GATE provides a framework where the language model undergoes self-improvement by being rewarded for generating useful, targeted questions that elicit missing preferences from the user. Within this architecture, the agent acts as the "Questioner." If the user describes a partnership but fails to specify how losses are distributed—a vital component for determining if the contract is a valid *Mudarabah* or *Musharakah*—the agent generates a specific clarifying question. Instead of a generic "Please provide more details," the STaR-GATE tuned model asks: "In your described partnership, are financial losses borne solely by the capital provider, or are they distributed among partners based on their capital contribution ratios?". This targeted inquiry narrows down the ambiguity, forcing the user to provide the exact parameter required to finalize the Sharia compliance check against the AAOIFI standard.

## **Human-in-the-Loop Orchestration via LangGraph**

The capacity to generate intelligent clarifying questions is useless without a control flow mechanism capable of pausing the application, sending the question to the user, waiting indefinitely for a response, and then resuming the logic stream exactly where it left off. Traditional linear LLM chains cannot achieve this. The system requires a durable, stateful, and cyclic orchestration framework, establishing the necessity for LangGraph.

### **Graph-Based State Management**

LangGraph transitions the architecture from a sequential pipeline to a directed cyclic graph. The system is defined by three core components: the State, the Nodes, and the Edges. The GraphState is a strictly typed Python dictionary that persists throughout the entire user interaction. It stores the user's original query, the detected language, the retrieved AAOIFI document chunks, the partial Chain of Thought reasoning, and the list of identified ambiguities.  
The application logic is encapsulated within specialized Nodes (e.g., Retrieve\_AAOIFI, Evaluate\_Compliance, Generate\_Clarification). The execution flow between these nodes is governed by Conditional Edges. After the initial evaluation node runs, a router function inspects the state. If the ambiguity threshold is low, the conditional edge routes the flow to the Final\_Verdict node. However, if the threshold is high, the conditional edge routes execution to the Ask\_Human node.

### **The Interrupt Pattern and Checkpointing**

The execution of the Ask\_Human node triggers LangGraph's native interrupt() function. This function is the cornerstone of the Human-in-the-Loop architecture. When interrupt("Clarifying question text") is called, LangGraph completely halts the execution of the agent.  
To ensure this pause is resilient against server timeouts or asynchronous delays in the user's response, LangGraph utilizes persistent checkpointers. While an InMemorySaver is useful for prototyping, production systems require an AsyncSqliteSaver or similar durable database. The checkpointer serializes the entire state of the graph at the exact moment of the interrupt and stores it against a unique thread\_id corresponding to the user's session.

### **Frontend Synchronization with Chainlit**

The backend interrupt must be synchronized flawlessly with the chatbot's user interface. The architecture dictates the use of Chainlit, an open-source framework explicitly designed for advanced Conversational AI and agentic workflows.  
When the LangGraph orchestrator yields an interrupt, the Chainlit server intercepts the \_\_interrupt\_\_ payload from the streaming run. Chainlit interprets this signal and triggers the cl.AskUserMessage utility. This utility presents the generated clarifying question to the human user in the chat interface and locks the application, awaiting text input.  
Once the user reads the clarifying question and types their response (e.g., "Losses are distributed based on capital ratios"), Chainlit captures this text. It then issues a Command(resume=user\_response) object back to the LangGraph application, utilizing the stored thread\_id. The LangGraph checkpointer retrieves the frozen state, injects the user's new information, and resumes the graph execution. The agent's state now contains the missing parameter, allowing the conditional edge to bypass the Ask\_Human node and proceed to the Evaluate\_Compliance node, ultimately resulting in a definitive ruling backed by the accurate AAOIFI file reference.

### **Table 1: NLP and Semantic Processing Frameworks**

| Operational Objective | Selected Open-Source Toolkit / Methodology | Implementation Strategy and Pipeline Integration |
| :---- | :---- | :---- |
| **Arabic Text Normalization** | camel\_tools (CAMeL-Lab) | Execute diacritic removal (dediac\_ar) and apply Buckwalter encoding maps. Strip morphological noise to prepare user input for uniform semantic matching. |
| **Morphological Disambiguation** | camel\_tools MLE / BERT-unfactored | Parse complex Arabic financial terms to identify lemmas and parts-of-speech. Resolve ambiguity in classical Fusha terms utilized in Sharia law. |
| **Code-Switching & Dialect Handling** | ArBanking77 Dataset Integration | Fine-tune intent classifiers on multi-dialect banking queries. Expand code-switched queries into parallel translation/transliteration variants. |
| **Semantic Entity Mapping** | CaIFE Ontology (Chatbot as Islamic Finance Expert) | Deploy specialized dictionaries (45 entities, 70 intents) to match colloquial descriptions to rigid AAOIFI terms (e.g., matching "leasing" to *Ijarah*). |

### **Table 2: Corpus Ingestion and Retrieval Architecture**

| Operational Objective | Selected Open-Source Toolkit / Methodology | Implementation Strategy and Pipeline Integration |
| :---- | :---- | :---- |
| **Bulk Corpus Ingestion** | chunky (GiovanniPasq) | Convert raw AAOIFI PDFs to Markdown. Clean formatting artifacts and prepare texts for structural analysis without destroying tabular data. |
| **Structure-Aware Chunking** | md2chunks (verloop) & Docling | Segment standards based on Markdown headers (\# vs \#\#\#). Inject parent title and standard number metadata into all child condition chunks. |
| **Cross-Lingual Vector Search** | Milvus Database & BGE-M3 / ArbEngVec | Store chunks in a multilingual vector space. Enable retrieving Arabic AAOIFI clauses using English queries via dense vector semantic proximity. |
| **Hybrid Search Routing** | BM25 \+ Reciprocal Rank Fusion (RRF) | Implement a multi-route strategy combining exact keyword matches for contract titles with semantic vector search, fusing results via RRF for maximum precision. |

### **Table 3: Generative Reasoning and Human-in-the-Loop Orchestration**

| Operational Objective | Selected Open-Source Toolkit / Methodology | Implementation Strategy and Pipeline Integration |
| :---- | :---- | :---- |
| **Sharia Compliance Reasoning** | SAHM Benchmark & SAHM-7B-Instruct | Utilize models instruction-tuned on 14,000+ Islamic finance instances. Apply Chain of Thought to map user mechanics against AAOIFI conditions. |
| **Clarifying Question Generation** | STaR-GATE (scandukuri/assistant-gate) | Empower the LLM to actively identify missing parameters required for a Sharia ruling and draft targeted, context-aware questions to elicit them. |
| **Stateful Agent Orchestration** | langchain-ai/langgraph | Construct a directed cyclic graph with GraphState dictionaries. Use conditional edges to route execution based on query ambiguity levels. |
| **Human-in-the-Loop Interrupts** | LangGraph interrupt() & AsyncSqliteSaver | Halt execution when ambiguity blocks compliance checks. Serialize thread state to a database until human input is received via a resume command. |
| **Interactive Chat UI** | chainlit/chainlit | Intercept LangGraph interrupt payloads. Render clarifying questions via cl.AskUserMessage and push human responses back into the execution stream. |

## **Detailed Project Blueprint and Execution Roadmap**

To successfully construct and deploy this AAOIFI Sharia-compliant financial chatbot, the project is divided into five exhaustive phases, integrating the methodologies, libraries, and architectural paradigms discussed above.

### **Phase 1: Data Acquisition, Normalization, and Ontology Construction**

**Task 1.1: AAOIFI Standards Procurement and Conversion**

* **Keywords:** Corpus Ingestion, PDF-to-Markdown, Text Extraction.  
* **Action:** Systematically download the full suite of AAOIFI Sharia Standards text/PDF files in both English and Arabic. Deploy the chunky repository to perform bulk extraction and transformation into clean, AST-compliant Markdown files.  
* **Resources:** github.com/GiovanniPasq/chunky.

**Task 1.2: Specialized NLP Pipeline Development**

* **Keywords:** Arabic NLP, Tokenization, Diacritic Removal, Disambiguation.  
* **Action:** Integrate camel\_tools to establish a preprocessing pipeline capable of receiving raw user text, stripping diacritical marks via dediac\_ar, and determining lexical roots using MLE disambiguation.  
* **Resources:** github.com/CAMeL-Lab/camel\_tools.

**Task 1.3: Islamic Finance Dictionary and Ontology Mapping**

* **Keywords:** Entity Recognition, Intent Classification, Synonym Mapping.  
* **Action:** Leverage the methodologies from the CaIFE project and the ArBanking77 dataset to build a localized ontology. Map multi-dialect colloquialisms and varied English translations to their canonical AAOIFI contract titles to facilitate Entity-First retrieval.  
* **Resources:** CaIFE documentation , ArBanking77 repository.

### **Phase 2: Hierarchical Ingestion and Multilingual Vectorization**

**Task 2.1: Context-Enriched Markdown Chunking**

* **Keywords:** Structural Chunking, Metadata Injection, RAG Optimization.  
* **Action:** Process the Markdown corpus utilizing md2chunks. Ensure the chunking algorithm respects standard boundaries, appending the specific AAOIFI standard number and title (e.g., "SS (8) Murabahah") to the metadata payload of every subordinate clause and condition.  
* **Resources:** github.com/verloop/md2chunks.

**Task 2.2: Vector Database Deployment and Cross-Lingual Embedding**

* **Keywords:** Hybrid Search, Milvus, Multilingual Embeddings.  
* **Action:** Initialize a Milvus or Vectara instance configured for hybrid search. Generate dense vectors using BGE-M3 or ArbEngVec to map both Arabic and English standard chunks into a unified, semantically coherent vector space.  
* **Resources:** ArbEngVec paper , Milvus documentation.

### **Phase 3: Agentic Reasoning and Core Evaluation Logic**

**Task 3.1: Domain-Specific LLM Integration**

* **Keywords:** Sharia Reasoning, Financial Agent, Prompt Engineering.  
* **Action:** Deploy a financially adapted LLM, such as SAHM-7B-Instruct, capable of accurately interpreting legal conditions. Configure a Chain of Thought prompt template that forces the model to sequentially evaluate user input against retrieved AAOIFI clauses before rendering a compliance verdict.  
* **Resources:** github.com/mbzuai-nlp/SAHM.

**Task 3.2: Clarifying Question Logic (Active RAG)**

* **Keywords:** STaR-GATE, Question Generation, Ambiguity Detection.  
* **Action:** Implement algorithms inspired by the STaR-GATE self-improvement loop. Train the agent to recognize when retrieved conditions cannot be satisfied by the user's initial prompt, triggering the generation of a specific, targeted question rather than a hallucinated ruling.  
* **Resources:** github.com/scandukuri/assistant-gate.

### **Phase 4: Human-in-the-Loop Orchestration**

**Task 4.1: LangGraph Workflow Design**

* **Keywords:** State Graph, Conditional Routing, Node Management.  
* **Action:** Architect the GraphState dictionary to hold memory across the session. Define executable nodes for preprocessing, retrieval, reasoning, and clarification. Program conditional edges to route traffic dynamically based on the model's confidence in its compliance evaluation.  
* **Resources:** github.com/langchain-ai/langgraph.

**Task 4.2: The Interrupt Checkpoint System**

* **Keywords:** Thread Persistence, interrupt(), State Serialization.  
* **Action:** Configure the interrupt\_before logic on the Ask\_Human node. Deploy an AsyncSqliteSaver checkpointer to serialize and safely store the LangGraph state indefinitely while the system waits for the user to answer the clarifying question.  
* **Resources:** LangGraph interrupts documentation.

### **Phase 5: User Interface and Iterative Benchmarking**

**Task 5.1: Chainlit Frontend Integration**

* **Keywords:** Chat UI, Asynchronous Handling, Bidirectional Streaming.  
* **Action:** Develop the user-facing application utilizing Chainlit. Write asynchronous event handlers to catch LangGraph \_\_interrupt\_\_ payloads. Display the agent's clarifying questions using cl.AskUserMessage and format the user's reply into a Command(resume=...) object to restart the graph.  
* **Resources:** github.com/Chainlit/chainlit.

**Task 5.2: Evaluation against the SAHM Benchmark**

* **Keywords:** Accuracy Testing, Hallucination Mitigation, Performance Metrics.  
* **Action:** Subject the completed end-to-end pipeline to the 14,000+ evaluation instances provided by the SAHM benchmark. Critically assess the system's performance on AAOIFI Shari'ah Standards QA and Event-Cause Reasoning to guarantee production-ready accuracy.  
* **Resources:** SAHM evaluation suite.

## **Conclusions**

The development of a conversational AI system capable of rendering accurate judgments on AAOIFI Sharia compliance necessitates a profound departure from conventional LLM deployments. The intricacies of Islamic jurisprudence require absolute fidelity to regulatory documentation, making hallucination an unacceptable risk. By treating the architecture as an intersection of specialized engineering domains—structural document parsing, deep cross-lingual natural language processing, agentic reasoning, and stateful human-in-the-loop orchestration—this blueprint provides a definitive roadmap to achieving the objective.  
The strategic utilization of hierarchical markdown chunkers guarantees that the dense legal context and exact reference numbers of the AAOIFI standards are forever linked to their underlying text within the vector space. Concurrently, the deployment of Arabic-centric NLP pipelines and hybrid retrieval pathways ensures that users are never penalized for utilizing colloquialisms, regional dialects, or code-switched queries. By mapping these diverse inputs to a strict Islamic finance ontology, the system establishes a deterministic foundation for evaluation.  
Crucially, the integration of LangGraph and Chainlit transforms the chatbot from a static information retrieval tool into a collaborative legal assistant. By embedding the STaR-GATE logic and utilizing persistent interrupts, the system acknowledges the limits of its knowledge. It pauses, seeks human clarification, and resumes its cognitive processes, mimicking the meticulous dialogue of a true domain expert. Through rigorous adherence to this architectural strategy and continuous benchmarking against datasets like SAHM, the resulting application will serve as an authoritative, interactive, and highly reliable arbiter of Sharia compliance in modern financial operations.

This comprehensive technical implementation plan breaks down your AAOIFI Sharia Compliance Chatbot into core engineering tasks, map matching keywords, and matching them directly with state-of-the-art open-source GitHub frameworks, architectures, and models.

---

## 🛠️ Task & Keyword Architecture Matrix

| Task Area | Core Objectives | Technical Keywords | Recommended Open-Source Frameworks |
| --- | --- | --- | --- |
| **1. Specialized Ingestion & Hybrid RAG** | High-fidelity Arabic parsing, structural chunking, bilingual dense/sparse index building. | PDF Parsing, Hybrid Retrieval, Late-Interaction Scoring, Metadata Filtering. | `logiccrafterdz/nassij`<br>

<br>`BAAI/bge-m3`<br>

<br>`qdrant/qdrant` |
| **2. Multi-Dialect & Code-Switching NLP** | Handling MSA, Classical Sharia Arabic, colloquial dialects, and mixed English/Arabic queries. | Cross-Lingual Alignment, Dense Representation, Morphological Analysis. | `U4RASD/NeoAraBERT`<br>

<br>`CAMeL-Lab/camel_tools` |
| **3. Financial Entity & Concept Linking** | Mapping vague user terminology to formal Islamic finance contracts (e.g., *Murabaha*, *Ijara*). | Zero-Shot NER, Entity Disambiguation, Financial Ontology Mapping. | `urchade/GLiNER`<br>

<br>`Knowledgator/GLinker` |
| **4. Stateful Clarification Engine & HITL** | Detecting ambiguity, asking conversational follow-up questions, and managing Human-in-the-Loop loops. | Agentic State Machine, Chain-of-Thought (CoT), Interruption Breakpoints. | `langchain-ai/langgraph`<br>

<br>`run-llama/llama_index` |

---

## 🚀 Deep-Dive Engineering Plan

### Section 1: Intelligent Bilingual Document Ingestion & Hybrid RAG Pipeline

AAOIFI standards feature complex legal structures and heavy use of footnotes/tables. Standard token-based splitting breaks up critical contextual rulings.

* **Extraction:** Use **Nassij**, an open-source Arabic-centric document parser that maintains Right-to-Left (RTL) linguistic integrity and layout preservation during PDF-to-text extraction.
* **Chunking Strategy:** Implement *Parent-Child chunking* or *Hierarchical splitting*. Chunk documents into granular child nodes (150–300 tokens) for vector matching while preserving the parent context (the entire clause or section) for LLM synthesis. Inject mandatory metadata tags into every chunk: `{"standard_number": 8, "standard_title": "Ijarah", "clause": "Section 4/1/2"}`.
* **Retrieval Model:** Deploy **BGE-M3** as your core embedding engine. It native-scores cross-lingually and supports three parallel retrieval layers, combined via an ensemble ranker:
1. *Dense Retrieval:* Captures high-level semantic meaning using normalized `[CLS]` vectors.
2. *Sparse Retrieval:* Employs lexical token weights (like BM25) to preserve exact numeric matches (e.g., "Standard No. 21").
3. *Multi-Vector Interaction:* Calculates fine-grained late-interaction scoring to accurately capture relationships inside complex paragraphs.



The hybrid scoring mechanism calculates the final relevance value as follows:


$$s_{\text{rank}} = w_1 \cdot s_{\text{dense}} + w_2 \cdot s_{\text{lex}} + w_3 \cdot s_{\text{mul}}$$

---

### Section 2: Linguistic Adaptability Engine (Bilingual, Code-Switching, Dialects)

Users often mix English financial terms with colloquial Arabic (e.g., *"Is a hybrid auto lease structure allowed under Murabaha rules without paying down payment?"* or *"عايز أعمل تمويل عقاري بصيغة المشاركة المتناقصة"*).

* **Dense Semantic Embedding Layer:** Use **NeoAraBERT**, a state-of-the-art open-source text-representation model fine-tuned precisely for Classical Arabic, Modern Standard Arabic (MSA), and dialect variations. It projects regional phrasing into the same vector space as the structured AAOIFI data.
* **Pre-retrieval Query Rewriting:** Build a lightweight query expansion node. When a raw user query enters the system, an LLM generates an expanded query JSON containing:
* The original query text.
* A normalized MSA translation (if colloquial or English).
* A list of core Islamic financial equivalents (e.g., "lease-to-own" $\rightarrow$ *الإجارة المنتهية بالتمليك*).



---

### Section 3: Domain-Specific Entity Extraction & Contract Alignment

Before querying the vector database, the chatbot must confidently align loose conversational descriptions with structural Sharia contract types.

```
[User Query: "I want to buy a car through a bank where they buy it first then sell it to me with a profit margin in installments"]
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │    GLiNER (Zero-Shot NER)     │ ──► Labels Extracted:
                   └───────────────────────────────┘     {"Action": "buy", "Structure": "installments"}
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │    GLinker (Entity Linker)    │ ──► Maps behavior to standardized concept:
                   └───────────────────────────────┘     "Murabaha to the Purchase Orderer" (مرابحة للأمر بالشراء)
                                   │
                                   ▼
                    [Targeted Vector Index Query]
                    Filters: {"standard_title": "Murabaha"}

```

* **Zero-Shot Information Extraction:** Use **GLiNER** to perform low-latency, zero-shot entity extraction on the query. Unlike rigid legacy NER models, you pass arbitrary, real-time labels directly into GLiNER:
```python

```



labels = ["financial_contract", "payment_method", "underlying_asset", "prohibited_element"]
entities = model.predict_entities(user_query, labels, threshold=0.5)

```
*   **Concept Linking:** Pipe GLiNER’s outputs into **GLinker** to resolve surface-level variants against a unified dictionary of standardized operations. This ensures that terms like "profit-sharing deposit account" link directly to the *Mudaraba* standard vector space, accelerating search accuracy.

---

### Section 4: Stateful Chain-of-Thought (CoT) Clarification Loop with Human-in-the-Loop
When user statements lack critical information (e.g., *"Is crypto trading halal?"*), the system must step back and request specific details (the exact asset backing, utility token structures, or staking mechanisms) before rendering a compliance judgment.

*   **Orchestration Framework:** Deploy **LangGraph** to build a stateful, cyclic agent framework. Unlike linear chains, LangGraph models the conversation as a directed graph where nodes act as functions and edges dictate state updates.
*   **Ambiguity Detection Logic:** Create a routing evaluator node. If the top candidate chunks fetched from the vector database yield a low confidence score or present conflicting conditions, the state transitions to a `Clarification Node`. This node uses a Chain-of-Thought framework to formulate targeted, conversational multi-turn questions.
*   **Human-in-the-Loop (HITL) Interruption:** Use LangGraph's native `interrupt` functionality. When an answer involves highly sensitive financial transactions or critical compliance rulings, the system pauses execution, saves the state to its persistence storage layer, and flags the transaction for a Sharia expert to review via an administrative interface before dispatching the answer back to the user.

---

## 📂 Open-Source Production Resources & Repositories

### 1. Document Extraction & Preprocessing
*   **Nassij (High-Accuracy Arabic PDF Parser):** [GitHub - logiccrafterdz/nassij](https://github.com/logiccrafterdz/nassij)
    *   *Utility:* High-fidelity text extraction from complex Arabic layouts, protecting original RTL scripts and alignments from fragmentation.
*   **CAMeL Tools (Arabic NLP Suite):** [GitHub - CAMeL-Lab/camel_tools](https://github.com/CAMeL-Lab/camel_tools)
    *   *Utility:* Provides morphological analysis, normalization, and dialect identification tools to clean up incoming conversational strings.

### 2. Multi-lingual Embedding & Retrieval Engines
*   **BGE-M3 (FlagEmbedding):** [GitHub - FlagOpen/FlagEmbedding](https://github.com/FlagOpen/FlagEmbedding)
    *   *Utility:* High-performance unified dense, sparse, and late-interaction multi-vector retriever designed for multi-lingual and cross-lingual RAG architectures.
*   **NeoAraBERT (SOTA Arabic Representations):** [HuggingFace - U4RASD/NeoAraBERT](https://huggingface.co/U4RASD/NeoAraBERT)
    *   *Utility:* Built on the NeoBERT backbone, optimized for parsing mixed classical, standard, and regional dialect text strings.

### 3. Entity Extraction & Information Linking
*   **GLiNER (Generalist Lightweight NER):** [GitHub - urchade/GLiNER](https://github.com/urchade/GLiNER)
    *   *Utility:* Performs arbitrary, zero-shot field and transaction-type extraction directly from multi-lingual user inputs without model fine-tuning.
*   **GLinker (Production Entity Linker):** [GitHub - Knowledgator/GLinker](https://github.com/Knowledgator/GLinker)
    *   *Utility:* Maps loose conversational terms to standardized financial dictionary terminology across a multi-layered cache system (Redis/Elasticsearch).

### 4. Agentic State Orchestration & HITL
*   **LangGraph (Stateful Multi-Agent Runtime):** [GitHub - langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)
    *   *Utility:* Orchestrates stateful, multi-turn clarification nodes and handles operational breakpoints for human-in-the-loop expert oversight.

```