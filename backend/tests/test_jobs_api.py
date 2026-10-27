import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.career_skills import career_requirements
from backend.main import (
    app,
    job_search_error_detail,
    search_jobs,
    _configured_jooble_api_key,
)
from backend import database


class JoobleSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api_key = "test-secret-key"
        self.environment = patch.dict(os.environ, {"JOOBLE_API_KEY": self.api_key})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.local_search_patcher = patch(
            "backend.main.search_local_jobs",
            return_value=[],
        )
        self.local_search = self.local_search_patcher.start()
        self.addCleanup(self.local_search_patcher.stop)
        self.client = TestClient(app)

    def test_database_connection_uses_project_root_database_path(self) -> None:
        expected_path = Path(database.__file__).resolve().parent.parent / "jobpylot.db"
        connection = Mock()

        with patch("backend.database.sqlite3.connect", return_value=connection) as connect:
            result = database.connect_db()

        self.assertEqual(database.DB_PATH, expected_path)
        connect.assert_called_once_with(expected_path)
        self.assertIs(result, connection)

    @staticmethod
    def response(status_code: int, data: object = None) -> Mock:
        response = Mock()
        response.status_code = status_code
        response.json.return_value = data
        return response

    def test_city_search_sends_selected_title_and_location(self) -> None:
        searches = (
            ("Backend Engineer", "Lagos"),
            ("Frontend Engineer", "Abuja"),
            ("Data Analyst", "Minna"),
        )
        listing = {
            "title": "Backend Engineer",
            "company": "Example Company",
            "location": "Lagos, Nigeria",
            "snippet": "Build backend services.",
            "updated": "2026-10-20",
            "link": "https://jobs.example/listing",
        }

        for title, city in searches:
            with self.subTest(title=title, city=city):
                with patch(
                    "backend.main.requests.post",
                    return_value=self.response(200, {"totalCount": 1, "jobs": [listing]}),
                ) as post:
                    result = search_jobs(title, city, "Nigeria", "Any")

                self.assertEqual(
                    post.call_args.kwargs["json"],
                    {"keywords": title, "location": f"{city}, Nigeria"},
                )
                self.assertEqual(
                    post.call_args.args[0],
                    f"https://jooble.org/api/{self.api_key}",
                )
                self.assertEqual(
                    post.call_args.kwargs["headers"],
                    {"Content-Type": "application/json"},
                )
                self.assertEqual(
                    post.call_args.kwargs["timeout"],
                    15,
                )
                self.assertEqual(result["jobs"][0]["title"], listing["title"])
                self.assertEqual(result["jobs"][0]["source"], "Jooble")
                self.assertEqual(result["jobs"][0]["url"], listing["link"])

    def test_empty_results_are_returned_without_claiming_no_jobs_exist(self) -> None:
        with patch(
            "backend.main.requests.post",
            return_value=self.response(200, {"totalCount": 0, "jobs": []}),
        ):
            result = search_jobs("Data Analyst", "Minna", "Nigeria", "Any")

        self.assertEqual(result["jobs"], [])
        self.assertEqual(result["total_count"], 0)

    def test_existing_title_only_search_remains_available(self) -> None:
        with patch(
            "backend.main.requests.post",
            return_value=self.response(200, {"jobs": []}),
        ) as post:
            result = search_jobs("Backend Engineer", "", "Nigeria", "Any")

        self.assertEqual(
            post.call_args.kwargs["json"],
            {"keywords": "Backend Engineer", "location": "Nigeria"},
        )
        self.assertEqual(result["city"], "Nigeria")
        self.local_search.assert_not_called()

    def test_missing_api_key_returns_clear_configuration_error(self) -> None:
        with (
            patch.dict(os.environ, {"JOOBLE_API_KEY": ""}),
            patch("backend.main.load_dotenv"),
        ):
            with self.assertRaises(HTTPException) as raised:
                search_jobs("Backend Engineer", "Lagos", "Nigeria", "Any")

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("JOOBLE_API_KEY", raised.exception.detail)

    def test_missing_process_key_is_reloaded_from_local_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / ".env"
            env_file.write_text(
                "JOOBLE_API_KEY=local-test-key\n",
                encoding="utf-8",
            )
            with (
                patch("backend.main.ENV_FILE", env_file),
                patch.dict(os.environ, {"JOOBLE_API_KEY": ""}),
            ):
                self.assertEqual(
                    _configured_jooble_api_key(),
                    "local-test-key",
                )

    def test_valid_process_key_takes_precedence_over_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / ".env"
            env_file.write_text(
                "JOOBLE_API_KEY=file-test-key\n",
                encoding="utf-8",
            )
            with (
                patch("backend.main.ENV_FILE", env_file),
                patch.dict(os.environ, {"JOOBLE_API_KEY": "process-test-key"}),
                patch("backend.main.load_dotenv") as load_dotenv,
            ):
                self.assertEqual(
                    _configured_jooble_api_key(),
                    "process-test-key",
                )
                load_dotenv.assert_not_called()

    def test_rejected_api_key_does_not_expose_key(self) -> None:
        with patch(
            "backend.main.requests.post",
            return_value=self.response(403),
        ):
            with self.assertRaises(HTTPException) as raised:
                search_jobs("Backend Engineer", "Lagos", "Nigeria", "Any")

        self.assertEqual(raised.exception.status_code, 502)
        self.assertNotIn(self.api_key, raised.exception.detail)

    def test_rate_limit_has_beginner_friendly_message(self) -> None:
        with patch(
            "backend.main.requests.post",
            return_value=self.response(429),
        ):
            with self.assertRaises(HTTPException) as raised:
                search_jobs("Backend Engineer", "Lagos", "Nigeria", "Any")

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("try again", raised.exception.detail)

    def test_job_search_error_detail_explains_503_response(self) -> None:
        responses = (
            self.response(
                503,
                {"detail": "Job search is not configured. Add a valid JOOBLE_API_KEY."},
            ),
            self.response(
                503,
                {"detail": "Jooble's search limit has been reached. Please try again."},
            ),
        )

        self.assertIn("JOOBLE_API_KEY", job_search_error_detail(responses[0]))
        self.assertIn("search limit", job_search_error_detail(responses[1]))

    def test_job_search_error_detail_ignores_unreadable_or_unexpected_response(self) -> None:
        unreadable = self.response(503)
        unreadable.json.side_effect = ValueError("invalid JSON")
        unexpected = self.response(503, {"detail": ["not", "text"]})
        missing = self.response(503, {"error": "unavailable"})

        self.assertIsNone(job_search_error_detail(unreadable))
        self.assertIsNone(job_search_error_detail(unexpected))
        self.assertIsNone(job_search_error_detail(missing))

    def test_network_error_is_sanitized(self) -> None:
        with patch(
            "backend.main.requests.post",
            side_effect=requests.ConnectionError(
                f"https://jooble.org/api/{self.api_key}"
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                search_jobs("Backend Engineer", "Lagos", "Nigeria", "Any")

        self.assertEqual(raised.exception.status_code, 502)
        self.assertNotIn(self.api_key, raised.exception.detail)

    def test_timeout_is_reported_separately_without_exposing_key(self) -> None:
        with patch(
            "backend.main.requests.post",
            side_effect=requests.Timeout(
                f"Request timed out for {self.api_key}"
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                search_jobs("Backend Engineer", "Lagos", "Nigeria", "Any")

        self.assertEqual(raised.exception.status_code, 504)
        self.assertIn("timed out", raised.exception.detail)
        self.assertNotIn(self.api_key, raised.exception.detail)

    def test_unexpected_api_response_is_reported(self) -> None:
        with patch(
            "backend.main.requests.post",
            return_value=self.response(200, {"unexpected": []}),
        ):
            with self.assertRaises(HTTPException) as raised:
                search_jobs("Backend Engineer", "Lagos", "Nigeria", "Any")

        self.assertEqual(raised.exception.status_code, 502)
        self.assertIn("unexpected response", raised.exception.detail)

    def test_arrangement_filter_uses_only_returned_listing_text(self) -> None:
        data = {
            "totalCount": 2,
            "jobs": [
                {"title": "Remote Data Analyst", "location": "Lagos"},
                {"title": "Data Analyst", "location": "Lagos"},
            ],
        }
        with patch(
            "backend.main.requests.post",
            return_value=self.response(200, data),
        ):
            result = search_jobs("Data Analyst", "Lagos", "Nigeria", "Remote")

        self.assertEqual([job["title"] for job in result["jobs"]], ["Remote Data Analyst"])

    def test_local_search_adds_sqlite_listing_without_arrangement_filter(self) -> None:
        local_row = (
            1,
            "Data Analyst",
            "Local Test Company",
            "Lagos",
            "https://example.invalid/local-listing",
        )
        with (
            patch(
                "backend.main.requests.post",
                return_value=self.response(200, {"totalCount": 7, "jobs": []}),
            ),
            patch("backend.main.search_local_jobs", return_value=[local_row]) as local_search,
        ):
            result = search_jobs(" Data Analyst ", " Lagos ", "Nigeria", "Remote")

        local_search.assert_called_once_with("Data Analyst", "Lagos")
        self.assertEqual(result["total_count"], 7)
        self.assertEqual(result["source"], "Jooble")
        self.assertEqual(
            result["jobs"],
            [
                {
                    "title": "Data Analyst",
                    "source": "SQLite",
                    "potentially_entry_level": False,
                    "company": "Local Test Company",
                    "location": "Lagos",
                    "url": "https://example.invalid/local-listing",
                }
            ],
        )

    def test_local_search_matches_user_skills_to_the_selected_career(self) -> None:
        local_row = (
            1,
            "Data Analyst",
            "Local Test Company",
            "Lagos",
            "https://example.invalid/local-listing",
        )
        with (
            patch(
                "backend.main.requests.post",
                return_value=self.response(200, {"jobs": []}),
            ),
            patch("backend.main.search_local_jobs", return_value=[local_row]),
        ):
            response = self.client.get(
                "/jobs",
                params=[
                    ("title", "Data Analyst"),
                    ("city", "Lagos"),
                    ("user_skills", "Python, SQL"),
                ],
            )

        self.assertEqual(response.status_code, 200)
        job = response.json()["jobs"][0]
        self.assertEqual(job["matched_skills"], ["python", "sql"])
        self.assertEqual(
            job["missing_skills"],
            [
                "excel",
                "power bi",
                "tableau",
                "statistics and probability",
                "data visualization",
            ],
        )
        self.assertAlmostEqual(job["match_score"], 200 / 7)

    def test_local_results_duplicate_of_jooble_are_skipped(self) -> None:
        jooble_listing = {
            "title": "Data Analyst",
            "company": "Example Company",
            "location": "Lagos",
            "link": "https://example.invalid/listing",
        }
        local_rows = [
            (
                1,
                " data ANALYST ",
                " example company ",
                "LAGOS",
                " https://example.invalid/listing ",
            ),
            (
                2,
                "Data Analyst",
                "Different Company",
                "Lagos",
                "https://example.invalid/other-listing",
            ),
        ]
        with (
            patch(
                "backend.main.requests.post",
                return_value=self.response(
                    200, {"totalCount": 1, "jobs": [jooble_listing]}
                ),
            ),
            patch("backend.main.search_local_jobs", return_value=local_rows),
        ):
            result = search_jobs("Data Analyst", "Lagos", "Nigeria", "Any")

        self.assertEqual(len(result["jobs"]), 2)
        self.assertEqual(result["jobs"][0]["source"], "Jooble")
        self.assertEqual(result["jobs"][1]["company"], "Different Company")
        self.assertEqual(result["jobs"][1]["source"], "SQLite")

    def test_local_search_errors_are_reported(self) -> None:
        with (
            patch(
                "backend.main.requests.post",
                return_value=self.response(200, {"jobs": []}),
            ),
            patch(
                "backend.main.search_local_jobs",
                side_effect=sqlite3.OperationalError("database unavailable"),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                search_jobs("Data Analyst", "Lagos", "Nigeria", "Any")

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("Local job search", raised.exception.detail)

    def test_empty_city_skips_local_search(self) -> None:
        with patch(
            "backend.main.requests.post",
            return_value=self.response(200, {"jobs": []}),
        ):
            result = search_jobs("Data Analyst", "", "Nigeria", "Any")

        self.local_search.assert_not_called()
        self.assertEqual(result["jobs"], [])

    def test_health_endpoint_returns_ok(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_home_endpoint_serves_the_search_page(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("JobPylot", response.text)

    def test_jobs_endpoint_validates_query_parameters(self) -> None:
        for params in (
            {},
            {"title": " "},
            {"title": "Backend Engineer", "arrangement": "Flexible"},
            {"title": "x" * 101},
        ):
            with self.subTest(params=params):
                response = self.client.get("/jobs", params=params)

                self.assertEqual(response.status_code, 422)

    def test_jobs_endpoint_returns_normalized_search_results(self) -> None:
        listing = {
            "title": "Backend Engineer",
            "company": "Example Company",
            "location": "Lagos, Nigeria",
            "snippet": "Build backend services.",
            "updated": "2026-10-20",
            "link": "https://jobs.example/listing",
        }

        with patch(
            "backend.main.requests.post",
            return_value=self.response(200, {"totalCount": 1, "jobs": [listing]}),
        ) as post:
            response = self.client.get(
                "/jobs",
                params={
                    "title": " Backend Engineer ",
                    "city": " Lagos ",
                    "country": " Nigeria ",
                    "arrangement": "Any",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "query": "Backend Engineer",
                "city": "Lagos",
                "country": "Nigeria",
                "arrangement": "Any",
                "source": "Jooble",
                "jobs": [
                    {
                        "title": "Backend Engineer",
                        "company": "Example Company",
                        "location": "Lagos, Nigeria",
                        "description": "Build backend services.",
                        "posted_at": "2026-10-20",
                        "url": "https://jobs.example/listing",
                        "source": "Jooble",
                        "potentially_entry_level": False,
                    }
                ],
                "total_count": 1,
            },
        )
        self.assertEqual(
            post.call_args.kwargs["json"],
            {"keywords": "Backend Engineer", "location": "Lagos, Nigeria"},
        )

    def test_jobs_endpoint_marks_entry_level_and_ordinary_titles(self) -> None:
        listings = [
            {"title": "  Junior Data Analyst ", "company": "Example Company"},
            {"title": "Senior Data Analyst", "company": "Example Company"},
            {"title": "", "company": "Example Company"},
            {"company": "Example Company"},
        ]

        with patch(
            "backend.main.requests.post",
            return_value=self.response(200, {"jobs": listings}),
        ):
            response = self.client.get(
                "/jobs",
                params={"title": "Data Analyst", "country": "Nigeria"},
            )

        self.assertEqual(response.status_code, 200)
        jobs = response.json()["jobs"]
        self.assertEqual(
            [job["potentially_entry_level"] for job in jobs],
            [True, False, False, False],
        )
        self.assertEqual(jobs[0]["title"], "Junior Data Analyst")
        self.assertEqual(jobs[0]["company"], "Example Company")

    def test_jobs_endpoint_matches_user_skills_against_structured_requirements(self) -> None:
        listing = {
            "title": "Junior Data Analyst",
            "snippet": "Build reports using Python and Power BI.",
            "required_skills": ["Python", "SQL", "Power BI"],
        }

        with patch(
            "backend.main.requests.post",
            return_value=self.response(200, {"jobs": [listing]}),
        ):
            response = self.client.get(
                "/jobs",
                params=[
                    ("title", "Data Analyst"),
                    ("country", "Nigeria"),
                    ("user_skills", "Python"),
                    ("user_skills", "Excel"),
                ],
            )

        self.assertEqual(response.status_code, 200)
        job = response.json()["jobs"][0]
        self.assertEqual(job["matched_skills"], ["python"])
        self.assertEqual(job["missing_skills"], ["sql", "power bi"])
        self.assertAlmostEqual(job["match_score"], 100 / 3)
        self.assertTrue(job["potentially_entry_level"])
        self.assertEqual(job["title"], "Junior Data Analyst")

    def test_jobs_endpoint_uses_career_requirements_without_inferencing_description(self) -> None:
        listing = {
            "title": "Data Analyst",
            "snippet": "Requires Python, SQL, and Power BI experience.",
        }

        with patch(
            "backend.main.requests.post",
            return_value=self.response(200, {"jobs": [listing]}),
        ):
            response = self.client.get(
                "/jobs",
                params={
                    "title": "Data Analyst",
                    "country": "Nigeria",
                    "user_skills": "Python",
                },
            )

        self.assertEqual(response.status_code, 200)
        job = response.json()["jobs"][0]
        self.assertEqual(job["description"], listing["snippet"])
        self.assertEqual(job["matched_skills"], ["python"])
        self.assertEqual(
            job["missing_skills"],
            [
                "excel",
                "sql",
                "power bi",
                "tableau",
                "statistics and probability",
                "data visualization",
            ],
        )
        self.assertAlmostEqual(job["match_score"], 100 / 7)

    def test_jobs_endpoint_prefers_structured_requirements_over_career_defaults(self) -> None:
        listing = {
            "title": "Data Analyst",
            "required_skills": ["R", "SQL"],
        }

        with patch(
            "backend.main.requests.post",
            return_value=self.response(200, {"jobs": [listing]}),
        ):
            response = self.client.get(
                "/jobs",
                params={
                    "title": "Data Analyst",
                    "country": "Nigeria",
                    "user_skills": "SQL",
                },
            )

        self.assertEqual(response.status_code, 200)
        job = response.json()["jobs"][0]
        self.assertEqual(job["matched_skills"], ["sql"])
        self.assertEqual(job["missing_skills"], ["r"])
        self.assertEqual(job["match_score"], 50)

    def test_all_recent_career_additions_use_their_mapped_requirements(self) -> None:
        career_titles = (
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
        )

        for career_title in career_titles:
            with self.subTest(career_title=career_title):
                required_skills = career_requirements[career_title]
                user_skill = required_skills[0]
                with patch(
                    "backend.main.requests.post",
                    return_value=self.response(
                        200,
                        {"jobs": [{"title": career_title}]},
                    ),
                ):
                    response = self.client.get(
                        "/jobs",
                        params={
                            "title": career_title,
                            "country": "Nigeria",
                            "user_skills": user_skill,
                        },
                    )

                self.assertEqual(response.status_code, 200)
                job = response.json()["jobs"][0]
                self.assertEqual(job["matched_skills"], [user_skill.lower()])
                self.assertEqual(
                    job["missing_skills"],
                    [skill.lower() for skill in required_skills[1:]],
                )
                self.assertAlmostEqual(
                    job["match_score"],
                    100 / len(required_skills),
                )

    def test_jobs_endpoint_reports_missing_api_key_as_configuration_error(self) -> None:
        with (
            patch.dict(os.environ, {"JOOBLE_API_KEY": ""}),
            patch("backend.main.load_dotenv"),
        ):
            response = self.client.get(
                "/jobs",
                params={"title": "Data Analyst", "country": "Nigeria"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("JOOBLE_API_KEY", response.json()["detail"])

    def test_submit_job_successfully(self) -> None:
        with patch(
            'backend.main.add_job',
            return_value= True,
        ) as add_job:
            response = self.client.post(
                '/jobs',
                json={
                    'title' : 'python developer',
                    'company' : 'Tech Company',
                    'city' : 'Minna',
                    'application_link' : 'https://example.com/jobs/python',
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {'message': 'Job submitted successfully'},
        )
        add_job.assert_called_once()
    def test_submit_duplicate_job_returns_conflict(self) -> None:
        with patch(
            'backend.main.add_job',
            return_value = False,
        ) as add_job:
            response = self.client.post(
                '/jobs',
                json= {
                    'title' : 'python developer',
                    'company' :'Tech Company',
                    'city' : 'Minna',
                    'application_link' :'https://example.com/jobs/python',
                }
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(),
            {'detail' : 'This job already exists'}
        )
        add_job.assert_called_once()

    def test_submit_job_with_empty_title_returns_bad_request(self) -> None:
        with patch(
            'backend.main.add_job',
            return_value = True,
        ) as add_job:
            response = self.client.post(
                '/jobs',
                json = {
                    'title' : ' ',
                    'company' : 'Tech Company',
                    'city' : 'Minna',
                    'application_link' : 'https://example.com/jobs/python',
                }
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {'detail' : 'Title, company, and city cannot be empty.'}
        )
        add_job.assert_not_called()
        
    def test_submit_job_with_empty_company_returns_bad_request(self) -> None:
        with patch(
            'backend.main.add_job',
            return_value = True,
        ) as add_job:
            response = self.client.post(
                '/jobs',
                json = {
                    'title' : 'python developer',
                    'company' : ' ',
                    'city' : 'Minna',
                    'application_link' : 'https://example.com/jobs/python',
                }
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {'detail' : 'Title, company, and city cannot be empty.'}
        )
        add_job.assert_not_called()

    def test_submit_job_with_empty_city_returns_bad_request(self) -> None:
        with patch(
            'backend.main.add_job',
            return_value= True,
        ) as add_job:
            response = self.client.post(
                '/jobs',
                json = {
                    'title' : 'python developer',
                    'company' : 'Tech Company',
                    'city' : ' ',
                    'application_link' :'https://example.com/jobs/python',
                }
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {'detail' : 'Title, company, and city cannot be empty.'}
        )
        add_job.assert_not_called()




if __name__ == "__main__":
    unittest.main()
