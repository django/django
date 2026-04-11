from typing import Optional

from ._util import to_string
from .document import Document


class Result:
    """
    Represents the result of a search query, and has an array of Document
    objects
    """

    def __init__(
        self,
        res,
        hascontent,
        duration=0,
        has_payload=False,
        with_scores=False,
        field_encodings: Optional[dict] = None,
    ):
        """
        - duration: the execution time of the query
        - has_payload: whether the query has payloads
        - with_scores: whether the query has scores
        - field_encodings: a dictionary of field encodings if any is provided
        """

        self.total = res[0]
        self.duration = duration
        self.docs = []

        step = 1
        if hascontent:
            step = step + 1
        if has_payload:
            step = step + 1
        if with_scores:
            step = step + 1

        offset = 2 if with_scores else 1

        for i in range(1, len(res), step):
            id = to_string(res[i])
            payload = to_string(res[i + offset]) if has_payload else None
            # fields_offset = 2 if has_payload else 1
            fields_offset = offset + 1 if has_payload else offset
            score = float(res[i + 1]) if with_scores else None

            fields = {}
            if hascontent and res[i + fields_offset] is not None:
                keys = map(to_string, res[i + fields_offset][::2])
                values = res[i + fields_offset][1::2]

                for key, value in zip(keys, values):
                    if field_encodings is None or key not in field_encodings:
                        fields[key] = to_string(value)
                        continue

                    encoding = field_encodings[key]

                    # If the encoding is None, we don't need to decode the value
                    if encoding is None:
                        fields[key] = value
                    else:
                        fields[key] = to_string(value, encoding=encoding)

            try:
                del fields["id"]
            except KeyError:
                pass

            try:
                fields["json"] = fields["$"]
                del fields["$"]
            except KeyError:
                pass

            doc = (
                Document(id, score=score, payload=payload, **fields)
                if with_scores
                else Document(id, payload=payload, **fields)
            )
            self.docs.append(doc)

    def __repr__(self) -> str:
        return f"Result{{{self.total} total, docs: {self.docs}}}"
