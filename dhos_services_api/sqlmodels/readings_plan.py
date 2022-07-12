from __future__ import annotations

from typing import Any

from flask_batteries_included.sqldb import db

from dhos_services_api.sqlmodels.mixins import (
    ModelIdentifier,
    ValidationSchema,
    construct_children,
)

# Sentinel for default value as we have to be able to distinguish passing an explicit None
# from not passing the argument (in recursive_patch explicit None will clear the metadata field
# but not passing any value leaves it unchanged).
_SENTINEL: Any = object()


class ReadingsPlan(ModelIdentifier, db.Model):
    diagnosis_id = db.Column(
        db.String, db.ForeignKey("diagnosis.uuid", ondelete="CASCADE"), nullable=False
    )

    days_per_week_to_take_readings = db.Column(db.Integer)
    readings_per_day = db.Column(db.Integer)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    sct_code = db.Column(db.String, nullable=False)

    changes = db.relationship(
        "ReadingsPlanChange",
        order_by="desc(ReadingsPlanChange.created)",
        cascade="all, delete-orphan",
    )

    @classmethod
    def new(
        cls,
        *,
        diagnosis_id: str = None,
        changes: list[dict | ReadingsPlanChange] | None = _SENTINEL,
        days_per_week_to_take_readings: int | None = None,
        readings_per_day: int | None = None,
        **kwargs: Any,
    ) -> "ReadingsPlan":
        with db.session.no_autoflush:
            if changes is _SENTINEL:
                # If 'changes' is not passed in explicitly we add an initial change.
                # If it is passed explicitly we assume any initial change is included.
                # Migration from neo4j will pass an explicit None to prevent automatic
                # creation and will migrate existing changes separately.
                _changes: list[ReadingsPlanChange] = [
                    (
                        ReadingsPlanChange(
                            days_per_week_to_take_readings=days_per_week_to_take_readings,
                            readings_per_day=readings_per_day,
                        )
                    )
                ]
            else:
                _changes = construct_children(changes, ReadingsPlanChange)

            self = cls(
                diagnosis_id=diagnosis_id,
                changes=_changes,
                days_per_week_to_take_readings=days_per_week_to_take_readings,
                readings_per_day=readings_per_day,
                **kwargs,
            )
            db.session.add(self)
        return self

    def on_patch(self, _json: dict[str, int] = None, *args: Any, **kwargs: Any) -> None:
        if _json is None:
            return

        days_per_week_to_take_readings = _json.get(
            "days_per_week_to_take_readings", self.days_per_week_to_take_readings
        )
        readings_per_day = _json.get("readings_per_day", self.readings_per_day)

        new_days_per_week_to_take_readings = None
        new_readings_per_day = None

        if days_per_week_to_take_readings != self.days_per_week_to_take_readings:
            new_days_per_week_to_take_readings = days_per_week_to_take_readings

        if readings_per_day != self.readings_per_day:
            new_readings_per_day = readings_per_day

        ReadingsPlanChange.new(
            readings_plan_id=self.uuid,
            days_per_week_to_take_readings=new_days_per_week_to_take_readings,
            readings_per_day=new_readings_per_day,
        )

        super(ReadingsPlan, self).on_patch()

    @classmethod
    def schema(cls) -> ValidationSchema:
        return {
            "optional": {
                "days_per_week_to_take_readings": int,
                "readings_per_day": int,
                "start_date": str,
                "end_date": str,
            },
            "required": {"sct_code": str},
            "updatable": {
                "days_per_week_to_take_readings": int,
                "readings_per_day": int,
                "start_date": str,
                "end_date": str,
                "sct_code": str,
            },
        }


class ReadingsPlanChange(ModelIdentifier, db.Model):
    readings_plan_id = db.Column(
        db.String,
        db.ForeignKey("readings_plan.uuid", ondelete="CASCADE"),
        nullable=False,
    )

    days_per_week_to_take_readings = db.Column(db.Integer)
    readings_per_day = db.Column(db.Integer)

    @classmethod
    def new(
        cls, *, readings_plan_id: str = None, **kwargs: Any
    ) -> "ReadingsPlanChange":
        self = cls(readings_plan_id=readings_plan_id, **kwargs)
        db.session.add(self)
        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
        return {
            "optional": {
                "days_per_week_to_take_readings": int,
                "readings_per_day": int,
            },
            "required": {},
            "updatable": {},
        }
