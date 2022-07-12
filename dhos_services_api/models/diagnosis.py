from typing import Any, Dict, List, Optional

from flask_batteries_included.helpers import schema
from flask_batteries_included.helpers.timestamp import (
    parse_date_to_iso8601,
    parse_iso8601_to_date,
)
from neomodel import (
    ArrayProperty,
    DateProperty,
    IntegerProperty,
    RelationshipTo,
    StringProperty,
    StructuredNode,
    ZeroOrOne,
)

from dhos_services_api.helpers.responses import QueryResponse, response_to_dict
from dhos_services_api.neodb import NeomodelIdentifier

from .management_plan import ManagementPlan
from .observable_entity import ObservableEntity
from .readings_plan import ReadingsPlan


class Diagnosis(NeomodelIdentifier, StructuredNode):

    sct_code = StringProperty()
    diagnosis_other = StringProperty()

    diagnosed_ = DateProperty()
    resolved_ = DateProperty()
    presented_ = DateProperty()
    episode = IntegerProperty()

    diagnosis_tool = ArrayProperty(StringProperty(), default=[])
    diagnosis_tool_other = StringProperty()

    risk_factors = ArrayProperty(StringProperty(), default=[])

    management_plan = RelationshipTo(
        ".management_plan.ManagementPlan", "HAS_MANAGEMENT_PLAN", ZeroOrOne
    )
    readings_plan = RelationshipTo(
        ".readings_plan.ReadingsPlan", "HAS_READINGS_PLAN", ZeroOrOne
    )
    observable_entities = RelationshipTo(
        ".observable_entity.ObservableEntity", "RELATED_OBSERVATION"
    )

    @property
    def presented(self) -> Optional[str]:
        return parse_date_to_iso8601(self.presented_)

    @presented.setter
    def presented(self, value: Optional[str]) -> None:
        self.presented_ = parse_iso8601_to_date(value)

    @property
    def diagnosed(self) -> Optional[str]:
        return parse_date_to_iso8601(self.diagnosed_)

    @diagnosed.setter
    def diagnosed(self, value: str) -> None:
        self.diagnosed_ = parse_iso8601_to_date(value)

    @property
    def resolved(self) -> Optional[Any]:
        return parse_date_to_iso8601(self.resolved_)

    @resolved.setter
    def resolved(self, value: Optional[Any]) -> None:
        self.resolved_ = parse_iso8601_to_date(value)

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "Diagnosis":

        schema.post(json_in=kwargs, **cls.schema())

        management_plan_dict = kwargs.pop("management_plan", dict())
        management_plan = ManagementPlan.new(**management_plan_dict)

        readings_plan_dict = kwargs.pop("readings_plan", None)
        readings_plan = (
            ReadingsPlan.new(**readings_plan_dict) if readings_plan_dict else None
        )

        obs = kwargs.pop("observable_entities", []) or []
        observable_entities = [ObservableEntity.new(**ent) for ent in obs]

        obj = cls(*args, **kwargs)
        obj.save()

        management_plan.save()
        obj.management_plan.connect(management_plan)

        if readings_plan:
            readings_plan.save()
            obj.readings_plan.connect(readings_plan)

        for ent in observable_entities:
            ent.save()
            obj.observable_entities.connect(ent)

        return obj

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "optional": {
                "diagnosis_other": str,
                "resolved": str,
                "presented": str,
                "episode": int,
                "diagnosis_tool": [str],
                "diagnosis_tool_other": str,
                "management_plan": dict,
                "readings_plan": dict,
                "risk_factors": [str],
                "observable_entities": [dict],
                "diagnosed": str,
            },
            "required": {"sct_code": str},
            "updatable": {
                "diagnosed": str,
                "sct_code": str,
                "diagnosis_other": str,
                "resolved": str,
                "presented": str,
                "episode": int,
                "diagnosis_tool": [str],
                "diagnosis_tool_other": str,
                "management_plan": dict,
                "readings_plan": dict,
                "risk_factors": [str],
                "observable_entities": [dict],
            },
        }

    def to_dict_no_relations(
        self,
        management_plan: Dict = None,
        readings_plan: Dict = None,
        observable_entities: List[Dict] = None,
    ) -> Dict:
        """to_dict_no_relations: convert to a dictionary but will not touch related nodes."""

        return {
            "sct_code": self.sct_code,
            "diagnosis_other": self.diagnosis_other,
            "diagnosed": self.diagnosed,
            "resolved": self.resolved,
            "episode": self.episode,
            "presented": self.presented,
            "diagnosis_tool": self.diagnosis_tool,
            "diagnosis_tool_other": self.diagnosis_tool_other,
            "risk_factors": self.risk_factors,
            "observable_entities": []
            if observable_entities is None
            else observable_entities,
            "management_plan": management_plan,
            "readings_plan": readings_plan,
            **self.pack_identifier(),
        }

    def to_dict(self) -> Dict:
        """to_dict: convert to a dictionary."""
        mp = self.management_plan.single()
        management_plan = mp.to_dict() if mp is not None else None

        rp = self.readings_plan.single()
        readings_plan = rp.to_dict() if rp is not None else None

        observable_entities = [
            observable_entity.to_dict()
            for observable_entity in sorted(
                self.observable_entities, key=lambda x: x.date_observed_
            )
        ]
        return self.to_dict_no_relations(
            management_plan=management_plan,
            readings_plan=readings_plan,
            observable_entities=observable_entities,
        )

    def to_compact_dict(
        self,
        management_plan: Dict = None,
        readings_plan: Dict = None,
        observable_entities: List[Dict] = None,
    ) -> Dict:
        return {
            "management_plan": management_plan,
            "sct_code": self.sct_code,
            "diagnosed": self.diagnosed,
            **self.compack_identifier(),
        }

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        """Inflate from a response that may include include dicts for related nodes
        then convert to a dict. Any related nodes must be included in the dict or
        they are ignored.
        """
        result = response_to_dict(
            cls,
            response,
            primary="diagnosis",
            single={"management_plan": ManagementPlan, "readings_plan": ReadingsPlan},
            multiple={"observable_entities": ObservableEntity},
            method=method,
        )
        return result
