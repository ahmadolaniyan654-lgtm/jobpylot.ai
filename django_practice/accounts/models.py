from django.db import models
from django.conf import settings
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete= models.CASCADE)
    is_job_seeker = models.BooleanField(default=True)
    is_employer= models.BooleanField(default=False)
    desired_job= models.CharField(max_length=255, blank=True)
    skills= models.TextField(blank= True)
    education= models.TextField(blank= True)
    experience= models.TextField(blank= True)
    preferred_location= models.CharField(max_length=255, blank= True)
    preferred_arrangement= models.CharField(max_length=10, choices=[
        ('any', 'Any'),
        ('hybrid', 'Hybrid'),
        ('remote', 'Remote'),
        ('onsite', 'On-site'),
    ], blank= True, default= 'any')
    @property
    def completion_percentage(self):
        fields=[
            self.desired_job,
            self.skills,
            self.education,
            self.experience,
            self.preferred_location,
            self.preferred_arrangement,
        ]

        completed_fields = sum(bool(field.strip()) for field in fields)
        return round(completed_fields / len(fields) * 100)
    def __str__(self):
        return self.user.username
class EmployerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete= models.CASCADE)
    company_name= models.CharField(max_length=255)
    company_description= models.TextField(blank= True)
    website= models.URLField(blank= True)
    location = models.CharField(max_length=255, blank= True)
    created_at= models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.company_name
# Create your models here.
