from django.db import models

class CustomField(models.Field):
    description = "A custom field type"

class DescriptionLackingField(models.Field):
    pass
