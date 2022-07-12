from typing import Any, Dict

from flask_batteries_included.helpers import schema
from neomodel import StringProperty, StructuredNode

from dhos_services_api.helpers.responses import QueryResponse, response_to_dict
from dhos_services_api.neodb import NeomodelIdentifier


class Note(NeomodelIdentifier, StructuredNode):
    content = StringProperty()
    clinician_uuid = StringProperty()

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "Note":
        schema.post(json_in=kwargs, **cls.schema())
        obj = cls(*args, **kwargs)
        obj.save()
        return obj

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, type]]:
        return {
            "optional": {},
            "required": {"content": str, "clinician_uuid": str},
            "updatable": {"content": str, "clinician_uuid": str},
        }

    def to_dict_no_relations(self) -> Dict:
        return {
            "content": self.content,
            "clinician_uuid": self.clinician_uuid,
            **self.pack_identifier(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "clinician_uuid": self.clinician_uuid,
            **self.pack_identifier(),
        }

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        """Inflate from a response that may include include dicts for related nodes
        then convert to a dict. Any related nodes must be included in the dict or
        they are ignored.
        """
        return response_to_dict(
            cls,
            response,
            primary="note",
            method=method,
        )
