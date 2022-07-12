from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional, Sequence

from flask_batteries_included.sqldb import db
from werkzeug.exceptions import abort

from dhos_services_api.sqlmodels.mixins import (
    ModelIdentifier,
    ValidationSchema,
    construct_children,
)

_MARKER: Any = object()


class DraysonHealthProductChangeEvent(Enum):
    ARCHIVE = "archive"
    STOP_MONITORING = "stop monitoring"
    START_MONITORING = "start monitoring"
    # UNARCHIVE = "unarchive"  NOT IMPLEMENTED YET


class DraysonHealthProduct(ModelIdentifier, db.Model):
    patient_id = db.Column(
        db.String, db.ForeignKey("patient.uuid", ondelete="CASCADE"), nullable=False
    )

    product_name = db.Column(db.String, nullable=False)
    opened_date = db.Column(db.Date, nullable=True, default=datetime.now().date)
    closed_date = db.Column(db.Date, nullable=True, default=None)
    closed_reason = db.Column(db.String, nullable=True)
    closed_reason_other = db.Column(db.String, nullable=True)

    def pack_base_product(self) -> dict[str, Optional[str]]:

        return {
            "product_name": self.product_name,
            "opened_date": self.opened_date,
            "closed_date": self.closed_date,
            **self.pack_identifier(),
        }

    accessibility_discussed = db.Column(db.Boolean, nullable=False, default=False)
    accessibility_discussed_with = db.Column(db.String, nullable=True)
    accessibility_discussed_date = db.Column(db.Date, nullable=True)

    monitored_by_clinician = db.Column(db.Boolean, nullable=False, default=True)
    # N.B. Changes are sorted oldest first.
    changes = db.relationship(
        "DraysonHealthProductChange",
        order_by="asc(DraysonHealthProductChange.created)",
        cascade="all, delete-orphan",
    )

    @classmethod
    def new(
        cls,
        *,
        patient_id: str = None,
        changes: "Sequence[dict | DraysonHealthProductChange] | None" = None,
        **kwargs: Any,
    ) -> "DraysonHealthProduct":
        with db.session.no_autoflush:
            self = cls(
                patient_id=patient_id,
                changes=construct_children(changes, DraysonHealthProductChange),
                **kwargs,
            )
            db.session.add(self)
        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
        return {
            "optional": {
                "closed_date": str,
                "closed_reason": str,
                "closed_reason_other": str,
                "accessibility_discussed": bool,
                "accessibility_discussed_with": str,
                "accessibility_discussed_date": str,
                "monitored_by_clinician": bool,
            },
            "required": {"product_name": str, "opened_date": str},
            "updatable": {
                "product_name": str,
                "opened_date": str,
                "closed_date": str,
                "closed_reason": str,
                "closed_reason_other": str,
                "monitored_by_clinician": bool,
            },
        }

    def _new_event(self, event: DraysonHealthProductChangeEvent) -> None:
        change_node = DraysonHealthProductChange.new(
            event=event.value, drayson_health_product_id=self.uuid
        )

    def on_patch(self, _json: dict = None, *args: Any, **kwargs: Any) -> None:
        if _json is None:
            return

        product_name = _json.get("product_name", None)
        if product_name is not None and product_name != self.product_name:
            query = db.session.query(DraysonHealthProduct).filter(
                DraysonHealthProduct.patient_id == self.patient_id,
                DraysonHealthProduct.product_name == product_name,
                DraysonHealthProduct.closed_date == None,
            )
            if query.first() is not None:
                abort(400, f"patient is already active on {_json['product_name']}")

        super().on_patch()

    def close(
        self,
        closed_date: str,
        closed_reason: Optional[str] = None,
        closed_reason_other: Optional[str] = None,
    ) -> None:
        self.closed_date = closed_date
        self.closed_reason = closed_reason
        self.closed_reason_other = closed_reason_other

        if self.monitored_by_clinician:
            self.stop_monitoring()

        self._new_event(event=DraysonHealthProductChangeEvent.ARCHIVE)
        db.session.add(self)
        db.session.commit()

    def stop_monitoring(self) -> None:
        self.monitored_by_clinician = False
        db.session.add(self)
        self._new_event(event=DraysonHealthProductChangeEvent.STOP_MONITORING)
        db.session.commit()

    def start_monitoring(self) -> None:
        self.monitored_by_clinician = True
        db.session.add(self)
        self._new_event(event=DraysonHealthProductChangeEvent.START_MONITORING)
        db.session.commit()


class DraysonHealthProductChange(ModelIdentifier, db.Model):
    drayson_health_product_id = db.Column(
        db.String,
        db.ForeignKey("drayson_health_product.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    event = db.Column(db.String)

    @classmethod
    def new(
        cls, *, drayson_health_product_id: str = None, **kwargs: Any
    ) -> "DraysonHealthProductChange":
        self = cls(drayson_health_product_id=drayson_health_product_id, **kwargs)
        db.session.add(self)
        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
        return {
            "optional": {},
            "required": {"event": str},
            "updatable": {},
        }
