from datetime import date
from typing import Dict, List

import pytest
from flask_sqlalchemy import SQLAlchemy

from dhos_services_api.sqlmodels.pydantic_models import ReadingsPlanResponse
from dhos_services_api.sqlmodels.readings_plan import ReadingsPlan, ReadingsPlanChange


@pytest.mark.usefixtures("uses_sql_database", "app")
class TestReadingsPlan:
    @pytest.fixture
    def readings_plan_details(self) -> Dict:
        return {
            "days_per_week_to_take_readings": 7,
            "end_date": date(2021, 2, 2),
            "readings_per_day": 7,
            "sct_code": "33747003",
            "start_date": date(2020, 7, 15),
        }

    def test_readings_plan_created_with_history(
        self, readings_plan_details: Dict
    ) -> None:
        plan: ReadingsPlan = ReadingsPlan.new(**readings_plan_details)
        changes: List[ReadingsPlanChange] = plan.changes
        assert len(changes) == 1
        assert (
            changes[0].days_per_week_to_take_readings
            == plan.days_per_week_to_take_readings
            == readings_plan_details["days_per_week_to_take_readings"]
        )
        assert (
            changes[0].readings_per_day
            == plan.readings_per_day
            == readings_plan_details["readings_per_day"]
        )

    def test_readings_plan_updated_with_history(
        self,
        _db: SQLAlchemy,
        readings_plan_details: Dict,
        diagnosis_uuid: str,
        wildcard_identifier: dict,
    ) -> None:
        new_days_per_week = 4
        new_readings_per_day = 4
        plan: ReadingsPlan = ReadingsPlan.new(
            diagnosis_id=diagnosis_uuid, **readings_plan_details
        )
        _db.session.commit()
        plan.recursive_patch(days_per_week_to_take_readings=new_days_per_week)
        plan.recursive_patch(readings_per_day=new_readings_per_day)
        _db.session.commit()

        actual = ReadingsPlanResponse.from_orm(plan).dict()
        assert actual == {
            **readings_plan_details,
            "days_per_week_to_take_readings": new_days_per_week,
            "readings_per_day": new_readings_per_day,
            **wildcard_identifier,
            "changes": [
                {
                    "days_per_week_to_take_readings": None,
                    "readings_per_day": new_readings_per_day,
                    **wildcard_identifier,
                },
                {
                    "days_per_week_to_take_readings": new_days_per_week,
                    "readings_per_day": None,
                    **wildcard_identifier,
                },
                {
                    "days_per_week_to_take_readings": 7,
                    "readings_per_day": 7,
                    **wildcard_identifier,
                },
            ],
        }
