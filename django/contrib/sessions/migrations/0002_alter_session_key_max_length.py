from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sessions', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='session',
            name='session_key',
            field=models.CharField(max_length=70, serialize=False, verbose_name='session key', primary_key=True),
        ),
    ]
