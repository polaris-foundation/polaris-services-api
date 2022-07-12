import contextlib
from datetime import datetime, timedelta
from typing import Any, Callable, Generator, List, Optional, Tuple, Type

import pytest
from mock import Mock
from pytest_mock import MockerFixture

from dhos_services_api.blueprint_patients import alerting_controller
from dhos_services_api.helpers import audit
from dhos_services_api.models.api_spec import ActivityAlertingPatientResponse
from dhos_services_api.sqlmodels import pydantic_models


class _Anything:
    def __init__(self, _type: Optional[Type] = None) -> None:
        self._type = _type

    def __eq__(self, other: Any) -> bool:
        if self._type is not None:
            return isinstance(other, self._type)
        return True


ANY = _Anything()
ANY_STRING = _Anything(str)
ANY_DATETIME = _Anything(datetime)


def timestamp(iso: str) -> float:
    return datetime.fromisoformat(iso).timestamp()


@pytest.mark.usefixtures("app", "uses_sql_database")
class TestAlertingController:
    @pytest.fixture(autouse=True)
    def mock_audit_record_patient_viewed(self, mocker: MockerFixture) -> Mock:
        return mocker.patch.object(audit, "record_patient_viewed")

    @pytest.fixture(autouse=True)
    def mock_audit_record_patient_updated(self, mocker: MockerFixture) -> Mock:
        return mocker.patch.object(audit, "record_patient_updated")

    @pytest.fixture(autouse=True)
    def mock_audit_record_patient_archived(self, mocker: MockerFixture) -> Mock:
        return mocker.patch.object(audit, "record_patient_archived")

    @pytest.fixture
    def gdm_open_patients_for_test(
        self, patient_context: Callable
    ) -> Generator[List[str], None, None]:
        @contextlib.contextmanager
        def generate_patient(
            name: str, days_ago: int, diagnosis_code: str
        ) -> Generator[str, None, None]:
            open_date = str(datetime.now().date() - timedelta(days=days_ago))
            with patient_context(
                name,
                product="GDM",
                hospital_number=f"hn-{name}",
                opened_date=open_date,
                diagnosis_code=diagnosis_code,
            ) as patient:
                yield patient.uuid

        with generate_patient("three-weeks", 21, "D0000001") as p3wk, generate_patient(
            "eight-days", 8, "11687002"
        ) as p8, generate_patient("seven-days", 7, "D0000001") as p7, generate_patient(
            "three-days", 3, "11687002"
        ) as p3, generate_patient(
            "wrong-code", 8, "D9999999"
        ) as pw:
            yield [p3wk, p8]

    def test_retrieve_open_gdm_patients(
        self,
        gdm_open_patients_for_test: List[str],
        assert_valid_schema: Callable,
        any_datetime: datetime,
        any_uuid: str,
        any_string: str,
    ) -> None:
        results: List[dict] = alerting_controller.retrieve_open_gdm_patients()
        assert len(results) == 2
        assert_valid_schema(ActivityAlertingPatientResponse, results, many=True)

        assert set(r["uuid"] for r in results) == set(gdm_open_patients_for_test)
        expected = {
            "readings_plans": [
                {
                    "created": any_datetime,
                    "days_per_week_to_take_readings": 4,
                    "readings_per_day": 4,
                },
            ],
            "uuid": any_uuid,
            "first_name": any_string,
            "locations": [any_uuid],
        }
        assert all(r == expected for r in results)
        # Check datetime is localised.
        tz = results[0]["readings_plans"][0]["created"].tzinfo
        assert tz is not None and tz.utcoffset(None) == timedelta(0)

    @pytest.mark.parametrize(
        "plans,expected_plans,id",
        [
            ([], [], "no-plans"),
            (
                [(timestamp("2020-07-15T12:00"), 1, 1)],
                [
                    ("2020-07-15T12:00:00.000+00:00", 1, 1),
                ],
                "single-plan",
            ),
            (
                [
                    (timestamp("2020-07-15T12:00"), 4, 4),
                    (timestamp("2020-07-10T12:00"), 4, None),
                    (timestamp("2020-07-05T12:00"), 3, 4),
                ],
                [
                    ("2020-07-05T12:00:00.000+00:00", 3, 4),
                    ("2020-07-10T12:00:00.000+00:00", 4, 4),
                ],
                "merge-and-remove-duplicate",
            ),
            (
                [
                    (timestamp("2020-07-15T12:00"), 4, 4),
                    (timestamp("2020-07-10T12:00"), 4, None),
                    (timestamp("2020-06-25T12:00"), None, None),
                    (timestamp("2020-07-05T12:00"), 3, 4),
                ],
                [
                    ("2020-07-05T12:00:00.000+00:00", 3, 4),
                    ("2020-07-10T12:00:00.000+00:00", 4, 4),
                ],
                "merge-and-remove-missing",
            ),
            (
                [
                    (timestamp("2020-07-15T12:00"), None, 1),
                    (timestamp("2020-07-10T12:00"), 0, None),
                    (timestamp("2020-06-25T12:00"), None, None),
                    (timestamp("2020-07-05T12:00"), 1, 0),
                ],
                [
                    ("2020-07-05T12:00:00.000+00:00", 1, 0),
                    ("2020-07-10T12:00:00.000+00:00", 0, 0),
                    ("2020-07-15T12:00:00.000+00:00", 0, 1),
                ],
                "Don't ignore zero values",
            ),
            (
                [
                    (timestamp("2020-07-15T12:00"), 4, 4),
                    (timestamp("2020-07-05T12:00"), 3, 1),
                ],
                [
                    ("2020-07-05T12:00:00.000+00:00", 3, 1),
                    ("2020-07-15T12:00:00.000+00:00", 4, 4),
                ],
                "missing-latest-change",
            ),
        ],
        ids=lambda s: s if isinstance(s, str) else "",
    )
    def test_fix_patient(
        self,
        plans: List[Tuple[float, int, int]],
        expected_plans: List[Tuple[str, int, int]],
        id: str,
    ) -> None:
        patient: pydantic_models.ActivityAlertingPatientResponse = (
            alerting_controller.ActivityAlertingPatientResponse(
                first_name="Jemima",
                locations=["locn"],
                uuid="uuid",
                readings_plans=[
                    pydantic_models.SimpleReadingsPlan(
                        created=created,
                        days_per_week_to_take_readings=dpwttr,
                        readings_per_day=rpd,
                    )
                    for created, dpwttr, rpd in plans
                ],
            )
        )
        expected: pydantic_models.ActivityAlertingPatientResponse = (
            pydantic_models.ActivityAlertingPatientResponse(
                first_name="Jemima",
                locations=["locn"],
                uuid="uuid",
                readings_plans=[
                    pydantic_models.SimpleReadingsPlan(
                        created=created,
                        days_per_week_to_take_readings=dpwttr,
                        readings_per_day=rpd,
                    )
                    for created, dpwttr, rpd in expected_plans
                ],
            )
        )
        actual = alerting_controller._fix_patient(patient)

        assert actual == expected
