from __future__ import annotations

from typing import Any, Sequence

from flask_batteries_included.sqldb import db

from dhos_services_api import sqlmodels
from dhos_services_api.sqlmodels.mixins import (
    ModelIdentifier,
    ValidationSchema,
    construct_children,
)

# Sentinel for default value as we have to be able to distinguish passing an explicit None
# from not passing the argument (in recursive_patch explicit None will clear the metadata field
# but not passing any value leaves it unchanged).
_SENTINEL: Any = object()


class Dose(ModelIdentifier, db.Model):
    management_plan_id = db.Column(
        db.String,
        db.ForeignKey("management_plan.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    medication_id = db.Column(db.String)
    dose_amount = db.Column(db.Float)
    routine_sct_code = db.Column(db.String)

    changes = db.relationship(
        "DoseChange", order_by="desc(DoseChange.created)", cascade="all, delete-orphan"
    )

    @classmethod
    def new(
        cls,
        *,
        management_plan_id: str = None,
        changes: "Sequence[dict | DoseChange] | None" = _SENTINEL,
        medication_id: str | None = None,
        dose_amount: float | None = None,
        routine_sct_code: str | None = None,
        plan_add_history: bool = True,
        **kwargs: Any,
    ) -> "Dose":
        with db.session.no_autoflush:
            if changes is _SENTINEL:
                _changes: list[DoseChange] = []
            else:
                _changes = construct_children(changes, DoseChange)

            self = cls(
                management_plan_id=management_plan_id,
                changes=_changes,
                medication_id=medication_id,
                dose_amount=dose_amount,
                routine_sct_code=routine_sct_code,
                **kwargs,
            )

            db.session.add(self)

            # Migration restores history separately and suppresses the add_history call.
            if plan_add_history and self.management_plan_id:
                # Can't use the relationship until this Dose is committed so get the parent by id
                plan = db.session.get(sqlmodels.ManagementPlan, self.management_plan_id)
                if plan is not None:
                    plan.add_history(self, "insert")

        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
        return {
            "optional": {"routine_sct_code": str},
            "required": {"medication_id": str, "dose_amount": float},
            "updatable": {
                "routine_sct_code": str,
                "medication_id": str,
                "dose_amount": int,
            },
        }

    def on_patch(self, _json: dict = None, *args: Any, **kwargs: Any) -> None:
        if _json is None:
            return

        medication_id = _json.get("medication_id", self.medication_id)
        dose_amount = _json.get("dose_amount", self.dose_amount)
        routine_sct_code = _json.get("routine_sct_code", self.routine_sct_code)

        medication_change: str | None = None
        new_dose: str | None = None
        routine_sct_code_change: str | None = None

        if medication_id != self.medication_id:
            self.medication_id = medication_change = medication_id

        if dose_amount != self.dose_amount:
            self.dose_amount = new_dose = dose_amount

        if routine_sct_code != self.routine_sct_code:
            self.routine_sct_code = routine_sct_code_change = routine_sct_code

        DoseChange.new(
            dose_id=self.uuid,
            medication_id=medication_change,
            routine_sct_code=routine_sct_code_change,
            dose_amount=new_dose,
        )
        super(Dose, self).on_patch()

    def on_delete(self, parent: sqlmodels.ManagementPlan) -> None:
        parent.add_history(self, "delete")
        self.management_plan_id = None
        db.session.add(self)


class DoseChange(ModelIdentifier, db.Model):
    dose_id = db.Column(
        db.String, db.ForeignKey("dose.uuid", ondelete="CASCADE"), nullable=False
    )

    medication_id = db.Column(db.String, nullable=True)
    dose_amount = db.Column(db.Float, nullable=True)
    routine_sct_code = db.Column(db.String, nullable=True)

    @classmethod
    def new(cls, *, dose_id: str = None, **kwargs: Any) -> "DoseChange":
        self = cls(dose_id=dose_id, **kwargs)
        db.session.add(self)
        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
        return {
            "optional": {
                "medication_id": str,
                "dose_amount": float,
                "routine_sct_code": str,
            },
            "required": {},
            "updatable": {},
        }
