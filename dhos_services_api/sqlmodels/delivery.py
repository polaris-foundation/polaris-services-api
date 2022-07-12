from __future__ import annotations

from typing import Any

from flask_batteries_included.sqldb import db

from dhos_services_api import sqlmodels
from dhos_services_api.sqlmodels.mixins import (
    ModelIdentifier,
    ValidationSchema,
    construct_single_child,
)


class Delivery(ModelIdentifier, db.Model):
    pregnancy_id = db.Column(
        db.String, db.ForeignKey("pregnancy.uuid", ondelete="CASCADE"), nullable=False
    )

    birth_outcome = db.Column(db.String)
    outcome_for_baby = db.Column(db.String)
    neonatal_complications = db.Column(db.JSON, default=[])
    neonatal_complications_other = db.Column(db.String)
    admitted_to_special_baby_care_unit = db.Column(db.Boolean)
    birth_weight_in_grams = db.Column(db.Integer)
    length_of_postnatal_stay_for_baby = db.Column(db.Integer)
    apgar_1_minute = db.Column(db.Integer)
    apgar_5_minute = db.Column(db.Integer)
    feeding_method = db.Column(db.String)
    date_of_termination = db.Column(db.Date, nullable=True)

    patient_id = db.Column(db.String, db.ForeignKey("patient.uuid"), index=True)
    patient = db.relationship("Patient", backref="delivery", uselist=False)

    @classmethod
    def new(
        cls,
        *,
        pregnancy_id: str | None = None,
        patient: dict | sqlmodels.Patient | None = None,
        **kwargs: Any,
    ) -> "Delivery":
        if "patient_id" not in kwargs:
            kwargs["patient"] = construct_single_child(
                {} if patient is None else patient, sqlmodels.Patient
            )

        self = cls(
            pregnancy_id=pregnancy_id,
            **kwargs,
        )

        db.session.add(self)
        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
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

    def recursive_patch(
        self,
        *,
        patient: dict | None = None,
        **kwargs: object,
    ) -> None:
        if patient:
            if self.patient is None:
                self.patient = sqlmodels.Patient.new(**patient)
            else:
                self.patient.recursive_patch(**patient)
        super().recursive_patch(**kwargs)
