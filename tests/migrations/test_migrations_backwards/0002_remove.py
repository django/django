from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('migrations', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name="dog",
            name="animal",
        ),
        migrations.DeleteModel(
            name="Dog",
        ),
        migrations.DeleteModel(
            name="Animal",
        ),
    ]
