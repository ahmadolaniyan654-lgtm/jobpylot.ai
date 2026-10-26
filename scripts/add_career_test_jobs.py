import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "jobpylot.db"

# Allow imports from the project root, even if launched from another directory.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.career_skills import career_requirements


LEGACY_SAMPLE_DETAILS = {
    "Data Analyst": ("Lagos", "https://example.invalid/jobpylot-test/listing-01"),
    "Web Developer": ("Abuja", "https://example.invalid/jobpylot-test/listing-02"),
    "Python Developer": ("Port Harcourt", "https://example.invalid/jobpylot-test/listing-03"),
    "Cybersecurity Analyst": ("Ibadan", "https://example.invalid/jobpylot-test/listing-04"),
    "Financial Accountant": ("Kano", "https://example.invalid/jobpylot-test/listing-05"),
    "Business Analyst": ("Enugu", "https://example.invalid/jobpylot-test/listing-06"),
    "Marketing Officer": ("Kaduna", "https://example.invalid/jobpylot-test/listing-07"),
    "Head of a Company": ("Benin City", "https://example.invalid/jobpylot-test/listing-08"),
    "Project Manager": ("Jos", "https://example.invalid/jobpylot-test/listing-09"),
    "Physiotherapist": ("Ilorin", "https://example.invalid/jobpylot-test/listing-10"),
    "Civil Engineer": ("Abeokuta", "https://example.invalid/jobpylot-test/listing-11"),
    "Electrical and Electronics Engineer": ("Uyo", "https://example.invalid/jobpylot-test/listing-12"),
    "Chemical Engineer": ("Owerri", "https://example.invalid/jobpylot-test/listing-13"),
    "Food Engineer": ("Asaba", "https://example.invalid/jobpylot-test/listing-14"),
    "Architect": ("Maiduguri", "https://example.invalid/jobpylot-test/listing-15"),
    "Mechanical Engineer": ("Calabar", "https://example.invalid/jobpylot-test/listing-16"),
    "Agricultural and Bioresources Engineer": ("Akure", "https://example.invalid/jobpylot-test/listing-17"),
    "Psychologist": ("Warri", "https://example.invalid/jobpylot-test/listing-18"),
    "Medical Laboratory Scientist": ("Bauchi", "https://example.invalid/jobpylot-test/listing-19"),
    "Nurse": ("Sokoto", "https://example.invalid/jobpylot-test/listing-20"),
    "Teacher/Lecturer": ("Minna", "https://example.invalid/jobpylot-test/listing-21"),
    "Shop Attendant": ("Onitsha", "https://example.invalid/jobpylot-test/listing-22"),
    "Cashier": ("Makurdi", "https://example.invalid/jobpylot-test/listing-23"),
    "Office Assistant": ("Ado-Ekiti", "https://example.invalid/jobpylot-test/listing-24"),
    "Economist": ("Yenagoa", "https://example.invalid/jobpylot-test/listing-25"),
    "Petroleum and Gas Engineer": ("Lafia", "https://example.invalid/jobpylot-test/listing-26"),
}

SAMPLE_CITIES = (
    "Lagos",
    "Abuja",
    "Port Harcourt",
    "Ibadan",
    "Kano",
    "Enugu",
    "Kaduna",
    "Benin City",
    "Jos",
    "Ilorin",
    "Abeokuta",
    "Uyo",
    "Owerri",
    "Asaba",
    "Maiduguri",
    "Calabar",
    "Akure",
    "Warri",
    "Bauchi",
    "Sokoto",
    "Minna",
    "Onitsha",
    "Makurdi",
    "Ado-Ekiti",
    "Yenagoa",
    "Lafia",
)


def build_samples() -> list[tuple[str, str, str, str]]:
    samples = []
    for index, title in enumerate(career_requirements, start=1):
        city, application_link = LEGACY_SAMPLE_DETAILS.get(
            title,
            (
                SAMPLE_CITIES[(index - 1) % len(SAMPLE_CITIES)],
                f"https://example.invalid/jobpylot-test/listing-{index:02d}",
            ),
        )
        samples.append(
            (
                title,
                f"JobPylot TEST DATA {index:02d}",
                city,
                application_link,
            )
        )
    return samples


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
                    WHERE title = ? AND company = ? AND city = ? AND application_link = ?
                    LIMIT 1
                    """,
                    sample,
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
    print(f"Inserted {inserted} listings; skipped {skipped} exact matches.")


if __name__ == "__main__":
    main()
