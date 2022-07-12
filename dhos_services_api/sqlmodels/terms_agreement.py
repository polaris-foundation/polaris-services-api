from typing import Any

from flask_batteries_included.sqldb import db
from sqlalchemy import func

from dhos_services_api.sqlmodels.mixins import ModelIdentifier, ValidationSchema


class TermsAgreement(ModelIdentifier, db.Model):
    patient_id = db.Column(
        db.String, db.ForeignKey("patient.uuid", ondelete="CASCADE"), nullable=False
    )

    product_name = db.Column(db.String)
    version = db.Column(db.Integer)
    accepted_timestamp = db.Column(
        db.DateTime(timezone=True), server_default=func.now()
    )

    tou_version = db.Column(db.Integer)
    tou_accepted_timestamp = db.Column(
        db.DateTime(timezone=True), server_default=func.now()
    )

    patient_notice_version = db.Column(db.Integer)
    patient_notice_accepted_timestamp = db.Column(
        db.DateTime(timezone=True), server_default=func.now()
    )

    @classmethod
    def new(cls, *, patient_id: str = None, **kwargs: Any) -> Any:
        self = cls(patient_id=patient_id, **kwargs)
        db.session.add(self)
        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
        return {
            "optional": {
                "version": int,
                "accepted_timestamp": str,
                "tou_version": int,
                "tou_accepted_timestamp": str,
                "patient_notice_version": int,
                "patient_notice_accepted_timestamp": str,
            },
            "required": {
                "product_name": str,
            },
            "updatable": {},
        }
