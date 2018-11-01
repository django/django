from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('admin', '0001_initial'),
    ]

    # No database changes; removes auto_add and adds default/editable.
    operations = [
        migrations.AlterField(
            model_name='logentry',
            name='action_time',
            field=models.DateTimeField(
                verbose_name='action time',
                default=timezone.now,
                editable=False,
            ),
        ),
    ]
