from django.db import models


class PersonWithDefaultMaxLengths(models.Model):
    email = models.EmailField()
    vcard = models.FileField(upload_to='/tmp')
    homepage = models.URLField()
    avatar = models.FilePathField()


class PersonWithCustomMaxLengths(models.Model):
    email = models.EmailField(max_length=250)
    vcard = models.FileField(upload_to='/tmp', max_length=250)
    homepage = models.URLField(max_length=250)
    avatar = models.FilePathField(max_length=250)
