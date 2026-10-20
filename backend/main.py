import re
import time

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="JobPylot AI API")

JOBS_API_URL = "https://himalayas.app/jobs/api"
MAX_JOB_BATCHES = 25
MAX_JOB_RESULTS = 5
JOB_REQUEST_TIMEOUT = 15
JOB_REQUEST_ATTEMPTS = 3

JOB_WORD_GROUPS = (
    {"accountant", "accountants", "accounting"},
    {"analyst", "analysts", "analysis", "analytic", "analytics"},
    {"architect", "architects", "architecture"},
    {"designer", "designers", "design", "designing"},
    {"developer", "developers", "development"},
    {"economist", "economists", "economic", "economics"},
    {"engineer", "engineers", "engineering"},
    {"lecturer", "lecturers", "teacher", "teachers", "teaching", "educator", "educators"},
    {"manager", "managers", "management"},
    {"marketer", "marketers", "marketing"},
    {"nurse", "nurses", "nursing"},
    {"programmer", "programmers", "programming"},
    {"psychologist", "psychologists", "psychology"},
    {"researcher", "researchers", "research"},
    {"scientist", "scientists", "science"},
)


def _word_forms(word: str) -> set[str]:
    forms = {word}
    for group in JOB_WORD_GROUPS:
        if word in group:
            forms.update(group)
    if len(word) > 4 and word.endswith("ies"):
        forms.add(word[:-3] + "y")
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        forms.add(word[:-1])
    if len(word) > 5 and word.endswith("ing"):
        stem = word[:-3]
        forms.update((stem, stem + "e"))
        if len(stem) > 2 and stem[-1] == stem[-2]:
            forms.add(stem[:-1])
    if len(word) > 4 and word.endswith("ed"):
        stem = word[:-2]
        forms.update((stem, stem + "e"))
        if len(stem) > 2 and stem[-1] == stem[-2]:
            forms.add(stem[:-1])
    return forms


def _title_matches(title: str, query_variants: list[list[str]]) -> bool:
    title_words = re.findall(r"[a-z0-9]+", title.casefold())
    title_forms = [_word_forms(word) for word in title_words]
    for query_words in query_variants:
        unmatched_title_words = list(title_forms)
        for query_word in query_words:
            query_forms = _word_forms(query_word)
            matching_index = next(
                (
                    index for index, forms in enumerate(unmatched_title_words)
                    if forms & query_forms
                ),
                None,
            )
            if matching_index is None:
                break
            unmatched_title_words.pop(matching_index)
        else:
            return True
    return False


def _is_nigeria_eligible(job: dict) -> bool:
    restrictions = job.get("locationRestrictions")
    return isinstance(restrictions, list) and any(
        isinstance(location, str) and location.strip().casefold() == "nigeria"
        for location in restrictions
    )


def _get_jobs_page(cursor: str | None) -> requests.Response:
    params = {"cursor": cursor} if cursor else None
    for attempt in range(JOB_REQUEST_ATTEMPTS):
        try:
            response = requests.get(
                JOBS_API_URL,
                params=params,
                timeout=JOB_REQUEST_TIMEOUT,
            )
            if response.status_code in (429, 500, 502, 503, 504):
                if attempt < JOB_REQUEST_ATTEMPTS - 1:
                    retry_after = response.headers.get("Retry-After")
                    try:
                        delay = (
                            max(0.0, min(float(retry_after), 5.0))
                            if retry_after
                            else 0.5 * (2 ** attempt)
                        )
                    except ValueError:
                        delay = 0.5 * (2 ** attempt)
                    time.sleep(delay)
                    continue
            response.raise_for_status()
            return response
        except (requests.ConnectionError, requests.Timeout):
            if attempt == JOB_REQUEST_ATTEMPTS - 1:
                raise
            time.sleep(0.5 * (2 ** attempt))

    raise RuntimeError("The job listings request ended without a response.")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/")
def home():
    html_file = Path(__file__).parent / "templates" / "index.html"
    return FileResponse(html_file)



@app.get("/jobs")
def search_jobs(
    title: str = Query(min_length=1, max_length=100, description="Desired job title"),
) -> dict[str, object]:
    ignored_words = {"a", "an", "and", "for", "in", "of", "or", "the", "to"}
    query_variants = [
        [
            word for word in re.findall(r"[a-z0-9]+", phrase.casefold())
            if word not in ignored_words
        ]
        for phrase in re.split(r"\s*(?:/|\bor\b)\s*", title, flags=re.IGNORECASE)
    ]
    query_variants = [words for words in query_variants if words]
    matching_jobs = []
    cursor = None
    seen_cursors = set()
    batches_checked = 0
    jobs_checked = 0

    try:
        while (
            query_variants
            and batches_checked < MAX_JOB_BATCHES
            and len(matching_jobs) < MAX_JOB_RESULTS
        ):
            response = _get_jobs_page(cursor)
            data = response.json()
            if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
                raise ValueError("The jobs service returned an unexpected response.")

            batches_checked += 1
            jobs_checked += len(data["jobs"])
            matching_jobs.extend(
                {
                    "title": job["title"],
                    "companyName": job.get("companyName") or "Not provided",
                    "applicationLink": job.get("applicationLink") or "",
                    "locationRestrictions": job.get("locationRestrictions") or [],
                }
                for job in data["jobs"]
                if isinstance(job, dict)
                and isinstance(job.get("title"), str)
                and _title_matches(job["title"], query_variants)
                and _is_nigeria_eligible(job)
            )

            next_cursor = data.get("nextCursor")
            if (
                not isinstance(next_cursor, str)
                or not next_cursor
                or next_cursor in seen_cursors
            ):
                break
            seen_cursors.add(next_cursor)
            cursor = next_cursor
    except (requests.RequestException, ValueError) as error:
        raise HTTPException(
            status_code=502,
            detail=f"Job listings could not be loaded: {error}",
        ) from error

    return {
        "query": title,
        "location": "Nigeria",
        "jobs_checked": jobs_checked,
        "batches_checked": batches_checked,
        "jobs": matching_jobs[:MAX_JOB_RESULTS],
    }
