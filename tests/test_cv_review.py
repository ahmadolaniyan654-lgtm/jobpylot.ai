import tempfile
import unittest
from pathlib import Path

from docx import Document
from reportlab.pdfgen import canvas

from cv_review import (
    CVReviewError,
    extract_cv_text,
    format_cv_review,
    review_cv_file,
    review_cv_text,
)


class CVDocumentExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.directory = Path(self.temp_dir.name)

    def make_pdf(self, name: str, lines: list[str]) -> Path:
        path = self.directory / name
        pdf = canvas.Canvas(str(path))
        y = 800
        for line in lines:
            pdf.drawString(60, y, line)
            y -= 24
        pdf.save()
        return path

    def make_docx(self, name: str, paragraphs: list[str]) -> Path:
        path = self.directory / name
        document = Document()
        for paragraph in paragraphs:
            document.add_paragraph(paragraph)
        document.save(path)
        return path

    def test_extracts_pdf_text_and_keeps_section_order(self) -> None:
        path = self.make_pdf(
            "candidate.pdf",
            ["Education", "Example College 2021", "Work Experience", "Assistant 2022"],
        )

        text = extract_cv_text(path)

        self.assertLess(text.index("Education"), text.index("Work Experience"))
        self.assertIn("Example College 2021", text)

    def test_extracts_docx_paragraphs_and_table_content_in_order(self) -> None:
        path = self.directory / "candidate.docx"
        document = Document()
        document.add_paragraph("Education")
        document.add_paragraph("Example College")
        table = document.add_table(rows=1, cols=2)
        table.cell(0, 0).text = "Work Experience"
        table.cell(0, 1).text = "Assistant"
        document.add_paragraph("Technical Skills")
        document.save(path)

        text = extract_cv_text(path)

        self.assertLess(text.index("Education"), text.index("Work Experience"))
        self.assertLess(text.index("Work Experience"), text.index("Technical Skills"))
        self.assertIn("Work Experience | Assistant", text)

    def test_rejects_unsupported_file_formats(self) -> None:
        path = self.directory / "candidate.txt"
        path.write_text("Education", encoding="utf-8")

        with self.assertRaisesRegex(CVReviewError, "Unsupported file type"):
            extract_cv_text(path)

    def test_rejects_empty_documents(self) -> None:
        path = self.directory / "empty.pdf"
        path.touch()

        with self.assertRaisesRegex(CVReviewError, "empty"):
            extract_cv_text(path)

    def test_reports_missing_and_unreadable_files(self) -> None:
        path = self.directory / "missing.docx"

        with self.assertRaisesRegex(CVReviewError, "could not be found"):
            extract_cv_text(path)

    def test_reports_pdf_extraction_failures_without_crashing(self) -> None:
        path = self.directory / "damaged.pdf"
        path.write_bytes(b"%PDF damaged document")

        with self.assertRaisesRegex(CVReviewError, "PDF could not be read"):
            extract_cv_text(path)

    def test_reports_docx_extraction_failures_without_crashing(self) -> None:
        path = self.directory / "damaged.docx"
        path.write_bytes(b"not a Word document")

        with self.assertRaisesRegex(CVReviewError, "DOCX file could not be opened"):
            extract_cv_text(path)

    def test_rejects_documents_without_extractable_text(self) -> None:
        path = self.make_pdf("image-only.pdf", [])

        with self.assertRaisesRegex(CVReviewError, "No readable text"):
            extract_cv_text(path)

    def test_formats_clear_review_sections_for_a_short_cv(self) -> None:
        text = (
            "Jordan Example\n"
            "jordan@example.com\n"
            "Education\n"
            "Example College\n"
            "Technical Skills\n"
            "Python\n"
        )

        report = format_cv_review("candidate.pdf", text)
        feedback = review_cv_text(text)

        for heading in (
            "What is already good:",
            "What needs improvement:",
            "Specific suggested corrections:",
            "Recommended next steps:",
        ):
            self.assertIn(heading, report)
        self.assertTrue(feedback["good"])
        self.assertTrue(feedback["improvements"])
        self.assertFalse(
            any(
                "work experience" in item.casefold()
                for item in feedback["improvements"]
            )
        )
        self.assertTrue(
            any(
                "not necessarily a problem" in item
                for item in feedback["next_steps"]
            )
        )

    def test_flags_known_wording_without_inventing_replacements(self) -> None:
        feedback = review_cv_text(
            "Work Experience\nI was responsible of filing documents."
        )

        wording_finding = next(
            item
            for item in feedback["corrections"]
            if item["excerpt"] == "I was responsible of filing documents."
        )
        self.assertEqual(wording_finding["section"], "Work Experience")
        self.assertIn("responsible of", wording_finding["excerpt"])
        self.assertIn("responsible for", wording_finding["reason"])
        self.assertEqual(
            wording_finding["suggestion"],
            "I was responsible for filing documents.",
        )
        self.assertTrue(
            any("verify" in item.casefold() or "accurate" in item.casefold()
                for item in feedback["next_steps"])
        )

    def test_objective_finding_quotes_and_rewrites_sample_text(self) -> None:
        objective = (
            "To strengthen my technical and analytical skills, gain practical experience, "
            "and continue learning so I can become a competent Data Analyst."
        )
        feedback = review_cv_text(
            "Professional Summary\n"
            "Currently developing Python skills and building practical projects. "
            "Eager to gain practical experience.\n"
            "Career Objective\n"
            f"{objective}\n"
            "Education\nBachelor of Engineering 2024-2029"
        )

        finding = next(
            item
            for item in feedback["corrections"]
            if item["section"] == "Career Objective"
        )
        self.assertEqual(finding["excerpt"], objective)
        self.assertIn("repeats", finding["reason"])
        self.assertEqual(
            finding["suggestion"],
            "To strengthen technical and analytical skills, gain practical experience, "
            "and continue learning toward a Data Analyst role.",
        )
        self.assertNotIn("experienced", finding["suggestion"].casefold())

    def test_lowercase_volunteering_bullet_gets_fact_preserving_rewrite(self) -> None:
        feedback = review_cv_text(
            "Volunteering\n"
            "STEM Programme Facilitator\n"
            "- participated as a panelist\n"
            "- managed student sign-in and sign-out."
        )

        finding = next(
            item
            for item in feedback["corrections"]
            if item["excerpt"] == "- participated as a panelist"
        )
        self.assertEqual(finding["section"], "Volunteering")
        self.assertIn("capital letter", finding["reason"])
        self.assertEqual(finding["suggestion"], "- Participated as a panelist")

    def test_skill_training_award_and_reference_findings_are_specific(self) -> None:
        feedback = review_cv_text(
            "Education\nBachelor of Engineering 2024-2029\n"
            "Technical Skills\nPython, FastAPI\n"
            "Soft Skills\nPython, Communication\n"
            "Training and Certifications\nSWEP Training Programme\n"
            "Awards and Honours\nBest Student Award\n"
            "References\nDr Example"
        )

        findings = feedback["corrections"]
        self.assertTrue(
            any(item["section"] == "Soft Skills" and "Python" in item["excerpt"]
                and "Technical Skills" in item["suggestion"] for item in findings)
        )
        self.assertTrue(
            any(item["section"] == "Training and Certifications"
                and "No date" in item["reason"] for item in findings)
        )
        self.assertTrue(
            any(item["section"] == "Awards and Honours"
                and "No date" in item["reason"] for item in findings)
        )
        self.assertTrue(
            any(item["section"] == "References"
                and "No email address" in item["reason"] for item in findings)
        )

    def test_project_title_without_description_is_flagged_with_excerpt(self) -> None:
        feedback = review_cv_text("Projects\nJobPylot AI")

        finding = next(
            item for item in feedback["corrections"]
            if item["section"] == "Projects and Achievements"
        )
        self.assertEqual(finding["excerpt"], "JobPylot AI")
        self.assertIn("no description", finding["reason"])
        self.assertIn("actual contribution", finding["suggestion"])

    def test_spacing_warning_requires_two_spaces_between_words(self) -> None:
        aligned_pdf_text = (
            "Education\nBachelor of Engineering                    2024-2029\n"
            "Volunteering\n-  managed student sign-in."
        )
        feedback = review_cv_text(aligned_pdf_text)

        self.assertFalse(
            any(item["section"] == "Document formatting"
                for item in feedback["corrections"])
        )

        genuine_double_space = review_cv_text(
            "Technical Skills\nPython  FastAPI"
        )
        spacing_finding = next(
            item for item in genuine_double_space["corrections"]
            if item["section"] == "Document formatting"
        )
        self.assertEqual(spacing_finding["excerpt"], "Python  FastAPI")
        self.assertEqual(spacing_finding["suggestion"], "Python FastAPI")

    def test_review_of_well_formed_sections_does_not_create_generic_findings(self) -> None:
        feedback = review_cv_text(
            "Professional Summary\nData analyst developing Python projects.\n"
            "Career Objective\nBuild practical data analysis experience.\n"
            "Education\nBEng Mechatronics 2024-2029\n"
            "Projects\nBuilt a career assistant using Python.\n"
            "Volunteering\n- Facilitated STEM activities.\n"
            "Technical Skills\nPython, FastAPI\n"
            "Soft Skills\nCommunication, teamwork\n"
            "Training and Certifications\nSWEP Programme 2025\n"
            "Awards and Honours\nBest Student Award 2024\n"
            "References\nDr Example example@example.com"
        )

        self.assertEqual(feedback["corrections"], [])
        self.assertFalse(
            any("work experience" in item.casefold()
                for item in feedback["improvements"])
        )
        self.assertTrue(
            any("not necessarily a problem" in item
                for item in feedback["next_steps"])
        )

    def test_report_summarises_detected_corrections_as_improvements(self) -> None:
        text = (
            "jordan@example.com\n"
            "Professional Summary\n"
            "Developing analytical skills and practical experience.\n"
            "Career Objective\n"
            "To strengthen my technical and analytical skills, gain practical experience, "
            "and continue learning so I can become a competent Data Analyst.\n"
            "Volunteering\n"
            "- participated as a panelist\n"
            "- provided videography support\n"
            "- managed student sign-in and sign-out.\n"
            "Education\nBachelor of Engineering 2024-2029\n"
            "Projects\nBuilt a local career assistant for CV creation.\n"
            "Technical Skills\nPython, FastAPI\n"
            "Soft Skills\nCommunication, teamwork\n"
            "Training and Certifications\n"
            "SWEP Training Programme"
        )

        report = format_cv_review("candidate.pdf", text)
        improvements = report.split(
            "What needs improvement:\n", 1
        )[1].split("\nSpecific suggested corrections:", 1)[0]
        corrections = report.split("Specific suggested corrections:\n", 1)[1]

        self.assertNotIn("No specific items were identified.", improvements)
        self.assertIn("Volunteering: 3 bullet(s) need consistent capitalisation.", improvements)
        self.assertIn("Career Objective:", improvements)
        self.assertIn("Training and Certifications: No date was detected", improvements)
        self.assertIn("Suggested rewrite: - Participated as a panelist", corrections)
        self.assertIn("Suggested rewrite: - Provided videography support", corrections)
        self.assertIn("Suggested rewrite: - Managed student sign-in and sign-out.", corrections)
        self.assertIn(
            "Suggested rewrite: To strengthen technical and analytical skills",
            corrections,
        )
        self.assertNotIn("Suggested rewrite:", improvements)

    def test_review_file_works_end_to_end_for_docx(self) -> None:
        path = self.make_docx(
            "candidate.docx",
            ["Career Objective", "Seeking an entry-level role.", "Education", "Example College"],
        )

        report = review_cv_file(path)

        self.assertIn("candidate.docx", report)
        self.assertIn("Career Objective", report)
        self.assertIn("Education", report)
        self.assertIn("local rule-based checks", report)


if __name__ == "__main__":
    unittest.main()
