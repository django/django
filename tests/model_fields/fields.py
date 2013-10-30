from django.db import models


class UpdateOnlyField(models.CharField):
    use_on_insert = False


class SelectOnlyField(models.CharField):
    use_on_insert = False
    use_on_update = False
