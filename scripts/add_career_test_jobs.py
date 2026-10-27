import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "jobpylot.db"

# Allow imports from the project root, even if launched from another directory.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.career_skills import career_requirements

SAMPLE_CITIES = (
    "Abuja",
    "Lagos",
    "Minna",
    "Ibadan",
    "Kano",
    "Port Harcourt",
)


def build_samples() -> list[tuple[str, str, str, str]]:
    return [
        (
            title,
            f"JobPylot TEST DATA {career_index:02d}",
            city,
            (
                "https://example.invalid/jobpylot-test/"
                f"listing-{career_index:02d}-{city_index:02d}"
            ),
        )
        for career_index, title in enumerate(career_requirements, start=1)
        for city_index, city in enumerate(SAMPLE_CITIES, start=1)
    ]


def seed_jobs(db_path: Path) -> tuple[int, int]:
    if not db_path.is_file():
        raise FileNotFoundError(f"Existing database not found: {db_path}")

    # mode=rw prevents SQLite from creating a database if the path is unavailable.
    db_uri = f"{db_path.resolve().as_uri()}?mode=rw"
    conn = sqlite3.connect(db_uri, uri=True)

    try:
        with conn:
            # Reserve the write transaction before checking duplicates.
            conn.execute("BEGIN IMMEDIATE")

            table_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                ("jobs",),
            ).fetchone()

            if table_exists is None:
                raise RuntimeError(f"The jobs table does not exist in {db_path}.")

            samples = build_samples()
            missing = []
            for sample in samples:
                existing = conn.execute(
                    """
                    SELECT 1 FROM jobs
                    WHERE LOWER(title) = LOWER(?)
                    AND LOWER(company) = LOWER(?)
                    AND LOWER(city) = LOWER(?)
                    LIMIT 1
                    """,
                    sample[:3],
                ).fetchone()

                if existing is None:
                    missing.append(sample)

            conn.executemany(
                """
                INSERT INTO jobs (title, company, city, application_link)
                VALUES (?, ?, ?, ?)
                """,
                missing,
            )
    finally:
        conn.close()

    return len(missing), len(samples) - len(missing)


def main() -> None:
    inserted, skipped = seed_jobs(DB_PATH)
    print(f"Inserted {inserted} listings; skipped {skipped} existing career/city listings.")


if __name__ == "__main__":
    main()
