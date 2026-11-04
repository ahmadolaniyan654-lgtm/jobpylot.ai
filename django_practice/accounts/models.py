from django.db import models
from django.conf import settings
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete= models.CASCADE)
    is_job_seeker = models.BooleanField(default=True)
    is_employer= models.BooleanField(default=False)
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
