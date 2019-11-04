from django.db import models


class CustomTypedField(models.TextField):
    def db_type(self, connection):
        return 'custom_field'
