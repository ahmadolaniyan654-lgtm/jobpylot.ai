from django.urls import path
from .import views
urlpatterns= [
    path('register/', views.register, name= 'register'),
    path('edit-profile/', views.edit_profile, name= 'edit_profile'),
    path('employer-onboarding/', views.employer_onboarding, name= 'employer_onboarding'),
    path('verify/<uidb64>/<token>/', views.verify_email, name= 'verify_email')
]