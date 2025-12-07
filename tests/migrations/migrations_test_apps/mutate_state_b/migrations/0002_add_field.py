from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mutate_state_b", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            [],
            [
                migrations.AddField(
                    model_name="B",
                    name="added",
                    field=models.TextField(),
                ),
            ],
        )
    ]
