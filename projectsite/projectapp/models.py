from django.db import models

# Create your models here.
# Following the tutorial here https://realpython.com/get-started-with-django-1/#why-you-should-learn-django

class ProjectApp(models.Model):
    title= models.CharField(max_length=100)
    escription = models.TextField()
    technology = models.CharField(max_length=20)
    image = models.FilePathField(path="/img")
