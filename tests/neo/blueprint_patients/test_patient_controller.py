import json
from typing import Any, Callable, Dict, List, Optional

import pytest
from flask_batteries_included.helpers.error_handler import EntityNotFoundException
from marshmallow import RAISE
from mock import Mock
from neomodel import db
from pytest_mock import MockerFixture

from dhos_services_api.blueprint_patients import patient_controller_neo
from dhos_services_api.helpers import audit
from dhos_services_api.models.api_spec import (
    AbbreviatedPatientResponse,
    PatientResponse,
    PatientTermsResponse,
    PatientTermsResponseV2,
)
from tests.conftest import remove_dates


@pytest.mark.usefixtures("app", "neo4j_clear_database")
class TestPatientController:
    @pytest.fixture(autouse=True)
    def mock_audit_record_patient_viewed(self, mocker: MockerFixture) -> Mock:
        return mocker.patch.object(audit, "record_patient_viewed")

    @pytest.fixture(autouse=True)
    def mock_audit_record_patient_updated(self, mocker: MockerFixture) -> Mock:
        return mocker.patch.object(audit, "record_patient_updated")

    @pytest.fixture(autouse=True)
    def mock_audit_record_patient_diabetes_type_changed(
        self, mocker: MockerFixture
    ) -> Mock:
        return mocker.patch.object(audit, "record_patient_diabetes_type_changed")

    @pytest.fixture(autouse=True)
    def mock_audit_record_patient_archived(self, mocker: MockerFixture) -> Mock:
        return mocker.patch.object(audit, "record_patient_archived")

    @pytest.fixture
    def _patient_with_delivery_uuid(
        self,
        gdm_patient_uuid: str,
        mock_audit_record_patient_viewed: MockerFixture,
        mock_audit_record_patient_updated: MockerFixture,
        diabetes_patient_product: str,
    ) -> str:
        patient = patient_controller_neo.get_patient(
            patient_uuid=gdm_patient_uuid, product_name=diabetes_patient_product
        )
        pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
        update_data = {
            "record": {
                "pregnancies": [
                    {
                        "uuid": pregnancy_id,
                        "height_at_booking_in_mm": 1230,
                        "weight_at_booking_in_g": 78000,
                        "length_of_postnatal_stay_in_days": 2,
                        "induced": True,
                        "deliveries": [
                            {
                                "neonatal_complications": [],
                                "patient": {"first_name": "Paul", "last_name": "Smith"},
                            }
                        ],
                    }
                ]
            }
        }
        patient = patient_controller_neo.update_patient(
            patient_uuid=gdm_patient_uuid, patient_details=update_data
        )
        return patient["uuid"]

    @pytest.fixture
    def _search_responses(self, diabetes_patient_product: str) -> Dict[str, Dict]:
        return {
            "P1": {
                "bookmarked": False,
                "dh_products": [
                    {
                        "closed_date": None,
                        "closed_reason": None,
                        "closed_reason_other": None,
                        "product_name": diabetes_patient_product,
                        "uuid": "DH1",
                        "monitored_by_clinician": True,
                    }
                ],
                "dob": None,
                "first_name": "Jane",
                "hospital_number": "MRN1",
                "last_name": "Grey Dudley",
                "locations": ["L1"],
                "nhs_number": "8888888888",
                "record": {
                    "diagnoses": [
                        {
                            "diagnosed": None,
                            "management_plan": {
                                "end_date": "2020-01-01",
                                "sct_code": "67866001",
                                "start_date": "2019-08-26",
                            },
                            "sct_code": "11687002",
                            "uuid": "DG1",
                        }
                    ],
                    "pregnancies": [],
                    "uuid": "R1",
                },
                "sex": None,
                "uuid": "P1",
                "fhir_resource_id": None,
            },
            "P4": {
                "bookmarked": False,
                "dh_products": [
                    {
                        "closed_date": None,
                        "closed_reason": None,
                        "closed_reason_other": None,
                        "product_name": diabetes_patient_product,
                        "uuid": "DH4",
                        "monitored_by_clinician": True,
                    }
                ],
                "dob": None,
                "first_name": "Jane Grey",
                "hospital_number": "9998887771",
                "last_name": "Dudley",
                "locations": ["L4"],
                "nhs_number": None,
                "record": {
                    "diagnoses": [
                        {
                            "diagnosed": None,
                            "management_plan": None,
                            "sct_code": "11687002",
                            "uuid": "DG4",
                        }
                    ],
                    "pregnancies": [
                        {
                            "deliveries": [],
                            "estimated_delivery_date": "2020-06-04",
                            "uuid": "Pr1",
                        }
                    ],
                    "uuid": "R4",
                },
                "sex": None,
                "uuid": "P4",
                "fhir_resource_id": None,
            },
            "P5": {
                "bookmarked": False,
                "dh_products": [
                    {
                        "closed_date": "2020-01-01",
                        "closed_reason": None,
                        "closed_reason_other": None,
                        "product_name": diabetes_patient_product,
                        "uuid": "DH5",
                        "monitored_by_clinician": False,
                    }
                ],
                "dob": None,
                "first_name": None,
                "hospital_number": None,
                "last_name": None,
                "locations": ["L5"],
                "nhs_number": None,
                "record": {"diagnoses": [], "pregnancies": [], "uuid": "R5"},
                "sex": None,
                "uuid": "P5",
                "fhir_resource_id": None,
            },
            "P6": {
                "accessibility_considerations": [],
                "accessibility_considerations_other": None,
                "allowed_to_email": None,
                "allowed_to_text": None,
                "bookmarked": None,
                "created_by": "unknown",
                "dh_products": [
                    {
                        "closed_date": None,
                        "closed_reason": None,
                        "closed_reason_other": None,
                        "created_by": "unknown",
                        "modified_by": "unknown",
                        "product_name": "SEND",
                        "uuid": "DH1S",
                        "monitored_by_clinician": True,
                    }
                ],
                "dob": None,
                "dod": None,
                "email_address": None,
                "ethnicity": None,
                "ethnicity_other": None,
                "first_name": "Jane",
                "has_been_bookmarked": False,
                "height_in_mm": None,
                "highest_education_level": None,
                "highest_education_level_other": None,
                "hospital_number": "MRN6",
                "last_name": "Grey Dudley",
                "locations": ["L1"],
                "modified_by": "unknown",
                "nhs_number": "8888888888",
                "other_notes": None,
                "personal_addresses": None,
                "phone_number": None,
                "record": {
                    "created_by": "unknown",
                    "diagnoses": [],
                    "history": None,
                    "modified_by": "unknown",
                    "notes": [],
                    "pregnancies": [],
                    "uuid": "R6",
                    "visits": [],
                },
                "sex": None,
                "terms_agreement": None,
                "uuid": "P6",
                "weight_in_g": None,
                "fhir_resource_id": None,
            },
        }

    @pytest.fixture
    def patient_search_response(
        self, request: Any, _search_responses: Dict[str, Dict]
    ) -> List[Dict]:
        return [_search_responses[p] for p in request.param]

    def test_get_patient_fail(self) -> None:
        with pytest.raises(EntityNotFoundException):
            patient_controller_neo.get_patient(patient_uuid="123", product_name="SEND")

    @pytest.mark.parametrize(
        "product_name",
        ["SEND", None],
    )
    def test_get_patient(
        self,
        patient_uuid: str,
        product_name: Optional[str],
        mock_audit_record_patient_viewed: Mock,
    ) -> None:

        patient_data = patient_controller_neo.get_patient(
            patient_uuid=patient_uuid, product_name=product_name
        )
        assert mock_audit_record_patient_viewed.called
        assert patient_data["first_name"] == "Carol"
        PatientResponse().load(patient_data, unknown=RAISE)

    def test_retrieve_patient_by_uuids(self, four_patient_uuids: List[str]) -> None:
        patient_data: List[Dict] = patient_controller_neo.retrieve_patients_by_uuids(
            patient_uuids=four_patient_uuids, product_name="SEND", compact=False
        )
        assert len(patient_data) == 4
        PatientResponse().load(patient_data, many=True, unknown=RAISE)

    def test_retrieve_patient_by_uuids_fail_no_gdm_patients(
        self,
        four_patient_uuids: List[str],
        diabetes_patient_product: str,
    ) -> None:
        with pytest.raises(EntityNotFoundException):
            patient_controller_neo.retrieve_patients_by_uuids(
                patient_uuids=four_patient_uuids,
                product_name=diabetes_patient_product,
                compact=False,
            )

    def test_get_patient_abbreviated(self, patient_uuid: str) -> None:
        patient_data = patient_controller_neo.get_patient_abbreviated(
            patient_uuid=patient_uuid
        )
        assert patient_data["uuid"] == patient_uuid
        AbbreviatedPatientResponse().load(patient_data, unknown=RAISE)

    def test_get_patient_by_record_uuid_not_compact(
        self, patient_record_uuid: str
    ) -> None:
        patient_data = patient_controller_neo.get_patient_by_record_uuid(
            record_id=patient_record_uuid, compact=False
        )
        assert patient_data["first_name"] == "Carol"
        PatientResponse().load(patient_data, unknown=RAISE)

    def test_get_patient_by_record_uuid_compact(self, patient_record_uuid: str) -> None:
        patient_data = patient_controller_neo.get_patient_by_record_uuid(
            record_id=patient_record_uuid, compact=True
        )
        assert patient_data["first_name"] == "Carol"
        assert "terms_agreement" not in patient_data

    def test_get_patient_by_record_uuid_compact_fail_no_matching_record(self) -> None:
        with pytest.raises(EntityNotFoundException):
            patient_controller_neo.get_patient_by_record_uuid(
                record_id="123", compact=True
            )

    @pytest.mark.parametrize(
        "product_name",
        ["GDM", "SEND", "NEW-PRODUCT", "DBM"],
    )
    def test_create_patient(
        self, product_name: str, location_uuid: str, clinician: str
    ) -> None:
        patient_one = {
            "accessibility_considerations": [],
            "allowed_to_text": True,
            "dh_products": [
                {
                    "accessibility_discussed": True,
                    "accessibility_discussed_date": "2019-04-29",
                    "accessibility_discussed_with": clinician,
                    "opened_date": "2019-04-29",
                    "product_name": product_name,
                }
            ],
            "dob": "1992-04-23",
            "email_address": "dolly@email.com",
            "ethnicity": "185988007",
            "first_name": "Diane",
            "highest_education_level": "426769009",
            "hospital_number": "147777799",
            "last_name": "Smith",
            "locations": [location_uuid],
            "nhs_number": "7777777777",
            "other_notes": "",
            "personal_addresses": [
                {
                    "address_line_1": "School House Stony Bridge Park",
                    "address_line_2": "",
                    "address_line_3": "",
                    "address_line_4": "",
                    "lived_from": "2013-12-31",
                    "locality": "Oxford",
                    "postcode": "OX5 3NA",
                    "region": "Oxfordshire",
                }
            ],
            "phone_number": "07123456789",
            "record": {},
            "sex": "248152002",
            "height_in_mm": 1666,
            "weight_in_g": 688,
        }

        created_patient = patient_controller_neo.create_patient(
            product_name=product_name, patient_details=patient_one
        )
        assert created_patient["first_name"] == "Diane"
        assert created_patient["height_in_mm"] == 1666
        PatientResponse().load(created_patient, unknown=RAISE)

    @pytest.mark.parametrize("new_dpwttr", [5, 0])
    def test_update_patient(
        self,
        patient_uuid: str,
        diagnosis_uuid: str,
        mock_audit_record_patient_updated: Mock,
        new_dpwttr: int,
    ) -> None:
        fhir_resource_id = "some uuid"
        update_data = {
            "first_name": "Trudie",
            "record": {
                "diagnoses": [
                    {
                        "uuid": diagnosis_uuid,
                        "readings_plan": {"days_per_week_to_take_readings": new_dpwttr},
                    }
                ]
            },
            "fhir_resource_id": fhir_resource_id,
        }
        updated_patient = patient_controller_neo.update_patient(
            patient_uuid=patient_uuid, patient_details=update_data
        )
        assert updated_patient["first_name"] == "Trudie"
        assert (
            updated_patient["record"]["diagnoses"][0]["readings_plan"][
                "days_per_week_to_take_readings"
            ]
            == new_dpwttr
        )
        assert mock_audit_record_patient_updated.called
        assert updated_patient["fhir_resource_id"] == fhir_resource_id
        PatientResponse().load(updated_patient, unknown=RAISE)

    @pytest.mark.parametrize("field", ["phone_number", "nhs_number"])
    def test_remove_from_patient(
        self, patient_uuid: str, mock_audit_record_patient_updated: Mock, field: str
    ) -> None:
        data_to_remove = {field: None}
        patient_data = patient_controller_neo.update_patient(
            patient_uuid=patient_uuid, patient_details=data_to_remove
        )
        assert patient_data[field] is None
        assert mock_audit_record_patient_updated.called

    def test_close_patient_fail_no_height_at_booking_in_mm(
        self, gdm_patient_uuid: str, diabetes_patient_product: str
    ) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=gdm_patient_uuid, product_name=diabetes_patient_product
        )
        with pytest.raises(KeyError):
            patient_controller_neo.close_patient(
                patient_uuid=patient["uuid"],
                product_uuid=patient["dh_products"][0]["uuid"],
                patient_details=closing_data,
            )

    def test_close_patient_fail_not_gdm(self, patient_uuid: str) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=patient_uuid, product_name="SEND"
        )
        with pytest.raises(ValueError) as e:
            patient_controller_neo.close_patient(
                patient_uuid=patient["uuid"],
                product_uuid=patient["dh_products"][0]["uuid"],
                patient_details=closing_data,
            )
        assert str(e.value) == "You cannot close SEND patients"

    def test_close_patient_fail_no_weight_at_booking_in_g(
        self, gdm_patient_uuid: str, diabetes_patient_product: str
    ) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=gdm_patient_uuid, product_name=diabetes_patient_product
        )
        pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
        update_data = {
            "record": {
                "pregnancies": [{"uuid": pregnancy_id, "height_at_booking_in_mm": 1230}]
            }
        }
        patient_controller_neo.update_patient(
            patient_uuid=gdm_patient_uuid, patient_details=update_data
        )

        with pytest.raises(KeyError):
            patient_controller_neo.close_patient(
                patient_uuid=patient["uuid"],
                product_uuid=patient["dh_products"][0]["uuid"],
                patient_details=closing_data,
            )

    def test_close_patient_fail_no_length_of_postnatal_stay_in_days(
        self, gdm_patient_uuid: str, diabetes_patient_product: str
    ) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=gdm_patient_uuid, product_name=diabetes_patient_product
        )
        pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
        update_data = {
            "record": {
                "pregnancies": [
                    {
                        "uuid": pregnancy_id,
                        "height_at_booking_in_mm": 1230,
                        "weight_at_booking_in_g": 78000,
                    }
                ]
            }
        }
        patient_controller_neo.update_patient(
            patient_uuid=gdm_patient_uuid, patient_details=update_data
        )

        with pytest.raises(KeyError):
            patient_controller_neo.close_patient(
                patient_uuid=patient["uuid"],
                product_uuid=patient["dh_products"][0]["uuid"],
                patient_details=closing_data,
            )

    def test_close_patient_fail_no_induced(
        self, gdm_patient_uuid: str, diabetes_patient_product: str
    ) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=gdm_patient_uuid, product_name=diabetes_patient_product
        )
        pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
        update_data = {
            "record": {
                "pregnancies": [
                    {
                        "uuid": pregnancy_id,
                        "height_at_booking_in_mm": 1230,
                        "weight_at_booking_in_g": 78000,
                        "length_of_postnatal_stay_in_days": 2,
                    }
                ]
            }
        }
        patient_controller_neo.update_patient(
            patient_uuid=gdm_patient_uuid, patient_details=update_data
        )

        with pytest.raises(KeyError):
            patient_controller_neo.close_patient(
                patient_uuid=patient["uuid"],
                product_uuid=patient["dh_products"][0]["uuid"],
                patient_details=closing_data,
            )

    def test_close_patient_fail_no_birth_weight_in_grams(
        self, _patient_with_delivery_uuid: str, diabetes_patient_product: str
    ) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=_patient_with_delivery_uuid,
            product_name=diabetes_patient_product,
        )
        with pytest.raises(KeyError):
            patient_controller_neo.close_patient(
                patient_uuid=patient["uuid"],
                product_uuid=patient["dh_products"][0]["uuid"],
                patient_details=closing_data,
            )

    def test_close_patient_fail_no_birth_outcome(
        self, _patient_with_delivery_uuid: str, diabetes_patient_product: str
    ) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=_patient_with_delivery_uuid,
            product_name=diabetes_patient_product,
        )
        pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
        delivery_id = patient["record"]["pregnancies"][0]["deliveries"][0]["uuid"]
        update_data = {
            "record": {
                "pregnancies": [
                    {
                        "uuid": pregnancy_id,
                        "deliveries": [
                            {"uuid": delivery_id, "birth_weight_in_grams": 2300}
                        ],
                    }
                ]
            }
        }
        patient_controller_neo.update_patient(
            patient_uuid=_patient_with_delivery_uuid, patient_details=update_data
        )

        with pytest.raises(KeyError):
            patient_controller_neo.close_patient(
                patient_uuid=patient["uuid"],
                product_uuid=patient["dh_products"][0]["uuid"],
                patient_details=closing_data,
            )

    def test_close_patient_fail_no_outcome_for_baby(
        self, _patient_with_delivery_uuid: str, diabetes_patient_product: str
    ) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=_patient_with_delivery_uuid,
            product_name=diabetes_patient_product,
        )
        pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
        delivery_id = patient["record"]["pregnancies"][0]["deliveries"][0]["uuid"]
        update_data = {
            "record": {
                "pregnancies": [
                    {
                        "uuid": pregnancy_id,
                        "deliveries": [
                            {
                                "uuid": delivery_id,
                                "birth_weight_in_grams": 2300,
                                "birth_outcome": "45718005",
                            }
                        ],
                    }
                ]
            }
        }
        patient_controller_neo.update_patient(
            patient_uuid=_patient_with_delivery_uuid, patient_details=update_data
        )

        with pytest.raises(KeyError):
            patient_controller_neo.close_patient(
                patient_uuid=patient["uuid"],
                product_uuid=patient["dh_products"][0]["uuid"],
                patient_details=closing_data,
            )

    def test_close_patient_fail_no_neonatal_complications(
        self, _patient_with_delivery_uuid: str, diabetes_patient_product: str
    ) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=_patient_with_delivery_uuid,
            product_name=diabetes_patient_product,
        )
        pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
        delivery_id = patient["record"]["pregnancies"][0]["deliveries"][0]["uuid"]
        update_data = {
            "record": {
                "pregnancies": [
                    {
                        "uuid": pregnancy_id,
                        "deliveries": [
                            {
                                "uuid": delivery_id,
                                "birth_weight_in_grams": 2300,
                                "birth_outcome": "45718005",
                                "outcome_for_baby": "169826009",
                            }
                        ],
                    }
                ]
            }
        }
        patient_controller_neo.update_patient(
            patient_uuid=_patient_with_delivery_uuid, patient_details=update_data
        )

        with pytest.raises(KeyError):
            patient_controller_neo.close_patient(
                patient_uuid=patient["uuid"],
                product_uuid=patient["dh_products"][0]["uuid"],
                patient_details=closing_data,
            )

    def test_close_patient_fail_no_admitted_to_special_baby_care_unit(
        self, _patient_with_delivery_uuid: str, diabetes_patient_product: str
    ) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=_patient_with_delivery_uuid,
            product_name=diabetes_patient_product,
        )
        pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
        delivery_id = patient["record"]["pregnancies"][0]["deliveries"][0]["uuid"]
        update_data = {
            "record": {
                "pregnancies": [
                    {
                        "uuid": pregnancy_id,
                        "deliveries": [
                            {
                                "uuid": delivery_id,
                                "birth_weight_in_grams": 2300,
                                "birth_outcome": "45718005",
                                "outcome_for_baby": "169826009",
                                "neonatal_complications": ["shoulderDystocia"],
                            }
                        ],
                    }
                ]
            }
        }
        patient_controller_neo.update_patient(
            patient_uuid=_patient_with_delivery_uuid, patient_details=update_data
        )

        with pytest.raises(KeyError):
            patient_controller_neo.close_patient(
                patient_uuid=patient["uuid"],
                product_uuid=patient["dh_products"][0]["uuid"],
                patient_details=closing_data,
            )

    def test_close_patient_fail_no_length_of_postnatal_stay_for_baby(
        self, _patient_with_delivery_uuid: str, diabetes_patient_product: str
    ) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=_patient_with_delivery_uuid,
            product_name=diabetes_patient_product,
        )
        pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
        delivery_id = patient["record"]["pregnancies"][0]["deliveries"][0]["uuid"]
        update_data = {
            "record": {
                "pregnancies": [
                    {
                        "uuid": pregnancy_id,
                        "deliveries": [
                            {
                                "uuid": delivery_id,
                                "birth_weight_in_grams": 2300,
                                "birth_outcome": "45718005",
                                "outcome_for_baby": "169826009",
                                "neonatal_complications": ["shoulderDystocia"],
                                "admitted_to_special_baby_care_unit": True,
                            }
                        ],
                    }
                ]
            }
        }
        patient_controller_neo.update_patient(
            patient_uuid=_patient_with_delivery_uuid, patient_details=update_data
        )

        with pytest.raises(KeyError):
            patient_controller_neo.close_patient(
                patient_uuid=patient["uuid"],
                product_uuid=patient["dh_products"][0]["uuid"],
                patient_details=closing_data,
            )

    def test_close_patient_fail_dob_is_none(
        self, _patient_with_delivery_uuid: str, diabetes_patient_product: str
    ) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=_patient_with_delivery_uuid,
            product_name=diabetes_patient_product,
        )
        pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
        delivery_id = patient["record"]["pregnancies"][0]["deliveries"][0]["uuid"]
        update_data = {
            "record": {
                "pregnancies": [
                    {
                        "uuid": pregnancy_id,
                        "deliveries": [
                            {
                                "uuid": delivery_id,
                                "birth_weight_in_grams": 2300,
                                "birth_outcome": "45718005",
                                "outcome_for_baby": "169826009",
                                "neonatal_complications": ["shoulderDystocia"],
                                "admitted_to_special_baby_care_unit": True,
                                "length_of_postnatal_stay_for_baby": 3,
                            }
                        ],
                    }
                ]
            }
        }
        patient_controller_neo.update_patient(
            patient_uuid=_patient_with_delivery_uuid, patient_details=update_data
        )

        with pytest.raises(KeyError):
            patient_controller_neo.close_patient(
                patient_uuid=patient["uuid"],
                product_uuid=patient["dh_products"][0]["uuid"],
                patient_details=closing_data,
            )

    def test_close_patient_fail_date_of_termination_is_not_none(
        self, _patient_with_delivery_uuid: str, diabetes_patient_product: str
    ) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=_patient_with_delivery_uuid,
            product_name=diabetes_patient_product,
        )
        pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
        delivery_id = patient["record"]["pregnancies"][0]["deliveries"][0]["uuid"]
        update_data = {
            "record": {
                "pregnancies": [
                    {
                        "uuid": pregnancy_id,
                        "deliveries": [
                            {
                                "uuid": delivery_id,
                                "birth_weight_in_grams": 2300,
                                "birth_outcome": "45718005",
                                "outcome_for_baby": "169826009",
                                "neonatal_complications": ["shoulderDystocia"],
                                "admitted_to_special_baby_care_unit": True,
                                "length_of_postnatal_stay_for_baby": 3,
                                "date_of_termination": "2018-08-09",
                                "patient": {
                                    "first_name": "Paul",
                                    "last_name": "Smith",
                                    "dob": "2018-08-09",
                                },
                            }
                        ],
                    }
                ]
            }
        }
        patient_controller_neo.update_patient(
            patient_uuid=_patient_with_delivery_uuid, patient_details=update_data
        )

        with pytest.raises(KeyError):
            patient_controller_neo.close_patient(
                patient_uuid=patient["uuid"],
                product_uuid=patient["dh_products"][0]["uuid"],
                patient_details=closing_data,
            )

    def test_close_patient_fail_date_of_termination_none(
        self, _patient_with_delivery_uuid: str, diabetes_patient_product: str
    ) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=_patient_with_delivery_uuid,
            product_name=diabetes_patient_product,
        )
        pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
        delivery_id = patient["record"]["pregnancies"][0]["deliveries"][0]["uuid"]
        update_data = {
            "record": {
                "pregnancies": [
                    {
                        "uuid": pregnancy_id,
                        "deliveries": [
                            {
                                "uuid": delivery_id,
                                "birth_outcome": "386639001",
                                "outcome_for_baby": "169826009",
                                "length_of_postnatal_stay_for_baby": 3,
                            }
                        ],
                    }
                ]
            }
        }
        patient_controller_neo.update_patient(
            patient_uuid=_patient_with_delivery_uuid, patient_details=update_data
        )

        with pytest.raises(KeyError):
            patient_controller_neo.close_patient(
                patient_uuid=patient["uuid"],
                product_uuid=patient["dh_products"][0]["uuid"],
                patient_details=closing_data,
            )

    def test_close_patient_fail_no_diagnosis_tool(
        self, _patient_with_delivery_uuid: str, diabetes_patient_product: str
    ) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=_patient_with_delivery_uuid,
            product_name=diabetes_patient_product,
        )
        pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
        delivery_id = patient["record"]["pregnancies"][0]["deliveries"][0]["uuid"]
        diagnosis_id = patient["record"]["diagnoses"][0]["uuid"]
        update_data = {
            "record": {
                "diagnoses": [{"uuid": diagnosis_id}],
                "pregnancies": [
                    {
                        "uuid": pregnancy_id,
                        "deliveries": [
                            {
                                "uuid": delivery_id,
                                "birth_outcome": "386639001",
                                "outcome_for_baby": "169826009",
                                "length_of_postnatal_stay_for_baby": 3,
                                "date_of_termination": "2018-08-09",
                            }
                        ],
                    }
                ],
            }
        }
        patient_controller_neo.update_patient(
            patient_uuid=_patient_with_delivery_uuid, patient_details=update_data
        )
        with pytest.raises(KeyError):
            patient_controller_neo.close_patient(
                patient_uuid=patient["uuid"],
                product_uuid=patient["dh_products"][0]["uuid"],
                patient_details=closing_data,
            )

    def test_close_patient_fail_no_risk_factors(
        self, _patient_with_delivery_uuid: str, diabetes_patient_product: str
    ) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=_patient_with_delivery_uuid,
            product_name=diabetes_patient_product,
        )
        pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
        delivery_id = patient["record"]["pregnancies"][0]["deliveries"][0]["uuid"]
        diagnosis_id = patient["record"]["diagnoses"][0]["uuid"]
        update_data = {
            "record": {
                "diagnoses": [{"uuid": diagnosis_id, "diagnosis_tool": ["D0000012"]}],
                "pregnancies": [
                    {
                        "uuid": pregnancy_id,
                        "deliveries": [
                            {
                                "uuid": delivery_id,
                                "birth_outcome": "386639001",
                                "outcome_for_baby": "169826009",
                                "length_of_postnatal_stay_for_baby": 3,
                                "date_of_termination": "2018-08-09",
                            }
                        ],
                    }
                ],
            }
        }
        patient_controller_neo.update_patient(
            patient_uuid=_patient_with_delivery_uuid, patient_details=update_data
        )
        with pytest.raises(KeyError):
            patient_controller_neo.close_patient(
                patient_uuid=patient["uuid"],
                product_uuid=patient["dh_products"][0]["uuid"],
                patient_details=closing_data,
            )

    def test_close_patient_gdm(
        self,
        _patient_with_delivery_uuid: str,
        mock_audit_record_patient_archived: Mock,
        diabetes_patient_product: str,
    ) -> None:
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=_patient_with_delivery_uuid,
            product_name=diabetes_patient_product,
        )
        pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
        delivery_id = patient["record"]["pregnancies"][0]["deliveries"][0]["uuid"]
        diagnosis_id = patient["record"]["diagnoses"][0]["uuid"]
        update_data = {
            "record": {
                "diagnoses": [
                    {
                        "uuid": diagnosis_id,
                        "diagnosis_tool": ["D0000012"],
                        "risk_factors": ["416855002"],
                    }
                ],
                "pregnancies": [
                    {
                        "uuid": pregnancy_id,
                        "deliveries": [
                            {
                                "uuid": delivery_id,
                                "birth_outcome": "386639001",
                                "outcome_for_baby": "169826009",
                                "length_of_postnatal_stay_for_baby": 3,
                                "date_of_termination": "2018-08-09",
                            }
                        ],
                    }
                ],
            }
        }
        patient_controller_neo.update_patient(
            patient_uuid=_patient_with_delivery_uuid, patient_details=update_data
        )
        patient_data = patient_controller_neo.close_patient(
            patient_uuid=patient["uuid"],
            product_uuid=patient["dh_products"][0]["uuid"],
            patient_details=closing_data,
        )
        assert patient_data["first_name"] == "Carol"
        assert mock_audit_record_patient_archived.called
        PatientResponse().load(patient_data, unknown=RAISE)

    @pytest.mark.parametrize("diabetes_patient_product", ["DBM"])
    def test_close_patient_dbm(
        self,
        _patient_with_delivery_uuid: str,
        mock_audit_record_patient_archived: Mock,
        diabetes_patient_product: str,
    ) -> None:
        # DBM allows closing a patient without all the fields needed by GDM
        closing_data = {"closed_date": "2019-08-01"}
        patient = patient_controller_neo.get_patient(
            patient_uuid=_patient_with_delivery_uuid,
            product_name=diabetes_patient_product,
        )
        patient_data = patient_controller_neo.close_patient(
            patient_uuid=patient["uuid"],
            product_uuid=patient["dh_products"][0]["uuid"],
            patient_details=closing_data,
        )
        assert patient_data["first_name"] == "Carol"
        assert mock_audit_record_patient_archived.called
        PatientResponse().load(patient_data, unknown=RAISE)

    def test_update_patient_diabetes_type(
        self,
        gdm_patient_uuid: str,
        mock_audit_record_patient_updated: Mock,
        mock_audit_record_patient_diabetes_type_changed: Mock,
        diabetes_patient_product: str,
    ) -> None:
        patient = patient_controller_neo.get_patient(
            patient_uuid=gdm_patient_uuid, product_name=diabetes_patient_product
        )
        diagnosis_id: str = patient["record"]["diagnoses"][0]["uuid"]
        old_diagnosis_sct_code: str = patient["record"]["diagnoses"][0]["sct_code"]
        new_diagnosis_sct_code = "different_code_12345"
        update_data = {
            "record": {
                "diagnoses": [
                    {"sct_code": new_diagnosis_sct_code, "uuid": diagnosis_id}
                ],
            }
        }
        update_patient = patient_controller_neo.update_patient(
            patient_uuid=gdm_patient_uuid, patient_details=update_data
        )
        assert (
            update_patient["record"]["diagnoses"][0]["sct_code"]
            == new_diagnosis_sct_code
        )
        assert mock_audit_record_patient_updated.called
        assert mock_audit_record_patient_diabetes_type_changed.call_count == 1
        mock_audit_record_patient_diabetes_type_changed.assert_called_with(
            patient_uuid=gdm_patient_uuid,
            new_type=new_diagnosis_sct_code,
            old_type=old_diagnosis_sct_code,
        )

    def test_create_send_patient(self) -> None:
        patient = {
            "first_name": "Simone",
            "last_name": "Biles",
            "hospital_number": "10101010",
            "record": {},
        }
        p = patient_controller_neo.create_patient("SEND", patient)
        assert p["first_name"] == patient["first_name"]
        assert p["last_name"] == patient["last_name"]
        assert p["hospital_number"] == patient["hospital_number"]
        PatientResponse().load(p, unknown=RAISE)

    def test_create_send_dod_patient(self) -> None:
        patient = {
            "first_name": "Nadia",
            "last_name": "Comăneci",
            "hospital_number": "10",
            "dod": "2050-10-10",
            "record": {},
        }
        p = patient_controller_neo.create_patient("SEND", patient)
        assert p["first_name"] == patient["first_name"]
        assert p["last_name"] == patient["last_name"]
        assert p["hospital_number"] == patient["hospital_number"]
        PatientResponse().load(p, unknown=RAISE)

    @pytest.mark.parametrize(
        "q,active,patient_search_response",
        [
            ("MRN2", True, []),
            ("MRN1", True, ["P1"]),
            ("mrn1", True, ["P1"]),
            ("8888888888", True, ["P1"]),
            ("9998887771", True, ["P4"]),
            (None, True, ["P1", "P4"]),
            (None, False, ["P5"]),
            ("Jane", True, ["P1", "P4"]),
            ("Jane Grey Dudley", True, ["P1", "P4"]),
            ("Jane Grey", True, ["P1", "P4"]),
            ("Grey", True, ["P1"]),
            ("Dudley", True, ["P4"]),
        ],
        indirect=["patient_search_response"],
    )
    def test_search_patients(
        self,
        mocker: MockerFixture,
        q: str,
        patient_search_response: List[Dict],
        active: bool,
        two_gdm_patients_one_with_children: Mock,
        closed_gdm_patient: Mock,
        diabetes_patient_product: str,
    ) -> None:
        locs: List = ["L1", "L2", "L3", "L4", "L5"]
        cypher_spy = mocker.patch.object(db, "cypher_query", wraps=db.cypher_query)
        actual = patient_controller_neo.search_patients(
            search_text=q,
            locations=locs,
            product_name=diabetes_patient_product,
            active=active,
            expanded=False,
        )
        assert (
            remove_dates(sorted(actual, key=lambda p: p["uuid"]))
            == patient_search_response
        )
        out = json.dumps(actual)  # Verifies we have plain data rather than Nodes
        assert cypher_spy.call_count == 1

    @pytest.mark.parametrize(
        "q,active,patient_search_response",
        [
            ("MRN6", True, ["P6"]),
        ],
        indirect=["patient_search_response"],
    )
    def test_search_patients_expanded(
        self,
        mocker: MockerFixture,
        q: str,
        patient_search_response: List[Dict],
        active: bool,
        one_send_patient: Mock,
    ) -> None:
        locs: List = ["L1"]
        cypher_spy = mocker.patch.object(db, "cypher_query", wraps=db.cypher_query)
        actual = patient_controller_neo.search_patients(
            search_text=q,
            locations=locs,
            product_name="SEND",
            active=active,
            expanded=True,
        )

        assert (
            remove_dates(sorted(actual, key=lambda p: p["uuid"]))
            == patient_search_response
        )
        json.dumps(actual)  # Verifies we have plain data rather than Nodes
        cypher_spy.assert_called_once()

    def test_search_patients_modified_since(
        self,
        mocker: MockerFixture,
        two_gdm_patients_one_with_children: Mock,
        closed_gdm_patient: Mock,
        gdm_patients_modified: Mock,
        diabetes_patient_product: str,
    ) -> None:
        locs: List = ["L1", "L2", "L3", "L4", "L5"]
        cypher_spy = mocker.patch.object(db, "cypher_query", wraps=db.cypher_query)
        actual = patient_controller_neo.search_patients(
            locations=locs,
            search_text=None,
            product_name=diabetes_patient_product,
            modified_since="2000-01-01T01:01:01.123+01:00",
        )
        for entity in actual:
            assert entity["uuid"] == "P6"
        out = json.dumps(actual)  # Verifies we have plain data rather than Nodes
        assert cypher_spy.call_count == 1

    def test_delete_diagnosis(
        self, gdm_patient_uuid: str, diabetes_patient_product: str
    ) -> None:
        patient = patient_controller_neo.get_patient(
            patient_uuid=gdm_patient_uuid, product_name=diabetes_patient_product
        )
        assert len(patient["record"]["diagnoses"]) == 1
        diagnosis_uuid = patient["record"]["diagnoses"][0]["uuid"]
        data_to_delete = {"record": {"diagnoses": [{"uuid": diagnosis_uuid}]}}
        updated_patient = patient_controller_neo.remove_from_patient(
            patient_uuid=gdm_patient_uuid, fields_to_remove=data_to_delete
        )
        assert len(updated_patient["record"]["diagnoses"]) == 0
        PatientResponse().load(updated_patient, unknown=RAISE)

    def test_delete_diagnosis2(
        self,
        gdm_patient_uuid: str,
        diabetes_patient_product: str,
        assert_valid_schema: Callable,
    ) -> None:
        patient = patient_controller_neo.get_patient(
            patient_uuid=gdm_patient_uuid, product_name=diabetes_patient_product
        )
        assert len(patient["record"]["diagnoses"]) == 1
        diagnosis_uuid = patient["record"]["diagnoses"][0]["uuid"]
        data_to_delete = {
            "record": {
                "diagnoses": [
                    {
                        "diagnosed": None,
                        "sct_code": "D0000001",
                        "diagnosis_other": None,
                        "uuid": diagnosis_uuid,
                        "management_plan": {"doses": []},
                    }
                ]
            }
        }
        updated_patient = patient_controller_neo.remove_from_patient(
            patient_uuid=gdm_patient_uuid, fields_to_remove=data_to_delete
        )
        # Delete diagnosis when other fields are present doesn't delete the diagnosis
        assert len(updated_patient["record"]["diagnoses"]) == 1
        assert_valid_schema(PatientResponse, updated_patient)

    @pytest.fixture
    def gdm_diagnosis_uuid(
        self,
        gdm_patient_uuid: str,
        diabetes_patient_product: str,
    ) -> str:
        patient = patient_controller_neo.get_patient(
            patient_uuid=gdm_patient_uuid, product_name=diabetes_patient_product
        )
        assert len(patient["record"]["diagnoses"]) == 1
        diagnosis_uuid = patient["record"]["diagnoses"][0]["uuid"]
        return diagnosis_uuid

    @pytest.fixture
    def gdm_dose_uuid(
        self,
        gdm_patient_uuid: str,
        diabetes_patient_product: str,
        assert_valid_schema: Callable,
        gdm_diagnosis_uuid: str,
    ) -> str:
        patch_data = {
            "record": {
                "diagnoses": [
                    {
                        "diagnosed": None,
                        "sct_code": "D0000001",
                        "diagnosis_other": None,
                        "uuid": gdm_diagnosis_uuid,
                        "management_plan": {
                            "doses": [
                                {
                                    "medication_id": "99b1668c-26f1-4aec-88ca-597d3a20d977",
                                    "dose_amount": 1.5,
                                    "routine_sct_code": "12345",
                                }
                            ]
                        },
                    }
                ]
            }
        }
        updated_patient = patient_controller_neo.update_patient(
            patient_uuid=gdm_patient_uuid, patient_details=patch_data
        )
        return updated_patient["record"]["diagnoses"][0]["management_plan"]["doses"][0][
            "uuid"
        ]

    def test_delete_dose(
        self,
        gdm_patient_uuid: str,
        gdm_diagnosis_uuid: str,
        gdm_dose_uuid: str,
        diabetes_patient_product: str,
        assert_valid_schema: Callable,
    ) -> None:
        data_to_delete = {
            "record": {
                "diagnoses": [
                    {
                        "uuid": gdm_diagnosis_uuid,
                        "management_plan": {"doses": [{"uuid": gdm_dose_uuid}]},
                    }
                ]
            }
        }
        updated_patient = patient_controller_neo.remove_from_patient(
            patient_uuid=gdm_patient_uuid, fields_to_remove=data_to_delete
        )
        assert len(updated_patient["record"]["diagnoses"]) == 1
        assert (
            len(updated_patient["record"]["diagnoses"][0]["management_plan"]["doses"])
            == 0
        )
        assert (
            len(
                updated_patient["record"]["diagnoses"][0]["management_plan"][
                    "dose_history"
                ]
            )
            == 2
        )
        assert (
            updated_patient["record"]["diagnoses"][0]["management_plan"][
                "dose_history"
            ][0]["action"]
            == "delete"
        )
        assert (
            updated_patient["record"]["diagnoses"][0]["management_plan"][
                "dose_history"
            ][1]["action"]
            == "insert"
        )

    def test_create_patient_tos(
        self, gdm_patient_uuid: str, diabetes_patient_product: str
    ) -> None:
        terms = {
            "product_name": diabetes_patient_product,
            "version": 4,
            "accepted_timestamp": "2020-01-01T00:00:00.000Z",
        }
        result = patient_controller_neo.create_patient_tos(
            patient_uuid=gdm_patient_uuid, terms_details=terms
        )
        assert result["version"] == terms["version"]
        PatientTermsResponse().load(result, unknown=RAISE)

    def test_create_patient_tos_v2(
        self, gdm_patient_uuid: str, diabetes_patient_product: str
    ) -> None:
        terms = {
            "product_name": diabetes_patient_product,
            "tou_version": 4,
            "tou_accepted_timestamp": "2020-01-01T00:00:00.000Z",
            "patient_notice_version": 3,
            "patient_notice_accepted_timestamp": "2020-01-01T00:00:00.000Z",
        }
        result = patient_controller_neo.create_patient_tos_v2(
            patient_uuid=gdm_patient_uuid, terms_details=terms
        )
        assert result["tou_version"] == terms["tou_version"]
        assert result["patient_notice_version"] == terms["patient_notice_version"]
        PatientTermsResponseV2().load(result, unknown=RAISE)

    VALID_NHS_NUMBERS = [
        "1111111111",
        "3314191243",
        "0724930108",
        "0327211369",
        "4417554676",
        "0406548390",
        "9396398268",
        "7566846191",
        "0262326302",
        "4597895833",
        "8794137838",
        "1208151150",
        "1796099473",
        "6076101741",
        "0602459419",
        "3179476176",
    ]

    @pytest.mark.parametrize("nhs_number", VALID_NHS_NUMBERS)
    def test_ensure_valid_nhs_number_success(self, nhs_number: str) -> None:
        result = patient_controller_neo.ensure_valid_nhs_number(nhs_number)
        assert result is True

    @pytest.mark.parametrize(
        "nhs_number",
        [
            "abcdefghij",
            "123",
            "123456789a",
            *[format(int(v) + 1, "010") for v in VALID_NHS_NUMBERS],
            *[format(int(v) - 1, "010") for v in VALID_NHS_NUMBERS],
        ],
    )
    def test_ensure_valid_nhs_number_failure(self, nhs_number: str) -> None:
        with pytest.raises(ValueError):
            patient_controller_neo.ensure_valid_nhs_number(nhs_number)

    def test_stop_monitoring_patient(
        self, mocker: MockerFixture, monitored_gdm_patient: Any
    ) -> None:
        mock_audit_record_patient_not_monitored_anymore = mocker.patch.object(
            audit, "record_patient_not_monitored_anymore"
        )

        patient_data = patient_controller_neo.set_patient_monitored_by_clinician(
            patient_id="P9", product_id="DH9", monitored_by_clinician=False
        )

        assert not patient_data["dh_products"][0]["monitored_by_clinician"]
        assert patient_data["dh_products"][0]["changes"]
        assert (
            patient_data["dh_products"][0]["changes"][0]["event"] == "stop monitoring"
        )

        mock_audit_record_patient_not_monitored_anymore.assert_called_once_with(
            patient_id="P9", product_id="DH9"
        )

    def test_stop_monitoring_patient_not_found(
        self, monitored_gdm_patient: Any
    ) -> None:
        with pytest.raises(EntityNotFoundException):
            patient_controller_neo.set_patient_monitored_by_clinician(
                patient_id="P9",
                product_id="asdasd;jkasdl;",
                monitored_by_clinician=False,
            )

        with pytest.raises(EntityNotFoundException):
            patient_controller_neo.set_patient_monitored_by_clinician(
                patient_id="P1238123", product_id="GDM", monitored_by_clinician=False
            )

    def test_stop_monitoring_patient_closed(self) -> None:
        with pytest.raises(EntityNotFoundException):
            patient_controller_neo.set_patient_monitored_by_clinician(
                patient_id="P5", product_id="DH5", monitored_by_clinician=False
            )

    def test_stop_monitoring_patient_already_stopped(
        self, not_monitored_gdm_patient: Any
    ) -> None:
        with pytest.raises(ValueError):
            patient_controller_neo.set_patient_monitored_by_clinician(
                patient_id="P8", product_id="DH8", monitored_by_clinician=False
            )

    def test_start_monitoring_patient(
        self, mocker: MockerFixture, not_monitored_gdm_patient: Any
    ) -> None:
        mock_audit_record_patient_monitored = mocker.patch.object(
            audit, "record_patient_monitored"
        )

        patient_data = patient_controller_neo.set_patient_monitored_by_clinician(
            patient_id="P8", product_id="DH8", monitored_by_clinician=True
        )

        assert patient_data["dh_products"][0]["monitored_by_clinician"]
        assert patient_data["dh_products"][0]["changes"]
        assert (
            patient_data["dh_products"][0]["changes"][0]["event"] == "start monitoring"
        )

        mock_audit_record_patient_monitored.assert_called_once_with(
            patient_id="P8", product_id="DH8"
        )

    def test_start_monitoring_patient_not_found(
        self,
        gdm_patient_uuid: str,
        diabetes_patient_product: str,
    ) -> None:
        with pytest.raises(EntityNotFoundException):
            patient_controller_neo.set_patient_monitored_by_clinician(
                patient_id="P9",
                product_id="asdasd;jkasdl;",
                monitored_by_clinician=True,
            )

        with pytest.raises(EntityNotFoundException):
            patient_controller_neo.set_patient_monitored_by_clinician(
                patient_id="P1238123", product_id="GDM", monitored_by_clinician=True
            )

    def test_start_monitoring_patient_closed(self) -> None:
        with pytest.raises(EntityNotFoundException):
            patient_controller_neo.set_patient_monitored_by_clinician(
                patient_id="P5", product_id="DH5", monitored_by_clinician=True
            )

    def test_start_monitoring_patient_already_monitored(
        self, monitored_gdm_patient: Any
    ) -> None:
        with pytest.raises(ValueError):
            patient_controller_neo.set_patient_monitored_by_clinician(
                patient_id="P9", product_id="DH9", monitored_by_clinician=True
            )

    def test_patient_uuids(self, two_gdm_patients_one_with_children: Any) -> None:
        uuids = patient_controller_neo.get_patient_uuids(product_name="GDM")

        assert len(uuids) == 2
        assert isinstance(uuids, list)

    def test_patch_delivery_creates_patient(
        self,
        gdm_patient_uuid: str,
        mock_audit_record_patient_viewed: MockerFixture,
        mock_audit_record_patient_updated: MockerFixture,
        diabetes_patient_product: str,
    ) -> None:
        patient = patient_controller_neo.get_patient(
            patient_uuid=gdm_patient_uuid, product_name=diabetes_patient_product
        )
        pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
        update_data = {
            "record": {
                "pregnancies": [
                    {
                        "uuid": pregnancy_id,
                        "height_at_booking_in_mm": 1230,
                        "weight_at_booking_in_g": 78000,
                        "length_of_postnatal_stay_in_days": 2,
                        "induced": True,
                        "deliveries": [
                            {
                                "admitted_to_special_baby_care_unit": False,
                                "neonatal_complications": ["D0000025"],
                            }
                        ],
                    }
                ]
            }
        }
        patient = patient_controller_neo.update_patient(
            patient_uuid=gdm_patient_uuid, patient_details=update_data
        )
        deliveries = patient["record"]["pregnancies"][0]["deliveries"]
        assert len(deliveries) == 1
        baby = deliveries[0]["patient"]
        assert baby is not None and baby["dob"] is None
