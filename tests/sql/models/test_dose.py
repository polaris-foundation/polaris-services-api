from typing import Optional

import pytest
from flask_sqlalchemy import SQLAlchemy

from dhos_services_api.sqlmodels.dose import Dose
from dhos_services_api.sqlmodels.pydantic_models import DoseResponse


@pytest.mark.usefixtures("app", "uses_sql_database")
@pytest.mark.parametrize(
    "dose_update,dose_update_changes",
    [
        (
            {
                "medication_id": "new_med",
                "dose_amount": 2.5,
                "routine_sct_code": "def",
            },
            {
                "medication_id": "new_med",
                "dose_amount": 2.5,
                "routine_sct_code": "def",
            },
        ),
        (
            {
                "medication_id": "new_med",
                "dose_amount": 1.5,
                "routine_sct_code": "def",
            },
            {
                "medication_id": "new_med",
                "dose_amount": None,
                "routine_sct_code": "def",
            },
        ),
        (
            {
                "medication_id": "original_med",
                "dose_amount": 2.5,
                "routine_sct_code": "abc",
            },
            {
                "medication_id": None,
                "dose_amount": 2.5,
                "routine_sct_code": None,
            },
        ),
    ],
)
class TestDose:
    def test_on_patch(
        self,
        _db: SQLAlchemy,
        wildcard_identifier: dict,
        dose_update: dict,
        dose_update_changes: dict,
    ) -> None:
        dose_details: dict = {
            "medication_id": "original_med",
            "dose_amount": 1.5,
            "routine_sct_code": "abc",
        }
        dose_uuid: str = Dose.new(management_plan_id=None, **dose_details).uuid
        _db.session.flush()
        original_dose: Optional[Dose] = _db.session.get(Dose, dose_uuid)
        assert original_dose is not None
        original_dose.on_patch(dose_update)
        _db.session.add(original_dose)
        _db.session.flush()
        updated_dose: Optional[Dose] = _db.session.get(Dose, dose_uuid)
        assert updated_dose is not None

        # After
        assert DoseResponse.from_orm(updated_dose).dict() == {
            **dose_update,
            **wildcard_identifier,
            "changes": [
                {
                    **dose_update_changes,
                    **wildcard_identifier,
                },
            ],
        }
