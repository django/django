from django.db import connection

if connection.vendor == "postgresql":
    from django.contrib.postgres.fields import UUID4AutoField

    FieldForTesting = UUID4AutoField
else:
    from django.db.models import AutoField

    FieldForTesting = AutoField
