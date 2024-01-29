from django.db import connection, migrations

if connection.features.supports_raster:
    from django.contrib.postgres.operations import CreateExtension

    class Migration(migrations.Migration):
        operations = [
            CreateExtension("postgis_raster"),
        ]

else:

    class Migration(migrations.Migration):
        operations = []
