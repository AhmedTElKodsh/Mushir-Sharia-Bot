# L6 Scrape Runtime Artifacts

Runtime scrape output belongs here during local development unless a run config points to external object storage.

Expected subfolders after implementation:

- `raw/` - downloaded public HTML, PDFs, XLSX, DOC/DOCX, and screenshots when allowed.
- `extracted_text/` - parser or OCR output.
- `metadata/` - crawl manifests, hashes, source provenance, and access-status records.
- `logs/` - bounded discovery, crawl, and extraction logs.
- `errors/` - parser failures, blocked pages, unreachable sites, and manual-review packets.

Generated runtime contents should remain out of git. Keep only this README tracked.
