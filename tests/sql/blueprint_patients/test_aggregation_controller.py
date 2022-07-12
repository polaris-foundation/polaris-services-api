from typing import Any, Callable, Dict, List, Type, Union

import pytest

from dhos_services_api.blueprint_patients import aggregation_controller
from dhos_services_api.models.api_spec import PatientResponse
from dhos_services_api.sqlmodels.patient import query_options_full_patient_response
from tests.conftest import sanitize_json

LIMIT_FULL_PATIENT_RESPONSE = len(query_options_full_patient_response())


@pytest.mark.usefixtures("app", "uses_sql_database")
class TestAggregationController:
    def test_get_aggregated_patients(
        self,
        patient_with_delivery_uuid: str,
        gdm_location_uuid: str,
        jwt_system: str,
        any_date: Any,
        any_datetime: Any,
        any_uuid: Any,
        gdm_clinician: str,
        assert_valid_schema: Callable[[Type, Union[Dict, List], bool], None],
        statement_counter: Callable,
    ) -> None:
        ignored = {
            "created",
            "created_by",
            "modified",
            "modified_by",
            "uuid",
        }
        expected: List[Dict] = [
            {
                "accessibility_considerations": [],
                "accessibility_considerations_other": None,
                "allowed_to_email": True,
                "allowed_to_text": True,
                "bookmarked": False,
                "dh_products": [
                    {
                        "accessibility_discussed": True,
                        "accessibility_discussed_date": any_date,
                        "accessibility_discussed_with": any_uuid,
                        "changes": [],
                        "closed_date": None,
                        "closed_reason": None,
                        "closed_reason_other": None,
                        "opened_date": any_date,
                        "product_name": "GDM",
                        "monitored_by_clinician": True,
                    }
                ],
                "dob": any_date,
                "dod": None,
                "email_address": "Carol.patient@mail.com",
                "ethnicity": None,
                "ethnicity_other": None,
                "first_name": "Carol",
                "has_been_bookmarked": False,
                "highest_education_level": None,
                "highest_education_level_other": None,
                "hospital_number": "435y9999",
                "last_name": "Patient",
                "locations": [gdm_location_uuid],
                "nhs_number": None,
                "other_notes": None,
                "fhir_resource_id": None,
                "personal_addresses": [
                    {
                        "address_line_1": "42 Some Street",
                        "address_line_2": "",
                        "address_line_3": "",
                        "address_line_4": "",
                        "country": "England",
                        "lived_from": any_date,
                        "lived_until": any_date,
                        "locality": "Oxford",
                        "postcode": "OX3 5TF",
                        "region": "Oxfordshire",
                    }
                ],
                "phone_number": "07594203248",
                "record": {
                    "diagnoses": [
                        {
                            "diagnosed": any_date,
                            "diagnosis_other": "Some diagnosis with no snomed " "code",
                            "diagnosis_tool": ["1234567890"],
                            "diagnosis_tool_other": "some tool",
                            "episode": 1,
                            "management_plan": {
                                "actions": [{"action_sct_code": "12345"}],
                                "dose_history": [
                                    {
                                        "action": "insert",
                                        "clinician_uuid": "dhos-robot",
                                        "dose": {
                                            "changes": [],
                                            "dose_amount": 1.5,
                                            "medication_id": "99b1668c-26f1-4aec-88ca-597d3a20d977",
                                            "routine_sct_code": "12345",
                                        },
                                    }
                                ],
                                "doses": [
                                    {
                                        "changes": [],
                                        "dose_amount": 1.5,
                                        "medication_id": "99b1668c-26f1-4aec-88ca-597d3a20d977",
                                        "routine_sct_code": "12345",
                                    }
                                ],
                                "end_date": any_date,
                                "plan_history": [],
                                "sct_code": "386359008",
                                "start_date": any_date,
                            },
                            "observable_entities": [
                                {
                                    "date_observed": any_date,
                                    "sct_code": "123456789",
                                    "value_as_string": "A value",
                                    "metadata": {},
                                },
                            ],
                            "presented": any_date,
                            "readings_plan": {
                                "changes": [
                                    {
                                        "days_per_week_to_take_readings": 7,
                                        "readings_per_day": 4,
                                    }
                                ],
                                "days_per_week_to_take_readings": 7,
                                "end_date": any_date,
                                "readings_per_day": 4,
                                "sct_code": "33747003",
                                "start_date": any_date,
                            },
                            "resolved": None,
                            "risk_factors": ["1234567890"],
                            "sct_code": "1234567890",
                        },
                        {
                            "diagnosed": any_date,
                            "diagnosis_other": None,
                            "diagnosis_tool": [],
                            "diagnosis_tool_other": None,
                            "episode": None,
                            "management_plan": {
                                "actions": [],
                                "dose_history": [],
                                "doses": [],
                                "end_date": any_date,
                                "plan_history": [],
                                "sct_code": "D0000007",
                                "start_date": any_date,
                            },
                            "observable_entities": [],
                            "presented": None,
                            "readings_plan": {
                                "changes": [
                                    {
                                        "days_per_week_to_take_readings": 4,
                                        "readings_per_day": 4,
                                    }
                                ],
                                "days_per_week_to_take_readings": 4,
                                "end_date": any_date,
                                "readings_per_day": 4,
                                "sct_code": "33747003",
                                "start_date": any_date,
                            },
                            "resolved": None,
                            "risk_factors": [],
                            "sct_code": "11687002",
                        },
                    ],
                    "history": {"gravidity": 1, "parity": 1},
                    "notes": [
                        {
                            "clinician_uuid": gdm_clinician,
                            "content": "Will need to monitor patient closely",
                        }
                    ],
                    "pregnancies": [
                        {
                            "colostrum_harvesting": None,
                            "deliveries": [
                                {
                                    "admitted_to_special_baby_care_unit": None,
                                    "apgar_1_minute": None,
                                    "apgar_5_minute": None,
                                    "birth_outcome": None,
                                    "birth_weight_in_grams": None,
                                    "date_of_termination": None,
                                    "feeding_method": None,
                                    "length_of_postnatal_stay_for_baby": None,
                                    "neonatal_complications": ["123456", "123456"],
                                    "neonatal_complications_other": None,
                                    "outcome_for_baby": None,
                                    "patient": {
                                        "dob": None,
                                        "first_name": "Paul",
                                        "last_name": "Smith",
                                        "phone_number": None,
                                        "sex": None,
                                    },
                                }
                            ],
                            "delivery_place": None,
                            "delivery_place_other": None,
                            "estimated_delivery_date": any_date,
                            "expected_number_of_babies": None,
                            "first_medication_taken": None,
                            "first_medication_taken_recorded": None,
                            "height_at_booking_in_mm": 1230,
                            "induced": True,
                            "length_of_postnatal_stay_in_days": 2,
                            "planned_delivery_place": None,
                            "pregnancy_complications": [],
                            "weight_at_36_weeks_in_g": None,
                            "weight_at_booking_in_g": 78000,
                            "weight_at_diagnosis_in_g": None,
                        }
                    ],
                    "visits": [
                        {
                            "clinician_uuid": gdm_clinician,
                            "diagnoses": [],
                            "location": any_uuid,
                            "summary": "Talked about GDM",
                            "visit_date": any_datetime,
                        }
                    ],
                },
                "sex": "248152002",
                "height_in_mm": None,
                "weight_in_g": None,
                "terms_agreement": None,
            }
        ]

        with statement_counter(limit=LIMIT_FULL_PATIENT_RESPONSE):
            patients = aggregation_controller.get_aggregated_patients(
                gdm_location_uuid, "GDM", active=None
            )
        assert_valid_schema(PatientResponse, patients, True)
        patients = sanitize_json(patients, ignored=ignored)
        assert expected == patients
