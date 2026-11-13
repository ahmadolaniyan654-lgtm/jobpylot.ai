from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from .services import match_profile_to_jobs, get_user_skills, get_required_skills

from .models import CareerRequirement


class MatchProfileToJobsTests(TestCase):
    @patch("jobs.services.Job.objects.all")
    def test_returns_each_job_with_its_job_specific_match_info(self, all_jobs):
        profile = SimpleNamespace(
            skills="Python, SQL",
            desired_job="Data Analyst",
        )
        python_job = SimpleNamespace(
            title="Python Analyst",
            job_description="Python",
        )
        sql_job = SimpleNamespace(
            title="SQL Analyst",
            job_description="SQL and Power BI",
        )
        all_jobs.return_value = [python_job, sql_job]

        results = match_profile_to_jobs(profile)

        self.assertEqual(len(results), 2)
        self.assertIs(results[0]["job"], python_job)
        self.assertEqual(
            results[0]["match_info"]["matched_skills"],
            ["python"],
        )
        self.assertEqual(results[0]["match_info"]["missing_skills"], [])
        self.assertEqual(results[0]["match_info"]["match_score"], 100)
        self.assertIs(results[1]["job"], sql_job)
        self.assertEqual(
            results[1]["match_info"]["matched_skills"],
            ["sql"],
        )
        self.assertEqual(
            results[1]["match_info"]["missing_skills"],
            ["power bi"],
        )
        self.assertEqual(results[1]["match_info"]["match_score"], 50)

    def test_matches_jobs_using_database_career_skills(self):
        CareerRequirement.objects.create(
            career_title= 'Marine Biologist',
            required_skills= 'Marine Ecology, Oceanography, Research'
        )
        profile= SimpleNamespace(
            skills= 'Marine Ecology, Research',
            desired_job= 'Marine Biologist'
        )
        marine_job = SimpleNamespace(
            title= 'Junior Marine Biologist',
            job_description= 'Marine Ecology and Oceanography'
        )
        with patch('jobs.services.Job.objects.all') as all_jobs:
            all_jobs.return_value= [marine_job]
            results= match_profile_to_jobs(profile)
        self.assertEqual(
            results[0]['match_info']['matched_skills'],
            ['marine ecology']
        )
        self.assertEqual(
            results[0]['match_info']['missing_skills'],
            ['oceanography']
        )
class GetUserSkillsTests(SimpleTestCase):
    def test_returns_clean_skills(self):
        profile= SimpleNamespace(skills='Python, SQL, Excel')
        result= get_user_skills(profile)
        self.assertEqual(result, ['Python', 'SQL', 'Excel'])

    def test_returns_empty_list_when_skiills_are_missing(self):
        profile= SimpleNamespace(skills='')
        result= get_user_skills(profile)
        self.assertEqual(result, [])
    
    def test_ignores_extra_commas_and_spaces(self):
        profile= SimpleNamespace(skills= 'Python, , SQL, Excel,')
        result= get_user_skills(profile)
        self.assertEqual(result, ['Python', 'SQL', 'Excel'])


class GetRequiredSkillsTests(TestCase):
    def test_returns_skills_for_desired_job(self):
        profile= SimpleNamespace(desired_job= 'Data Analyst')
        result= get_required_skills(profile)
        self.assertEqual(result, ['Excel', 'SQL', 'Python', 'Power BI', 'Tableau', 'Statistics and Probability', 'Data Visualization'])

    def test_returns_empty_list_when_desired_job_is_missing(self):
        profile= SimpleNamespace(desired_job= '')
        result= get_required_skills(profile)
        self.assertEqual(result, [])

    def test_recognizes_desired_job_with_lowercase_letters(self):
        profile= SimpleNamespace(desired_job= 'data analyst')
        result= get_required_skills(profile)
        self.assertEqual(result, ["Excel", "SQL", "Python", "Power BI", "Tableau", "Statistics and Probability", "Data Visualization"])

    def test_returns_empty_list_for_unknown_career(self):
        profile= SimpleNamespace(desired_job= 'Marine Biologist')
        result= get_required_skills(profile)
        self.assertEqual(result, [])

    def test_returns_saved_skills_from_database(self):
        CareerRequirement.objects.create(
            career_title='Marine Biologist',
            required_skills= 'Marine Ecology, Oceanography, Research'
        )
        profile= SimpleNamespace(desired_job= 'Marine Biologist')
        result= get_required_skills(profile)
        self.assertEqual(
            result,
            ['Marine Ecology', 'Oceanography', 'Research']
        )

