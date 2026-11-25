from django import forms
from .models import JobApplication
class JobApplicationForm(forms.ModelForm):
    class Meta:
        model= JobApplication
        fields = ['job_title', 'company', 'job_url', 'cover_letter']

class InternalJobApplicationForm(forms.ModelForm):
    class Meta:
        model= JobApplication
        fields= ['cover_letter']