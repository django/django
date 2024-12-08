from django.db import migrations, models


class Migration(migrations.Migration):
    """
    This is a wee bit crazy, but it's just to show that run_before works.
    """

    dependencies = [
        ("migrations", "0001_initial"),
    ]

    run_before = [
        ("migrations", "0002_second"),
    ]

    operations = [
        migrations.CreateModel(
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(null=True)),
                ("age", models.IntegerField(default=0)),
            ],
        )
    ]
