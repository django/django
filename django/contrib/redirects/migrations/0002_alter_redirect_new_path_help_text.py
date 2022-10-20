from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("redirects", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="redirect",
            name="new_path",
            field=models.CharField(
                blank=True,
                help_text=(
                    "This can be either an absolute path (as above) or a full "
                    "URL starting with a scheme such as “https://”."
                ),
                max_length=200,
                verbose_name="redirect to",
            ),
        ),
    ]
