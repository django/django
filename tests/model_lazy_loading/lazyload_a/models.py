from django.db import models


class A(models.Model):
    # Refer to a model in lazyload_b, without actually importing lazyload_b
    b = models.ForeignKey('lazyload_b.B')
