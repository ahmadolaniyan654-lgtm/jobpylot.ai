"""Local extraction and rule-based feedback for existing CV documents."""

import re
from pathlib import Path


class CVReviewError(Exception):
    """An expected problem while opening or extracting a CV."""


SECTION_ALIASES = {
    "Professional Summary": {
        "professional summary",
        "profile",
        "professional profile",
        "profile summary",
        "summary",
    },
    "Career Objective": {"career objective", "objective", "career goal"},
    "Education": {"education", "educational background", "academic background"},
    "Work Experience": {
        "work experience",
        "work history",
        "employment history",
        "professional experience",
        "experience",
    },
    "Projects and Achievements": {
        "projects",
        "project experience",
        "achievements",
        "projects and achievements",
    },
    "Technical Skills": {"technical skills", "technical skill", "tools", "technologies"},
    "Soft Skills": {"soft skills", "interpersonal skills"},
    "Training and Certifications": {
        "training",
        "certifications",
        "certificates",
        "training and certifications",
        "certifications and training",
    },
    "Awards and Honours": {"awards", "honors", "honours", "awards and honours"},
    "Volunteering": {"volunteering", "volunteer experience", "community involvement"},
    "References": {"references", "referees"},
}

WORDING_REWRITES = {
    "responsible of": (
        "Use 'responsible for' with the activity that follows.",
        "responsible for",
    ),
    "discuss about": (
        "The verb 'discuss' does not need 'about'.",
        "discuss",
    ),
    "informations": (
        "'Information' is normally uncountable in this context.",
        "information",
    ),
    "equipments": (
        "'Equipment' is normally uncountable in this context.",
        "equipment",
    ),
    "i am agree": (
        "This phrasing is ungrammatical; 'I agree' keeps the same meaning.",
        "I agree",
    ),
    "hard working": (
        "Use the standard compound adjective spelling.",
        "hard-working",
    ),
    "acheivement": ("This appears to be a spelling error.", "achievement"),
    "communcation": ("This appears to be a spelling error.", "communication"),
    "experiance": ("This appears to be a spelling error.", "experience"),
    "managment": ("This appears to be a spelling error.", "management"),
    "recieve": ("This appears to be a spelling error.", "receive"),
    "teh": ("This appears to be a spelling error.", "the"),
}

SECTION_DATE_PATTERNS = {
    "Education": r"\b(?:19|20)\d{2}\b",
    "Work Experience": r"\b(?:19|20)\d{2}\b|\bpresent\b",
    "Training and Certifications": r"\b(?:19|20)\d{2}\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b",
    "Awards and Honours": r"\b(?:19|20)\d{2}\b",
}


def _normalise_heading(line: str) -> str:
    heading = re.sub(r"[^a-z0-9 ]+", "", line.casefold())
    return re.sub(r"\s+", " ", heading).strip()


def _identify_heading(line: str) -> str | None:
    heading = _normalise_heading(line)
    if not heading or len(heading) > 60:
        return None
    for section, aliases in SECTION_ALIASES.items():
        if heading in aliases:
            return section
    return None


def _extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise CVReviewError(
            "PDF review needs pypdf. Install the project dependencies with: "
            ".\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt"
        ) from error

    try:
        reader = PdfReader(str(path), strict=True)
        if reader.is_encrypted:
            raise CVReviewError(
                "This PDF is password-protected. Remove the password and try again."
            )
        pages = [
            page.extract_text(extraction_mode="layout") or ""
            for page in reader.pages
        ]
    except CVReviewError:
        raise
    except Exception as error:
        raise CVReviewError(
            "The PDF could not be read or its text could not be extracted. "
            "Check that it is a valid, readable PDF."
        ) from error
    return "\n\n".join(pages)


def _extract_docx(path: Path) -> str:
    try:
        from docx import Document
    except ImportError as error:
        raise CVReviewError(
            "DOCX review needs python-docx. Install the project dependencies with: "
            ".\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt"
        ) from error

    try:
        document = Document(str(path))
        extracted = []
        for item in document.iter_inner_content():
            if hasattr(item, "text"):
                if item.text.strip():
                    extracted.append(item.text)
            else:
                for row in item.rows:
                    cells = [
                        re.sub(r"\s+", " ", cell.text).strip()
                        for cell in row.cells
                    ]
                    if any(cells):
                        extracted.append(" | ".join(cell for cell in cells if cell))
    except Exception as error:
        raise CVReviewError(
            "The DOCX file could not be opened or its text could not be extracted. "
            "Check that it is a valid, readable Word document."
        ) from error
    return "\n".join(extracted)


