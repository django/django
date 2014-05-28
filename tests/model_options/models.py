from django.db import models


class Country(models.Model):
    name = models.CharField(max_length=50)


class Person(models.Model):
    name = models.CharField(max_length=10)
    person_country = models.ForeignObject(Country,
        from_fields=['person_country_id'], to_fields=['id'])
