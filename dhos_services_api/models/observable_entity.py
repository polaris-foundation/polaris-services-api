from typing import Any, Dict, Optional

from flask_batteries_included.helpers import schema
from flask_batteries_included.helpers.timestamp import (
    parse_date_to_iso8601,
    parse_iso8601_to_date,
)
from neomodel import DateProperty, JSONProperty, StringProperty, StructuredNode

# =SNOMED codes:
#  - HbA1c level (1003671000000109)
#  - Biological sex (429019009)
#  - Highest education level ()
#  - Glucose tolerance test (113076002)
from dhos_services_api.helpers.responses import QueryResponse, response_to_dict
from dhos_services_api.neodb import NeomodelIdentifier


class ObservableEntity(NeomodelIdentifier, StructuredNode):

    sct_code = StringProperty()
    date_observed_ = DateProperty(db_property="date_observed")
    value_as_string = StringProperty()
    metadata = JSONProperty()

    @property
    def date_observed(self) -> Optional[str]:

        return parse_date_to_iso8601(self.date_observed_)

    @date_observed.setter
    def date_observed(self, value: str) -> None:

        self.date_observed_ = parse_iso8601_to_date(value)

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "ObservableEntity":
        schema.post(json_in=kwargs, **cls.schema())
        return cls(*args, **kwargs)

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, type]]:
        return {
            "optional": {"metadata": dict, "value_as_string": str},
            "required": {"sct_code": str, "date_observed": str},
            "updatable": {
                "sct_code": str,
                "date_observed": str,
                "value_as_string": str,
                "metadata": dict,
            },
        }

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "sct_code": self.sct_code,
            "date_observed": self.date_observed,
            "value_as_string": self.value_as_string,
            "metadata": self.metadata,
            **self.pack_identifier(),
        }

    to_dict_no_relations = to_dict

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        return response_to_dict(
            cls, response, primary="observable_entity", method=method
        )