def extract_cv_text(file_path: str | Path) -> str:
    """Extract CV text from a local PDF or DOCX while keeping reading order."""
    path = Path(file_path).expanduser()
    if path.suffix.casefold() not in {".pdf", ".docx"}:
        raise CVReviewError("Unsupported file type. Please choose a PDF or DOCX file.")
    try:
        if not path.is_file():
            raise CVReviewError("That file could not be found or is not a regular file.")
        if path.stat().st_size == 0:
            raise CVReviewError("The selected file is empty.")
    except OSError as error:
        raise CVReviewError("The selected file could not be accessed.") from error

    text = _extract_pdf(path) if path.suffix.casefold() == ".pdf" else _extract_docx(path)
    text = text.replace("\x00", "")
    if not text.strip():
        raise CVReviewError(
            "No readable text was found. The document may be blank or scanned as images; "
            "image-only OCR is not supported."
        )
    return text


def _collect_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    active_section = None
    for line in text.splitlines():
        heading = _identify_heading(line)
        if heading:
            active_section = heading
            sections.setdefault(heading, [])
        elif active_section and line.strip():
            sections[active_section].append(line.strip())
    return sections


def _make_finding(
    section: str,
    excerpt: str,
    reason: str,
    suggestion: str,
) -> dict[str, str]:
    return {
        "section": section,
        "excerpt": _short_excerpt(excerpt, normalise_spacing=False),
        "reason": reason,
        "suggestion": suggestion.strip(),
    }


def _short_excerpt(
    text: str,
    limit: int = 180,
    *,
    normalise_spacing: bool = True,
) -> str:
    if normalise_spacing:
        excerpt = re.sub(r"\s+", " ", text).strip()
    else:
        excerpt = re.sub(r"[\x00-\x1f\x7f\ufffd]", "", text).strip()
    if len(excerpt) > limit:
        return excerpt[: limit - 1].rstrip() + "…"
    return excerpt


def _objective_rewrite(text: str) -> str | None:
    """Tighten a common goal sentence without changing its stated intent."""
    match = re.fullmatch(
        r"(?P<opening>To .+?)\s+so I can become a competent "
        r"(?P<role>[^.!?]+)(?P<ending>[.!?]?)",
        text.strip(),
        re.IGNORECASE,
    )
    if not match:
        return None
    opening = re.sub(r"\bmy\s+", "", match.group("opening"), flags=re.IGNORECASE)
    role = match.group("role").strip()
    return f"{opening} toward a {role} role{match.group('ending') or '.'}"


def _wording_findings(sections: dict[str, list[str]]) -> list[dict[str, str]]:
    findings = []
    for section, lines in sections.items():
        for line in lines:
            for phrase, (reason, replacement) in WORDING_REWRITES.items():
                match = re.search(re.escape(phrase), line, re.IGNORECASE)
                if not match:
                    continue
                suggestion = re.sub(
                    re.escape(phrase),
                    replacement,
                    line,
                    count=1,
                    flags=re.IGNORECASE,
                )
                findings.append(
                    _make_finding(
                        section,
                        line,
                        reason,
                        suggestion,
                    )
                )

            bullet = re.match(r"^(\s*[-•]\s+)([a-z])", line)
            if bullet:
                suggestion = (
                    line[: bullet.start(2)]
                    + bullet.group(2).upper()
                    + line[bullet.end(2) :]
                )
                findings.append(
                    _make_finding(
                        section,
                        line,
                        "Starting each duty bullet with a capital letter makes the list consistent.",
                        suggestion,
                    )
                )

    objective = " ".join(sections.get("Career Objective", []))
    summary = " ".join(sections.get("Professional Summary", []))
    objective_rewrite = _objective_rewrite(objective)
    if objective_rewrite:
        shared_themes = (
            "practical experience" in summary.casefold()
            and "skill" in summary.casefold()
            and "practical experience" in objective.casefold()
            and "skill" in objective.casefold()
        )
        if shared_themes or re.search(r"\bmy\b|\bI\b", objective):
            reason = (
                "This objective repeats skill-development and practical-experience themes "
                "already in the summary and uses first-person wording."
                if shared_themes
                else "Removing first-person wording makes this objective more direct."
            )
            findings.append(
                _make_finding(
                    "Career Objective",
                    objective,
                    reason,
                    objective_rewrite,
                )
            )
    return findings


