from typing import Any, Dict, Iterable, List

from flask_batteries_included.helpers import schema
from flask_batteries_included.helpers.error_handler import EntityNotFoundException
from neomodel import (
    FloatProperty,
    RelationshipDefinition,
    RelationshipTo,
    StringProperty,
    StructuredNode,
)

from dhos_services_api.helpers.responses import QueryResponse, response_to_dict
from dhos_services_api.neodb import NeomodelIdentifier, db

from . import management_plan

# =GDM times:
#
#  - breakfast - 307160001
#  - lunchtime - 444752003
#  - evening meal - 307163004
#  - before sleeping - 307155000


class Dose(NeomodelIdentifier, StructuredNode):

    medication_id = StringProperty()
    dose_amount = FloatProperty()
    routine_sct_code = StringProperty()

    changes: RelationshipDefinition = RelationshipTo(".dose.DoseChange", "HAS_CHANGE")

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "Dose":
        schema.post(json_in=kwargs, **cls.schema())
        obj = cls(**kwargs)
        return obj

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, type]]:
        return {
            "optional": {"routine_sct_code": str},
            "required": {"medication_id": str, "dose_amount": float},
            "updatable": {
                "routine_sct_code": str,
                "medication_id": str,
                "dose_amount": int,
            },
        }

    def get_medication_plan(self) -> "management_plan.ManagementPlan":
        query = """
            match (m:ManagementPlan)-[r:HAS_DOSE]-(d:Dose)
            where d.uuid = {d_uuid}
            return m
        """

        results, meta = db.cypher_query(query, {"d_uuid": self.uuid})
        try:
            plan = results[0][0]
            plan = management_plan.ManagementPlan.inflate(plan)
            return plan

        except IndexError:
            raise EntityNotFoundException(
                f"ManagementPlan not found with dose {self.uuid}"
            )

    def on_create(self) -> None:
        self.on_patch(
            {
                "medication_id": self.medication_id,
                "dose_amount": self.dose_amount,
                "routine_sct_code": self.routine_sct_code,
            }
        )
        plan = self.get_medication_plan()
        plan.add_history(self, "insert")

    def on_patch(self, _json: Dict = None, *args: Any, **kwargs: Any) -> None:

        if _json is None:
            return

        medication_id = _json.pop("medication_id", self.medication_id)
        if medication_id == self.medication_id:
            medication_change = None
        else:
            medication_change = medication_id

        dose_amount = _json.pop("dose_amount", self.dose_amount)
        if dose_amount == self.dose_amount:
            new_dose = None
        else:
            new_dose = dose_amount

        routine_sct_code = _json.pop("routine_sct_code", self.routine_sct_code)
        if routine_sct_code == self.routine_sct_code:
            routine_sct_code_change = None
        else:
            routine_sct_code_change = dose_amount - self.dose_amount

        self.medication_id = medication_change or self.medication_id
        self.dose_amount = new_dose or self.dose_amount
        self.routine_sct_code = routine_sct_code_change or self.routine_sct_code

        node = DoseChange.new()
        node.medication_id = medication_change
        node.routine_sct_code = routine_sct_code_change
        node.dose_amount = new_dose
        node.save()

        self.changes.connect(node)

        super(Dose, self).on_patch()
        self.save()

    def on_delete(self) -> bool:
        plan = self.get_medication_plan()
        plan.add_history(self, "delete")
        plan.doses.disconnect(self)
        plan.save()
        return False

    @property
    def created_by(self) -> str:
        return self.created_by_

    @created_by.setter
    def created_by(self, v: str) -> None:
        self.created_by_ = v

    @property
    def modified_by(self) -> str:
        return self.modified_by_

    @modified_by.setter
    def modified_by(self, v: str) -> None:
        self.modified_by_ = v

    def to_dict_no_relations(self, changes: Iterable[Dict] = None) -> Dict:
        """Convert to dict but don't follow any relations"""
        return {
            "medication_id": self.medication_id,
            "dose_amount": self.dose_amount,
            "routine_sct_code": self.routine_sct_code,
            "changes": [] if changes is None else changes,
            **self.pack_identifier(),
        }

    def to_dict(self) -> Dict:
        changes: List[Dict] = [change.to_dict() for change in self.changes]

        return {
            "medication_id": self.medication_id,
            "dose_amount": self.dose_amount,
            "routine_sct_code": self.routine_sct_code,
            "changes": [] if changes is None else changes,
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
            primary="dose",
            multiple={"changes": DoseChange},
            method=method,
        )


class DoseChange(NeomodelIdentifier, StructuredNode):

    medication_id = StringProperty()
    dose_amount = FloatProperty()
    routine_sct_code = StringProperty()

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "DoseChange":
        schema.post(json_in=kwargs, **cls.schema())
        return cls(*args, **kwargs)

    @classmethod
    def schema(cls) -> Dict:
        return {
            "optional": {
                "medication_id": str,
                "dose_amount": float,
                "routine_sct_code": str,
            },
            "required": {},
            "updatable": {},
        }

    @property
    def created_by(self) -> str:
        return self.created_by_

    @created_by.setter
    def created_by(self, v: str) -> None:
        self.created_by_ = v

    @property
    def modified_by(self) -> str:
        return self.modified_by_

    @modified_by.setter
    def modified_by(self, v: str) -> None:
        self.modified_by_ = v

    def to_dict(self) -> Dict[str, Any]:
        return {
            "medication_id": self.medication_id,
            "dose_amount": self.dose_amount,
            "routine_sct_code": self.routine_sct_code,
            **self.pack_identifier(),
        }

    to_dict_no_relations = to_dict

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        """Inflate from a response that may include include dicts for related nodes
        then convert to a dict. Any related nodes must be included in the dict or
        they are ignored.
        """
        return response_to_dict(cls, response, primary="dose_change", method=method)
