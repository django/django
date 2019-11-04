import django.contrib.contenttypes.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ContentType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('app_label', models.CharField(max_length=100)),
                ('model', models.CharField(max_length=100, verbose_name='python model class name')),
            ],
            options={
                'ordering': ('name',),
                'db_table': 'django_content_type',
                'verbose_name': 'content type',
                'verbose_name_plural': 'content types',
            },
            bases=(models.Model,),
            managers=[
                ('objects', django.contrib.contenttypes.models.ContentTypeManager()),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='contenttype',
            unique_together={('app_label', 'model')},
        ),
    ]
