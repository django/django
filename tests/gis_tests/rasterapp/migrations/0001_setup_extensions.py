from django.db import connection, migrations

if connection.features.supports_raster:
    from django.contrib.postgres.operations import CreateExtension

    pg_version = connection.ops.postgis_version_tuple()

    class Migration(migrations.Migration):
        # PostGIS 3+ requires postgis_raster extension.
        if pg_version[1:] >= (3,):
            operations = [
                CreateExtension("postgis_raster"),
            ]
        else:
            operations = []

else:

    class Migration(migrations.Migration):
        operations = []
