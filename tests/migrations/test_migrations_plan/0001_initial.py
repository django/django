from django.db import migrations, models


def grow_tail(x, y):
    """Grow salamander tail."""
    pass


def shrink_tail(x, y):
    """Shrink salamander tail."""
    pass


class Migration(migrations.Migration):

    initial = True

    operations = [
        migrations.CreateModel(
            "Salamander",
            [
                ("id", models.AutoField(primary_key=True)),
                ("tail", models.IntegerField(default=0)),
                ("silly_field", models.BooleanField(default=False)),
            ],
        ),
        migrations.RunPython(grow_tail, shrink_tail),
    ]
