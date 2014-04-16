from django.db import models, migrations
import django.contrib.gis.db.models.fields


# Used for regression test of ticket #22001: https://code.djangoproject.com/ticket/22001
class Migration(migrations.Migration):

    operations = [
        migrations.CreateModel(
            name='Neighborhood',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('geom', django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Household',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('neighborhood', models.ForeignKey(to='gis.Neighborhood', to_field='id', null=True)),
                ('address', models.CharField(max_length=100)),
                ('zip_code', models.IntegerField(null=True, blank=True)),
                ('geom', django.contrib.gis.db.models.fields.PointField(srid=4326, null=True, geography=True)),
            ],
            options={
            },
            bases=(models.Model,),
        )
    ]
