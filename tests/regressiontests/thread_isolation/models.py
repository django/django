from django.db import models

# models
class MQ(models.Model):
    val = models.CharField(maxlength=10)
    class Meta:
        app_label = 'ti'


class MX(models.Model):
    val = models.CharField(maxlength=10)
    class Meta:
        app_label = 'ti'

        
class MY(models.Model):
    val = models.CharField(maxlength=10)
    class Meta:
        app_label = 'ti'
