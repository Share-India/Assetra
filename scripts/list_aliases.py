#!/usr/bin/env python3
"""
CLI tool to list and remove Fixed Asset Register (FAR) column aliases.

Usage:
    python scripts/list_aliases.py
    python scripts/list_aliases.py --status pending
    python scripts/list_aliases.py --remove <alias_id> [--force]
"""
import sys
import os
import argparse
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from database import SessionLocal
import models
import auth
from column_mapper import CANONICAL_FIELDS, save_alias_cache

def list_aliases(status_filter=None):
    db = SessionLocal()
    try:
        q = db.query(models.ColumnAliasCache, models.User.name).outerjoin(
            models.User, models.ColumnAliasCache.submitted_by == models.User.id
        )
        if status_filter:
            q = q.filter(models.ColumnAliasCache.status == status_filter.lower())
        rows = q.order_by(models.ColumnAliasCache.id.asc()).all()

        if not rows:
            print("\nNo column aliases found matching filter." if status_filter else "\nNo column aliases found in database.")
            return

        print("\n" + "=" * 110)
        print("FIXED ASSET REGISTER (FAR) - COLUMN ALIASES")
        print("=" * 110)
        header_line = f"{'ID':<5} | {'Original Header':<22} | {'Canonical Field':<20} | {'Status':<10} | {'Validation Summary':<30} | {'User ID':<8}"
        print(header_line)
        print("-" * 110)

        counts = {"approved": 0, "pending": 0, "rejected": 0}
        for alias, user_name in rows:
            counts[alias.status] = counts.get(alias.status, 0) + 1
            orig = (alias.original_header or alias.normalized_header or "")[:20]
            canon = alias.canonical_field[:18]
            st = alias.status.upper()
            summary = (alias.validation_summary or "Validation passed")[:28]
            user_str = f"#{alias.submitted_by}" if alias.submitted_by else "System"

            print(f"{alias.id:<5} | {orig:<22} | {canon:<20} | {st:<10} | {summary:<30} | {user_str:<8}")

        print("-" * 110)
        print(f"Total: {len(rows)} | Approved: {counts.get('approved', 0)} | Pending: {counts.get('pending', 0)} | Rejected: {counts.get('rejected', 0)}\n")
    finally:
        db.close()


def remove_alias(alias_id: int, force: bool = False):
    db = SessionLocal()
    try:
        alias = db.query(models.ColumnAliasCache).filter(models.ColumnAliasCache.id == alias_id).first()
        if not alias:
            print(f"\n[ERROR] Column alias #{alias_id} does not exist in the database.")
            sys.exit(1)

        orig_header = alias.original_header or alias.normalized_header
        canon_field = alias.canonical_field
        norm_header = alias.normalized_header

        if not force:
            confirm = input(f"Are you sure you want to remove alias #{alias_id} ('{orig_header}' -> '{canon_field}')? [y/N]: ").strip().lower()
            if confirm not in ("y", "yes"):
                print("Removal cancelled.")
                return

        # Clean from memory cache
        if canon_field in CANONICAL_FIELDS and norm_header in CANONICAL_FIELDS[canon_field]:
            CANONICAL_FIELDS[canon_field] = [a for a in CANONICAL_FIELDS[canon_field] if a != norm_header]
        if canon_field == "major_category" and norm_header in CANONICAL_FIELDS.get("category", []):
            CANONICAL_FIELDS["category"] = [a for a in CANONICAL_FIELDS["category"] if a != norm_header]
        save_alias_cache()

        # Delete database record
        db.delete(alias)
        db.commit()

        # Audit log entry (User IDs only! Strictly no email addresses!)
        auth.record_audit_event(
            db=db,
            actor_id=None,
            action="COLUMN_ALIAS_REMOVED",
            target=f"alias_id:{alias_id}",
            user_email=None,
            status="SUCCESS",
            details=f"CLI scripts/list_aliases.py removed column alias #{alias_id} ('{orig_header}' -> '{canon_field}')"
        )

        print(f"\n[OK] Column alias #{alias_id} ('{orig_header}' -> '{canon_field}') removed successfully.")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="List and remove FAR column aliases from the command line.")
    parser.add_argument("--status", choices=["approved", "pending", "rejected"], help="Filter aliases by status")
    parser.add_argument("--remove", "-r", type=int, metavar="ALIAS_ID", help="Remove an alias by its numeric ID")
    parser.add_argument("--force", "-f", action="store_true", help="Skip confirmation prompt when removing an alias")

    args = parser.parse_args()

    if args.remove is not None:
        remove_alias(args.remove, force=args.force)
    else:
        list_aliases(status_filter=args.status)


if __name__ == "__main__":
    main()
