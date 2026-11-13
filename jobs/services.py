from accounts.models import UserProfile
from .models import Job, CareerRequirement
from backend.job_matcher import match_job
from backend.career_skills import career_requirements
def get_user_skills(profile):
    return [
        skill.strip()
        for skill in profile.skills.split(',')
        if skill.strip()
    ]
def get_required_skills(profile):
    career= profile.desired_job.strip().lower()
    saved_career= CareerRequirement.objects.filter(
        career_title__iexact= career
    ).first()
    if saved_career:
        return [
            skill.strip()
            for skill in saved_career.required_skills.split(',')
            if skill.strip()
        ]
    for job_title, skills in career_requirements.items():
        if job_title.lower() == career:
            return skills
    return []
def match_profile_to_jobs(profile):
    user_skills= get_user_skills(profile)
    career_skills= get_required_skills(profile)
    jobs= Job.objects.filter(title__icontains=profile.desired_job.strip())

    results = []
    for job in jobs:
        job_required_skills = get_job_required_skills(job, career_skills)
        match_info = match_job(job.title, user_skills, job_required_skills)
        results.append({"job": job, "match_info": match_info})

    return results

def get_job_required_skills(job, career_skills):
    description= job.job_description.lower()

    required_skills= [
        skill for skill in career_skills
        if skill.lower() in description
    ]
    return required_skills if required_skills else career_skills