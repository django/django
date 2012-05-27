from django.contrib.localflavor.mx.models import (
    MXStateField, MXRFCField, MXCURPField, MXZipCodeField,
    MXSocialSecurityNumberField)
from django.db import models


class MXPersonProfile(models.Model):
    state = MXStateField()
    rfc = MXRFCField()
    curp = MXCURPField()
    zip_code = MXZipCodeField()
    ssn = MXSocialSecurityNumberField()

    class Meta:
        app_label = 'localflavor'
