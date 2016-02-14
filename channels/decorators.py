import functools


def linearize(func):
    """
    Makes sure the contained consumer does not run at the same time other
    consumers are running on messages with the same reply_channel.

    Required if you don't want weird things like a second consumer starting
    up before the first has exited and saved its session. Doesn't guarantee
    ordering, just linearity.
    """
    raise NotImplementedError("Not yet reimplemented")

    @functools.wraps(func)
    def inner(message, *args, **kwargs):
        # Make sure there's a reply channel
        if not message.reply_channel:
            raise ValueError(
                "No reply_channel in message; @linearize can only be used on messages containing it."
            )
        # TODO: Get lock here
        pass
        # OK, keep going
        try:
            return func(message, *args, **kwargs)
        finally:
            # TODO: Release lock here
            pass
    return inner
