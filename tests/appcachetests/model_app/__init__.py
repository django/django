from django.core.apps import App

class MyApp(App):
    models_path = 'model_app.othermodels'

    def __repr__(self):
        return '<MyApp: %s>' % self.name

