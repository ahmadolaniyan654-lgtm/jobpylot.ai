from django.urls import path
from .views import (
    employer_applications,
    employer_accept_application,
    employer_reject_application,
    employer_mark_under_review,
    my_applications,
    create_application,
    start_application,
    approve_application,
    reject_application,
    submit_application,
    dashboard,
    apply_to_job,
)
urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('my_applications/', my_applications, name= 'my_applications'),
    path('create/', create_application, name= 'create_application'),
    path('apply/<int:job_id>/', apply_to_job, name='apply_to_job'),
    path('start/<int:application_id>/', start_application, name= 'start_application'),
    path('approve/<int:application_id>/', approve_application, name='approve_application'),
    path('reject/<int:application_id>/', reject_application, name= 'reject_application'),
    path('submit/<int:application_id>/', submit_application, name= 'submit_application'),
    path(
        'employer/jobs/<int:job_id>/',
        employer_applications,
        name='employer_applications'
    ),
    path('employer/jobs/applications/<int:application_id>/accept/', employer_accept_application, name='employer_accept_application'),
    path('employer/jobs/applications/<int:application_id>/reject/', employer_reject_application, name='employer_reject_application'),
    path('employer/jobs/applications/<int:application_id>/review/', employer_mark_under_review, name='employer_mark_under_review'),
]