import unittest

from backend.job_matcher import entry_level, match_job, match_skills


class JobMatcherTests(unittest.TestCase):
    def test_entry_level_titles_ignore_capitalization_and_extra_spaces(self) -> None:
        titles = (
            "  Software ENGINEER Internship  ",
            "  JUNIOR Data Analyst ",
            "Graduate TRAINEE ",
        )

        for title in titles:
            with self.subTest(title=title):
                self.assertTrue(entry_level(title))

    def test_ordinary_title_is_not_marked_entry_level(self) -> None:
        self.assertFalse(entry_level("  Senior Data Analyst  "))

    def test_match_job_preserves_skill_results_for_both_title_types(self) -> None:
        cases = (
            ("  Junior Data Analyst ", True),
            ("Senior Data Analyst", False),
        )

        for job_title, expected_entry_level in cases:
            with self.subTest(job_title=job_title):
                result = match_job(
                    job_title,
                    ["Python", "SQL", "Excel"],
                    ["Python", "SQL", "Power BI"],
                )

                self.assertEqual(
                    result["potentially_entry_level"],
                    expected_entry_level,
                )
                self.assertEqual(result["matched_skills"], ["python", "sql"])
                self.assertEqual(result["missing_skills"], ["power bi"])
                self.assertAlmostEqual(result["match_score"], 200 / 3)

    def test_existing_match_skills_interface_is_unchanged(self) -> None:
        self.assertEqual(
            match_skills(["Python"], ["Python", "SQL"]),
            (["python"], ["sql"], 50),
        )


if __name__ == "__main__":
    unittest.main()
