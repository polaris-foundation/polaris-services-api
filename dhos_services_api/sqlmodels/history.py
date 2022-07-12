from typing import Any

from flask_batteries_included.sqldb import db

from dhos_services_api.sqlmodels.mixins import ModelIdentifier, ValidationSchema


class History(ModelIdentifier, db.Model):
    record_id = db.Column(
        db.String, db.ForeignKey("record.uuid", ondelete="CASCADE"), nullable=False
    )

    parity = db.Column(db.Integer)
    gravidity = db.Column(db.Integer)

    @classmethod
    def new(cls, *, record_id: str = None, **kwargs: Any) -> "History":
        self = cls(record_id=record_id, **kwargs)
        db.session.add(self)
        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
        return {
            "optional": {"parity": int, "gravidity": int},
            "required": {},
            "updatable": {"parity": int, "gravidity": int},
        }
