from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                ("email", models.EmailField(max_length=191, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="Domain",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                ("owner", models.ForeignKey("migrations.User", models.SET_NULL)),
            ],
        ),
        migrations.CreateModel(
            name="RRset",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                ("subname", models.CharField(blank=True, max_length=178)),
                ("domain", models.ForeignKey("migrations.Domain", models.SET_NULL)),
            ],
        ),
        migrations.CreateModel(
            name="Token",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True)),
                ("user", models.ForeignKey("migrations.User", models.SET_NULL)),
            ],
        ),
        migrations.AlterField(
            model_name="RRset",
            name="subname",
            field=models.CharField(blank=False, max_length=178),
        ),
    ]
