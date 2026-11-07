from django.db import migrations


def query_through_foreign_key(apps, schema_editor):
    A = apps.get_model("delayed_reload_b", "A")
    B = apps.get_model("delayed_reload_b", "B")
    # Raises ValueError if B.a points to a stale class of A.
    B.objects.filter(a=A(pk=1))


class Migration(migrations.Migration):
    dependencies = [
        ("delayed_reload_a", "0001_initial"),
        ("delayed_reload_b", "0002_alter_c_options"),
    ]

    operations = [
        migrations.RunPython(query_through_foreign_key, query_through_foreign_key),
    ]
