from django.db import models


class PersonWithDefaultMaxLengths(models.Model):
    email = models.EmailField()
    vcard = models.FileField()
    homepage = models.URLField()
    avatar = models.FilePathField()


class PersonWithCustomMaxLengths(models.Model):
    email = models.EmailField(max_length=250)
    vcard = models.FileField(max_length=250)
    homepage = models.URLField(max_length=250)
    avatar = models.FilePathField(max_length=250)
