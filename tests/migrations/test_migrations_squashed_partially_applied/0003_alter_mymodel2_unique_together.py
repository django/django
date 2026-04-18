from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("migrations", "0002_mymodel1_field_1_mymodel2_field_2_and_more")]

    operations = [
        migrations.AlterUniqueTogether(
            name="mymodel2",
            unique_together={("field_1", "field_2")},
        ),
    ]
