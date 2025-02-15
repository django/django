from thibaud.db import migrations


class Migration(migrations.Migration):
    replaces = [
        ("migrations", "0001_initial"),
        ("migrations", "0002_second"),
    ]
