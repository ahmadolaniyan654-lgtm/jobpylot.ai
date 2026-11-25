from datetime import timedelta

from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.staticfiles.finders import find
from django.utils import timezone
from .models import JobApplication
from django.urls import resolve, reverse
from .views import dashboard, my_applications


class JobApplicationPageRoutingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='routinguser',
            password='testpassword123',
        )
        self.client.force_login(self.user)

    def test_dashboard_url_uses_dashboard_view(self):
        url = reverse('dashboard')
        self.assertEqual(url, '/applications/')
        self.assertIs(resolve(url).func, dashboard)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'job_applications/dashboard.html')
        expected_destinations = (
            reverse('dashboard'),
            reverse('job_matching'),
            reverse('my_applications'),
            reverse('create_application'),
            reverse('edit_profile'),
        )
        for destination in expected_destinations:
            with self.subTest(destination=destination):
                self.assertContains(response, f'href="{destination}"')
        self.assertContains(response, 'Welcome to JobPylot AI')
        self.assertContains(
            response,
            'Track your career progress and manage your job search in one place.',
        )
        self.assertContains(response, 'Explore Jobs')
        self.assertContains(response, 'Get Started')
        self.assertContains(response, 'View Applications')
        self.assertContains(response, 'Update Profile')
        self.assertContains(response, 'View all applications')
        self.assertContains(
            response,
            'href="/static/job_applications/style.css"',
        )
        self.assertIsNotNone(find('job_applications/style.css'))

        for destination in expected_destinations:
            with self.subTest(page=destination):
                linked_page = self.client.get(destination)
                self.assertEqual(linked_page.status_code, 200)

    def test_my_applications_url_uses_my_applications_view(self):
        url = reverse('my_applications')
        self.assertEqual(url, '/applications/my_applications/')
        self.assertIs(resolve(url).func, my_applications)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'job_applications/my_applications.html')
        self.assertContains(response, 'href="/applications/"')
        self.assertContains(
            response,
            'href="/applications/my_applications/" class="active"',
        )


class DashboardDataTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='dashboarduser',
            password='testpassword123',
        )
        self.other_user = User.objects.create_user(
            username='otherdashboarduser',
            password='testpassword123',
        )
        self.client.force_login(self.user)

    def create_application(self, applicant, job_title, status='saved'):
        return JobApplication.objects.create(
            applicant=applicant,
            job_title=job_title,
            company='Example Company',
            job_url='https://example.com/jobs/',
            cover_letter='Application cover letter.',
            status=status,
        )

    def test_summary_and_recent_applications_are_user_scoped(self):
        statuses = ('saved', 'pending', 'approved', 'rejected', 'submitted')
        for index, status in enumerate(statuses):
            application = self.create_application(
                self.user,
                f'{status.title()} Role',
                status,
            )
            JobApplication.objects.filter(pk=application.pk).update(
                created_at=timezone.now() + timedelta(seconds=index),
            )

        private_application = self.create_application(
            self.other_user,
            'Private Role',
            'submitted',
        )
        JobApplication.objects.filter(pk=private_application.pk).update(
            created_at=timezone.now() + timedelta(days=1),
        )

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_applications'], len(statuses))
        for status in statuses:
            with self.subTest(status=status):
                self.assertEqual(response.context[f'total_{status}'], 1)

        recent_titles = [
            application.job_title
            for application in response.context['recent_applications']
        ]
        self.assertEqual(
            recent_titles,
            ['Submitted Role', 'Rejected Role', 'Approved Role'],
        )
        self.assertContains(response, 'Submitted Role')
        self.assertContains(response, 'Example Company')
        self.assertContains(response, 'Submitted')
        self.assertNotContains(response, 'Private Role')
        self.assertNotContains(response, 'Pending Role')
        self.assertContains(response, 'View all applications')

    def test_dashboard_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse('dashboard'))

        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("dashboard")}',
        )


