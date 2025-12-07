from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("migrations", "0003_alter_mymodel2_unique_together")]

    operations = [
        migrations.RemoveField(
            model_name="mymodel1",
            name="field_1",
        ),
        migrations.AddField(
            model_name="mymodel1",
            name="field_3",
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name="mymodel1",
            name="field_4",
            field=models.IntegerField(null=True),
        ),
    ]
