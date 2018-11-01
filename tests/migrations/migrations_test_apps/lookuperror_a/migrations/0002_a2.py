from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lookuperror_a', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='A2',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
            ],
        ),
    ]
