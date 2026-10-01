"""Copy decision reviews between the remote PostgreSQL store and the local archive file.

  python scripts/backup_decision_reviews.py            # pull everything from Postgres into the local archive
  python scripts/backup_decision_reviews.py --ping-only  # just touch the database (for an external scheduler)

Safe to run repeatedly: records already in the archive are skipped. Run it from a scheduler
(for example a daily GitHub Actions job) so the database sees activity and a backup exists
even while the app itself is asleep.
"""
import argparse
import sys

from dotenv import load_dotenv


def backup(remote, archive, batch: int = 500) -> tuple[int, int]:
    """Return (records seen on the remote, records newly added to the archive). Annotations are copied too."""
    before = archive.count()
    seen = 0
    for record in remote.iter_records(batch):
        archive.append(record, synced=True, ignore_duplicates=True)
        seen += 1
    for annotation in getattr(remote, "iter_annotations", lambda: ())():
        archive.insert_annotation(annotation, synced=True)
    return seen, archive.count() - before


def main(argv=None) -> int:
    load_dotenv()
    from src.storage.decision_review_store import _postgres_url, configured_archive_store
    from src.storage.postgres_decision_review_store import PostgresDecisionReviewStore

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ping-only", action="store_true", help="touch the database and exit")
    args = parser.parse_args(argv)
    url = _postgres_url()
    if not url:
        print("No PostgreSQL URL configured (DECISION_REVIEW_DATABASE_URL).", file=sys.stderr)
        return 2
    remote = PostgresDecisionReviewStore(url)
    if args.ping_only:
        remote.ping()
        print("database reachable")
        return 0
    archive = configured_archive_store()
    if archive is None:
        print("The local archive is disabled (DECISION_REVIEW_ARCHIVE_PATH=off).", file=sys.stderr)
        return 2
    seen, added = backup(remote, archive)
    print(f"{seen} records on the remote; {added} added to {archive.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
