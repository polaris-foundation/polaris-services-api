from __future__ import annotations

from typing import Any, Sequence

from flask_batteries_included.sqldb import db

from dhos_services_api import sqlmodels
from dhos_services_api.sqlmodels.mixins import (
    ModelIdentifier,
    ValidationSchema,
    construct_children,
)


class Pregnancy(ModelIdentifier, db.Model):
    record_id = db.Column(
        db.String, db.ForeignKey("record.uuid", ondelete="CASCADE"), nullable=False
    )
    estimated_delivery_date = db.Column(db.Date)
    planned_delivery_place = db.Column(db.String)
    length_of_postnatal_stay_in_days = db.Column(db.Integer)
    colostrum_harvesting = db.Column(db.Boolean)
    expected_number_of_babies = db.Column(db.Integer)
    pregnancy_complications: list[str] = db.Column(db.JSON, default=[])

    induced = db.Column(db.Boolean)

    deliveries = db.relationship("Delivery", cascade="all, delete-orphan")

    height_at_booking_in_mm = db.Column(db.Integer)
    weight_at_booking_in_g = db.Column(db.Integer)

    weight_at_diagnosis_in_g = db.Column(db.Integer)
    weight_at_36_weeks_in_g = db.Column(db.Integer)

    delivery_place = db.Column(db.String)
    delivery_place_other = db.Column(db.String)

    first_medication_taken = db.Column(db.String)
    first_medication_taken_recorded = db.Column(db.Date)

    @classmethod
    def new(
        cls,
        *,
        record_id: str = None,
        deliveries: Sequence[dict | sqlmodels.Delivery] | None = None,
        **kwargs: Any,
    ) -> "Pregnancy":
        with db.session.no_autoflush:
            self = cls(
                record_id=record_id,
                deliveries=construct_children(deliveries, sqlmodels.Delivery),
                **kwargs,
            )
            db.session.add(self)
        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
        return {
            "optional": {
                "length_of_postnatal_stay_in_days": int,
                "colostrum_harvesting": bool,
                "pregnancy_complications": [str],
                "induced": bool,
                "deliveries": [dict],
                "delivery_place": str,
                "delivery_place_other": str,
                "planned_delivery_place": str,
                "height_at_booking_in_mm": int,
                "weight_at_diagnosis_in_g": int,
                "weight_at_booking_in_g": int,
                "weight_at_36_weeks_in_g": int,
                "expected_number_of_babies": int,
                "first_medication_taken_recorded": str,
                "first_medication_taken": str,
            },
            "required": {"estimated_delivery_date": str},
            "updatable": {
                "length_of_postnatal_stay_in_days": int,
                "colostrum_harvesting": bool,
                "pregnancy_complications": [str],
                "induced": bool,
                "deliveries": [dict],
                "estimated_delivery_date": str,
                "planned_delivery_place": str,
                "height_at_booking_in_mm": int,
                "weight_at_diagnosis_in_g": int,
                "weight_at_booking_in_g": int,
                "weight_at_36_weeks_in_g": int,
                "delivery_place": str,
                "delivery_place_other": str,
                "expected_number_of_babies": int,
                "first_medication_taken_recorded": str,
                "first_medication_taken": str,
            },
        }

    def recursive_patch(
        self, *, deliveries: list | None = None, **kwargs: object
    ) -> None:
        super().recursive_patch(**kwargs)
        if deliveries:
            sqlmodels.Delivery.patch_related_objects(
                related_column=sqlmodels.Delivery.pregnancy_id,
                parent_id=self.uuid,
                patch_data=deliveries,
            )
