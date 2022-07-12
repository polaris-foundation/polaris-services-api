from __future__ import annotations

from typing import Any

from flask_batteries_included.sqldb import db

from dhos_services_api.sqlmodels.mixins import ModelIdentifier, ValidationSchema

# Sentinel for default value as we have to be able to distinguish passing an explicit None
# from not passing the argument (in recursive_patch explicit None will clear the metadata field
# but not passing any value leaves it unchanged).
_SENTINEL: Any = object()


class ObservableEntity(ModelIdentifier, db.Model):
    diagnosis_id = db.Column(
        db.String, db.ForeignKey("diagnosis.uuid", ondelete="CASCADE")
    )

    sct_code = db.Column(db.String)
    date_observed = db.Column(db.Date)
    value_as_string = db.Column(db.String)
    metadata_ = db.Column(db.JSON, default={}, nullable=False)

    @classmethod
    def new(
        cls,
        *,
        diagnosis_id: str = None,
        metadata: dict | None = _SENTINEL,
        **kwargs: Any,
    ) -> "ObservableEntity":
        if metadata is not _SENTINEL:
            kwargs["metadata_"] = metadata or {}
        self = cls(diagnosis_id=diagnosis_id, **kwargs)
        db.session.add(self)
        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
        return {
            "optional": {"metadata": dict, "value_as_string": str},
            "required": {"sct_code": str, "date_observed": str},
            "updatable": {
                "sct_code": str,
                "date_observed": str,
                "value_as_string": str,
                "metadata": dict,
            },
        }

    def recursive_patch(
        self,
        *,
        metadata: dict | None = _SENTINEL,
        **kwargs: object,
    ) -> None:
        if metadata is not _SENTINEL:
            kwargs["metadata_"] = metadata or {}
        super().recursive_patch(**kwargs)
