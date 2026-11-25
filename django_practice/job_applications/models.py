from django.db import models
from django.contrib.auth.models import User
from jobs.models import Job
STATUS_CHOICES= [
    ('saved', 'Saved'),
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('submitted', 'Submitted'),
]
class JobApplication(models.Model):
    job= models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications'
    )
    applicant= models.ForeignKey(
        User,
        on_delete= models.CASCADE
    )
    job_title= models.CharField(max_length= 200)
    company= models.CharField(max_length=200)
    job_url= models.URLField(blank=True)
    cover_letter = models.TextField()
    status = models.CharField(max_length=20, choices= STATUS_CHOICES, default= 'saved')
    created_at= models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.job_title} at {self.company}"
    def can_submit(self):
        return self.status == 'approved'
    def submit_application(self):
        if not self.can_submit():
            raise ValueError('Application must be approved before submission.')
        self.status= 'submitted'
        self.save()