from django.db import migrations
from django.contrib.gis.db import models
from django.contrib.gis.geos.polygon import Polygon


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
                check=models.Q(('location__within', Polygon(((1, 1), (1, 1), (1, 1), (1, 1), (1, 1))))),
                name='location_constraint'),
        ),
    ]
