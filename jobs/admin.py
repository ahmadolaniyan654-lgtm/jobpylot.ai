from django.contrib import admin
from .models import Job
@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display= (
        'title',
        'company_name',
        'employer',
        'job_location',
        'arrangement',
        'source_type',
        'source_name',
    )

    list_filter= ('arrangement', 'source_type', 'source_name')
    search_fields= ('title', 'company_name', 'job_location')
# Register your models here.
