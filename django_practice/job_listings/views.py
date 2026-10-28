from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from .models import job_listing
def job_list(request):
    my_job_listings= job_listing.objects.all().values()
    template = loader.get_template('index.html')
    context= {
        'my_job_listings' : my_job_listings,
    }
    return HttpResponse(template.render(context, request))
