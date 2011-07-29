from django.db import models
from django.contrib.localflavor.mx.models import (
    MXStateField, MXRFCField, MXCURPField, MXZipCodeField)

class MXPersonProfile(models.Model):
    state = MXStateField()
    rfc = MXRFCField()
    curp = MXCURPField()
    zip_code = MXZipCodeField()

    class Meta:
        app_label = 'localflavor'
