from __future__ import annotations

from typing import Any

from flask_batteries_included.sqldb import db
from sqlalchemy.dialects import postgresql

from dhos_services_api.sqlmodels.mixins import ModelIdentifier, ValidationSchema


class Visit(ModelIdentifier, db.Model):
    record_id = db.Column(
        db.String, db.ForeignKey("record.uuid", ondelete="CASCADE"), nullable=False
    )

    # Ideally this would be an array of foreignkey references to diagnosis.uuid but Postgres doesn't yet have
    # foreignkey arrays.
    diagnoses = db.Column(postgresql.ARRAY(db.String), default=[])

    # Says it's a date, but its actually a datetimem.
    visit_date = db.Column(db.DateTime(timezone=True))

    summary = db.Column(db.String)

    clinician_uuid = db.Column(db.String, nullable=True)
    location: str = db.Column(db.String, nullable=True)

    @classmethod
    def new(cls, *, record_id: str = None, **kwargs: Any) -> "Visit":
        self = cls(record_id=record_id, **kwargs)
        db.session.add(self)
        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
        return {
            "optional": {"summary": str, "diagnoses": [dict]},
            "required": {"visit_date": str, "clinician_uuid": str, "location": str},
            "updatable": {
                "visit_date": str,
                "clinician_uuid": str,
                "summary": str,
                "location": str,
                "diagnoses": [dict],
            },
        }
