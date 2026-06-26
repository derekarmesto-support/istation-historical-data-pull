#!/usr/bin/env python3
"""
filter_exports.py
=================
One-off script to filter Denver Language School exports by student ID.

Reads all CSV files from the Denver Language School folder on Google Drive,
filters rows matching the specified student ID(s), and saves filtered copies
locally on your Mac — Drive originals are never touched.

Usage:
  python filter_exports.py
"""

import csv
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

DRIVE_BASE = Path.home() / (
    "Library/CloudStorage/"
    "GoogleDrive-derek.armesto@amiralearning.com/"
    "My Drive"
)

PROJECT_LABEL  = "Historical Data Request (Istation) - April 2026 Pull"
DISTRICT       = "Denver Language School"
DISTRICT_STATE = "Florida"

# Student IDs to keep — add more as needed
STUDENT_IDS = {"904270"}

# Local folder where filtered files are saved
LOCAL_OUTPUT = Path.home() / "Documents" / "Istation Filtered Exports" / DISTRICT

# ID column name varies by report type
ASSESSMENT_ID_COL = "STUDENT_ID"
USAGE_ID_COL      = "ID"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def id_column_for(fieldnames: list) -> str | None:
    """Return the student ID column name for this file, or None if unrecognised."""
    if ASSESSMENT_ID_COL in fieldnames:
        return ASSESSMENT_ID_COL
    if USAGE_ID_COL in fieldnames:
        return USAGE_ID_COL
    return None


def filter_csv(src: Path, dst: Path, id_col: str) -> tuple:
    """
    Read src, write only rows where id_col is in STUDENT_IDS to dst.
    Returns (total_rows, kept_rows).
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp")

    total = kept = 0
    with open(src, newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = list(reader.fieldnames)

        with open(tmp, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            for row in reader:
                total += 1
                if str(row.get(id_col, "")).strip() in STUDENT_IDS:
                    writer.writerow(row)
                    kept += 1

    tmp.rename(dst)
    return total, kept


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    source_root = DRIVE_BASE / PROJECT_LABEL / DISTRICT_STATE / DISTRICT

    if not source_root.exists():
        print(f"❌ Source folder not found:\n   {source_root}")
        return

    print(f"📂 Source : {source_root}")
    print(f"📁 Output : {LOCAL_OUTPUT}")
    print(f"🔍 Filtering for student ID(s): {', '.join(sorted(STUDENT_IDS))}")
    print("=" * 70)

    csv_files = sorted(source_root.rglob("*.csv"))
    if not csv_files:
        print("⚠️  No CSV files found.")
        return

    processed = skipped = matched = 0

    for src in csv_files:
        relative = src.relative_to(source_root)
        dst = LOCAL_OUTPUT / relative

        with open(src, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            id_col = id_column_for(list(reader.fieldnames or []))

        if id_col is None:
            print(f"  ⚠️  Skipping (no ID column): {src.name}")
            skipped += 1
            continue

        total, kept = filter_csv(src, dst, id_col)
        processed += 1
        matched += kept
        print(f"  ✅  {relative}  —  {kept}/{total} rows kept")

    print("=" * 70)
    print(f"✔  Processed : {processed} files")
    print(f"   Skipped   : {skipped} files")
    print(f"   Rows kept : {matched} total across all files")
    print(f"\n📁 Filtered files saved to:\n   {LOCAL_OUTPUT}")


if __name__ == "__main__":
    main()
