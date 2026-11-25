from django.test import TestCase
from django.urls import reverse

from .models import job_listing


class JobListingDetailTests(TestCase):
    def test_missing_listing_returns_not_found(self):
        response = self.client.get(
            reverse("details", args=[999999]),
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 404)

    def test_existing_listing_renders_details(self):
        listing = job_listing.objects.create(
            firstname="Taylor",
            lastname="Candidate",
        )

        response = self.client.get(
            reverse("details", args=[listing.pk]),
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Taylor Candidate")


class HomepageTests(TestCase):
    def test_homepage_serves_the_existing_designed_landing_page(self):
        response = self.client.get(reverse("main"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html; charset=utf-8")
        self.assertContains(response, 'id="hero-title"')
        self.assertContains(response, 'id="job-search-form"')
        self.assertContains(response, "/jobs?")
