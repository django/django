class App(object):
    def __init__(self, label):
        if '.' in label:
            label = label.split('.')[-1]
        self.label = label
        self.errors = {}
        self.models = []
        self.models_module = None

    def __repr__(self):
        return '<App: %s>' % self.label
