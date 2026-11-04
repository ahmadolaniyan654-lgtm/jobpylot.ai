from django.http import HttpResponse
from django.template import loader
from .models import job_listing


CAREERS = [
    "Data Analyst",
    "Web Developer",
    "Python Developer",
    "Cybersecurity Analyst",
    "Financial Accountant",
    "Business Analyst",
    "Marketing Officer",
    "Head of a Company",
    "Project Manager",
    "Physiotherapist",
    "Civil Engineer",
    "Electrical and Electronics Engineer",
    "Chemical Engineer",
    "Food Engineer",
    "Architect",
    "Mechanical Engineer",
    "Agricultural and Bioresources Engineer",
    "Psychologist",
    "Medical Laboratory Scientist",
    "Nurse",
    "Teacher/Lecturer",
    "Shop Attendant",
    "Cashier",
    "Office Assistant",
    "Economist",
    "Petroleum and Gas Engineer",
    "Frontend Developer",
    "Backend Developer",
    "Full-Stack Developer",
    "Mobile App Developer",
    "Software Engineer",
    "DevOps Engineer",
    "Cloud Engineer",
    "UI/UX Designer",
    "Data Scientist",
    "AI/Machine Learning Engineer",
    "Database Administrator",
    "IT Support Specialist",
    "Network Engineer",
]


def job_list(request):
    my_job_listings= job_listing.objects.all().values()
    template = loader.get_template('index.html')
    context= {
        'my_job_listings' : my_job_listings,
    }
    return HttpResponse(template.render(context, request))
def details(request, id):
    my_job_listing= job_listing.objects.get(id=id)
    template= loader.get_template('details.html')
    context= {
        'mymember' : my_job_listing,
    }
    return HttpResponse(template.render(context, request))
def main(request):
    template = loader.get_template('main.html')
    return HttpResponse(template.render({'careers': CAREERS}, request))


def testing(request):
    template = loader.get_template('template.html')
    context = {
        'careers': CAREERS,
    }
    return HttpResponse(template.render(context, request))
