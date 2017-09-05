from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Redirect',

            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('old_path', models.CharField(
                    help_text=(
                        "This should be an absolute path, excluding the domain name. Example: '/events/search/'."
                    ), max_length=200, verbose_name='redirect from', db_index=True
                )),
                ('new_path', models.CharField(
                    help_text="This can be either an absolute path (as above) or a full URL starting with 'http://'.",
                    max_length=200, verbose_name='redirect to', blank=True
                )),
                # We need to add `domain` field to migrate sites references
                # data. Some db backends add fields by creating new table
                # and copying all fields which are in project state. This
                # field helps preserve `sites` references without requiring
                # dependency on 'django.contrib.sites' migrations.
                ('site_id', models.IntegerField(null=True)),
            ],
            options={
                'ordering': ('old_path',),
                'db_table': 'django_redirect',
                'verbose_name': 'redirect',
                'verbose_name_plural': 'redirects',
            },
            bases=(models.Model,),
        ),
    ]