class JobApplicationModelTest(TestCase):
    def test_application_creation(self):
        user = User.objects.create_user(
            username='ahmad',
            email='ahmad@example.com',
            password='testpassword123'
        )
        application=JobApplication.objects.create(
            applicant=user,
            job_title= 'Python Developer',
            company='Tech Solutions',
            job_url= 'https://example.com/jobs/python-developer',
            cover_letter='I am interested in this Python Developer position.'
        )
        self.assertEqual(application.job_title, 'Python Developer')
        self.assertEqual(application.status, 'saved')
        self.assertEqual(str(application), 'Python Developer at Tech Solutions')
    def test_application_rejection(self):
        user = User.objects.create_user(
            username='testuser',
            email= 'testuser@example.com',
            password= 'testpassword123'
        )
        application=JobApplication.objects.create(
            applicant= user,
            job_title= 'Data Analyst',
            company= 'ABC Technologies',
            job_url= 'https://example.com/jobs/data-analyst',
            cover_letter= 'I am applying for the Data Analyst position.'
        )
        application.status= 'rejected'
        application.save()
        self.assertEqual(application.status, 'rejected')
    def test_application_approval(self):
        user = User.objects.create_user(
            username= 'approvaluser',
            email= 'approvaluser@example.com',
            password= 'testpassword123'
        )
        application=JobApplication.objects.create(
            applicant=user,
            job_title='Web Developer',
            company= 'Bright Tech',
            job_url= 'https://example.com/jobs/web-developer',
            cover_letter= 'I am interested in the Web Developer position'
        )
        application.status= 'approved'
        application.save()
        self.assertEqual(application.status, 'approved')
    def test_can_submit(self):
        user =User.objects.create_user(
            username='submituser',
            email= 'submituser@example.com',
            password= 'testpassword123'
        )
        application=JobApplication.objects.create(
            applicant = user,
            job_title= 'Python Developer',
            company= 'Tech Solutions',
            job_url='https://example.com/jobs/python-developer',
            cover_letter= 'I am interested in this position.'
        )
        self.assertFalse(application.can_submit())
        application.status= 'approved'
        self.assertTrue(application.can_submit())
    def test_pending_application_cannot_be_submitted(self):
        user = User.objects.create_user(
            username='pendinguser',
            email='pendinguser@example.com',
            password= 'testpassword123'
        )
        application=JobApplication.objects.create(
            applicant= user,
            job_title= 'Python Developer',
            company= 'Tech Solutions',
            job_url= 'https://example.com/jobs/python-developer',
            cover_letter= 'I am interested in this position.'
        )
        application.status = 'pending'
        application.save()
        with self.assertRaises(ValueError):
            application.submit_application()
    def test_approved_application_can_be_submitted(self):
        user= User.objects.create_user(
            username='approveduser',
            email='approveduser@example.com',
            password= 'testpassword123'
        )
        application=JobApplication.objects.create(
            applicant= user,
            job_title= 'Python Developer',
            company= 'Tech Solutions',
            job_url= 'https://example.com/jobs/python-developer.',
            cover_letter= 'I am interested in this position.'
        )
        application.status= 'approved'
        application.submit_application()
        self.assertEqual(application.status, 'submitted')
class JobApplicationViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username= 'testuser',
            email= 'ahmad@example.com',
            password= 'testpassword123',
        )
        self.other_user= User.objects.create_user(
            username= 'Jobpylotuser',
            email= 'olaniyan@example.com',
            password= 'Jobpylotpassword123',
        )
        self.application = JobApplication.objects.create(
            applicant= self.user,
            job_title='Python Developer',
            company= 'Tech Solutions',
            job_url= 'https://example.com/jobs/python',
            cover_letter='I am interested in this position.'
        )
        self.application.status = 'pending'
        self.application.save()

    def test_start_application(self):
        self.client.force_login(self.user)
        self.application.status = 'saved'
        self.application.save()

        response = self.client.post(
            reverse('start_application', args=[self.application.pk])
        )

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'pending')
        self.assertRedirects(response, reverse('my_applications'))

    def test_other_user_cannot_start_application(self):
        self.client.force_login(self.other_user)
        self.application.status = 'saved'
        self.application.save()

        response = self.client.post(
            reverse('start_application', args=[self.application.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'saved')

    def test_approve_application(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('approve_application', args=[self.application.pk])
        )
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'approved')
        self.assertRedirects(response, reverse('my_applications'))

    def test_reject_application(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('reject_application', args=[self.application.pk])
        )
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'rejected')
        self.assertRedirects(response, reverse('my_applications'))
    def test_other_user_cannot_approve_application(self):
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse('approve_application', args=[self.application.pk])
        )
        self.assertEqual(response.status_code, 404)
    def test_other_user_cannot_reject_application(self):
        self.client.force_login(self.other_user)
        response= self.client.post(
            reverse('reject_application', args=[self.application.pk])
        )
        self.assertEqual(response.status_code, 404)
    def test_other_user_cannot_submit_application(self):
        self.client.force_login(self.other_user)
        response= self.client.post(
            reverse('submit_application', args=[self.application.pk])
        )
        self.assertEqual(response.status_code, 404)
    def test_pending_application_cannot_be_submitted(self):
        self.client.force_login(self.user)
        response= self.client.post(
            reverse('submit_application', args=[self.application.pk])
        )
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'pending')
        self.assertRedirects(response, reverse('my_applications'))
    def test_approved_application_can_be_submitted(self):
        self.client.force_login(self.user)
        self.application.status = 'approved'
        self.application.save()
        response= self.client.post(
            reverse('submit_application', args=[self.application.pk])
        )
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'submitted')
        self.assertRedirects(response, reverse('my_applications'))
    def test_my_application_requires_login(self):
        response= self.client.get(
            reverse('my_applications')
        )
        self.assertEqual(response.status_code, 302)
    def test_create_application_requires_login(self):
        url = reverse('create_application')

        for method in (self.client.get, self.client.post):
            with self.subTest(method=method.__name__):
                response = method(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(f"{reverse('login')}?next=", response.url)

        self.assertEqual(JobApplication.objects.count(), 1)
    def test_approve_application_requires_login(self):
        response= self.client.get(
            reverse('approve_application', args=[self.application.pk])
        )
        self.assertEqual(response.status_code, 302)
    def test_reject_application_requires_login(self):
        response = self.client.get(
            reverse('reject_application', args=[self.application.pk])
        )
        self.assertEqual(response.status_code, 302)
    def test_submit_application_requires_login(self):
        response= self.client.get(
            reverse('submit_application', args=[self.application.pk])
        )
        self.assertEqual(response.status_code, 302)