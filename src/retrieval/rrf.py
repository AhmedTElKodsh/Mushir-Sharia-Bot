from typing import List, Any, Dict

def _result_id(item: Any) -> str:
    if isinstance(item, str):
        return item
    keys = ("doc_id", "chunk_id", "id")
    if isinstance(item, dict):
        for k in keys:
            val = item.get(k)
            if val is not None and val != "":
                return str(val)
        return ""
    for k in keys:
        val = getattr(item, k, None)
        if val is not None and val != "":
            return str(val)
    return ""

def rrf_merge(dense_results: List[Any], sparse_results: List[Any], k: int = 60) -> List[str]:
    """Return document IDs ranked by reciprocal-rank fusion."""

    scores: Dict[str, float] = {}
    for results in (dense_results or [], sparse_results or []):
        for rank, item in enumerate(results, start=1):
            doc_id = _result_id(item)
            if not doc_id:
                continue
            scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank))
    return [doc_id for doc_id, _ in sorted(scores.items(), key=lambda pair: pair[1], reverse=True)]
