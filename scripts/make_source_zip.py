#!/usr/bin/env python3
"""Build a source-only archive without credentials, runtime data, or uploads."""
from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules", "dist", "build",
    "__pycache__", ".pytest_cache", "htmlcov", "coverage", "uploads", "pgdata", "__MACOSX",
    "test-results", "playwright-report", ".vite", ".turbo", ".nyc_output", "logs", "log", "tmp", "temp",
}
EXCLUDED_SUFFIXES = {
    ".pyc", ".pyo", ".sqlite", ".sqlite3", ".sqlite-wal", ".sqlite-shm", ".sqlite3-journal",
    ".db", ".db-wal", ".db-shm", ".sql", ".dump", ".backup", ".bak", ".csv", ".tsv", ".jsonl", ".ndjson",
    ".zip", ".pdf", ".doc", ".docx", ".odt", ".rtf", ".ppt", ".pptx", ".xls", ".xlsx",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".log", ".pem", ".key", ".crt", ".p12", ".pfx", ".secret",
}


def included(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return False
    lowered_name = path.name.lower()
    if (path.name == ".DS_Store" or path.name.startswith(".coverage") or path.suffix.lower() in EXCLUDED_SUFFIXES
            or lowered_name.startswith(".log") or ".log." in lowered_name):
        return False
    if path.name == ".env.example":
        return True
    if path.name == ".env" or path.name.startswith(".env."):
        return False
    return path.is_file() and not path.is_symlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", nargs="?", default="/private/tmp/CandidateDashboardAAIRO-source.zip")
    destination = Path(parser.parse_args().archive).expanduser().resolve()
    if destination.exists():
        raise SystemExit(f"Refusing to overwrite existing archive: {destination}")
    if destination.is_relative_to(ROOT):
        raise SystemExit("Choose an archive destination outside the project directory.")
    destination.parent.mkdir(parents=True, exist_ok=True)

    files = sorted(path for path in ROOT.rglob("*") if included(path))
    if not any(path.name == ".env.example" for path in files):
        raise SystemExit("Expected .env.example template was not included.")
    with ZipFile(destination, "x", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
    print(f"Created source archive: {destination} ({len(files)} files)")


if __name__ == "__main__":
    main()
