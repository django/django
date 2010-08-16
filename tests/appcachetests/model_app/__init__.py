from django.core.apps import App

class MyApp(App):
    models_path = 'model_app.othermodels'

    def __repr__(self):
        return '<MyApp: %s>' % self.name

class MyOtherApp(MyApp):
    def __init__(self, name):
        super(MyOtherApp, self).__init__(name)
        self.db_prefix = 'nomodel_app'
