from django.db import models


class job_listing(models.Model):
    firstname = models.CharField(max_length=255)
    lastname = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, null= True)
    email = models.EmailField(null=True)
    skills = models.ManyToManyField('Skill')

    def __str__(self):
        return f'{self.firstname} {self.lastname}'


class Skill(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
class Career(models.Model):
    title = models.CharField(max_length=255)
    skills= models.ManyToManyField(Skill)

    def __str__(self):
        return self.title
