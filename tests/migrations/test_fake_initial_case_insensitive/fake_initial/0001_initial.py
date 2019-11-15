from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    operations = [
        migrations.CreateModel(
            'fakeinitialmodel',
            [
                ('id', models.AutoField(primary_key=True)),
                ('field', models.CharField(max_length=20)),
            ],
            options={
                'db_table': 'migrations_mIxEd_cAsE_mOdEl',
            },
        ),
        migrations.AddField(
            model_name='fakeinitialmodel',
            name='field_mixed_case',
            field=models.CharField(max_length=20, db_column='fIeLd_mIxEd_cAsE'),
        ),
        migrations.AddField(
            model_name='fakeinitialmodel',
            name='fake_initial_model',
            field=models.ManyToManyField(to='migrations.fakeinitialmodel', db_table='m2m_mIxEd_cAsE'),
        ),
    ]
