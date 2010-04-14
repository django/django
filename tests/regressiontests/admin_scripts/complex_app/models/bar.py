from django.db import models

from admin_scripts.complex_app.admin import foo
class Bar(models.Model):
    name = models.CharField(max_length=5)
    class Meta:
        app_label = 'complex_app'
