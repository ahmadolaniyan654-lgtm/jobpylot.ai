import ast
import contextlib
import io
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "ai 1"
TESTED_FUNCTIONS = {
    "professional_title",
    "normalize_skill",
    "generate_professional_summary",
    "parse_cv_targets",
    "default_career_objective",
    "capitalise_bullet_start",
    "save_cv_pdf",
}


def load_cv_functions():
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SCRIPT_PATH))
    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in TESTED_FUNCTIONS
    ]
    namespace = {"re": re}
    exec(
        compile(ast.Module(body=functions, type_ignores=[]), str(SCRIPT_PATH), "exec"),
        namespace,
    )
    return namespace


class CVBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cv = load_cv_functions()

    def test_single_and_multiple_career_targets_are_preserved(self) -> None:
        parse_targets = self.cv["parse_cv_targets"]

        self.assertEqual(
            parse_targets("", "Web Developer"),
            ["Web Developer"],
        )
        self.assertEqual(
            parse_targets("Data Analyst, Web Developer, data analyst"),
            ["Data Analyst", "Web Developer"],
        )
        self.assertEqual(parse_targets("general"), [])

    def test_objective_matches_single_multiple_and_general_targets(self) -> None:
        objective = self.cv["default_career_objective"]

        self.assertEqual(
            objective(["Web Developer"]),
            "Seeking an opportunity as a Web Developer.",
        )
        self.assertEqual(
            objective(["Architect"]),
            "Seeking an opportunity as an Architect.",
        )
        self.assertEqual(
            objective(["Data Analyst", "Web Developer"]),
            "Seeking opportunities in Data Analyst and Web Developer roles.",
        )
        self.assertEqual(objective([], "Find a role using my skills"), "Find a role using my skills")

    def test_summary_uses_supplied_education_skills_projects_and_targets(self) -> None:
        summary = self.cv["generate_professional_summary"]({
            "target_roles": ["Data Analyst", "Web Developer"],
            "education_entries": [{
                "qualification": "Bachelor of Engineering",
                "course": "Mechatronics Engineering",
                "institution": "Example University",
            }],
            "skills": ["Python", "SQL"],
            "projects_and_achievements": [{
                "title": "Career Assistant",
                "details": ["Built a career assistant for job searches."],
                "technologies": "Python",
            }],
            "work_experience": [],
        })

        self.assertIn("Data Analyst and Web Developer roles", summary)
        self.assertIn("Bachelor of Engineering in Mechatronics Engineering", summary)
        self.assertIn("Python, SQL", summary)
        self.assertIn("Built a career assistant for job searches", summary)
        self.assertNotIn("experienced", summary.casefold())
        self.assertNotIn("work experience", summary.casefold())

    def test_summary_is_modest_when_profile_information_is_limited(self) -> None:
        generate = self.cv["generate_professional_summary"]

        self.assertEqual(
            generate({"target_roles": ["Web Developer"]}),
            "Interested in a Web Developer role.",
        )
        self.assertEqual(generate({"target_roles": []}), "")

    def test_volunteering_capitalisation_is_a_suggestion_not_a_mutation(self) -> None:
        detail = "participated as a panelist"
        suggested = self.cv["capitalise_bullet_start"](detail)

        self.assertEqual(suggested, "Participated as a panelist")
        self.assertEqual(detail, "participated as a panelist")
        self.assertEqual(
            self.cv["capitalise_bullet_start"]("- managed student sign-in"),
            "- Managed student sign-in",
        )

    def test_pdf_keeps_section_heading_and_training_entry_together(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            home = Path(temporary_directory)
            cv_data = {
                "personal_details": {"full_name": "Sample Candidate"},
                "target_roles": ["Data Analyst", "Web Developer"],
                "target_role": "",
            }
            long_projects = [
                {
                    "title": f"Project {index}",
                    "dates": f"202{index % 5}-202{(index % 5) + 1}",
                    "details": [
                        "Documented project details for a test CV to check "
                        "flowing layout and pagination across multiple pages. " * 3
                    ],
                }
                for index in range(35)
            ]
            sections = [
                ("Projects", long_projects),
                (
                    "Training and Certifications",
                    [{
                        "title": "SWEP Training Programme",
                        "organization": "Federal University of Technology, Minna",
                        "dates": "2025",
                    }],
                ),
            ]

            with patch.object(Path, "home", return_value=home):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.cv["save_cv_pdf"](cv_data, sections)

            saved_path = Path(
                output.getvalue().split("Your CV PDF was saved to: ", 1)[1].strip()
            )
            pages = PdfReader(str(saved_path)).pages
            self.assertGreaterEqual(len(pages), 2)
            page_text = [page.extract_text() or "" for page in pages]
            training_page = next(
                text for text in page_text
                if "SWEP Training Programme" in text
            )
            self.assertIn("Training and Certifications", training_page)
            self.assertIn("Federal University of Technology, Minna", training_page)
            self.assertIn("Data Analyst, Web Developer", page_text[0])
            self.assertNotIn("References", "\n".join(page_text))
            for page_number, text in enumerate(page_text, start=1):
                self.assertIn(f"Page {page_number}", text)


if __name__ == "__main__":
    unittest.main()
