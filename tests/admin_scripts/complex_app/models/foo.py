from django.db import models


class Foo(models.Model):
    name = models.CharField(max_length=5)

    class Meta:
        app_label = "complex_app"
