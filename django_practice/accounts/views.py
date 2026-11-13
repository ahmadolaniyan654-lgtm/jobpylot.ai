from .forms import RegistrationForm, UserProfileForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import UserProfile
def register(request):
    if request.method == 'POST' :
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form= RegistrationForm()

    return render(request, 'registration/register.html', {'form' : form})
@login_required
def edit_profile(request):
    profile= get_object_or_404(UserProfile, user= request.user)
    form= UserProfileForm(request.POST or None, instance=profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('edit_profile')
    return render(request, 'accounts/edit_profile.html', {'form' : form, 'completion_percentage' : profile.completion_percentage})