from django.test.runner import DiscoverRunner


class CustomOptionsTestRunner(DiscoverRunner):

    def __init__(self, verbosity=1, interactive=True, failfast=True,
                 option_a=None, option_b=None, option_c=None, **kwargs):
        super(CustomOptionsTestRunner, self).__init__(
            verbosity=verbosity, interactive=interactive, failfast=failfast,
        )
        self.option_a = option_a
        self.option_b = option_b
        self.option_c = option_c

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('--option_a', '-a', action='store', dest='option_a', default='1'),
        parser.add_argument('--option_b', '-b', action='store', dest='option_b', default='2'),
        parser.add_argument('--option_c', '-c', action='store', dest='option_c', default='3'),

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        print("%s:%s:%s" % (self.option_a, self.option_b, self.option_c))