def _section_findings(
    sections: dict[str, list[str]],
) -> list[dict[str, str]]:
    findings = []
    for section, date_pattern in SECTION_DATE_PATTERNS.items():
        lines = sections.get(section, [])
        if lines and not re.search(date_pattern, " ".join(lines), re.IGNORECASE):
            findings.append(
                _make_finding(
                    section,
                    lines[0],
                    f"No date was detected in the {section.lower()} section.",
                    "Add the date or validity period if it is known; otherwise, leave it out.",
                )
            )

    project_lines = sections.get("Projects and Achievements", [])
    project_text = " ".join(project_lines).strip()
    if (
        project_text
        and len(project_text.split()) <= 5
        and not re.search(r"[.!?]", project_text)
    ):
        findings.append(
            _make_finding(
                "Projects and Achievements",
                project_text,
                "Only a project or achievement title was detected, with no description beneath it.",
                "Add a short description of what was done, using only the actual contribution and outcome.",
            )
        )

    technical = " ".join(sections.get("Technical Skills", []))
    soft = " ".join(sections.get("Soft Skills", []))
    if re.search(r"\bpython\b", soft, re.IGNORECASE):
        findings.append(
            _make_finding(
                "Soft Skills",
                _short_excerpt(soft),
                "Python is a programming language, so listing it as a soft skill may make the skills categories unclear.",
                "List Python under Technical Skills and keep Soft Skills for interpersonal abilities, if that matches the applicant's intent.",
            )
        )

    technical_items = {
        item.strip().casefold()
        for item in re.split(r"[,;|\n]", technical)
        if item.strip()
    }
    duplicate_soft_items = [
        item.strip()
        for item in re.split(r"[,;|\n]", soft)
        if item.strip() and item.strip().casefold() in technical_items
    ]
    if duplicate_soft_items and not re.search(r"\bpython\b", soft, re.IGNORECASE):
        findings.append(
            _make_finding(
                "Soft Skills",
                ", ".join(duplicate_soft_items),
                "These entries also appear under Technical Skills, so they may be redundant.",
                "Keep each skill in the section that best describes it and remove duplicate listings.",
            )
        )

    references = " ".join(sections.get("References", []))
    if sections.get("References") and not re.search(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|"
        r"\+?\d[\d ()-]{6,}\d",
        references,
        re.IGNORECASE,
    ):
        findings.append(
            _make_finding(
                "References",
                _short_excerpt(references) or "References",
                "No email address or phone number was detected in the reference details.",
                "Add a contact method only after confirming it is accurate and the referee has agreed to be listed.",
            )
        )
    return findings


