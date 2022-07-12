from __future__ import annotations

from typing import Any, Sequence

from flask_batteries_included.sqldb import db

from dhos_services_api import sqlmodels
from dhos_services_api.sqlmodels.mixins import (
    ModelIdentifier,
    ValidationSchema,
    construct_children,
    construct_single_child,
)


class Diagnosis(ModelIdentifier, db.Model):
    record_id = db.Column(
        db.String, db.ForeignKey("record.uuid", ondelete="CASCADE"), nullable=False
    )
    record = db.relationship("Record", back_populates="diagnoses", uselist=False)

    sct_code = db.Column(db.String)
    diagnosis_other = db.Column(db.String)

    diagnosed = db.Column(db.Date)
    resolved = db.Column(db.Date)
    presented = db.Column(db.Date)
    episode = db.Column(db.Integer)

    diagnosis_tool: list[str] = db.Column(db.JSON, default=[])
    diagnosis_tool_other = db.Column(db.String)

    risk_factors: list[str] = db.Column(db.JSON, default=[])

    management_plan = db.relationship(
        "ManagementPlan", uselist=False, cascade="all, delete-orphan"
    )
    readings_plan = db.relationship(
        "ReadingsPlan", uselist=False, cascade="all, delete-orphan"
    )
    observable_entities = db.relationship(
        "ObservableEntity", cascade="all, delete-orphan"
    )

    @classmethod
    def new(
        cls,
        *,
        record_id: str = None,
        management_plan: dict | None | sqlmodels.ManagementPlan | None = None,
        readings_plan: dict | None | sqlmodels.ReadingsPlan | None = None,
        observable_entities: Sequence[dict | sqlmodels.ObservableEntity] | None = None,
        **kwargs: Any,
    ) -> "Diagnosis":
        with db.session.no_autoflush:
            self = cls(
                record_id=record_id,
                management_plan=construct_single_child(
                    management_plan, sqlmodels.ManagementPlan
                ),
                readings_plan=construct_single_child(
                    readings_plan, sqlmodels.ReadingsPlan
                ),
                observable_entities=construct_children(
                    observable_entities, sqlmodels.ObservableEntity
                ),
                **kwargs,
            )
            db.session.add(self)
        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
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

    def recursive_patch(
        self,
        *,
        management_plan: dict | None = None,
        readings_plan: dict | None = None,
        observable_entities: list[dict] | None = None,
        **kwargs: object,
    ) -> None:
        super().recursive_patch(**kwargs)
        if management_plan:
            sqlmodels.ManagementPlan.patch_or_add(
                self.management_plan, management_plan, {"diagnosis_id": self.uuid}
            )
        if readings_plan:
            sqlmodels.ReadingsPlan.patch_or_add(
                self.readings_plan, readings_plan, {"diagnosis_id": self.uuid}
            )
        if observable_entities:
            sqlmodels.ObservableEntity.patch_related_objects(
                related_column=sqlmodels.ObservableEntity.diagnosis_id,
                parent_id=self.uuid,
                patch_data=observable_entities,
            )
