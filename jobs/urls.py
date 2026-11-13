from django.urls import path
from . import views
urlpatterns= [
    path('', views.job_matching, name= 'job_matching'),
    path('<int:job_id>/', views.job_detail, name= 'job_detail'),
]