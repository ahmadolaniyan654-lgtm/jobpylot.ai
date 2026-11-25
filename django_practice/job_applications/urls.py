from django.urls import path
from .views import (
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
]