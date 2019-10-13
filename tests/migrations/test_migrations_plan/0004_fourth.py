from django.db import migrations


def grow_tail(x, y):
    pass


def shrink_tail(x, y):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("migrations", "0003_third"),
    ]

    operations = [
        migrations.RunSQL('SELECT * FROM migrations_author WHERE id = 1'),
        migrations.RunPython(grow_tail, shrink_tail),
    ]
