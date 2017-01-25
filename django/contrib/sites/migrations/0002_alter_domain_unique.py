from django.contrib.sites.validators import _simple_domain_name_validator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='domain',
            field=models.CharField(
                max_length=100, unique=True, validators=[_simple_domain_name_validator],
                verbose_name='domain name'
            ),
        ),
    ]
