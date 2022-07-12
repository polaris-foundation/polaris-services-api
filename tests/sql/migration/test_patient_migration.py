from __future__ import annotations

import itertools
import json
from datetime import datetime
from typing import Callable

import pytest
from flask import Flask
from flask.testing import FlaskCliRunner
from flask_sqlalchemy import SQLAlchemy
from neomodel import db as neo_db
from sqlalchemy import select

from dhos_services_api import models, sqlmodels
from dhos_services_api.blueprint_patients import (
    patient_controller,
    patient_controller_neo,
)


@pytest.mark.usefixtures("clean_up_neo4j_after_test", "uses_sql_database")
class TestPatientMigration:
    @pytest.fixture
    def runner(self, app: Flask) -> FlaskCliRunner:
        return app.test_cli_runner()

    def test_nothing_to_migrate(
        self,
        runner: FlaskCliRunner,
    ) -> None:
        result = runner.invoke(args=["migrate", "patients"])
        assert "Nothing to migrate" in result.output

    @pytest.fixture
    def neo_patient_factory(
        self, app: Flask, location_uuid: str, clinician: str
    ) -> Callable:
        from dhos_services_api.models.patient import Patient

        counter = itertools.count()

        def make_patient(
            first_name: str,
            product: str = "SEND",
            last_name: str = "Patient",
            nhs_number: str | None = None,
            hospital_number: str | None = None,
            location_uuid: str = location_uuid,
            opened_date: str = "2018-06-22",
            diagnosis_code: str = "11687002",
        ) -> str:
            email_address = f"{first_name}.patient@mail.com"

            patient = {
                "allowed_to_text": True,
                "allowed_to_email": True,
                "first_name": first_name.title(),
                "last_name": last_name,
                "phone_number": "07594203248",
                "dob": "1957-06-9",
                "hospital_number": hospital_number or str(f"MRN{next(counter)}"),
                "nhs_number": nhs_number or str(111_000_000 + next(counter)),
                "email_address": email_address,
                "dh_products": [
                    {
                        "product_name": product,
                        "opened_date": opened_date,
                        "accessibility_discussed": True,
                        "accessibility_discussed_with": clinician,
                        "accessibility_discussed_date": opened_date,
                    }
                ],
                "personal_addresses": [
                    {
                        "address_line_1": "42 Some Street",
                        "address_line_2": "",
                        "address_line_3": "",
                        "address_line_4": "",
                        "locality": "Oxford",
                        "region": "Oxfordshire",
                        "postcode": "OX3 5TF",
                        "country": "England",
                        "lived_from": "1970-01-01",
                        "lived_until": "1970-01-01",
                    }
                ],
                "ethnicity": "13233008",
                "sex": "248152002",
                "height_in_mm": 1555,
                "weight_in_g": 737,
                "highest_education_level": "473461003",
                "accessibility_considerations": [],
                "other_notes": "",
                "record": {
                    "notes": [
                        {
                            "content": "This is a note",
                            "clinician_uuid": "some-clinician",
                        }
                    ],
                    "history": {"gravidity": 1, "parity": 1},
                    "pregnancies": [
                        {
                            "estimated_delivery_date": datetime.today().strftime(
                                "%Y-%m-%d"
                            ),
                            "planned_delivery_place": "99b1668c-26f1-4aec-88ca-597d3a20d977",
                            "length_of_postnatal_stay_in_days": 2,
                            "colostrum_harvesting": True,
                            "expected_number_of_babies": 1,
                            "deliveries": [
                                {
                                    "birth_outcome": "123456",
                                    "outcome_for_baby": "234567",
                                    "neonatal_complications": ["123456"],
                                    "neonatal_complications_other": "123456",
                                    "admitted_to_special_baby_care_unit": False,
                                    "birth_weight_in_grams": 1000,
                                    "length_of_postnatal_stay_for_baby": 2,
                                    "apgar_1_minute": 123,
                                    "apgar_5_minute": 321,
                                    "feeding_method": "132",
                                    "patient": {
                                        "first_name": "baby",
                                        "last_name": last_name,
                                    },
                                }
                            ],
                            "height_at_booking_in_mm": 2000,
                            "weight_at_diagnosis_in_g": 10000,
                            "weight_at_booking_in_g": 10000,
                            "weight_at_36_weeks_in_g": 10000,
                        }
                    ],
                    "diagnoses": [
                        {
                            "sct_code": diagnosis_code,
                            "diagnosed": "2018-06-22",
                            "episode": 1,
                            "presented": "1970-01-01",
                            "diagnosis_tool": ["1234567890"],
                            "diagnosis_tool_other": "1234567890",
                            "risk_factors": ["1234567890"],
                            "observable_entities": [
                                {
                                    "sct_code": "123456789",
                                    "date_observed": "1970-01-01",
                                    "value_as_string": "A value",
                                }
                            ],
                            "management_plan": {
                                "start_date": "2018-06-22",
                                "end_date": "2018-9-11",
                                "sct_code": "D0000007",
                                "doses": [
                                    {
                                        "medication_id": "99b1668c-26f1-4aec-88ca-597d3a20d977",
                                        "dose_amount": 1.5,
                                        "routine_sct_code": "12345",
                                    },
                                ],
                                "actions": [{"action_sct_code": "12345"}],
                            },
                            "readings_plan": {
                                "sct_code": "33747003",
                                "start_date": "2018-06-22",
                                "end_date": "2018-9-11",
                                "days_per_week_to_take_readings": 4,
                                "readings_per_day": 4,
                            },
                        }
                    ],
                    "visits": [
                        {
                            "clinician_uuid": clinician,
                            "diagnoses": [],
                            "location": location_uuid,
                            "summary": "a summary of the visit",
                            "visit_date": "2018-04-11T14:52:06.643Z",
                        }
                    ],
                },
                "locations": [location_uuid],
            }
            cls = models.SendPatient if product == "SEND" else models.Patient
            p: Patient = cls.new(**patient)
            p.save()
            return p.uuid

        return make_patient

    @pytest.fixture
    def bulk_patient_data(self, app: Flask, neo_patient_factory: Callable) -> None:
        with app.app_context():
            for i in range(42):
                neo_patient_factory(
                    first_name=f"first-name-{i}", last_name=f"last-name-{i}"
                )

    def test_migration(
        self,
        runner: FlaskCliRunner,
        bulk_patient_data: None,
        _db: SQLAlchemy,
    ) -> None:
        # Arrange

        # Act
        result = runner.invoke(args=["migrate", "patients"])

        # Assert
        assert result.exit_code == 0

        neo_result, meta = neo_db.cypher_query("""MATCH (n:Record) RETURN n.uuid""")
        neo_records = {uuid for (uuid,) in neo_result}
        sql_records = set(_db.session.scalars(select(sqlmodels.Record.uuid)).all())
        assert neo_records == sql_records
        # Babies have records too so twice as many records as we thought.
        assert len(sql_records) == 84

        assert "Bulk uploading 84 Records" in result.output
        assert "Created 84 new Records" in result.output
        assert "Bulk uploading 42 Management Plans" in result.output
        assert "Created 42 new Management Plans" in result.output
        assert "Migration completed" in result.output

        # Running migration a second time does nothing
        result = runner.invoke(args=["migrate", "patients"])
        assert result.exit_code == 0
        assert "Nothing to migrate" in result.output

    @pytest.fixture
    def migrated_neo_sql_patient(
        self, runner: FlaskCliRunner, neo_patient_factory: Callable
    ) -> str:
        patient_id = neo_patient_factory(
            first_name="Jemima", last_name="Puddleduck", product="GDM"
        )

        result = runner.invoke(args=["migrate", "patients"])
        assert result.exit_code == 0

        return patient_id

    def test_new_matches_old_get_patient(
        self, app: Flask, migrated_neo_sql_patient: str
    ) -> None:
        neo_patient = patient_controller_neo.get_patient(
            migrated_neo_sql_patient, product_name="GDM"
        )
        neo_serialised = json.loads(json.dumps(neo_patient, cls=app.json_encoder))

        sql_patient = patient_controller.get_patient(
            migrated_neo_sql_patient, product_name="GDM"
        )
        sql_serialised = json.loads(json.dumps(sql_patient, cls=app.json_encoder))

        assert neo_serialised == sql_serialised

    @pytest.mark.parametrize("compact", [True, False])
    def test_new_matches_old_retrieve_patients_by_uuids(
        self, app: Flask, migrated_neo_sql_patient: str, compact: bool
    ) -> None:
        neo_patients = patient_controller_neo.retrieve_patients_by_uuids(
            [migrated_neo_sql_patient], product_name="GDM", compact=compact
        )
        neo_serialised = json.loads(json.dumps(neo_patients, cls=app.json_encoder))

        sql_patients = patient_controller.retrieve_patients_by_uuids(
            [migrated_neo_sql_patient], product_name="GDM", compact=compact
        )
        sql_serialised: list[dict] = json.loads(
            json.dumps(sql_patients, cls=app.json_encoder)
        )

        if compact:
            # NEO response has a 'management_plan' field but it always contains None
            # SQL returns a compact management_plan (dates and sct_code only) so just ignore it.
            sql_serialised[0]["record"]["diagnoses"][0]["management_plan"] = None

        assert neo_serialised == sql_serialised

    @pytest.mark.parametrize("compact", [True, False])
    def test_new_matches_old_get_patient_by_record_uuid(
        self, app: Flask, migrated_neo_sql_patient: str, compact: bool
    ) -> None:
        record_id = patient_controller.get_patient(
            migrated_neo_sql_patient, product_name="GDM"
        )["record"]["uuid"]

        neo_patients = patient_controller_neo.get_patient_by_record_uuid(
            record_id, compact=compact
        )
        neo_serialised = json.loads(json.dumps(neo_patients, cls=app.json_encoder))

        sql_patients = patient_controller.get_patient_by_record_uuid(
            record_id, compact=compact
        )
        sql_serialised: dict = json.loads(
            json.dumps(sql_patients, cls=app.json_encoder)
        )

        if compact:
            # NEO response has a 'management_plan' field but it always contains None
            # SQL returns a compact management_plan (dates and sct_code only) so just ignore it.
            sql_serialised["record"]["diagnoses"][0]["management_plan"] = None

        assert neo_serialised == sql_serialised

    @pytest.mark.parametrize("expanded", [True, False])
    def test_new_matches_old_search_patients(
        self,
        app: Flask,
        migrated_neo_sql_patient: str,
        expanded: bool,
        location_uuid: str,
    ) -> None:
        neo_patients = patient_controller_neo.search_patients(
            locations=[location_uuid],
            search_text="Puddleduck",
            product_name="GDM",
            expanded=expanded,
        )
        neo_serialised = json.loads(json.dumps(neo_patients, cls=app.json_encoder))

        sql_patients = patient_controller.search_patients(
            locations=[location_uuid],
            search_text="Puddleduck",
            product_name="GDM",
            expanded=expanded,
        )
        sql_serialised: list[dict] = json.loads(
            json.dumps(sql_patients, cls=app.json_encoder)
        )

        if expanded:
            # Neo code returns bookmarked: None
            assert (
                bool(neo_serialised[0]["bookmarked"]) == sql_serialised[0]["bookmarked"]
            )
            sql_serialised[0]["bookmarked"] = neo_serialised[0]["bookmarked"]

            # SQL code returns an empty list here because returning None breaks the
            # marshmallow validation in other tests.
            assert neo_serialised[0]["personal_addresses"] is None
            assert sql_serialised[0]["personal_addresses"] == []
            sql_serialised[0]["personal_addresses"] = None

        assert neo_serialised == sql_serialised
