class AppConfig(object):
    """
    Class representing a Django application and its configuration.
    """

    def __init__(self, label, models_module):
        self.label = label
        self.models_module = models_module

    def __repr__(self):
        return '<AppConfig: %s>' % self.label
