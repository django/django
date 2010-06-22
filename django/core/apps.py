class App(object):
    def __init__(self, name, models):
        # fully qualified name (e.g. 'django.contrib.auth')
        self.name = name
        self.label = name.split('.')[-1]
        self.models = models

    def __repr__(self):
        return '<App: %s>' % self.name
