from django.contrib import admin
from .models import job_listing
from .models import Skill
from .models import Career

class JobListingAdmin(admin.ModelAdmin):
    list_display = ('firstname', 'lastname', 'phone', 'email')
    search_fields = ('firstname', 'lastname', 'email', 'phone')
    list_filter = ('firstname',)
    ordering = ('-id',)
    readonly_fields = ('email',)
    fieldsets = (
        ('Personal Information', {'fields': ('firstname', 'lastname', 'phone', 'email', 'skills')}),
    )
    filter_horizontal= ('skills',)
class SkillAdmin(admin.ModelAdmin):
    list_display= ('name',)
    search_fields= ('name',)
    ordering= ('name',)
class CareerAdmin(admin.ModelAdmin):
    list_display= ('title',)
    search_fields= ('title',)
    filter_horizontal= ('skills',)
admin.site.register(job_listing, JobListingAdmin)
admin.site.register(Skill)
admin.site.register(Career, CareerAdmin)
