from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import JobApplication
from .forms import JobApplicationForm
@login_required
def my_applications(request):
    applications= JobApplication.objects.filter(applicant=request.user)
    return render(request, 'job_applications/my_applications.html', {'applications': applications})
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
            'form' : form
        })

@login_required
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