from django.core.apps import App

class MyApp(App):

    def __repr__(self):
        return '<MyApp: %s>' % self.name
