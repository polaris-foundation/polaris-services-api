from typing import Any

from flask_batteries_included.sqldb import db

from dhos_services_api.sqlmodels.mixins import ModelIdentifier, ValidationSchema


class NonMedicationAction(ModelIdentifier, db.Model):
    management_plan_id = db.Column(
        db.String,
        db.ForeignKey("management_plan.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    # Examples of GDM non medication actions for `action_sct_code`:
    # - dietary education for GDM (439051004)
    # - recommendation to exercise (281090004)
    action_sct_code = db.Column(db.String)

    @classmethod
    def new(
        cls, *, management_plan_id: str = None, **kwargs: Any
    ) -> "NonMedicationAction":
        self = cls(management_plan_id=management_plan_id, **kwargs)
        db.session.add(self)
        return self

    @classmethod
    def schema(cls) -> ValidationSchema:
        return {
            "optional": {},
            "required": {"action_sct_code": str},
            "updatable": {"action_sct_code": str},
        }
