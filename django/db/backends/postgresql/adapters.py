from psycopg2.extensions import adapt as psycopg_adapt
from psycopg2.extras import DateRange, DateTimeRange, DateTimeTZRange, NumericRange


def adapt(param):
    for range_type, adapter in adapter_type_mapping.items():
        if isinstance(param, range_type):
            return adapter.getquoted(param)
    return psycopg_adapt(param).getquoted().decode()


class RangeAdapter:
    def __init__(self, name):
        self.name = name

    def getquoted(self, range):
        if range.isempty:
            return f"'empty'::{self.name}"

        if range.lower is not None:
            lower = psycopg_adapt(range.lower).getquoted().decode("ascii")
        else:
            lower = "NULL"

        if range.upper is not None:
            upper = psycopg_adapt(range.upper).getquoted().decode("ascii")
        else:
            upper = b"NULL"

        return f"{self.name}({lower}, {upper}, '{range._bounds}')"


class RangeNumericAdapter(RangeAdapter):
    def __init__(self):
        super().__init__("numrange")

    def getquoted(self, range):
        if range.isempty:
            return "'empty'"

        if not range.lower_inf:
            lower = psycopg_adapt(range.lower).getquoted().decode("ascii")
        else:
            lower = ""

        if not range.upper_inf:
            upper = psycopg_adapt(range.upper).getquoted().decode("ascii")
        else:
            upper = ""

        return f"'{range._bounds[0]}{lower},{upper}{range._bounds[1]}'"


adapter_type_mapping = {
    NumericRange: RangeNumericAdapter(),
    DateRange: RangeAdapter("daterange"),
    DateTimeRange: RangeAdapter("tsrange"),
    DateTimeTZRange: RangeAdapter("tstzrange"),
}
