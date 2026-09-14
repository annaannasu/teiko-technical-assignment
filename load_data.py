"""Create cell_counts.db in the repository root and load cell-count.csv."""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "cell-count.csv"
DB_PATH = ROOT / "cell_counts.db"
SCHEMA_PATH = ROOT / "schema.sql"
POPULATIONS = ("b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte")


def clean(value: str) -> str | None:
    value = value.strip()
    return value.lower() if value else None


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {CSV_PATH}")
    DB_PATH.unlink(missing_ok=True)
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.executescript(SCHEMA_PATH.read_text())
        seen_subjects: dict[str, tuple] = {}
        with CSV_PATH.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            required = {"project", "subject", "condition", "age", "sex", "treatment",
                        "response", "sample", "sample_type", "time_from_treatment_start",
                        *POPULATIONS}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"CSV is missing columns: {sorted(missing)}")
            with connection:
                for row_number, row in enumerate(reader, start=2):
                    subject = row["subject"].strip()
                    metadata = (row["project"].strip(), row["condition"].strip().lower(),
                                int(row["age"]), row["sex"].strip().upper(),
                                row["treatment"].strip().lower(), clean(row["response"]))
                    if subject in seen_subjects and seen_subjects[subject] != metadata:
                        raise ValueError(f"Inconsistent metadata for {subject} at row {row_number}")
                    if subject not in seen_subjects:
                        connection.execute(
                            "INSERT INTO subjects VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (subject, *metadata),
                        )
                        seen_subjects[subject] = metadata
                    sample = row["sample"].strip()
                    connection.execute(
                        "INSERT INTO samples VALUES (?, ?, ?, ?)",
                        (sample, subject, row["sample_type"].strip().upper(),
                         float(row["time_from_treatment_start"])),
                    )
                    connection.executemany(
                        "INSERT INTO cell_counts VALUES (?, ?, ?)",
                        [(sample, population, int(row[population])) for population in POPULATIONS],
                    )
        sample_count = connection.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
        count_count = connection.execute("SELECT COUNT(*) FROM cell_counts").fetchone()[0]
        if count_count != sample_count * len(POPULATIONS):
            raise RuntimeError("Load validation failed: incomplete cell counts")
        print(f"Loaded {sample_count:,} samples and {count_count:,} counts into {DB_PATH.name}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
