from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('migrations', '0002_data')]

    operations = [
        migrations.AlterModelBases('child', (models.Model,)),
        migrations.AlterField(
            model_name='child',
            name='parent_ptr',
            field=models.AutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name='ID',
            ),
        ),
        migrations.RenameField('child', 'parent_ptr', 'id'),
    ]
