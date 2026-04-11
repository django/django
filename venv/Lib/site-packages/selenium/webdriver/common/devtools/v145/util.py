
import typing


T_JSON_DICT = typing.Dict[str, typing.Any]
_event_parsers = dict()


def event_class(method):
    ''' A decorator that registers a class as an event class. '''
    def decorate(cls):
        _event_parsers[method] = cls
        cls.event_class = method
        return cls
    return decorate


def parse_json_event(json: T_JSON_DICT) -> typing.Any:
    ''' Parse a JSON dictionary into a CDP event. '''
    return _event_parsers[json['method']].from_json(json['params'])
