from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from accounts.models import UserProfile, EmployerProfile
from backend.job_matcher import entry_level, match_job
from .services import (
    get_career_requirements,
    get_job_required_skills,
    match_profile_to_jobs,
)
from .models import Job
from .forms import JobForm

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
@login_required
def post_job(request):
    profile= get_object_or_404(EmployerProfile, user= request.user)
    if request.method == 'POST':
        form= JobForm(request.POST)

        if form.is_valid():
            job= form.save(commit=False)
            job.employer= profile
            job.company_name= profile.company_name
            job.source_type = 'employer'
            job.source_name = profile.company_name
            job.save()
            return redirect('job_detail', job_id= job.id)
    else:
        form= JobForm()
    return render(request, 'jobs/post_job.html', {'form' : form})
@login_required
def my_posted_jobs(request):
    profile=get_object_or_404(EmployerProfile, user= request.user)
    jobs= Job.objects.filter(employer=profile).order_by('-posted_at', '-created_at')
    return render(request, 'jobs/my_posted_jobs.html', {'jobs': jobs})
@login_required
def edit_job(request, job_id):
    job= get_object_or_404(Job, id= job_id, employer__user= request.user)
    if request.method == 'POST':
        form= JobForm(request.POST, instance= job)
        if form.is_valid():
            form.save()
            return redirect('job_detail', job_id= job.id)
    else:
        form= JobForm(instance= job)
    return render(request, 'jobs/edit_job.html', {'form' : form, 'job': job})
@login_required
def delete_job(request, job_id):
    job= get_object_or_404(Job, id= job_id, employer__user= request.user)
    if request.method == 'POST':
        job.delete()
        return redirect('my_posted_jobs')
    return render(request, 'jobs/delete_job.html', {'job': job})
@require_GET
def homepage_job_search(request):
    title = request.GET.get("title", "").strip()
    city = request.GET.get("city", "").strip()
    country = request.GET.get("country", "").strip()
    arrangement = request.GET.get("arrangement", "Any").strip()
    application_method = request.GET.get("application_method", "Any").strip()
    user_skills = [
        skill.strip()
        for skill in request.GET.get("user_skills", "").split(",")
        if skill.strip()
    ]

    if not title or not country:
        return JsonResponse(
            {"detail": "Enter a job title and country before searching."},
            status=400,
        )
    if len(title) > 100 or len(city) > 100 or len(country) > 100:
        return JsonResponse(
            {"detail": "Search fields must be 100 characters or fewer."},
            status=400,
        )

    arrangement_values = {
        "any": None,
        "onsite": "onsite",
        "hybrid": "hybrid",
        "remote": "remote",
    }
    arrangement_key = arrangement.casefold()
    if arrangement_key not in arrangement_values:
        return JsonResponse(
            {"detail": "Choose Any, Onsite, Hybrid, or Remote work."},
            status=400,
        )
    normalized_arrangement = arrangement_values[arrangement_key]

    jobs = Job.objects.filter(
        title__icontains=title,
        country__icontains=country,
    )
    if city:
        jobs = jobs.filter(job_location__icontains=city)
    total_count = jobs.count()
    if normalized_arrangement:
        jobs = jobs.filter(arrangement=normalized_arrangement)

    career_skills = get_career_requirements(title)
    results = []
    for job in jobs.order_by("-posted_at", "-created_at")[:50]:
        result = {
            "title": job.title,
            "company": job.company_name,
            "location": job.job_location,
            "description": job.job_description,
            "posted_at": job.posted_at.isoformat() if job.posted_at else None,
            "url": job.application_url,
            "source": job.source_name or job.get_source_type_display(),
            "potentially_entry_level": entry_level(job.title),
        }
        if user_skills and career_skills:
            required_skills = get_job_required_skills(job, career_skills)
            result.update(match_job(job.title, user_skills, required_skills))
        results.append(result)

    response = {
        "query": title,
        "city": city or country,
        "country": country,
        "arrangement": "Any" if normalized_arrangement is None else normalized_arrangement.title(),
        "source": "Django",
        "jobs": results,
        "total_count": total_count,
    }
    return JsonResponse(response)
# Create your views here.
