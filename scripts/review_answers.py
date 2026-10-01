"""Filter, export and count the committed decision review records (operator use only).

  python scripts/review_answers.py --stats
  python scripts/review_answers.py --lane described_operation --status INSUFFICIENT_DATA --since 7d
  python scripts/review_answers.py --gate approved_rule --language ar --format csv --out withheld-ar.csv

Reads the full local archive when it exists, otherwise the working store (override with --db).
Opening an older file adds the classification columns (an additive migration); nothing is deleted.
Records hold user queries and internal signals: keep exports local and out of version control.
"""
import argparse
import csv
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # Runnable as a plain script from any directory.

TABLE_COLUMNS = ("recorded_at", "lane", "status", "language", "deciding_gate", "reason_code", "query")


def parse_since(value: str) -> datetime:
    """'7d', '24h', '30m' relative to now, or an ISO date/datetime (UTC when no zone is given)."""
    match = re.fullmatch(r"\s*(\d+)\s*([dhm])\s*", value or "")
    if match:
        amount, unit = int(match[1]), match[2]
        return datetime.now(UTC) - timedelta(**{{"d": "days", "h": "hours", "m": "minutes"}[unit]: amount})
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"--since must look like 7d, 24h or 2026-10-01, not {value!r}")
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def row_of(record) -> dict:
    from src.models.decision_audit import classify
    return {"recorded_at": record.recorded_at.astimezone(UTC).isoformat(timespec="seconds"),
            "review_id": record.review_id, **classify(record), "query": record.query}


def default_db() -> Path:
    from src.storage.decision_review_store import DEFAULT_ARCHIVE_PATH, DEFAULT_DB_PATH
    import os
    archive = os.getenv("DECISION_REVIEW_ARCHIVE_PATH") or DEFAULT_ARCHIVE_PATH
    if archive.strip().lower() not in {"off", "none", "disabled"} and Path(archive).exists():
        return Path(archive)
    return Path(os.getenv("DECISION_REVIEW_DB_PATH") or DEFAULT_DB_PATH)


def write_rows(records, fmt: str, out) -> None:
    if fmt == "jsonl":  # Complete records, including internal signals, for offline review.
        for record in records:
            out.write(record.model_dump_json() + "\n")
        return
    rows = [row_of(record) for record in records]
    if fmt == "csv":
        writer = csv.DictWriter(out, fieldnames=list(rows[0]) if rows else ["review_id"])
        writer.writeheader()
        writer.writerows(rows)
        return
    widths = {c: max([len(c)] + [len(str(r.get(c) or "-")[:60]) for r in rows]) for c in TABLE_COLUMNS}
    out.write("  ".join(c.ljust(widths[c]) for c in TABLE_COLUMNS) + "\n")
    for r in rows:
        out.write("  ".join(str(r.get(c) or "-")[:60].ljust(widths[c]) for c in TABLE_COLUMNS) + "\n")
    out.write(f"{len(rows)} record(s)\n")


def main(argv=None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, help="SQLite review file (default: archive, else working store)")
    for name in ("lane", "status", "language", "reason", "mechanism"):
        parser.add_argument(f"--{name}")
    parser.add_argument("--gate", help="deciding gate, e.g. approved_rule, source, clarification")
    parser.add_argument("--since", type=parse_since, help="7d, 24h, 30m or an ISO date")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--format", choices=("table", "jsonl", "csv"), default="table")
    parser.add_argument("--out", type=Path, help="write to this file instead of stdout")
    parser.add_argument("--stats", action="store_true", help="counts per class plus size on disk")
    args = parser.parse_args(argv)

    from src.storage.decision_review_store import SQLiteDecisionReviewStore
    db = args.db or default_db()
    if not db.exists():
        print(f"No review store at {db}.", file=sys.stderr)
        return 2
    store = SQLiteDecisionReviewStore(db)
    if args.stats:
        print(json.dumps({"db": str(db), **store.stats()}, ensure_ascii=False, indent=2))
        return 0
    records = store.query(lane=args.lane, status=args.status, language=args.language, deciding_gate=args.gate,
                          reason_code=args.reason, mechanism=args.mechanism, since=args.since, limit=args.limit)
    if args.out:
        with args.out.open("w", newline="", encoding="utf-8") as handle:
            write_rows(records, args.format, handle)
        print(f"{len(records)} record(s) written to {args.out}", file=sys.stderr)
    else:
        write_rows(records, args.format, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
