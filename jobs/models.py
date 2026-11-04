from django.db import models
from accounts.models import EmployerProfile

class Job(models.Model):
    SOURCE_TYPE_CHOICES= [
        ('external', 'External'),
        ('employer', 'Employer'),
    ]
    ARRANGEMENT_CHOICES =[
        ('onsite', 'Onsite'),
        ('hybrid', 'Hybrid'),
        ('remote', 'Remote'),
    ]
    employer = models.ForeignKey(
        EmployerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank= True,
        related_name='jobs'
    )
    title = models.CharField(max_length=100)
    company_name= models.CharField(max_length=255)
    job_description= models.TextField()
    job_location= models.CharField(max_length=100)
    country= models.CharField(max_length=120)
    arrangement= models.CharField(
        max_length=12,
        choices= ARRANGEMENT_CHOICES
    )
    source_type = models.CharField(
        max_length= 8,
        choices= SOURCE_TYPE_CHOICES
    )
    source_name= models.CharField(max_length=255)
    application_url= models.URLField()
    posted_at= models.DateTimeField(null=True, blank= True)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.title
# Create your models here.
