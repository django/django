from django.db import migrations


class Migration(migrations.Migration):
    initial = True

    replaces = [
        ("app1", "0001_initial"),
    ]

    dependencies = [
        ("app1", "0001_squashed_initial"),
        ("app2", "0001_squashed_initial"),
    ]

    operations = []
