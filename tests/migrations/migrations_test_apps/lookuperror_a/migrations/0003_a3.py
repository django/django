from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lookuperror_c', '0002_c2'),
        ('lookuperror_b', '0002_b2'),
        ('lookuperror_a', '0002_a2'),
    ]

    operations = [
        migrations.CreateModel(
            name='A3',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('b2', models.ForeignKey('lookuperror_b.B2', models.CASCADE)),
                ('c2', models.ForeignKey('lookuperror_c.C2', models.CASCADE)),
            ],
        ),
    ]
