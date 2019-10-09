from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("migrations", "0002_second")]

    operations = [
        migrations.AddField("Author", "date_of_birth", models.DateField(null=True)),
    ]
