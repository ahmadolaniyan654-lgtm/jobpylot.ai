import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\USER\OneDrive\Desktop\jobpylot Ai")
DB_PATH = PROJECT_ROOT / "jobpylot.db"

# Allow imports from the project root, even if launched from another directory.
sys.path.insert(0, str(PROJECT_ROOT))

from backend.career_skills import career_requirements


samples = [
    ("Data Analyst", "JobPylot TEST DATA 01", "Lagos", "https://example.invalid/jobpylot-test/listing-01"),
    ("Web Developer", "JobPylot TEST DATA 02", "Abuja", "https://example.invalid/jobpylot-test/listing-02"),
    ("Python Developer", "JobPylot TEST DATA 03", "Port Harcourt", "https://example.invalid/jobpylot-test/listing-03"),
    ("Cybersecurity Analyst", "JobPylot TEST DATA 04", "Ibadan", "https://example.invalid/jobpylot-test/listing-04"),
    ("Financial Accountant", "JobPylot TEST DATA 05", "Kano", "https://example.invalid/jobpylot-test/listing-05"),
    ("Business Analyst", "JobPylot TEST DATA 06", "Enugu", "https://example.invalid/jobpylot-test/listing-06"),
    ("Marketing Officer", "JobPylot TEST DATA 07", "Kaduna", "https://example.invalid/jobpylot-test/listing-07"),
    ("Head of a Company", "JobPylot TEST DATA 08", "Benin City", "https://example.invalid/jobpylot-test/listing-08"),
    ("Project Manager", "JobPylot TEST DATA 09", "Jos", "https://example.invalid/jobpylot-test/listing-09"),
    ("Physiotherapist", "JobPylot TEST DATA 10", "Ilorin", "https://example.invalid/jobpylot-test/listing-10"),
    ("Civil Engineer", "JobPylot TEST DATA 11", "Abeokuta", "https://example.invalid/jobpylot-test/listing-11"),
    ("Electrical and Electronics Engineer", "JobPylot TEST DATA 12", "Uyo", "https://example.invalid/jobpylot-test/listing-12"),
    ("Chemical Engineer", "JobPylot TEST DATA 13", "Owerri", "https://example.invalid/jobpylot-test/listing-13"),
    ("Food Engineer", "JobPylot TEST DATA 14", "Asaba", "https://example.invalid/jobpylot-test/listing-14"),
    ("Architect", "JobPylot TEST DATA 15", "Maiduguri", "https://example.invalid/jobpylot-test/listing-15"),
    ("Mechanical Engineer", "JobPylot TEST DATA 16", "Calabar", "https://example.invalid/jobpylot-test/listing-16"),
    ("Agricultural and Bioresources Engineer", "JobPylot TEST DATA 17", "Akure", "https://example.invalid/jobpylot-test/listing-17"),
    ("Psychologist", "JobPylot TEST DATA 18", "Warri", "https://example.invalid/jobpylot-test/listing-18"),
    ("Medical Laboratory Scientist", "JobPylot TEST DATA 19", "Bauchi", "https://example.invalid/jobpylot-test/listing-19"),
    ("Nurse", "JobPylot TEST DATA 20", "Sokoto", "https://example.invalid/jobpylot-test/listing-20"),
    ("Teacher/Lecturer", "JobPylot TEST DATA 21", "Minna", "https://example.invalid/jobpylot-test/listing-21"),
    ("Shop Attendant", "JobPylot TEST DATA 22", "Onitsha", "https://example.invalid/jobpylot-test/listing-22"),
    ("Cashier", "JobPylot TEST DATA 23", "Makurdi", "https://example.invalid/jobpylot-test/listing-23"),
    ("Office Assistant", "JobPylot TEST DATA 24", "Ado-Ekiti", "https://example.invalid/jobpylot-test/listing-24"),
    ("Economist", "JobPylot TEST DATA 25", "Yenagoa", "https://example.invalid/jobpylot-test/listing-25"),
    ("Petroleum and Gas Engineer", "JobPylot TEST DATA 26", "Lafia", "https://example.invalid/jobpylot-test/listing-26"),
]

def main() -> None:
    if len(samples) != 26 or [row[0] for row in samples] != list(career_requirements):
        raise RuntimeError("Sample titles do not exactly match career_requirements.")

    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Existing database not found: {DB_PATH}")

    # mode=rw prevents SQLite from creating a database if the path is unavailable.
    db_uri = f"{DB_PATH.as_uri()}?mode=rw"
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
                raise RuntimeError(f"The jobs table does not exist in {DB_PATH}.")

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

    print(
        f"Inserted {len(missing)} listings; "
        f"skipped {len(samples) - len(missing)} exact matches."
    )


if __name__ == "__main__":
    main()
