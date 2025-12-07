from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("migrations", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="mymodel1",
            name="field_1",
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name="mymodel2",
            name="field_2",
            field=models.IntegerField(null=True),
        ),
        migrations.AlterField(
            model_name="mymodel2",
            name="field_1",
            field=models.IntegerField(null=True),
        ),
    ]
