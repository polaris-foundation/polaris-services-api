from __future__ import annotations

from typing import Any, Sequence

from flask_batteries_included.helpers.security.jwt import current_jwt_user
from flask_batteries_included.sqldb import db

from dhos_services_api import sqlmodels
from dhos_services_api.sqlmodels.mixins import (
    ModelIdentifier,
    ValidationSchema,
    construct_children,
)


class ManagementPlan(ModelIdentifier, db.Model):
    diagnosis_id = db.Column(
        db.String, db.ForeignKey("diagnosis.uuid", ondelete="CASCADE"), nullable=False
    )

    doses = db.relationship(
        "Dose", order_by="desc(Dose.created)", backref="management_plan"
    )
    actions = db.relationship(
        "NonMedicationAction",
        order_by="desc(NonMedicationAction.created)",
        cascade="all, delete-orphan",
    )
    dose_history = db.relationship(
        "DoseHistory",
        order_by="desc(DoseHistory.created)",
        cascade="all, delete-orphan",
    )
    plan_history: list[str] = db.Column(db.JSON, default=[])
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    sct_code = db.Column(db.String, nullable=False)

    @classmethod
    def new(
        cls,
        *,
        diagnosis_id: str = None,
        doses: Sequence[dict | sqlmodels.Dose] | None = None,
        actions: Sequence[dict | sqlmodels.NonMedicationAction] | None = None,
        dose_history: Sequence[dict | sqlmodels.DoseHistory] | None = None,
        **kwargs: Any,
    ) -> "ManagementPlan":
        with db.session.no_autoflush:
            self = cls(
                diagnosis_id=diagnosis_id,
                doses=construct_children(doses, sqlmodels.Dose),
                actions=construct_children(actions, sqlmodels.NonMedicationAction),
                dose_history=construct_children(dose_history, sqlmodels.DoseHistory),
                **kwargs,
            )
            db.session.add(self)

            for dose in self.doses:
                self.add_history(dose, "insert")

        return self

    def add_history(self, dose: sqlmodels.Dose, action: str) -> None:
        dose_history = DoseHistory.new(
            management_plan_id=self.uuid,
            clinician_uuid=current_jwt_user(),
            dose_id=dose.uuid,
            action=action,
        )
        db.session.add(self)

    @classmethod
    def schema(cls) -> ValidationSchema:
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

    def recursive_patch(
        self,
        *,
        doses: list | None = None,
        actions: list | None = None,
        **kwargs: object,
    ) -> None:
        super().recursive_patch(**kwargs)
        if doses:
            sqlmodels.Dose.patch_related_objects(
                related_column=sqlmodels.Dose.management_plan_id,
                parent_id=self.uuid,
                patch_data=doses,
            )

        if actions:
            sqlmodels.NonMedicationAction.patch_related_objects(
                related_column=sqlmodels.NonMedicationAction.management_plan_id,
                parent_id=self.uuid,
                patch_data=actions,
            )


class DoseHistory(ModelIdentifier, db.Model):
    management_plan_id = db.Column(
        db.String,
        db.ForeignKey("management_plan.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    dose_id = db.Column(
        db.String, db.ForeignKey("dose.uuid", ondelete="CASCADE"), nullable=False
    )
    clinician_uuid = db.Column(db.String)
    dose = db.relationship("Dose", uselist=False)
    action = db.Column(db.String)

    @classmethod
    def new(
        cls, *, management_plan_id: str = None, dose_id: str = None, **kwargs: Any
    ) -> "DoseHistory":
        self = cls(management_plan_id=management_plan_id, dose_id=dose_id, **kwargs)
        db.session.add(self)
        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
        return {
            "optional": {
                "clinician_uuid": str,
                "action": str,
            },
            "required": {"dose_id": str},
            "updatable": {},
        }
