from random import randint
from typing import Dict, List

import pytest
from flask_sqlalchemy import SQLAlchemy

from dhos_services_api.blueprint_patients.patient_controller import create_patient
from dhos_services_api.blueprint_patients.pmcf_controller import (
    get_active_patient_count,
    get_created_patient_count,
)


@pytest.mark.usefixtures("app", "uses_sql_database")
class TestController:
    def create_five_patients(self, minimal_patient: dict) -> None:
        open_closed_dates: list = [
            ("2019-10-16", "2020-04-16"),
            ("2020-10-16", "2021-04-16"),
            ("2021-10-16", "2022-04-16"),
            ("2022-03-16", None),
            ("2022-05-16", None),
        ]

        for open, closed in open_closed_dates:
            minimal_patient["dh_products"][0]["opened_date"] = open
            minimal_patient["dh_products"][0]["closed_date"] = closed
            minimal_patient["hospital_number"] = "".join(
                ["{}".format(randint(0, 9)) for num in range(0, 7)]
            )
            create_patient(product_name="GDM", patient_details=minimal_patient)

    def test_get_active_patient_count(
        self, _db: SQLAlchemy, minimal_patient: dict
    ) -> None:

        self.create_five_patients(minimal_patient)

        results = get_active_patient_count(
            product_name="GDM", start_date="2022-01-01", end_date="2022-03-31"
        )
        expected: List[Dict] = [
            {"year_week": "2021-52", "count": 1},
            {"year_week": "2022-01", "count": 1},
            {"year_week": "2022-02", "count": 1},
            {"year_week": "2022-03", "count": 1},
            {"year_week": "2022-04", "count": 1},
            {"year_week": "2022-05", "count": 1},
            {"year_week": "2022-06", "count": 1},
            {"year_week": "2022-07", "count": 1},
            {"year_week": "2022-08", "count": 1},
            {"year_week": "2022-09", "count": 1},
            {"year_week": "2022-10", "count": 1},
            {"year_week": "2022-11", "count": 2},
            {"year_week": "2022-12", "count": 2},
            {"year_week": "2022-13", "count": 2},
        ]
        assert results == expected

    def test_get_active_patient_count_no_start_date(
        self, _db: SQLAlchemy, minimal_patient: dict
    ) -> None:
        self.create_five_patients(minimal_patient)

        results = get_created_patient_count(product_name="GDM")
        expected: List[Dict] = [
            {"date": "2019-10-16", "count": 1},
            {"date": "2020-10-16", "count": 1},
            {"date": "2021-10-16", "count": 1},
            {"date": "2022-03-16", "count": 1},
            {"date": "2022-05-16", "count": 1},
        ]
        assert results == expected
