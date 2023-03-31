from django.db import models
from django.contrib.auth.models import AbstractUser, , BaseUserManager
from django.conf import settings
from django.shortcuts import render
from rmigrate.amodels import A
from .managers import CustomUserManager



# Create your models here.

#class User(AbstractUser):
    #pass

#original
#class A(models.Model):
    #user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

class B(models.Model):
    #original
    #a = models.ForeignKey('A', on_delete=models.PROTECT)
    #alterar
    a = models.ForeignKey(A, on_delete=models.CASCADE)



class CustomUser(AbstractUser, PermissionsMixin):
    # remove o campo email
    # email = models.EmailField(unique=True)

    # adiciona os campos first_name, last_name e email à classe pai AbstractUser
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    email = models.EmailField(unique=True)

    # define o gerenciador de objetos personalizados para o modelo de usuário
    objects = CustomUserManager()

    def __str__(self):
        return self.email


