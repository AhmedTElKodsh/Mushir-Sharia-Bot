# Scholar Review Guidance

Use review_item_number and operation_id to match rows across the bilingual, English, Arabic, and scrape-result CSV files.

For each operation, review the Mushir engine status, rationale, evidence fields, and AAOIFI reference candidates against the cited public artifact before accepting or correcting the result.

Fill human_scholar_supervision_review or human_scholar_review with one of: scholar_accepted, scholar_rejected, needs_more_evidence, or corrected_mapping.

When correcting, include the AAOIFI standard file number and title, the relevant section/page if available, and a short note explaining the correction so the row can become future model/evaluation feedback.

Leave rows as needs_more_evidence when the public source does not show enough contract, operation, or service detail to judge Sharia/AAOIFI alignment.
