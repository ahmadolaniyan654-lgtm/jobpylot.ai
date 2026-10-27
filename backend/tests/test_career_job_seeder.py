from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.career_skills import career_requirements
from backend import database
from scripts.add_career_test_jobs import build_samples, seed_jobs


SAMPLE_CITIES = ("Abuja", "Lagos", "Minna", "Ibadan", "Kano", "Port Harcourt")


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

        self.assertEqual(
            {sample[0] for sample in samples},
            set(career_requirements),
        )
        self.assertEqual(
            len(samples),
            len(career_requirements) * len(SAMPLE_CITIES),
        )
        for title in career_requirements:
            with self.subTest(title=title):
                career_samples = [sample for sample in samples if sample[0] == title]
                self.assertEqual(
                    {sample[2] for sample in career_samples},
                    set(SAMPLE_CITIES),
                )
                self.assertTrue(
                    all(sample[1].startswith("JobPylot TEST DATA ") for sample in career_samples)
                )
                self.assertTrue(
                    all("/jobpylot-test/" in sample[3] for sample in career_samples)
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
        self.assertEqual(inserted, len(build_samples()))
        self.assertEqual(skipped, 0)

        inserted_again, skipped_again = seed_jobs(self.db_path)
        self.assertEqual(inserted_again, 0)
        self.assertEqual(skipped_again, len(build_samples()))

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
                len(build_samples()) + 1,
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

    def test_city_search_returns_only_the_requested_city_for_each_career(self) -> None:
        seed_jobs(self.db_path)

        with patch.object(database, "DB_PATH", self.db_path):
            for title in career_requirements:
                for city in SAMPLE_CITIES:
                    with self.subTest(title=title, city=city):
                        rows = database.search_jobs(title, city)
                        self.assertEqual(len(rows), 1)
                        self.assertEqual(rows[0][1], title)
                        self.assertEqual(rows[0][3], city)


if __name__ == "__main__":
    unittest.main()
