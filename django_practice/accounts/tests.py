from django.test import TestCase
from django.contrib.auth.models import User
from django.core import mail
from django.urls import reverse
from .models import EmployerProfile, UserProfile
import re

class RegistrationTests(TestCase):
     def test_user_can_register(self):
          response = self.client.get('/accounts/register/')
          self.assertEqual(response.status_code, 200)
          user_data = {
               'username' : 'testuser',
               'email' : 'testuser@example.com',
                'password1' : 'jobpylot123',
                'password2' : 'jobpylot123',
          }
          response= self.client.post('/accounts/register/', user_data)
          self.assertRedirects(response, '/accounts/login/')
          self.assertTrue(User.objects.filter(username='testuser').exists())
          self.assertEqual(UserProfile.objects.filter(user__username='testuser').count(), 1)
     def test_registration_fails_when_passwords_dont_match(self):
          user_data = {
               'username' : 'testuser',
               'email' : 'testuser@example.com',
               'password1' : 'jobpylot456',
               'password2' : 'jobpilot321',
          }
          response = self.client.post('/accounts/register/', user_data)
          self.assertEqual(response.status_code, 200)
          self.assertFalse(User.objects.filter(username='testuser').exists())

class LoginTests(TestCase):
     def test_user_can_login(self):
          User.objects.create_user(
               username= 'loginuser',
               email= 'loginuser@example.com',
               password= 'jobpylot123'
          )
          login_successful= self.client.login(
               username= 'loginuser',
               password = 'jobpylot123'
          )
          self.assertTrue(login_successful)
     def test_user_can_logout(self):
          User.objects.create_user(
               username= 'logoutuser',
               email= 'logoutuser@example.com',
               password= 'jobpylot123'
          )
          login_successful= self.client.login(
               username= 'logoutuser',
               password='jobpylot123'
          )
          self.assertTrue(login_successful)
          response = self.client.post('/accounts/logout/')
          self.assertRedirects(response, '/accounts/login/')
          self.assertFalse('_auth_user_id' in self.client.session)
class PasswordChangeTests(TestCase):
     def test_user_can_change_password(self):
            User.objects.create_user(
                 username= 'changeuser',
                 email= 'changeuser@example.com',
                 password= 'jobpylot123'
            )
            login_successful= self.client.login(
                 username= 'changeuser',
                 password='jobpylot123'
            )
            self.assertTrue(login_successful)
            response = self.client.get('/accounts/password_change/')
            self.assertEqual(response.status_code, 200)
            response= self.client.post('/accounts/password_change/',{
                 'old_password' : 'jobpylot123',
                 'new_password1' : 'newjobpylot456',
                 'new_password2' : 'newjobpylot456',
            })
            self.assertRedirects(response, '/accounts/password_change/done/')
            old_password_works = self.client.login(
               username= 'changeuser',
               password= 'jobpylot123'
            )
            self.assertFalse(old_password_works)
            new_password_works = self.client.login(
                 username= 'changeuser',
                 password= 'newjobpylot456'
            )
            self.assertTrue(new_password_works)
class PasswordResetTests(TestCase):
     def test_password_reset_email_is_sent(self):
          User.objects.create_user(
               username= 'resetuser',
               email= 'resetuser@example.com',
               password= 'jobpylot123'
          )
          response= self.client.post('/accounts/password_reset/', {'email': 'resetuser@example.com'})
          self.assertRedirects(response, '/accounts/password_reset/done/')
          self.assertEqual(len(mail.outbox), 1)
          self.assertIn('resetuser@example.com', mail.outbox[0].to)
     def test_password_reset_link_can_change_password(self):
          User.objects.create_user(
               username= 'resetuser2',
               email= 'resetuser2@example.com',
               password= 'jobpylot123'
          )
          response = self.client.post('/accounts/password_reset/', {'email' : 'resetuser2@example.com'})
          email= mail.outbox[0]
          reset_link= re.search(r'http://testserver/accounts/reset/\S+', email.body)
          reset_url = reset_link.group(0)
          response = self.client.get(reset_url, follow= True)
          self.assertEqual(response.status_code, 200)
          response= self.client.post(response.request['PATH_INFO'], {
               'new_password1' : 'newjobpylot789',
               'new_password2' : 'newjobpylot789',
          })
          self.assertRedirects(response, '/accounts/reset/done/')
          user = User.objects.get(username= 'resetuser2')
          self.assertTrue(user.check_password('newjobpylot789'))


class EmployerOnboardingTests(TestCase):
     def setUp(self):
          self.user = User.objects.create_user(
               username='employer',
               password='test-password',
          )
          self.profile = UserProfile.objects.get(user=self.user)
          self.url = reverse('employer_onboarding')

     def test_onboarding_requires_login(self):
          response = self.client.get(self.url)

          self.assertRedirects(
               response,
               f'{reverse("login")}?next={self.url}',
          )

     def test_first_visit_renders_form_without_existing_employer_profile(self):
          self.client.force_login(self.user)

          response = self.client.get(self.url)

          self.assertEqual(response.status_code, 200)
          self.assertTemplateUsed(response, 'accounts/employer_onboarding.html')
          self.assertFalse(EmployerProfile.objects.filter(user=self.user).exists())

     def test_post_creates_owned_employer_profile_and_marks_user_as_employer(self):
          self.client.force_login(self.user)

          response = self.client.post(
               self.url,
               {
                    'company_name': 'Example Company',
                    'company_description': 'A sample employer.',
                    'website': 'https://example.com',
                    'location': 'Lagos',
               },
          )

          self.assertRedirects(response, self.url)
          employer = EmployerProfile.objects.get(user=self.user)
          self.assertEqual(employer.company_name, 'Example Company')
          self.profile.refresh_from_db()
          self.assertTrue(self.profile.is_employer)

     def test_post_updates_existing_profile_without_creating_a_duplicate(self):
          employer = EmployerProfile.objects.create(
               user=self.user,
               company_name='Old Company',
          )
          self.client.force_login(self.user)

          response = self.client.post(
               self.url,
               {
                    'company_name': 'Updated Company',
                    'company_description': '',
                    'website': '',
                    'location': '',
                    'user': '99999',
               },
          )

          self.assertRedirects(response, self.url)
          employer.refresh_from_db()
          self.assertEqual(employer.company_name, 'Updated Company')
          self.assertEqual(employer.user, self.user)
          self.assertEqual(
               EmployerProfile.objects.filter(user=self.user).count(),
               1,
          )
          self.profile.refresh_from_db()
          self.assertTrue(self.profile.is_employer)