from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    operations = [
        migrations.CreateModel(
            name='fakeinitialmodel',
            fields=[
                ('id', models.AutoField(primary_key=True)),
                ('field', models.CharField(max_length=20)),
                ('field_mixed_case', models.CharField(max_length=20, db_column='FiEld_MiXeD_CaSe')),
                (
                    'fake_initial_mode',
                    models.ManyToManyField('migrations.FakeInitialModel', db_table='m2m_MiXeD_CaSe'),
                ),
            ],
            options={
                'db_table': 'migrations_MiXeD_CaSe_MoDel',
            },
        ),
    ]
