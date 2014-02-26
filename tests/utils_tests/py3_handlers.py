
def handler_with_kwargs_only(*, sender, instance=None, **kwargs):
    pass


def handler_with_annotations(sender, instance: 'annotation', **kwargs) -> None:
    pass


def handler_simple(sender, instance=None, **kwargs):
    pass