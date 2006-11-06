from django.db import models

class First(models.Model):
    second = models.IntegerField()

class Second(models.Model):
    first = models.ForeignKey(First, related_name = 'the_first')

# If ticket #1578 ever slips back in, these models will not be able to be
# created (the field names being lower-cased versions of their opposite
# classes is important here).

API_TESTS = ""
