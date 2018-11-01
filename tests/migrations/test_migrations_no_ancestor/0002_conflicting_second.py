from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [

        migrations.DeleteModel("Tribble"),

        migrations.RemoveField("Author", "silly_field"),

        migrations.AddField("Author", "rating", models.IntegerField(default=0)),

        migrations.CreateModel(
            "Book",
            [
                ("id", models.AutoField(primary_key=True)),
                ("author", models.ForeignKey("migrations.Author", models.SET_NULL, null=True)),
            ],
        )

    ]
