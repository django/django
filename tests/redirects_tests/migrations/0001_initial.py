from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('redirects', '0003_add_redirect_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='OverriddenRedirect',
            fields=[
                (
                    'redirect_ptr',
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to='redirects.redirect',
                    ),
                )
            ],
            bases=('redirects.redirect',),
        ),
    ]
