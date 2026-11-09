from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    operations = [
        migrations.CreateModel(
            name="Company",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField()),
                ("age", models.IntegerField()),
            ],
            options={
                "unique_together": {("name", "slug")},
            },
        ),
    ]
