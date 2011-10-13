from django.contrib.localflavor.au.models import AUStateField, AUPostCodeField
from django.db import models

class AustralianPlace(models.Model):
    state = AUStateField(blank=True)
    state_required = AUStateField()
    state_default = AUStateField(default="NSW", blank=True)
    postcode = AUPostCodeField(blank=True)
    postcode_required = AUPostCodeField()
    postcode_default = AUPostCodeField(default="2500", blank=True)
    name = models.CharField(max_length=20)

    class Meta:
        app_label = 'localflavor'
