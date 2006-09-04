from django.db import models

# models
class MX(models.Model):
    val = models.CharField(maxlength=10)
    class Meta:
        app_label = 'ri'

        
class MY(models.Model):
    val = models.CharField(maxlength=10)
    class Meta:
        app_label = 'ri'
