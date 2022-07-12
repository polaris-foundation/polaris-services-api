from typing import Any, Dict

from flask_batteries_included.helpers import schema
from neomodel import StringProperty, StructuredNode

from dhos_services_api.helpers.responses import QueryResponse, response_to_dict
from dhos_services_api.neodb import NeomodelIdentifier


class NonMedicationAction(NeomodelIdentifier, StructuredNode):
    # Examples of GDM non medication actions for `action_sct_code`:
    # - dietary education for GDM (439051004)
    # - recommendation to exercise (281090004)
    action_sct_code = StringProperty()

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "NonMedicationAction":
        schema.post(json_in=kwargs, **cls.schema())
        return cls(*args, **kwargs)

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, type]]:
        return {
            "optional": {},
            "required": {"action_sct_code": str},
            "updatable": {"action_sct_code": str},
        }

    def to_dict(self) -> Dict[str, str]:
        return {"action_sct_code": self.action_sct_code, **self.pack_identifier()}

    to_dict_no_relations = to_dict

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        return response_to_dict(
            cls, response, primary="non_medication_action", method=method
        )
