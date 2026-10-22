import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.main import (
    app,
    job_search_error_detail,
    search_jobs,
    _configured_jooble_api_key,
)


class JoobleSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api_key = "test-secret-key"
        self.environment = patch.dict(os.environ, {"JOOBLE_API_KEY": self.api_key})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client = TestClient(app)

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
                    }
                ],
                "total_count": 1,
            },
        )
        self.assertEqual(
            post.call_args.kwargs["json"],
            {"keywords": "Backend Engineer", "location": "Lagos, Nigeria"},
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


if __name__ == "__main__":
    unittest.main()
