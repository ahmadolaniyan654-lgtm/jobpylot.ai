from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.career_skills import career_requirements
from scripts.add_career_test_jobs import build_samples, seed_jobs


class CareerJobSeederTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.db_path = Path(self.temporary_directory.name) / "jobs.db"
        with closing(sqlite3.connect(self.db_path)) as connection, connection:
            connection.execute(
                """
                CREATE TABLE jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    company TEXT,
                    city TEXT,
                    application_link TEXT
                )
                """
            )

    def test_samples_follow_the_current_career_catalog(self) -> None:
        samples = build_samples()

        self.assertEqual([sample[0] for sample in samples], list(career_requirements))
        self.assertEqual(len(samples), len(career_requirements))
        self.assertTrue(
            {
                "Frontend Developer",
                "Backend Developer",
                "Full-Stack Developer",
                "Mobile App Developer",
                "Software Engineer",
                "DevOps Engineer",
                "Cloud Engineer",
                "UI/UX Designer",
                "Data Scientist",
                "AI/Machine Learning Engineer",
                "Database Administrator",
                "IT Support Specialist",
                "Network Engineer",
            }.issubset({sample[0] for sample in samples})
        )

    def test_repeated_seeding_preserves_existing_rows_and_schema(self) -> None:
        existing_row = (
            "Existing Listing",
            "Existing Company",
            "Lagos",
            "https://example.com/existing",
        )
        with closing(sqlite3.connect(self.db_path)) as connection, connection:
            connection.execute(
                """
                INSERT INTO jobs (title, company, city, application_link)
                VALUES (?, ?, ?, ?)
                """,
                existing_row,
            )
            original_schema = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'jobs'"
            ).fetchone()[0]

        inserted, skipped = seed_jobs(self.db_path)
        self.assertEqual(inserted, len(career_requirements))
        self.assertEqual(skipped, 0)

        inserted_again, skipped_again = seed_jobs(self.db_path)
        self.assertEqual(inserted_again, 0)
        self.assertEqual(skipped_again, len(career_requirements))

        with closing(sqlite3.connect(self.db_path)) as connection, connection:
            self.assertEqual(
                connection.execute(
                    "SELECT title, company, city, application_link FROM jobs WHERE title = ?",
                    (existing_row[0],),
                ).fetchone(),
                existing_row,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'jobs'"
                ).fetchone()[0],
                original_schema,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
                len(career_requirements) + 1,
            )
            self.assertEqual(
                {
                    row[0]
                    for row in connection.execute(
                        "SELECT title FROM jobs WHERE company LIKE 'JobPylot TEST DATA %'"
                    )
                },
                set(career_requirements),
            )


if __name__ == "__main__":
    unittest.main()
