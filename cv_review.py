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

COMMON_WORDING = {
    "responsible of": "responsible for",
    "discuss about": "discuss",
    "informations": "information",
    "equipments": "equipment",
    "i am agree": "I agree",
    "hard working": "hard-working",
    "acheivement": "achievement",
    "communcation": "communication",
    "experiance": "experience",
    "managment": "management",
    "recieve": "receive",
    "teh": "the",
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


def review_cv_text(text: str) -> dict[str, list[str]]:
    """Return evidence-based, local CV feedback without adding personal claims."""
    clean_text = text.strip()
    lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
    sections = _collect_sections(clean_text)
    section_names = set(sections)
    lower_text = clean_text.casefold()
    good = []
    improvements = []
    corrections = []
    next_steps = []

    if not clean_text:
        return {
            "good": [],
            "improvements": ["No CV text was available to review."],
            "corrections": ["Add readable CV text before requesting a review."],
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
        ("Work Experience", "Work experience"),
        ("Projects and Achievements", "Projects or achievements"),
        ("Technical Skills", "Technical skills"),
        ("Soft Skills", "Soft skills"),
    ):
        if section not in section_names and not re.search(
            {
                "Education": r"\b(education|degree|diploma|university|college)\b",
                "Work Experience": r"\b(work experience|employment|employer|job title)\b",
                "Projects and Achievements": r"\b(projects?|achievements?)\b",
                "Technical Skills": r"\b(technical skills|programming|software|tools)\b",
                "Soft Skills": r"\b(soft skills|communication|leadership|teamwork)\b",
            }[section],
            lower_text,
        ):
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

    if "Projects and Achievements" in section_names and sections["Projects and Achievements"]:
        good.append("Projects or achievements are included.")
    if "Technical Skills" in section_names and sections["Technical Skills"]:
        good.append("A technical-skills section is included.")
    if "Soft Skills" in section_names and sections["Soft Skills"]:
        good.append("A soft-skills section is included.")

    repeated_spaces = re.search(r"[ \t]{2,}", clean_text)
    if repeated_spaces:
        corrections.append(
            "Replace repeated spaces with single spaces; for example, "
            f"{repeated_spaces.group(0)!r} can be reduced to one space."
        )
    for phrase, replacement in COMMON_WORDING.items():
        match = re.search(re.escape(phrase), clean_text, re.IGNORECASE)
        if match:
            corrections.append(
                f"Change {match.group(0)!r} to {replacement!r} if that matches the intended meaning."
            )
    if re.search(r"\b(i|my|we|our)\b", clean_text, re.IGNORECASE):
        corrections.append(
            "Check first-person wording and use concise CV-style phrases where appropriate, without changing the facts."
        )
    if not corrections:
        corrections.append(
            "No obvious wording pattern was flagged by the basic local checks. Proofread names, dates, spelling, and punctuation manually."
        )

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
        report.extend(f"- {item}" for item in feedback[key])
        if not feedback[key]:
            report.append("- No specific items were identified.")
    return "\n".join(report)


def review_cv_file(file_path: str | Path) -> str:
    """Extract and review a local PDF or DOCX, returning a terminal-ready report."""
    text = extract_cv_text(file_path)
    return format_cv_review(file_path, text)
