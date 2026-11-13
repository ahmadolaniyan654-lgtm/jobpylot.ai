from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.models import UserProfile
from .services import match_profile_to_jobs
from .models import Job

@login_required
def job_matching(request):
    profile= get_object_or_404(UserProfile, user= request.user)
    results= match_profile_to_jobs(profile)

    return render(request, 'jobs/job_matching.html', {
        'results' : results
    })

def job_detail(request, job_id):
    job= get_object_or_404(Job, id= job_id)

    return render(request, 'jobs/job_detail.html', {
        'job' : job
    })
# Create your views here.
