from typing import Any, Dict, Optional, Union

from flask_batteries_included.helpers import schema
from flask_batteries_included.helpers.timestamp import (
    parse_date_to_iso8601,
    parse_iso8601_to_date,
)
from neomodel import DateProperty, StructuredNode

from dhos_services_api.helpers.responses import QueryResponse, response_to_dict
from dhos_services_api.models.mixins.address import AddressMixin
from dhos_services_api.neodb import NeomodelIdentifier


class PersonalAddress(NeomodelIdentifier, AddressMixin, StructuredNode):

    lived_from_ = DateProperty(db_property="lived_from")
    lived_until_ = DateProperty(db_property="lived_until")

    @property
    def lived_from(self) -> Optional[str]:
        return parse_date_to_iso8601(self.lived_from_)

    @lived_from.setter
    def lived_from(self, value: str) -> None:
        self.lived_from_ = parse_iso8601_to_date(value)

    @property
    def lived_until(self) -> Optional[str]:
        return parse_date_to_iso8601(self.lived_until_)

    @lived_until.setter
    def lived_until(self, value: Optional[str]) -> None:
        self.lived_until_ = parse_iso8601_to_date(value)

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "PersonalAddress":
        schema.post(json_in=kwargs, **cls.schema())
        return cls(*args, **kwargs)

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, type]]:
        return {
            "optional": {
                "address_line_1": str,
                "address_line_2": str,
                "address_line_3": str,
                "address_line_4": str,
                "locality": str,
                "region": str,
                "postcode": str,
                "country": str,
                "lived_from": str,
                "lived_until": str,
            },
            "required": {},
            "updatable": {
                "address_line_1": str,
                "address_line_2": str,
                "address_line_3": str,
                "address_line_4": str,
                "locality": str,
                "region": str,
                "postcode": str,
                "country": str,
                "lived_from": str,
                "lived_until": str,
            },
        }

    def to_dict(self) -> Union[Dict[str, Optional[str]], Dict[str, str]]:
        return {
            "lived_from": self.lived_from,
            "lived_until": self.lived_until,
            **self.pack_address(),
            **self.pack_identifier(),
        }

    to_dict_no_relations = to_dict

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        return response_to_dict(
            cls, response, primary="personal_address", method=method
        )
