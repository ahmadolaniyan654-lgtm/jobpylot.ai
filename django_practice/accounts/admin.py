from django.contrib import admin
from .models import UserProfile
from .models import EmployerProfile
admin.site.register(UserProfile)
admin.site.register(EmployerProfile)
# Register your models here.
