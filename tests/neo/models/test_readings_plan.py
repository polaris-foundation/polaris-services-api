from typing import Dict, List

import pytest

from dhos_services_api.models.readings_plan import ReadingsPlan, ReadingsPlanChange


@pytest.mark.neo4j
@pytest.mark.usefixtures("clean_up_neo4j_after_test", "app")
class TestReadingsPlan:
    @pytest.fixture
    def readings_plan_details(self) -> Dict:
        return {
            "days_per_week_to_take_readings": 7,
            "end_date": "2021-02-02",
            "readings_per_day": 7,
            "sct_code": "33747003",
            "start_date": "2020-07-15",
        }

    def test_readings_plan_created_with_history(
        self, readings_plan_details: Dict
    ) -> None:
        plan: ReadingsPlan = ReadingsPlan.new(**readings_plan_details)
        changes: List[ReadingsPlanChange] = plan.changes.all()
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
        self, readings_plan_details: Dict
    ) -> None:
        new_days_per_week = 4
        new_readings_per_day = 4
        plan: ReadingsPlan = ReadingsPlan.new(**readings_plan_details)
        plan.on_patch({"days_per_week_to_take_readings": new_days_per_week})
        plan.on_patch({"readings_per_day": new_readings_per_day})
        changes: List[ReadingsPlanChange] = plan.changes.all()
        changes.sort(key=lambda x: x.created or "")
        assert len(changes) == 3
        assert changes[1].days_per_week_to_take_readings == new_days_per_week
        assert changes[1].readings_per_day is None
        assert changes[2].days_per_week_to_take_readings is None
        assert changes[2].readings_per_day == new_readings_per_day
        assert plan.readings_per_day == new_readings_per_day
        assert plan.days_per_week_to_take_readings == new_days_per_week
