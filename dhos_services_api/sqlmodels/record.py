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

_SENTINEL: Any = object()


class Record(ModelIdentifier, db.Model):
    notes = db.relationship("Note")
    diagnoses = db.relationship(
        "Diagnosis",
        back_populates="record",
        order_by="desc(Diagnosis.created)",
        cascade="all, delete-orphan",
    )
    pregnancies = db.relationship(
        "Pregnancy", order_by="desc(Pregnancy.created)", cascade="all, delete-orphan"
    )
    visits = db.relationship(
        "Visit", order_by="desc(Visit.created)", cascade="all, delete-orphan"
    )
    history = db.relationship(
        "History",
        uselist=False,
        order_by="desc(History.created)",
        cascade="all, delete-orphan",
    )
    patient = db.relationship("Patient", back_populates="record", uselist=False)

    @classmethod
    def new(
        cls,
        *,
        notes: Sequence[dict[str, object] | sqlmodels.Note] = None,
        diagnoses: Sequence[dict[str, object] | sqlmodels.Diagnosis] = None,
        pregnancies: Sequence[dict[str, object] | sqlmodels.Pregnancy] = None,
        visits: Sequence[dict[str, object] | sqlmodels.Visit] = None,
        history: dict[str, object] | sqlmodels.History | None = _SENTINEL,
        **kwargs: Any,
    ) -> "Record":
        with db.session.no_autoflush:
            self = cls(
                notes=construct_children(notes, sqlmodels.Note),
                diagnoses=construct_children(diagnoses, sqlmodels.Diagnosis),
                pregnancies=construct_children(pregnancies, sqlmodels.Pregnancy),
                visits=construct_children(visits, sqlmodels.Visit),
                history=construct_single_child(
                    {} if history is _SENTINEL else history, sqlmodels.History
                ),
                **kwargs,
            )
            db.session.add(self)
        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
        return {
            "optional": {
                "pregnancies": [dict],
                "history": dict,
                "notes": [dict],
                "diagnoses": [dict],
                "visits": [dict],
            },
            "required": {},
            "updatable": {
                "pregnancies": [dict],
                "notes": [dict],
                "diagnoses": [dict],
                "visits": [dict],
                "history": dict,
            },
        }

    def recursive_patch(
        self,
        *,
        notes: list[dict | str] | None = None,
        diagnoses: list[dict | str] | None = None,
        pregnancies: list[dict | str] | None = None,
        visits: list[dict | str] | None = None,
        history: dict | None = None,
        **kwargs: Any,
    ) -> None:
        super().recursive_patch(**kwargs)
        if notes:
            sqlmodels.Note.patch_related_objects(
                related_column=sqlmodels.Note.record_id,
                parent_id=self.uuid,
                patch_data=notes,
            )

        if diagnoses:
            sqlmodels.Diagnosis.patch_related_objects(
                related_column=sqlmodels.Diagnosis.record_id,
                parent_id=self.uuid,
                patch_data=diagnoses,
            )

        if pregnancies:
            sqlmodels.Pregnancy.patch_related_objects(
                related_column=sqlmodels.Pregnancy.record_id,
                parent_id=self.uuid,
                patch_data=pregnancies,
            )

        if visits:
            sqlmodels.Visit.patch_related_objects(
                related_column=sqlmodels.Visit.record_id,
                parent_id=self.uuid,
                patch_data=visits,
            )

        if history:
            sqlmodels.History.patch_or_add(
                self.history, history, {"record_id": self.uuid}
            )
