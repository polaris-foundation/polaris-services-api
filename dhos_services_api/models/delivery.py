from typing import Any, Dict, Optional

from flask_batteries_included.helpers import schema, timestamp
from neomodel import (
    ArrayProperty,
    BooleanProperty,
    DateProperty,
    IntegerProperty,
    RelationshipTo,
    StringProperty,
    StructuredNode,
    ZeroOrOne,
)

import dhos_services_api.models.patient
from dhos_services_api.helpers.responses import QueryResponse, response_to_dict
from dhos_services_api.neodb import NeomodelIdentifier

_MARKER: Any = object()


class Delivery(NeomodelIdentifier, StructuredNode):

    birth_outcome = StringProperty()
    outcome_for_baby = StringProperty()
    neonatal_complications = ArrayProperty(StringProperty(), default=[])
    neonatal_complications_other = StringProperty()
    admitted_to_special_baby_care_unit = BooleanProperty()
    birth_weight_in_grams = IntegerProperty()
    length_of_postnatal_stay_for_baby = IntegerProperty()
    apgar_1_minute = IntegerProperty()
    apgar_5_minute = IntegerProperty()
    feeding_method = StringProperty()
    date_of_termination_ = DateProperty()

    patient = RelationshipTo(".patient.Baby", "IS_PATIENT", cardinality=ZeroOrOne)

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "Delivery":
        schema.post(json_in=kwargs, **cls.schema())

        patient = (
            dhos_services_api.models.patient.Baby.new(**kwargs.pop("patient"))
            if "patient" in kwargs
            else None
        )

        obj = cls(*args, **kwargs)
        obj.save()

        if patient is not None:
            patient.save()
            obj.patient.connect(patient)

        return obj

    @property
    def date_of_termination(self) -> Optional[str]:
        if self.date_of_termination_ is None:
            return None
        return timestamp.parse_date_to_iso8601(self.date_of_termination_)

    @date_of_termination.setter
    def date_of_termination(self, value: Optional[str]) -> None:
        if value is None:
            return
        self.date_of_termination_ = timestamp.parse_iso8601_to_date(value)

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "optional": {
                "birth_outcome": str,
                "outcome_for_baby": str,
                "neonatal_complications": [str],
                "neonatal_complications_other": str,
                "admitted_to_special_baby_care_unit": bool,
                "birth_weight_in_grams": int,
                "length_of_postnatal_stay_for_baby": int,
                "apgar_1_minute": int,
                "apgar_5_minute": int,
                "feeding_method": str,
                "date_of_termination": str,
                "patient": dict,
            },
            "required": {},
            "updatable": {
                "birth_outcome": str,
                "outcome_for_baby": str,
                "neonatal_complications": [str],
                "neonatal_complications_other": str,
                "admitted_to_special_baby_care_unit": bool,
                "birth_weight_in_grams": int,
                "length_of_postnatal_stay_for_baby": int,
                "apgar_1_minute": int,
                "apgar_5_minute": int,
                "feeding_method": str,
                "date_of_termination": str,
                "patient": dict,
            },
        }

    def to_dict_no_relations(self, patient: Dict = None) -> Dict:
        return {
            "birth_outcome": self.birth_outcome,
            "outcome_for_baby": self.outcome_for_baby,
            "neonatal_complications": self.neonatal_complications,
            "neonatal_complications_other": self.neonatal_complications_other,
            "admitted_to_special_baby_care_unit": self.admitted_to_special_baby_care_unit,
            "birth_weight_in_grams": self.birth_weight_in_grams,
            "length_of_postnatal_stay_for_baby": self.length_of_postnatal_stay_for_baby,
            "apgar_1_minute": self.apgar_1_minute,
            "apgar_5_minute": self.apgar_5_minute,
            "feeding_method": self.feeding_method,
            "date_of_termination": self.date_of_termination,
            "patient": patient,
            **self.pack_identifier(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "birth_outcome": self.birth_outcome,
            "outcome_for_baby": self.outcome_for_baby,
            "neonatal_complications": self.neonatal_complications,
            "neonatal_complications_other": self.neonatal_complications_other,
            "admitted_to_special_baby_care_unit": self.admitted_to_special_baby_care_unit,
            "birth_weight_in_grams": self.birth_weight_in_grams,
            "length_of_postnatal_stay_for_baby": self.length_of_postnatal_stay_for_baby,
            "apgar_1_minute": self.apgar_1_minute,
            "apgar_5_minute": self.apgar_5_minute,
            "feeding_method": self.feeding_method,
            "date_of_termination": self.date_of_termination,
            "patient": self.patient.single().to_dict()
            if self.patient.single() is not None
            else None,
            **self.pack_identifier(),
        }

    def to_compact_dict(self, patient: Dict = _MARKER) -> Dict:
        if patient is _MARKER:
            patient = (
                self.patient.single().to_compact_dict()
                if self.patient.single() is not None
                else None
            )

        return {"patient": patient, **self.compack_identifier()}

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        return response_to_dict(
            cls,
            response,
            primary="delivery",
            single={"patient": dhos_services_api.models.patient.Baby},
            method=method,
        )
