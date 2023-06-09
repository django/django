import json


class ParserException(Exception):
    """
    The selected parser cannot parse the contents of the request.
    """


class BaseParser:
    media_type = None

    def can_accept(self, media_type=None):
        if media_type == self.media_type:
            return True

    def parse(self, stream):
        pass


class JSONParser(BaseParser):
    media_type = "application/json"

    def parse(self, stream):
        try:
            return json.loads(stream)
        except ValueError as e:
            raise ParserException(f"JSON parse error - {e}")
