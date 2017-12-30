import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0009_alter_user_last_name_max_length'),
    ]

    operations = [
        migrations.AlterField(
            model_name='permission',
            name='content_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    to='contenttypes.ContentType', verbose_name='content type'),
        ),
        migrations.AddField(
            model_name='permission',
            name='app_label',
            field=models.CharField(max_length=100, blank=True, default=''),
        ),
    ]
