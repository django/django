from django.contrib.gis.db import models
from django.db import connection, migrations

ops = [
    migrations.CreateModel(
        name='Neighborhood',
        fields=[
            ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ('name', models.CharField(max_length=100, unique=True)),
            ('geom', models.MultiPolygonField(srid=4326)),
        ],
        options={
        },
        bases=(models.Model,),
    ),
    migrations.CreateModel(
        name='Household',
        fields=[
            ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ('neighborhood', models.ForeignKey(
                'gis_migrations.Neighborhood',
                models.SET_NULL,
                to_field='id',
                null=True,
            )),
            ('address', models.CharField(max_length=100)),
            ('zip_code', models.IntegerField(null=True, blank=True)),
            ('geom', models.PointField(srid=4326, geography=True)),
        ],
        options={
        },
        bases=(models.Model,),
    ),
    migrations.CreateModel(
        name='Family',
        fields=[
            ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ('name', models.CharField(max_length=100, unique=True)),
        ],
        options={
        },
        bases=(models.Model,),
    ),
    migrations.AddField(
        model_name='household',
        name='family',
        field=models.ForeignKey('gis_migrations.Family', models.SET_NULL, blank=True, null=True),
        preserve_default=True,
    )
]

if connection.features.supports_raster:
    ops += [
        migrations.CreateModel(
            name='Heatmap',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('rast', models.fields.RasterField(srid=4326)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]


class Migration(migrations.Migration):
    """
    Used for gis-specific migration tests.
    """
    dependencies = [
        ('gis_migrations', '0001_setup_extensions'),
    ]
    operations = ops