def review_cv_text(text: str) -> dict[str, list[str] | list[dict[str, str]]]:
    """Return evidence-based, local CV feedback without adding personal claims."""
    clean_text = text.strip()
    lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
    sections = _collect_sections(clean_text)
    section_names = set(sections)
    good = []
    improvements = []
    corrections = []
    next_steps = []

    if not clean_text:
        return {
            "good": [],
            "improvements": ["No CV text was available to review."],
            "corrections": [
                _make_finding(
                    "Document",
                    "No CV text",
                    "There is no text to review.",
                    "Provide readable CV text before requesting a review.",
                )
            ],
            "next_steps": ["Provide a non-empty PDF or DOCX containing selectable text."],
        }

    if len(lines) > 1:
        good.append("The document contains multiple readable lines of CV information.")
    if section_names:
        headings = [name for name in SECTION_ALIASES if name in section_names]
        good.append("Recognisable section headings were found: " + ", ".join(headings) + ".")
    else:
        improvements.append(
            "No familiar section headings were detected. Clear headings can make the CV easier to scan."
        )
        corrections.append(
            "Group the existing information under headings such as Education, Work Experience, and Skills where relevant."
        )
    if len(lines) == 1:
        improvements.append(
            "The extracted CV is one continuous line. Add paragraph breaks and section headings to improve readability."
        )
    elif any(len(line) > 180 for line in lines):
        improvements.append(
            "Some extracted lines are very long. Break dense paragraphs into shorter paragraphs or bullets where appropriate."
        )

    if re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", clean_text, re.IGNORECASE):
        good.append("An email address is present in the extracted text.")
    else:
        improvements.append(
            "No email address was detected. If appropriate, include a reliable contact email."
        )

    summary_sections = section_names.intersection(
        {"Professional Summary", "Career Objective"}
    )
    if summary_sections:
        summary_text = " ".join(
            line
            for name in summary_sections
            for line in sections.get(name, [])
        )
        if summary_text:
            good.append("A professional summary or career objective is included.")
            if len(summary_text.split()) > 100:
                improvements.append(
                    "The summary/objective is lengthy. Consider shortening it while preserving only relevant details already in the CV."
                )
        else:
            improvements.append(
                "A summary/objective heading is present but no text was detected beneath it."
            )
    else:
        improvements.append(
            "A professional summary or career objective was not detected. Add one only if it reflects the user's actual background and goals."
        )

    for section, label in (
        ("Education", "Education"),
        ("Projects and Achievements", "Projects or achievements"),
        ("Technical Skills", "Technical skills"),
        ("Soft Skills", "Soft skills"),
    ):
        if section not in section_names:
            improvements.append(
                f"{label} was not detected. Include this section only when the user has relevant information to add."
            )
        elif section in sections and not any(value.strip() for value in sections[section]):
            improvements.append(f"The {label.lower()} heading appears to have no details.")

    if "Education" in section_names:
        education = " ".join(sections["Education"])
        if education:
            good.append("Education details are present.")
            if not re.search(r"\b(?:19|20)\d{2}\b", education):
                improvements.append(
                    "No education dates or years were detected; add them if known and useful."
                )
    if "Work Experience" in section_names:
        experience = " ".join(sections["Work Experience"])
        if experience:
            good.append("Work experience details are present.")
            if not re.search(r"\b(?:19|20)\d{2}\b|\bpresent\b", experience, re.IGNORECASE):
                improvements.append(
                    "No work dates were detected; add dates if known so the timeline is clear."
                )
    else:
        next_steps.append(
            "No work-experience section was found. This is not necessarily a problem; add relevant experience only if available."
        )

    if "Projects and Achievements" in section_names and sections["Projects and Achievements"]:
        good.append("Projects or achievements are included.")
    if "Technical Skills" in section_names and sections["Technical Skills"]:
        good.append("A technical-skills section is included.")
    if "Soft Skills" in section_names and sections["Soft Skills"]:
        good.append("A soft-skills section is included.")

    repeated_spaces = re.search(r"(?<=\w) {2}(?=\w)", clean_text)
    if repeated_spaces:
        line = next(
            line for line in clean_text.splitlines()
            if repeated_spaces.group(0) in line
        )
        corrections.append(
            _make_finding(
                "Document formatting",
                _short_excerpt(line, normalise_spacing=False),
                "Two spaces appear between words in this extracted line, which can look inconsistent.",
                re.sub(r"(?<=\w) {2}(?=\w)", " ", line),
            )
        )
    corrections.extend(_wording_findings(sections))
    corrections.extend(_section_findings(sections))

    if not any(
        section in section_names
        for section in ("Training and Certifications", "Awards and Honours", "Volunteering")
    ):
        improvements.append(
            "Training, awards, and volunteering were not detected; these sections are optional and should be added only when applicable."
        )
    if not section_names:
        next_steps.append(
            "Reorganise the existing information with clear headings; do not add details that are not in the source CV."
        )
    next_steps.extend([
        "Check that every job title, organisation, qualification, achievement, and date is accurate.",
        "Proofread the original document; this local review does not use a full dictionary or grammar engine.",
    ])
    if len(clean_text.split()) < 80:
        next_steps.append(
            "The extracted CV is brief. Add relevant details only if they are true and useful; a short CV is better than invented content."
        )
    if not corrections:
        next_steps.append(
            "No specific wording issue was detected by these local checks; proofread names, dates, spelling, and punctuation manually."
        )

    return {
        "good": good,
        "improvements": improvements,
        "corrections": corrections,
        "next_steps": next_steps,
    }


def format_cv_review(file_path: str | Path, text: str) -> str:
    """Format a review into a readable terminal report."""
    feedback = review_cv_text(text)
    report = [
        "\n----- EXISTING CV REVIEW -----",
        f"File: {Path(file_path).name}",
        "Review method: local rule-based checks; no CV is sent to an external service.",
    ]
    detected_sections = list(_collect_sections(text))
    if detected_sections:
        report.append("Detected section order: " + " -> ".join(detected_sections))
    for heading, key in (
        ("What is already good", "good"),
        ("What needs improvement", "improvements"),
        ("Specific suggested corrections", "corrections"),
        ("Recommended next steps", "next_steps"),
    ):
        report.append(f"\n{heading}:")
        items = feedback[key]
        if key == "corrections":
            for finding in items:
                report.extend([
                    f"- Section: {finding['section']}",
                    f"  Excerpt: “{finding['excerpt']}”",
                    f"  Why: {finding['reason']}",
                    f"  Suggested rewrite: {finding['suggestion']}",
                ])
        else:
            report.extend(f"- {item}" for item in items)
        if not items:
            report.append("- No specific items were identified.")
    return "\n".join(report)


def review_cv_file(file_path: str | Path) -> str:
    """Extract and review a local PDF or DOCX, returning a terminal-ready report."""
    text = extract_cv_text(file_path)
    return format_cv_review(file_path, text)
