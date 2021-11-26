from django.contrib.gis.db import models
from django.contrib.gis.geos.polygon import Polygon
from django.db import migrations


class Migration(migrations.Migration):
    """
    Used for gis-specific migration tests.
    """

    dependencies = [
        ('gis_migrations', '0002_create_models'),
    ]
    operations = [
        migrations.AddField(
            model_name='household',
            name='location',
            field=models.PointField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name='household',
            constraint=models.CheckConstraint(
                check=models.Q(
                    ('location__within', Polygon(
                        ((0.0, 0.0), (0.0, 50.0), (50.0, 50.0), (50.0, 0.0), (0.0, 0.0))
                    ))),
                name='location_constraint'),
        ),
    ]
