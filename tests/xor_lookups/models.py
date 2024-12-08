from django.db import models


class Number(models.Model):
    num = models.IntegerField()

    def __str__(self):
        return str(self.num)
