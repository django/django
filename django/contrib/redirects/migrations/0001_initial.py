from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Redirect',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('site', models.ForeignKey(
                    to='sites.Site',
                    to_field='id',
                    on_delete=models.CASCADE,
                    verbose_name='site',
                )),
                ('old_path', models.CharField(
                    help_text=(
                        'This should be an absolute path, excluding the domain name. Example: “/events/search/”.'
                    ), max_length=200, verbose_name='redirect from', db_index=True
                )),
                ('new_path', models.CharField(
                    help_text='This can be either an absolute path (as above) or a full URL starting with “http://”.',
                    max_length=200, verbose_name='redirect to', blank=True
                )),
            ],
            options={
                'ordering': ('old_path',),
                'unique_together': {('site', 'old_path')},
                'db_table': 'django_redirect',
                'verbose_name': 'redirect',
                'verbose_name_plural': 'redirects',
            },
            bases=(models.Model,),
        ),
    ]
