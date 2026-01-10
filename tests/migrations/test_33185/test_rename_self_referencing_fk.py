from django.db import connection, migrations, models
from django.db.migrations.state import ProjectState
from django.test import TransactionTestCase

class RenameSelfReferencingFKTests(TransactionTestCase):
    available_apps = []

    
    def test_rename_model_with_self_referencing_fk(self):
        if connection.vendor != 'mysql':
            self.skipTest("This test is specific to MySQL's handling of RENAME TABLE.")

        
        class Employee(models.Model):
            manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True)
            class Meta:
                app_label = 'test_33185'

        
        class RenamedEmployee(models.Model):
            manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True)
            class Meta:
                app_label = 'test_33185'

        
        initial_state = ProjectState()
        initial_state.add_model(models.ModelState.from_model(Employee))

        
        new_state = ProjectState()
        new_state.add_model(models.ModelState.from_model(RenamedEmployee))

        
        operation = migrations.RenameModel(
            old_name='Employee',
            new_name='RenamedEmployee',
        )

        
        with connection.schema_editor() as editor:
            editor.create_model(Employee)

        
        try:
            with connection.schema_editor(collect_sql=True) as editor:
                operation.database_forwards('test_33185', editor, initial_state, new_state)
        finally:
            
            with connection.schema_editor() as editor:
                editor.delete_model(Employee)