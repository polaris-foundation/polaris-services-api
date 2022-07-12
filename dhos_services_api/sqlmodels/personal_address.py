from datetime import date
from typing import Any

from flask_batteries_included.sqldb import db

from dhos_services_api.sqlmodels.mixins import ModelIdentifier, ValidationSchema
from dhos_services_api.sqlmodels.mixins.address import AddressMixin

_MARKER: Any = object()


class PersonalAddress(ModelIdentifier, AddressMixin, db.Model):
    lived_from: date = db.Column(db.Date, nullable=True)
    lived_until: date = db.Column(db.Date, nullable=True)

    patient_id = db.Column(
        db.String, db.ForeignKey("patient.uuid", ondelete="CASCADE"), nullable=False
    )

    @classmethod
    def new(cls, *, patient_id: str = None, **kwargs: Any) -> "PersonalAddress":
        self = cls(patient_id=patient_id, **kwargs)
        db.session.add(self)
        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
        return {
            "optional": {
                "address_line_1": str,
                "address_line_2": str,
                "address_line_3": str,
                "address_line_4": str,
                "locality": str,
                "region": str,
                "postcode": str,
                "country": str,
                "lived_from": str,
                "lived_until": str,
            },
            "required": {},
            "updatable": {
                "address_line_1": str,
                "address_line_2": str,
                "address_line_3": str,
                "address_line_4": str,
                "locality": str,
                "region": str,
                "postcode": str,
                "country": str,
                "lived_from": str,
                "lived_until": str,
            },
        }
