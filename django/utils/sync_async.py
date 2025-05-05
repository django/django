import inspect


async def run_async_generator(gen):
    res = None
    try:
        while True:
            try:
                res = gen.send(res)
                if inspect.isawaitable(res):
                    res = await res
            except Exception as e:
                res = gen.throw(e)
    except StopIteration:
        pass

    return res


def run_sync_generator(gen):
    res = None
    try:
        while True:
            try:
                res = gen.send(res)
            except Exception as e:
                res = gen.throw(e)
    except StopIteration:
        pass

    return res
