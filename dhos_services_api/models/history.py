from typing import Any, Dict, List

from flask_batteries_included.helpers import schema
from neomodel import IntegerProperty, StructuredNode

from dhos_services_api.helpers.responses import QueryResponse, response_to_dict
from dhos_services_api.neodb import NeomodelIdentifier


class History(NeomodelIdentifier, StructuredNode):

    parity = IntegerProperty(default=None)
    gravidity = IntegerProperty(default=None)

    @classmethod
    def new(cls, *args: List[Any], **kwargs: Dict[str, Any]) -> "History":
        schema.post(json_in=kwargs, **cls.schema())
        return cls(*args, **kwargs)

    @classmethod
    def schema(cls) -> Dict:
        return {
            "optional": {"parity": int, "gravidity": int},
            "required": {},
            "updatable": {"parity": int, "gravidity": int},
        }

    def to_dict(self) -> Dict:
        return {
            "parity": self.parity,
            "gravidity": self.gravidity,
            **self.pack_identifier(),
        }

    to_dict_no_relations = to_dict

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        return response_to_dict(cls, response, primary="history", method=method)
