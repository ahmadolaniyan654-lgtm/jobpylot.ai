import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_FILE)

app = FastAPI(title="JobPylot AI API")

JOOBLE_API_URL = "https://jooble.org/api"
JOB_REQUEST_TIMEOUT = 15
MAX_JOB_RESULTS = 50
ARRANGEMENT_PATTERNS = {
    "Remote": re.compile(r"\bremote(?:ly)?\b|\bwork from home\b|\bwfh\b", re.IGNORECASE),
    "Hybrid": re.compile(r"\bhybrid\b", re.IGNORECASE),
    "Onsite": re.compile(
        r"\bonsite\b|\bon[\s-]site\b|\bin[\s-]office\b|\boffice[\s-]based\b",
        re.IGNORECASE,
    ),
}


def _optional_text(job: Mapping[str, object], field: str) -> str | None:
    value = job.get(field)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _configured_jooble_api_key() -> str:
    api_key = os.getenv("JOOBLE_API_KEY", "").strip()
    if not api_key or api_key == "YOUR_ACTUAL_API_KEY":
        load_dotenv(ENV_FILE, override=True)
        api_key = os.getenv("JOOBLE_API_KEY", "").strip()
    return api_key


def job_search_error_detail(response: requests.Response) -> str | None:
    try:
        data = response.json()
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    detail = data.get("detail")
    return detail.strip() if isinstance(detail, str) and detail.strip() else None


def _normalize_job(job: Mapping[str, object]) -> dict[str, str]:
    fields = {
        "title": "title",
        "company": "company",
        "location": "location",
        "description": "snippet",
        "posted_at": "updated",
        "url": "link",
    }
    normalized = {
        target: value
        for target, source in fields.items()
        if (value := _optional_text(job, source)) is not None
    }
    normalized["source"] = "Jooble"
    return normalized


def _matches_arrangement(job: Mapping[str, object], arrangement: str) -> bool:
    if arrangement == "Any":
        return True

    searchable_text = " ".join(
        value
        for field in ("title", "location", "snippet")
        if (value := _optional_text(job, field)) is not None
    )
    pattern = ARRANGEMENT_PATTERNS[arrangement]
    return bool(pattern.search(searchable_text))


def _search_jooble(
    title: str,
    city: str,
    country: str,
    arrangement: str,
) -> tuple[list[dict[str, str]], int | None]:
    api_key = _configured_jooble_api_key()
    if not api_key or api_key == "YOUR_ACTUAL_API_KEY":
        raise HTTPException(
            status_code=503,
            detail="Job search is not configured. Add a valid JOOBLE_API_KEY to the .env file and restart the backend.",
        )

    try:
        response = requests.post(
            f"{JOOBLE_API_URL}/{api_key}",
            json={
                "keywords": title,
                "location": f"{city}, {country}" if city else country,
            },
            timeout=JOB_REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to Jooble. Check your connection and try again.",
        ) from None

    if response.status_code in (401, 403):
        raise HTTPException(
            status_code=502,
            detail="Jooble did not accept the API key. Check that JOOBLE_API_KEY is valid.",
        )
    if response.status_code == 429:
        raise HTTPException(
            status_code=503,
            detail="Jooble's search limit has been reached. Please wait a little and try again.",
        )
    if response.status_code >= 500:
        raise HTTPException(
            status_code=502,
            detail="Jooble is temporarily unavailable. Please try again later.",
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail="Jooble could not process this search. Check the search details and try again.",
        )

    try:
        data = response.json()
    except (ValueError, requests.RequestException):
        raise HTTPException(
            status_code=502,
            detail="Jooble returned an unreadable response. Please try again later.",
        ) from None

    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise HTTPException(
            status_code=502,
            detail="Jooble returned an unexpected response. Please try again later.",
        )

    jobs = [
        _normalize_job(job)
        for job in data["jobs"]
        if isinstance(job, Mapping) and _matches_arrangement(job, arrangement)
    ][:MAX_JOB_RESULTS]
    total_count = data.get("totalCount")
    if not isinstance(total_count, int) or isinstance(total_count, bool) or total_count < 0:
        total_count = None
    return jobs, total_count


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def home() -> FileResponse:
    html_file = Path(__file__).parent / "templates" / "index.html"
    return FileResponse(html_file)


@app.get("/jobs")
def search_jobs(
    title: str = Query(min_length=1, max_length=100, description="Desired job title"),
    city: str = Query(default="", max_length=100, description="City to search"),
    country: str = Query(default="Nigeria", min_length=1, max_length=100),
    arrangement: Literal["Any", "Onsite", "Hybrid", "Remote"] = "Any",
) -> dict[str, object]:
    title = title.strip()
    city = city.strip()
    country = country.strip()
    if not title or not country:
        raise HTTPException(
            status_code=422,
            detail="Enter a job title and country before searching.",
        )

    jobs, total_count = _search_jooble(title, city, country, arrangement)

    result: dict[str, object] = {
        "query": title,
        "city": city or country,
        "country": country,
        "arrangement": arrangement,
        "source": "Jooble",
        "jobs": jobs,
    }
    if total_count is not None:
        result["total_count"] = total_count
    return result
