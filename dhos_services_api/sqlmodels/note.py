from typing import Any

from flask_batteries_included.sqldb import db

from dhos_services_api.sqlmodels.mixins import ModelIdentifier, ValidationSchema


class Note(ModelIdentifier, db.Model):
    record_id = db.Column(
        db.String, db.ForeignKey("record.uuid", ondelete="CASCADE"), nullable=False
    )
    content = db.Column(db.String)
    clinician_uuid = db.Column(db.String)

    @classmethod
    def new(cls, *, record_id: str = None, **kwargs: Any) -> "Note":
        self = cls(record_id=record_id, **kwargs)
        db.session.add(self)
        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
        return {
            "optional": {},
            "required": {"content": str, "clinician_uuid": str},
            "updatable": {"content": str, "clinician_uuid": str},
        }
