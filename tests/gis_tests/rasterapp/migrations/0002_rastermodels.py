from django.contrib.gis.db import models
from django.db import migrations
from django.db.models import deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rasterapp', '0001_setup_extensions'),
    ]

    operations = [
        migrations.CreateModel(
            name='RasterModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rast', models.fields.RasterField(
                    blank=True,
                    null=True,
                    srid=4326,
                    verbose_name='A Verbose Raster Name',
                )),
                ('rastprojected', models.fields.RasterField(
                    null=True,
                    srid=3086,
                    verbose_name='A Projected Raster Table',
                )),
                ('geom', models.fields.PointField(null=True, srid=4326)),
            ],
            options={
                'required_db_features': ['supports_raster'],
            },
        ),
        migrations.CreateModel(
            name='RasterRelatedModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rastermodel', models.ForeignKey(
                    on_delete=deletion.CASCADE,
                    to='rasterapp.rastermodel',
                )),
            ],
            options={
                'required_db_features': ['supports_raster'],
            },
        ),
    ]
