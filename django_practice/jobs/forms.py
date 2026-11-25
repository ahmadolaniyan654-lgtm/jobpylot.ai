from django import forms
from .models import Job
class JobForm(forms.ModelForm):
    class Meta:
        model= Job
        fields= [
            'title',
            'job_description',
            'job_location',
            'country',
            'arrangement',
            'application_method',
            'application_url',
        ]

    def clean(self):
        cleaned_data= super().clean()
        application_method= cleaned_data.get('application_method')
        application_url= cleaned_data.get('application_url')
        if application_method == 'external' and not application_url:
            raise forms.ValidationError(
                'An application URL is required for external applications.'
            )
        return cleaned_data