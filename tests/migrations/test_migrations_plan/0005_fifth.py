from django.db import migrations


def grow_tail(x, y):
    pass


def feed(x, y):
    """Feed salamander."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("migrations", "0004_fourth"),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop),
        migrations.RunPython(grow_tail),
        migrations.RunPython(feed, migrations.RunPython.noop),
    ]
