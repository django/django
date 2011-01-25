from django.db import models


class People(models.Model):
    name = models.CharField(max_length=255)

class Message(models.Model):
    from_field = models.ForeignKey(People, db_column='from_id')
