import django.contrib.sites.managers
import django.db.models.manager
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sites", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomArticle",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=50)),
                (
                    "places_this_article_should_appear",
                    models.ForeignKey("sites.Site", models.CASCADE),
                ),
            ],
            options={
                "abstract": False,
            },
            managers=[
                ("objects", django.db.models.manager.Manager()),
                (
                    "on_site",
                    django.contrib.sites.managers.CurrentSiteManager(
                        "places_this_article_should_appear"
                    ),
                ),
            ],
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="ExclusiveArticle",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=50)),
                ("site", models.ForeignKey("sites.Site", models.CASCADE)),
            ],
            options={
                "abstract": False,
            },
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("on_site", django.contrib.sites.managers.CurrentSiteManager()),
            ],
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="SyndicatedArticle",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=50)),
                ("sites", models.ManyToManyField("sites.Site")),
            ],
            options={
                "abstract": False,
            },
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("on_site", django.contrib.sites.managers.CurrentSiteManager()),
            ],
            bases=(models.Model,),
        ),
    ]
