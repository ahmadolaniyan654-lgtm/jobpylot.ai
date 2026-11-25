from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import UserProfile, EmployerProfile
from .models import CareerRequirement, Job
from .services import get_required_skills, get_user_skills, match_profile_to_jobs


class MatchProfileToJobsTests(TestCase):
    @patch("jobs.services.Job.objects.filter")
    def test_returns_each_job_with_its_job_specific_match_info(self, filtered_jobs):
        profile = SimpleNamespace(
            skills="Python, SQL",
            desired_job="Data Analyst",
        )
        python_job = SimpleNamespace(
            title="Data Analyst - Python",
            job_description="Python",
        )
        sql_job = SimpleNamespace(
            title="Data Analyst - SQL",
            job_description="SQL and Power BI",
        )
        filtered_jobs.return_value = [python_job, sql_job]

        results = match_profile_to_jobs(profile)

        filtered_jobs.assert_called_once_with(title__icontains="Data Analyst")
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
        with patch('jobs.services.Job.objects.filter') as filtered_jobs:
            filtered_jobs.return_value= [marine_job]
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


class JobViewTests(TestCase):
    def setUp(self):
        self.job = Job.objects.create(
            title="Data Analyst",
            company_name="Example Co",
            job_description="Analyze data with Python.",
            job_location="Remote",
            country="Example",
            arrangement="remote",
            source_type="employer",
            source_name="Example Co",
            application_url="https://example.com/apply",
        )

    def test_job_matching_requires_login_and_uses_account_profile(self):
        url = reverse("job_matching")
        self.assertRedirects(
            self.client.get(url),
            f"{reverse('login')}?next={url}",
        )

        user = get_user_model().objects.create_user(
            username="job-seeker",
            password="test-password",
        )
        profile = user.userprofile
        profile.desired_job = "Data Analyst"
        profile.skills = "Python"
        profile.save()
        self.client.force_login(user)

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["results"]), 1)
        self.assertEqual(response.context["results"][0]["job"], self.job)

    def test_job_detail_renders_the_requested_job(self):
        response = self.client.get(reverse("job_detail", args=[self.job.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["job"], self.job)


class HomepageJobSearchTests(TestCase):
    def setUp(self):
        self.job = Job.objects.create(
            title="Junior Data Analyst",
            company_name="Example Analytics",
            job_description="Use Python and Excel to analyze data.",
            job_location="Lagos",
            country="Nigeria",
            arrangement="remote",
            source_type="employer",
            source_name="Example Analytics",
            application_url="https://example.com/jobs/data-analyst",
        )

    def test_public_search_returns_django_jobs_and_skill_matches(self):
        response = self.client.get(
            reverse("homepage_job_search"),
            {
                "title": "Data Analyst",
                "city": "Lagos",
                "country": "Nigeria",
                "arrangement": "Remote",
                "user_skills": "Python",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_count"], 1)
        self.assertEqual(data["jobs"][0]["title"], self.job.title)
        self.assertEqual(data["jobs"][0]["company"], self.job.company_name)
        self.assertTrue(data["jobs"][0]["potentially_entry_level"])
        self.assertEqual(data["jobs"][0]["matched_skills"], ["python"])
        self.assertEqual(data["jobs"][0]["missing_skills"], ["excel"])
        self.assertEqual(data["jobs"][0]["match_score"], 50)

    def test_search_filters_by_arrangement_and_reports_matching_listings(self):
        response = self.client.get(
            reverse("homepage_job_search"),
            {
                "title": "Data Analyst",
                "city": "Lagos",
                "country": "Nigeria",
                "arrangement": "Onsite",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["jobs"], [])
        self.assertEqual(response.json()["total_count"], 1)

    def test_search_requires_title_and_country(self):
        response = self.client.get(
            reverse("homepage_job_search"),
            {"title": "", "country": "Nigeria"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())


class CareerRequirementLookupTests(TestCase):
    def test_get_required_skills_handles_a_missing_career(self):
        profile = SimpleNamespace(desired_job="")

        self.assertEqual(get_required_skills(profile), [])

class JobOwnershipTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="employer",
            password="test-password",
        )
        self.employer_profile = EmployerProfile.objects.create(
            user=self.user,
            company_name="Example Co",
        )
        self.job = Job.objects.create(
            employer=self.employer_profile,
            title="Data Analyst",
            company_name="Example Co",
            job_description="Analyze data with Python.",
            job_location="Remote",
            country="Example",
            arrangement="remote",
            source_type="employer",
            source_name="Example Co",
            application_url="https://example.com/apply",
        )

    def test_employer_can_edit_own_job(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("edit_job", args=[self.job.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Job")

    def test_other_users_cannot_edit_job(self):
        other_user = get_user_model().objects.create_user(
            username="other-user",
            password="test-password",
        )
        self.client.force_login(other_user)
        response= self.client.get(reverse('edit_job', args=[self.job.pk]))

        self.assertEqual(response.status_code, 404)
    def test_other_users_cannot_edit_job_with_post(self):
        other_user = get_user_model().objects.create_user(
            username="other-user",
            password="test-password",
        )
        self.client.force_login(other_user)
        response = self.client.post(
            reverse('edit_job', args=[self.job.pk]),
            data={"title": "New Title"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.job.title, 'Data Analyst')

    def test_other_users_cannot_delete_job_with_post(self):
        other_user= get_user_model().objects.create_user(
            username= 'other_user',
            password='test_password',
        )
        self.client.force_login(other_user)
        response= self.client.post(
            reverse('delete_job', args=[self.job.pk]),
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Job.objects.filter(pk=self.job.pk).exists())

    def test_employer_can_access_own_delete_page(self):
        self.client.force_login(self.user)
        response=self.client.get(reverse('delete_job', args=[self.job.pk]))

        self.assertEqual(response.status_code, 200)

    def test_other_users_cannot_access_delete_page(self):
        other_user=get_user_model().objects.create_user(
            username='another-employer',
            password='test-password',
        )
        self.client.force_login(other_user)
        response=self.client.get(reverse('delete_job', args=[self.job.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Job.objects.filter(pk=self.job.pk).exists())