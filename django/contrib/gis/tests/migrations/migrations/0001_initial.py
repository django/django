from django.db import models, migrations
import django.contrib.gis.db.models.fields


# Used for regression test of ticket #22001: https://code.djangoproject.com/ticket/22001
class Migration(migrations.Migration):

    operations = [
        migrations.CreateModel(
            name='Neighborhood',
            fields=[
                (u'id', models.AutoField(verbose_name=u'ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.TextField(unique=True)),
                ('geom', django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Household',
            fields=[
                (u'id', models.AutoField(verbose_name=u'ID', serialize=False, auto_created=True, primary_key=True)),
                ('neighborhood', models.ForeignKey(to='gis.Neighborhood', to_field=u'id', null=True)),
                ('address', models.TextField()),
                ('zip_code', models.IntegerField(null=True, blank=True)),
                ('geom', django.contrib.gis.db.models.fields.PointField(srid=4326, null=True, geography=True)),
            ],
            options={
            },
            bases=(models.Model,),
        )
    ]
