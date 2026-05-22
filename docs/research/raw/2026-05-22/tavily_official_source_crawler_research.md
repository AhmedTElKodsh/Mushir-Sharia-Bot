{
  "content": "# Official-source-first, provenance-safe crawler and extraction pipeline for completing Egyptian CBE / FRA registries\n\n## Executive summary\nDesign an evidence-first pipeline that (a) prioritises CBE and FRA official artifacts as sole compliance evidence, (b) treats third‑party sites as discovery signals only, and (c) records immutable provenance for every harvested artifact (HTTP response, original PDF, snapshot). Concrete crawling patterns, extraction logic (Arabic/English and mixed PDFs), provenance storage and deduplication heuristics are described below along with practical tooling guidance and known evidence gaps. [1], [2], [3]\n\n## Source prioritisation and discovery\n- Primary sources: seed with official CBE site and its sitemap to enumerate pages and PDFs as the highest-priority sources for bank and payment regulation artifacts [1], [2]. Treat FRA as an official authority for non‑bank licensing and registries; use FRA pages as primary seeds when available [3].\n- Fallback discovery: use sitemaps and site‑scoped search to find thin product pages and PDFs; expand keyword queries bidirectionally (English ↔ Arabic) using morphological and synonym expansion for Arabic (see example queries below) [1], [19].\n- Example discovery queries / heuristics (site: and phrase combos to prioritise official pages; use Arabic variants in parallel):\n  - \"site:cbe.org.eg filetype:pdf bank license\" (PDF-first)\n  - \"site:fra.gov.eg company register\" (FRA register seed — FRA domain assumed official)\n  - Product-focused expansion: bank name + (English product term OR Arabic product term) e.g. \"Faisal Bank Egypt New Car Murabaha\" and Arabic equivalents with Murabaha morphological variants; use synonym/morphological lists from Arabic IR research to expand queries programmatically [19]. [19], [1]\n\n## Crawling patterns per source type\n- CBE patterns:\n  - PDF-first: crawl sitemap entries and follow PDF links; download and store raw PDF bytes and headers immediately on discovery (high confidence official evidence) [1], [6].\n  - HTML-first with browser-fallback: fetch HTML; if link to PDF present, prefer PDF. If page requires client-side rendering to expose links or product details, invoke a headless browser via a controlled Chrome/CDP session and capture rendered DOM and screenshot alongside the raw HTTP response; store both as evidence [4], [6].\n  - Use browser only when static fetch reveals missing links or JavaScript-driven content (CDP control pattern described below) [4].\n- FRA patterns:\n  - If FRA exposes paginated registers or parameterised endpoints, iterate pages deterministically and record each page’s raw response, parameters used, and HTTP headers. Harvest linked official PDFs from each entry and treat those PDFs as primary evidence artifacts; for each PDF, store raw bytes and compute content integrity hashes [3], [6].\n  - If pagination and endpoints are not documented, use site sitemap and deterministic site-scoped query expansion to discover register endpoints (evidence gap: no FRA register URL patterns in the sources) [1], [3].\n- Thin/SEO-lite product pages and product PDFs:\n  - Use wide expansion to discover thin pages (see Search orchestration) and prefer linked official PDFs and downloadable brochures as evidence. If only thin HTML exists, capture full raw response + rendered DOM screenshot and mark as lower-evidence until corroborated by official PDF or register entry [6], [19].\n\n## Politeness, robots and legal checks\n- Parse and enforce robots.txt rules and crawl handling behaviour; adopt conservative retry/backoff consistent with crawler best practice (obey crawl-delay, treat 5xx robots.txt fetch errors per Google behaviour) [5].\n- Implement rate limiting by domain and exponential backoff on repeated server errors; session/cookie handling only when required to reach official content, and rotate session identities conservatively with session regeneration best practices for security [5], [4].\n- Record site terms/disclaimer crawl decisions; treat legal constraints as open-ended if unspecified in source material (e.g., CBE site includes a disclaimer about content use) [2].\n\n## Extraction and language handling\n- Text extraction:\n  - Born-digital PDFs: use text-layer extractors that preserve directionality and character order; several community tools and migration notes exist (pdfplumber, pypdf and PyMuPDF are referenced in community guidance) — validate Arabic visual order and apply bidi/reshaper corrections when necessary [7], [8].\n  - Scanned PDFs: apply Arabic-capable OCR engines; public experiments and tools demonstrate Arabic OCR is feasible but challenging (font/diacritics/quality issues) and benefit from image preprocessing [9], [12].\n- Tables:\n  - Use heuristic table detectors for born-digital PDFs (SPARTAN-style approaches) and fall back to OCR+layout reconstruction for scanned tables; commercial/OCR-capable systems are commonly used for scanned table reconstruction when accuracy is critical [10], [11].\n  - Post-process table cells with RTL-aware alignment (reverse columns where detected) and normalize numeric/date formats before ingestion [8], [10].\n- Entity heuristics:\n  - Extract canonical fields needed for registries: institution name variants, license/registration numbers, dates, contact details, product names. Combine pattern matching for structured fields (numbers, emails, phone patterns) with dictionary-based normalization of institution names and product-term expansion lists (Murabaha, car finance synonyms in Arabic/English) [24], [23], [19].\n\n## Evidence, provenance and deduplication model\n- Layered immutable storage:\n  - Store: (a) raw HTTP response bytes + headers; (b) original raw PDF bytes; (c) HTML snapshot and rendered DOM screenshot; (d) extracted normalized record(s) and extraction manifest.\n  - Compute and persist content hashes (e.g., SHA‑256) for raw artifacts and a manifest hash to provide integrity proof and timestamping for auditability [13], [14], [4].\n- Minimal per-item metadata (store at harvest time): source URL, domain identity (CBE/FRA tag), crawl timestamp, HTTP headers, response status, content-type, storage path, SHA‑256 (raw), extraction method/version, OCR confidence, normalized record IDs and links to originating artifact hashes [4], [13].\n- Deduplication and linkage:\n  - Use blocking + fuzzy string matching (SortedNeighbourhood, Jaro‑Winkler, edit-distance) to group candidate duplicates, then deterministic merges that preserve all source artifact links (do not replace provenance) [15], [16], [17], [18].\n  - Strict policy: accept only official artifacts (CBE/FRA PDFs or register entries) as compliance evidence; third‑party snippets remain discovery signals and are never elevated to evidence without a corresponding official artifact.\n\n## Search orchestration and wide expansion for thin pages\n- Orchestrate discovery with iterative query expansion (English ↔ Arabic synonyms; morphological expansions) and site-scoped queries to broaden recall; semantic expansion techniques for Arabic improve retrieval of product pages and variant terminology [19].\n- Prioritisation: prefer direct official PDFs and register endpoints, then rendered official pages, then thin product HTML. Use incremental re-crawl triggers when official sources publish updates (monitor CBE sitemap changes) [1], [21].\n\n## Operational defaults and alternatives\n- Sensible PoC defaults: modular fetcher (stateless workers), headless-browser pool (CDP-controlled) for fallbacks, object store for raw artifacts (S3 or equivalent), metadata DB for manifests (relational or document DB), search index for discovery and dedupe. These design choices mirror recommended architectures for scalable crawling and data separation of bytes/metadata [6], [21], [22].\n- Alternatives and trade-offs: fully managed OCR (Google Document AI / Amazon Textract) can speed development but introduces vendor dependency; local OCR stacks provide control but require heavier ops and may lower accuracy on Arabic scans [11], [12].\n\n## Tooling (names found in evidence) and integration notes\n- Fetching/browser fallback: Kraaler-style CDP control pattern for Chrome headless to capture rendered DOM and screenshots; record raw bodies separately from metadata [4]. Integration: use static fetch + CDP-only when JS necessary; store both artifacts.\n- HTML parsing: Beautiful Soup pattern shown in AWS guidance for HTML parsing after fetch [6]. Integration: lightweight parser for text + link extraction; fall back to browser-rendered DOM.\n- PDF/text extraction: PyMuPDF demonstrated for Arabic table extraction; pdfplumber and pypdf referenced for Arabic text issues and directionality fixes [8], [7]. Integration: extract text, validate RTL order, apply bidi/reshaper corrections.\n- OCR and scanned PDFs: i2OCR experimentation and Arabic OCR research point to pre-processing + OCR pipelines; commercial engines cited as higher-accuracy options for scanned tables [12], [9], [11].\n- Table detection: SPARTAN/heuristic approaches for born-digital table extraction; fall back to OCR+layout reconstruction for scans [10], [11].\n- Deduplication / record linkage: recordlinkage library techniques (SortedNeighbourhood) and fuzzy matching approaches (Jaro‑Winkler, blocking) are applicable for merging registry variants [15], [16], [17], [18].\n- Evidence-lineage: follow manifest + SHA‑256 patterns as used in SEC evidence example; timestamp and persist manifest hashes for auditability [13], [14].\n\nEvidence gaps\n- No FRA paginated company_records endpoint URL or concrete FRA register API patterns are present in the findings; register crawling patterns for FRA must be validated against live FRA endpoints [3].\n- The evidence set does not include GitHub repository URLs, license details, or activity indicators (stars/commits) for the open-source tools referenced; repository links and maintenance signals must be collected before final tooling selection.\n- No explicit archive (e.g., Wayback) usage patterns or archive URLs are present in the sources.\n\n## References\n[1] https://cbe.org.eg/sitemap.xml\n[2] https://cbe.org.eg/en\n[3] https://devex.com/organizations/financial-regulatory-authority-fra-egypt-127640\n[4] https://dl.ifip.org/db/conf/tma/tma2019/TMA_Paper_20.pdf\n[5] https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec\n[6] https://docs.aws.amazon.com/prescriptive-guidance/latest/web-crawling-system-esg-data/architecture.html\n[7] https://stackoverflow.com/questions/75050321/extracting-text-from-pdf-in-arabic-language-and-getting-backwards-text\n[8] https://youtube.com/watch?v=-V5zjhQ2UZs\n[9] https://arxiv.org/html/2312.11812v1\n[10] https://nature.com/articles/s41598-026-44325-7\n[11] https://lido.app/blog/best-table-extraction-software\n[12] https://i2ocr.com/pdf-ocr-arabic\n[13] https://sec.gov/files/ctf-written-fcck-pilot-evidence-02-16-2026.pdf\n[14] https://originstamp.com/en/blog/reader/trusted-timestamping-explained\n[15] https://recordlinkage.readthedocs.io/en/latest/guides/data_deduplication.html\n[16] https://senzing.com/what-is-fuzzy-matching\n[17] https://winpure.com/fuzzy-matching-guide\n[18] https://latentview.com/blog/understanding-fuzzy-data-deduplication\n[19] https://aclanthology.org/W14-3611.pdf\n[20] https://mobileaction.co/blog/custom-product-pages-for-global-expansion\n[21] https://ssa.group/blog/5-best-practices-for-scaling-your-web-crawling-infrastructure-successfully\n[22] https://ocaml.org/success-stories/petabyte-scale-web-crawling-and-data-processing\n[23] https://assets.kpmg.com/content/dam/kpmg/eg/other/KPMG%20POV%20-%20CBE%20Payment%20Tokenization%20Guidelines.pdf\n[24] https://eg.andersen.com/wp-content/uploads/2024/12/Register-a-Bank-in-Egypt-Legal-and-Tax-Considerations.pdf\n[25] https://ykgglobal.com/local-page/egypt-company-registry",
  "sources": [
    {
      "url": "https://cbe.org.eg/sitemap.xml",
      "title": "[XML] https://cbe.org.eg/sitemap.xml",
      "favicon": "https://cbe.org.eg/assets/cbe/img/favicon/apple-icon-144x144.png"
    },
    {
      "url": "https://www.cbe.org.eg/en",
      "title": "Home",
      "favicon": "https://cbe.org.eg/assets/cbe/img/favicon/apple-icon-144x144.png"
    },
    {
      "url": "https://eg.andersen.com/wp-content/uploads/2024/12/Register-a-Bank-in-Egypt-Legal-and-Tax-Considerations.pdf",
      "title": "[PDF] Part 1. The Legal and Regulatory Framework - Andersen in Egypt",
      "favicon": "https://eg.andersen.com/wp-content/uploads/2021/02/andersen-logo.jpg"
    },
    {
      "url": "https://www.devex.com/organizations/financial-regulatory-authority-fra-egypt-127640",
      "title": "Financial Regulatory Authority (FRA - Egypt) | Devex",
      "favicon": "https://www.devex.com/favicon.ico"
    },
    {
      "url": "https://www.ykgglobal.com/local-page/egypt-company-registry",
      "title": "Egypt Company Registry | Business Registration & Compliance with GAFI",
      "favicon": "https://www.ykgglobal.com/assets/img/favicon.png"
    },
    {
      "url": "https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec",
      "title": "How Google Interprets the robots.txt Specification | Google Crawling Infrastructure  |  Crawling infrastructure  |  Google for Developers",
      "favicon": "https://www.gstatic.com/devrel-devsite/prod/v579073a50c63499824df5a68b8922367066583d283ef78fdade1028efdb4ceb5/developers/images/touchicon-180-new.png"
    },
    {
      "url": "https://assets.kpmg.com/content/dam/kpmg/eg/other/KPMG%20POV%20-%20CBE%20Payment%20Tokenization%20Guidelines.pdf",
      "title": "[PDF] CBE Payment Tokenization Requirements - KPMG International",
      "favicon": "https://assets.kpmg.com/etc/designs/default/kpmg/favicons/favicon-32x32.png"
    },
    {
      "url": "https://www.youtube.com/watch?v=-V5zjhQ2UZs",
      "title": "How to Extract Table Data From Arabic Language PDF | Right-to-Left Text Handling",
      "favicon": "https://www.youtube.com/s/desktop/db09ef6e/img/favicon_144x144.png"
    },
    {
      "url": "https://stackoverflow.com/questions/75050321/extracting-text-from-pdf-in-arabic-language-and-getting-backwards-text",
      "title": "python - Extracting text from PDF in Arabic language and getting backwards text - Stack Overflow",
      "favicon": "https://stackoverflow.com/Content/Sites/stackoverflow/Img/apple-touch-icon.png?v=9168b8ec82a5"
    },
    {
      "url": "https://www.i2ocr.com/pdf-ocr-arabic",
      "title": "Free Arabic PDF OCR – Extract Arabic Text from Scanned PDFs",
      "favicon": "https://www.i2ocr.com/css/images/fav-icon.ico"
    },
    {
      "url": "https://arxiv.org/html/2312.11812v1",
      "title": "Advancements and Challenges in Arabic Optical Character Recognition: A Comprehensive Survey",
      "favicon": "https://arxiv.org/static/browse/0.3.4/images/icons/apple-touch-icon.png"
    },
    {
      "url": "https://www.nature.com/articles/s41598-026-44325-7",
      "title": "SPARTAN: automated table detection and extraction from documents using advanced OpenCV heuristics and OCR techniques | Scientific Reports",
      "favicon": "https://www.nature.com/static/images/favicons/nature/apple-touch-icon-f39cb19454.png"
    },
    {
      "url": "https://www.lido.app/blog/best-table-extraction-software",
      "title": "Best Table Extraction Software in 2026",
      "favicon": "https://cdn.prod.website-files.com/62b4c5fb2654ca32b9d9b38c/654c4aa61841ad95cb605041_Lido_Logo_SecondaryLogo_BlueGreenOrange%20(2).jpg"
    },
    {
      "url": "https://dl.ifip.org/db/conf/tma/tma2019/TMA_Paper_20.pdf",
      "title": "[PDF] Kraaler: A User-Perspective Web Crawler",
      "favicon": "https://dl.ifip.org/assets/favicon/apple-touch-icon.png"
    },
    {
      "url": "https://docs.aws.amazon.com/prescriptive-guidance/latest/web-crawling-system-esg-data/architecture.html",
      "title": "Architecture for a scalable web crawling system on AWS - AWS Prescriptive Guidance",
      "favicon": "https://docs.aws.amazon.com/assets/r/images/favicon.ico"
    },
    {
      "url": "https://originstamp.com/en/blog/reader/trusted-timestamping-explained",
      "title": "Trusted Timestamping & TSA: The Future of Data Integrity",
      "favicon": "https://originstamp.com/favicon.ico"
    },
    {
      "url": "https://www.sec.gov/files/ctf-written-fcck-pilot-evidence-02-16-2026.pdf",
      "title": "ctf-written-fcck-pilot-evidence-02-16-2026.pdf",
      "favicon": "https://www.sec.gov/themes/custom/uswds_sec/assets/img/favicons/apple-touch-icon.png"
    },
    {
      "url": "https://www.latentview.com/blog/understanding-fuzzy-data-deduplication",
      "title": "Understanding Fuzzy Data Deduplication | LatentView Analytics",
      "favicon": "https://www.latentview.com/favicon.ico"
    },
    {
      "url": "https://winpure.com/fuzzy-matching-guide",
      "title": "Fuzzy Data Matching Guide for Data-Driven Decision-Making - WinPure",
      "favicon": "https://winpure.com/wp-content/uploads/2024/04/WINPURE-SITE-ICON-300x300.png"
    },
    {
      "url": "https://senzing.com/what-is-fuzzy-matching",
      "title": "What is Fuzzy Matching? How It Works & Why It's Important - Senzing",
      "favicon": "https://senzing.com/nitropack_static/crzaQbtyeWSYnFXdIFjQVGcqpsKJVaBr/assets/images/optimized/rev-b857f32/senzing.com/wp-content/uploads/2024/05/cropped-Senzing-Favicon-180x180.jpg"
    },
    {
      "url": "https://recordlinkage.readthedocs.io/en/latest/guides/data_deduplication.html",
      "title": "Data deduplication — Python Record Linkage Toolkit 0.15 documentation",
      "favicon": "https://recordlinkage.readthedocs.io/favicon.ico"
    },
    {
      "url": "https://aclanthology.org/W14-3611.pdf",
      "title": "[PDF] Semantic Query Expansion for Arabic Information Retrieval",
      "favicon": "https://aclanthology.org/aclicon.ico"
    },
    {
      "url": "https://www.mobileaction.co/blog/custom-product-pages-for-global-expansion",
      "title": "How custom product pages support global expansion | MobileAction",
      "favicon": "https://www.mobileaction.co/wp-content/uploads/2025/05/cropped-favicon-1.png"
    },
    {
      "url": "https://www.ssa.group/blog/5-best-practices-for-scaling-your-web-crawling-infrastructure-successfully",
      "title": "5 Best practices for scaling web crawling infrastructure - SSA Group",
      "favicon": "https://www.ssa.group/wp-content/uploads/2020/11/favicon.png"
    },
    {
      "url": "https://ocaml.org/success-stories/petabyte-scale-web-crawling-and-data-processing",
      "title": "Petabyte-Scale Web Crawling and Data Processing · Success Stories",
      "favicon": "https://ocaml.org/_/ZDJmMjgzN2NkZmJlMzgxNGQxMTMxNGVlMzk1NzZkN2I/favicon.ico"
    }
  ],
  "status": "completed",
  "created_at": "2026-05-22T08:18:47.787982+00:00",
  "response_time": 211.82,
  "request_id": "bad57309-de13-4b35-9f9c-0753bd801486"
}
