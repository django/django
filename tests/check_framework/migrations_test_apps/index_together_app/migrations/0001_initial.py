from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    operations = [
        migrations.CreateModel(
            "SimpleModel",
            [
                ("field", models.IntegerField()),
            ],
        ),
        migrations.AlterIndexTogether("SimpleModel", index_together=(("id", "field"),)),
    ]
