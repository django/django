from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("migrations", "0003_third"),
    ]

    operations = [migrations.RunSQL("SELECT * FROM migrations_author WHERE id = 1")]
