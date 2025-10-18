from django.db import migrations


class Migration(migrations.Migration):
    initial = True

    replaces = [
        ("app1", "0001_initial"),
    ]

    run_before = [
        ("app2", "0001_squashed_initial"),
    ]

    dependencies = []

    operations = []
