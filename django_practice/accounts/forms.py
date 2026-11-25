from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile, EmployerProfile
class RegistrationForm(UserCreationForm):
    email= forms.EmailField(required=True)

    class Meta:
        model= User
        fields= ['username', 'email', 'password1', 'password2']

class UserProfileForm(forms.ModelForm):

    class Meta:
        model= UserProfile
        fields= [
            'desired_job',
            'skills',
            'education',
            'experience',
            'preferred_location',
            'preferred_arrangement',
        ]

class EmployerProfileForm(forms.ModelForm):

    class Meta:
        model= EmployerProfile
        fields= [
            'company_name',
            'company_description',
            'website',
            'location'
        ]