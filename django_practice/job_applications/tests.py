from django.test import TestCase
from django.contrib.auth.models import User
from .models import JobApplication
from django.urls import reverse
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
        response= self.client.get(
            reverse('create_application')
        )
        self.assertEqual(response.status_code, 302)
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