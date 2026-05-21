# Source Registry Seeds

This directory is for small tracked registry seeds and source configuration for the planned Egypt financial institutions evidence corpus.

It is not the runtime scrape output folder.

Use it for:

- sector and regulator category definitions;
- baseline source pointers;
- small seed manifests derived from reviewed planning artifacts;
- validation fixtures that help future code reject missing regulator/source provenance.
- reviewed loader inputs that can be converted into `InstitutionRegistryRecord` rows by `src/governance/institution_pipeline.py`.

Do not store full raw websites, downloaded PDFs, extracted text dumps, logs, or private/gated material here. Runtime captures belong under `artifacts/l6_scrape/` or a configured external store.
