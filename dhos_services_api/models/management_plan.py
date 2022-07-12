from typing import Any, Dict, Iterable, List, Optional

from flask_batteries_included.helpers import schema
from flask_batteries_included.helpers.security.jwt import current_jwt_user
from neomodel import ArrayProperty, One, RelationshipTo, StringProperty, StructuredNode

from dhos_services_api.helpers.responses import QueryResponse, response_to_dict
from dhos_services_api.models import dose
from dhos_services_api.models.dose import Dose
from dhos_services_api.models.mixins.plan import PlanMixin
from dhos_services_api.models.non_medication_action import NonMedicationAction
from dhos_services_api.neodb import NeomodelIdentifier


class ManagementPlan(NeomodelIdentifier, PlanMixin, StructuredNode):

    doses = RelationshipTo(".dose.Dose", "HAS_DOSE")
    actions = RelationshipTo(".non_medication_action.NonMedicationAction", "HAS_ACTION")

    dose_history = RelationshipTo(".management_plan.DoseHistory", "HAD_DOSE")
    plan_history = ArrayProperty(StringProperty(), default=[])

    def add_history(self, _dose: Dose, action: str) -> None:
        dose_history = DoseHistory.new(
            clinician_uuid=current_jwt_user(), dose=_dose, action=action
        )
        dose_history.save()

        self.dose_history.connect(dose_history)
        self.save()

    @classmethod
    def new(cls, *args: List[Any], **kwargs: Dict[str, Any]) -> "ManagementPlan":
        schema.post(json_in=kwargs, **cls.schema())

        doses: Dict = kwargs.pop("doses")
        dose_nodes = [dose.Dose.new(**d) for d in doses]

        actions: Dict = kwargs.pop("actions")
        action_nodes = [NonMedicationAction.new(**action) for action in actions]

        obj = cls(*args, **kwargs)
        obj.save()

        for d in dose_nodes:
            d.save()
            obj.doses.connect(d)
            obj.add_history(d, "insert")

        for action in action_nodes:
            action.save()
            obj.actions.connect(action)

        return obj

    def on_patch(self, _json: Dict = None, *args: Any, **kwargs: Any) -> None:

        if _json is None:
            return

        super(ManagementPlan, self).on_patch(_json, **kwargs)

        if "sct_code" in _json and _json["sct_code"] != self.sct_code:
            self.plan_history.append(self.sct_code)
            self.sct_code = _json.pop("sct_code", None)
            self.save()

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "optional": {
                "doses": [dict],
                "actions": [dict],
                "start_date": str,
                "end_date": str,
            },
            "required": {"sct_code": str},
            "updatable": {
                "doses": [dict],
                "actions": [dict],
                "start_date": str,
                "end_date": str,
                "sct_code": str,
            },
        }

    def to_dict_no_relations(
        self,
        actions: Iterable[Dict] = None,
        doses: Iterable[Dict] = None,
        dose_history: Iterable[Dict] = None,
    ) -> Dict:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "sct_code": self.sct_code,
            "actions": [] if actions is None else actions,
            "doses": [] if doses is None else doses,
            "plan_history": self.plan_history,
            "dose_history": []
            if dose_history is None
            else sorted(dose_history, key=lambda x: x["modified"], reverse=True),
            **self.pack_identifier(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.to_dict_no_relations(
            actions=[action.to_dict() for action in self.actions],
            doses=[dose.to_dict() for dose in self.doses],
            dose_history=[h.to_dict() for h in self.dose_history],
        )

    def to_compact_dict(self) -> Dict[str, Optional[str]]:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "sct_code": self.sct_code,
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
            primary="management_plan",
            multiple={
                "actions": NonMedicationAction,
                "doses": dose.Dose,
                "dose_history": DoseHistory,
            },
            method=method,
        )


class DoseHistory(NeomodelIdentifier, StructuredNode):
    clinician_uuid = StringProperty()
    dose = RelationshipTo(".dose.Dose", "RELATES_TO_DOSE", One)
    action = StringProperty()

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "DoseHistory":
        schema.post(json_in=kwargs, **cls.schema())

        _dose = kwargs.pop("dose", None)

        obj = cls(*args, **kwargs)
        obj.save()

        if _dose is not None:
            obj.dose.connect(_dose)

        return obj

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "optional": {
                "clinician_uuid": str,
                "dose": StructuredNode,
                "action": str,
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

    def to_dict_no_relations(self, dose: Dict = None) -> Dict:
        return {
            "clinician_uuid": self.clinician_uuid,
            "dose": dose,
            "action": self.action,
            **self.pack_identifier(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.to_dict_no_relations(
            dose=self.dose.single().to_dict(),
        )

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        """
        Inflate from a response that may include include dicts for related nodes
        then convert to a dict. Any related nodes must be included in the dict or
        they are ignored.
        """
        return response_to_dict(
            cls,
            response,
            primary="dose_history",
            single={"dose": dose.Dose},
            method=method,
        )
