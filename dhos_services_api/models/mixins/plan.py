from typing import Optional

from flask_batteries_included.helpers.timestamp import (
    parse_date_to_iso8601,
    parse_iso8601_to_date,
)
from neomodel import DateProperty, StringProperty


class PlanMixin:

    start_date_ = DateProperty(db_property="start_date")
    end_date_ = DateProperty(db_property="end_date")

    sct_code = (
        StringProperty()
    )  # monitoring procedure (182777000), glucose monitoring at home (359772000)

    @property
    def start_date(self) -> Optional[str]:
        if self.start_date_ is None:
            return None
        return parse_date_to_iso8601(self.start_date_)

    @start_date.setter
    def start_date(self, value: str) -> None:
        if value is None:
            return
        self.start_date_ = parse_iso8601_to_date(value)

    @property
    def end_date(self) -> Optional[str]:
        if self.end_date_ is None:
            return None
        return parse_date_to_iso8601(self.end_date_)

    @end_date.setter
    def end_date(self, value: str) -> None:
        if value is None:
            return
        self.end_date_ = parse_iso8601_to_date(value)
