from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import JobApplication
from .forms import JobApplicationForm, InternalJobApplicationForm
from jobs.models import Job
@login_required
def my_applications(request):
    applications= JobApplication.objects.filter(applicant=request.user)
    total_applications= applications.count()
    total_saved= applications.filter(status='saved').count()
    total_pending= applications.filter(status='pending').count()
    total_approved= applications.filter(status= 'approved').count()
    total_rejected= applications.filter(status= 'rejected').count()
    total_submitted= applications.filter(status= 'submitted').count()
    return render(request, 'job_applications/my_applications.html',{
        'applications' : applications,
        'total_applications' : total_applications,
        'total_saved' : total_saved,
        'total_pending' : total_pending,
        'total_approved' : total_approved,
        'total_rejected' : total_rejected,
        'total_submitted' : total_submitted
    })
@login_required
def dashboard(request):
    applications= JobApplication.objects.filter(applicant=request.user)
    total_applications= applications.count()
    total_saved= applications.filter(status='saved').count()
    total_approved= applications.filter(status='approved').count()
    total_pending= applications.filter(status='pending').count()
    total_rejected= applications.filter(status='rejected').count()
    total_submitted= applications.filter(status='submitted').count()
    recent_applications= applications.order_by('-created_at')[:3]
    return render(request, 'job_applications/dashboard.html', {
        'total_applications': total_applications,
        'total_saved': total_saved,
        'total_pending': total_pending,
        'total_approved': total_approved,
        'total_rejected': total_rejected,
        'total_submitted': total_submitted,
        'recent_applications' : recent_applications
    })
@login_required
def create_application(request):
    form= JobApplicationForm()
    if request.method == 'POST' :
        form = JobApplicationForm(request.POST)
        if form.is_valid():
            application= form.save(commit=False)
            application.applicant = request.user
            application.save()
            return redirect('my_applications')
    return render(request, 'job_applications/create_application.html', {
            'form' : form,
        })
@login_required
def apply_to_job(request, job_id):
    job= get_object_or_404(
        Job,
        id=job_id,
        application_method='internal'
    )
    if request.method == 'POST':
        form= InternalJobApplicationForm(request.POST)
        if form.is_valid():
            application= form.save(commit=False)
            application.applicant= request.user
            application.job= job
            application.job_title= job.title
            application.company= job.company_name
            application.job_url= job.application_url
            application.save()
            return redirect('my_applications')
    else:
        form= InternalJobApplicationForm()
    return render(request, 'job_applications/apply_to_job.html', {
        'form' : form,
        'job' : job
    })
@login_required
@require_POST
def start_application(request, application_id):
    if request.method == 'POST' :
        application = get_object_or_404(
            JobApplication,
            id=application_id,
            applicant=request.user
        )
        if application.status == 'saved':
            application.status = 'pending'
            application.save()
    return redirect('my_applications')

@login_required
@require_POST
def approve_application(request, application_id):
    if request.method == 'POST' :
        application= get_object_or_404(
            JobApplication,
            id= application_id,
            applicant=request.user
        )
        if application.status == 'pending' :
            application.status = 'approved'
            application.save()
    return redirect('my_applications')

@login_required
@require_POST
def reject_application(request, application_id):
    if request.method == 'POST' :
        application= get_object_or_404(
            JobApplication,
            id= application_id,
            applicant= request.user
        )
        if application.status == 'pending' :
            application.status = 'rejected'
            application.save()
    return redirect('my_applications')

@login_required
@require_POST
def submit_application(request, application_id):
    if request.method == 'POST':
        application= get_object_or_404(
            JobApplication,
            id= application_id,
            applicant= request.user
        )
        if application.status == 'approved':
            application.submit_application()
    return redirect('my_applications')

@login_required
def employer_applications(request, job_id):
        job= get_object_or_404(
            Job,
            id=job_id,
            employer__user= request.user
        )
        applications= JobApplication.objects.filter(
            job=job,
            status__in=['submitted', 'under_review']
        )
        return render(request, 'job_applications/employer_applications.html', {
            'job' : job,
            'applications' : applications
        })
@login_required
@require_POST
def employer_mark_under_review(request, application_id):
    if request.method == 'POST':
        application= get_object_or_404(
            JobApplication,
            id=application_id,
            job__employer__user=request.user,
            status= 'submitted'
        )

        application.status='under_review'
        application.save()
        return redirect('employer_applications', job_id= application.job.id)
@login_required
@require_POST
def employer_accept_application(request, application_id):
    if request.method == 'POST':
        application= get_object_or_404(
            JobApplication,
            id=application_id,
            job__employer__user=request.user,
            status__in=['submitted', 'under_review']
        )

        application.status= 'employer_accepted'
        application.save()
        return redirect('employer_applications', job_id= application.job.id)

@login_required
@require_POST
def employer_reject_application(request, application_id):
    if request.method == 'POST':
        application= get_object_or_404(
            JobApplication,
            id= application_id,
            job__employer__user=request.user,
            status__in=['submitted', 'under_review']
        )

        application.status= 'employer_rejected'
        application.save()
        return redirect('employer_applications', job_id=application.job.id)