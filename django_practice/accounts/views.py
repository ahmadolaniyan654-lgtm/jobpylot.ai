from .forms import RegistrationForm, UserProfileForm, EmployerProfileForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import UserProfile, EmployerProfile
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.urls import reverse
from django.core.mail import send_mail
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.conf import settings
def register(request):
    if request.method == 'POST' :
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user= form.save(commit=False)
            user.is_active = False
            user.save()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            verification_path = reverse(
                'verify_email',
                kwargs={'uidb64' : uid, 'token' : token}
            )
            verification_link = request.build_absolute_uri(verification_path)

            send_mail(
                'Verify your JobPylot AI account',
                f'Hello {user.username}, please verify your email using this link: {verification_link}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            messages.success(request, 'Account created! Please check your email to verify your account.')
            return redirect('login')
    else:
        form= RegistrationForm()

    return render(request, 'registration/register.html', {'form' : form})

def verify_email(request, uidb64, token):
    User= get_user_model()

    try:
        uid= urlsafe_base64_decode(uidb64).decode()
        user= User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user= None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save(update_fields=['is_active'])
        messages.success(request, 'Email verified successfully. You can log in.')
        return redirect('login')
    messages.error(request, 'Verification link is invalid or has expired.')
    return redirect('login')
@login_required
def edit_profile(request):
    profile= get_object_or_404(UserProfile, user= request.user)
    form= UserProfileForm(request.POST or None, instance=profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('edit_profile')
    return render(request, 'accounts/edit_profile.html', {'form' : form, 'completion_percentage' : profile.completion_percentage})
@login_required
def employer_onboarding(request):
    profile= get_object_or_404(UserProfile, user= request.user)
    employer= EmployerProfile.objects.filter(user=request.user).first()
    form= EmployerProfileForm(request.POST or None, instance=employer)
    if request.method == 'POST' and form.is_valid():
        employer_profile= form.save(commit=False)
        employer_profile.user= request.user
        employer_profile.save()
        profile.is_employer= True
        profile.save()
        messages.success(request, 'Employer profile saved successfully!')
        return redirect('employer_onboarding')
    return render(request, 'accounts/employer_onboarding.html', {'form' : form})