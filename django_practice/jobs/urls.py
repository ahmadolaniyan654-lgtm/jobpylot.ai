from django.urls import path
from . import views
urlpatterns= [
    path('', views.job_matching, name= 'job_matching'),
    path('post/', views.post_job, name='post_job'),
    path('my-posted-jobs/', views.my_posted_jobs, name='my_posted_jobs'),
    path('<int:job_id>/edit/', views.edit_job, name='edit_job'),
    path('<int:job_id>/delete/', views.delete_job, name='delete_job'),
    path('<int:job_id>/', views.job_detail, name= 'job_detail'),
]