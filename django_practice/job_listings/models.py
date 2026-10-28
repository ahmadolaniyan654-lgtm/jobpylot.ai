from django.db import models
class job_listing(models.Model):
    firstname= models.CharField(max_length= 255)
    lastname= models.CharField(max_length= 255)
    phone= models.CharField(null= True)
    email= models.EmailField(null= True)


# Create your models here.
