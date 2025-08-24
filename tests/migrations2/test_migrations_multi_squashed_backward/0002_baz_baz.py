from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("migrations2", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="baz",
            name="baz",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
