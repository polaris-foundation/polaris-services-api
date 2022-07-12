import uuid
from typing import Callable, Dict, Optional

import pytest
from flask_sqlalchemy import SQLAlchemy
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from dhos_services_api.sqlmodels.patient import Patient
from dhos_services_api.sqlmodels.terms_agreement import TermsAgreement


class TermsAgreementModel(BaseModel):
    """
    Patient terms agreement response
    """

    class Config:
        orm_mode = True

    product_name: Optional[str] = Field(...)
    tou_version: Optional[int] = Field(...)
    patient_notice_version: Optional[int] = Field(...)


@pytest.mark.usefixtures("app", "uses_sql_database")
class TestPatient:
    @pytest.mark.parametrize(
        "nhs1,hosp1,nhs2,hosp2",
        [
            ("123123123", "11111", "123123123", "222222"),
            ("123123123", "11111", "123123124", "11111"),
        ],
    )
    def test_patient_unique_fields_rejected(
        self, patient_context: Callable, nhs1: str, hosp1: str, nhs2: str, hosp2: str
    ) -> None:
        """This test bypasses our models and tests that the database constraints are present
        and will prevent duplicate patients with the same NHS number or the same hospital number."""
        with patient_context("Carol", nhs_number=nhs1, hospital_number=hosp1) as carol:
            with pytest.raises(IntegrityError) as exc_info:
                with patient_context(
                    "Jane", nhs_number=nhs2, hospital_number=hosp2
                ) as jane:
                    pass

    @pytest.mark.parametrize(
        "nhs1,hosp1,nhs2,hosp2",
        [(None, "11111", None, "222222"), ("123123123", None, "123123124", None)],
    )
    def test_patient_unique_fields_none_ok(
        self, patient_context: Callable, nhs1: str, hosp1: str, nhs2: str, hosp2: str
    ) -> None:
        """This test bypasses our models and tests that the database constraints are present
        and will prevent duplicate patients with the same NHS number or the same hospital number
        but that None is permitted."""
        with patient_context("Carol", nhs_number=nhs1, hospital_number=hosp1) as carol:
            with patient_context(
                "Jane", nhs_number=nhs2, hospital_number=hosp2
            ) as jane:
                pass

    @pytest.mark.parametrize(
        "terms_agreements,expected",
        [
            (
                [
                    {
                        "product_name": "GDM",
                        "version": 1,
                    },
                    {
                        "product_name": "GDM",
                        "patient_notice_version": 5,
                        "tou_version": 3,
                    },
                    {
                        "product_name": "GDM",
                        "patient_notice_version": 4,
                        "tou_version": 3,
                    },
                    {
                        "product_name": "GDM",
                        "patient_notice_version": 2,
                        "tou_version": 1,
                    },
                    {
                        "product_name": "GDM",
                        "patient_notice_version": 4,
                    },
                    {
                        "product_name": "GDM",
                        "version": 2,
                    },
                ],
                {
                    "product_name": "GDM",
                    "patient_notice_version": 5,
                    "tou_version": 3,
                },
            ),
            (None, None),
            (
                [
                    {
                        "product_name": "GDM",
                        "patient_notice_version": 4,
                        "tou_version": 3,
                    },
                    {
                        "product_name": "GDM",
                        "version": 9,
                    },
                ],
                {
                    "product_name": "GDM",
                    "patient_notice_version": 4,
                    "tou_version": 3,
                },
            ),
            (
                [
                    {
                        "product_name": "GDM",
                        "version": 2,
                    },
                    {
                        "product_name": "GDM",
                        "patient_notice_version": 5,
                        "tou_version": 3,
                    },
                    {
                        "product_name": "GDM",
                        "patient_notice_version": 2,
                        "tou_version": 1,
                    },
                ],
                {
                    "product_name": "GDM",
                    "patient_notice_version": 5,
                    "tou_version": 3,
                },
            ),
            (
                [
                    {
                        "product_name": "GDM",
                        "version": 1,
                    },
                    {
                        "product_name": "GDM",
                        "patient_notice_version": 5,
                        "tou_version": 3,
                    },
                    {
                        "product_name": "GDM",
                        "patient_notice_version": 2,
                        "tou_version": 1,
                    },
                ],
                {
                    "product_name": "GDM",
                    "patient_notice_version": 5,
                    "tou_version": 3,
                },
            ),
        ],
    )
    def test_latest_terms_agreement(
        self,
        _db: SQLAlchemy,
        terms_agreements: dict,
        expected: Dict,
        patient_context: Callable[..., Patient],
    ) -> None:
        pid = uuid.uuid4()
        with patient_context("Carol", hospital_number=pid) as carol:
            if not terms_agreements:
                assert carol._latest_terms_agreement == expected
            else:
                for term in terms_agreements:
                    TermsAgreement.new(patient_id=carol.uuid, **term)
                _db.session.commit()

                assert (
                    TermsAgreementModel.from_orm(carol._latest_terms_agreement).dict()
                    == expected
                )

    def test_populated_patient(self, _db: SQLAlchemy) -> None:
        data: dict = {
            "allowed_to_text": False,
            "first_name": "Rose",
            "last_name": "Huff",
            "phone_number": "07123456789",
            "dob": "1981-12-23",
            "nhs_number": "6628918564",
            "hospital_number": "000000",
            "email_address": "Rose@email.com",
            "dh_products": [
                {
                    "accessibility_discussed": True,
                    "accessibility_discussed_with": "static_clinician_gdm_standard_5",
                    "accessibility_discussed_date": "2022-01-16",
                    "opened_date": "2022-01-16",
                    "created": "2022-01-16T04:58:17.541Z",
                    "created_by": "static_clinician_gdm_standard_5",
                    "modified": "2022-01-16T04:58:17.541Z",
                    "modified_by": "static_clinician_gdm_standard_5",
                    "product_name": "GDM",
                }
            ],
            "personal_addresses": [
                {
                    "address_line_1": "School House Mill Byway",
                    "address_line_2": "",
                    "address_line_3": "",
                    "address_line_4": "",
                    "locality": "Nottingham",
                    "region": "Nottinghamshire",
                    "postcode": "NG4 5JY",
                    "lived_from": "2018-05-08",
                }
            ],
            "ethnicity": "315279003",
            "sex": "248152002",
            "highest_education_level": "365460000",
            "accessibility_considerations": [],
            "other_notes": "",
            "record": {
                "notes": [
                    {
                        "content": "Discussed diet with patient",
                        "clinician_uuid": "static_clinician_gdm_standard_5",
                        "created": "2022-04-04T23:23:30.920Z",
                        "modified": "2022-04-04T23:23:30.920Z",
                    },
                    {
                        "content": "Had good discussion with patient about managing blood glucose levels",
                        "clinician_uuid": "static_clinician_gdm_standard_5",
                        "created": "2022-01-03T23:01:30.920Z",
                        "modified": "2022-01-03T23:01:30.920Z",
                    },
                    {
                        "content": "Discussed diet with patient",
                        "clinician_uuid": "static_clinician_gdm_standard_5",
                        "created": "2022-01-31T19:31:30.920Z",
                        "modified": "2022-01-31T19:31:30.920Z",
                    },
                    {
                        "content": "Had good discussion with patient about managing blood glucose levels",
                        "clinician_uuid": "static_clinician_gdm_standard_5",
                        "created": "2022-01-14T00:59:30.920Z",
                        "modified": "2022-01-14T00:59:30.920Z",
                    },
                    {
                        "content": "Patient expressed concerns about blood glucose levels",
                        "clinician_uuid": "static_clinician_gdm_standard_5",
                        "created": "2021-12-22T21:44:30.920Z",
                        "modified": "2021-12-22T21:44:30.920Z",
                    },
                    {
                        "content": "Note to check on patient's medication",
                        "clinician_uuid": "static_clinician_gdm_standard_5",
                        "created": "2022-04-29T21:56:30.920Z",
                        "modified": "2022-04-29T21:56:30.920Z",
                    },
                    {
                        "content": "Asked patients to tag their readings",
                        "clinician_uuid": "static_clinician_gdm_standard_5",
                        "created": "2022-04-26T21:02:30.920Z",
                        "modified": "2022-04-26T21:02:30.920Z",
                    },
                    {
                        "content": "Patient expressed concerns about blood glucose levels",
                        "clinician_uuid": "static_clinician_gdm_standard_5",
                        "created": "2022-06-06T03:23:30.920Z",
                        "modified": "2022-06-06T03:23:30.920Z",
                    },
                    {
                        "content": "Patient expressed concerns about blood glucose levels",
                        "clinician_uuid": "static_clinician_gdm_standard_5",
                        "created": "2022-04-28T23:54:30.920Z",
                        "modified": "2022-04-28T23:54:30.920Z",
                    },
                    {
                        "content": "Reminded patients to add comments to blood glucose readings",
                        "clinician_uuid": "static_clinician_gdm_standard_5",
                        "created": "2022-05-29T00:50:30.920Z",
                        "modified": "2022-05-29T00:50:30.920Z",
                    },
                    {
                        "content": "Patient has been struggling lately",
                        "clinician_uuid": "static_clinician_gdm_standard_5",
                        "created": "2022-03-31T02:24:30.920Z",
                        "modified": "2022-03-31T02:24:30.920Z",
                    },
                    {
                        "content": "Asked patients to tag their readings",
                        "clinician_uuid": "static_clinician_gdm_standard_5",
                        "created": "2022-03-24T19:43:30.920Z",
                        "modified": "2022-03-24T19:43:30.920Z",
                    },
                ],
                "history": {"gravidity": 4, "parity": 2},
                "pregnancies": [
                    {
                        "estimated_delivery_date": "2022-09-13",
                        "planned_delivery_place": "99b1668c-26f1-4aec-88ca-597d3a20d977",
                        "length_of_postnatal_stay_in_days": 1,
                        "colostrum_harvesting": True,
                        "expected_number_of_babies": 1,
                        "deliveries": [],
                        "height_at_booking_in_mm": 1877,
                        "weight_at_diagnosis_in_g": 91017,
                        "weight_at_booking_in_g": 100118,
                        "weight_at_36_weeks_in_g": 110129,
                        "pregnancy_complications": ["398254007"],
                        "created": "2022-01-16T04:58:17.541Z",
                        "created_by": "static_clinician_gdm_standard_5",
                        "modified": "2022-01-16T04:58:17.541Z",
                        "modified_by": "static_clinician_gdm_standard_5",
                    }
                ],
                "diagnoses": [
                    {
                        "sct_code": "44054006",
                        "diagnosis_other": None,
                        "diagnosed": "2022-01-16",
                        "episode": 1,
                        "presented": "2022-01-16",
                        "diagnosis_tool": ["D0000011", "D0000018"],
                        "diagnosis_tool_other": None,
                        "risk_factors": ["162864005"],
                        "observable_entities": [
                            {
                                "sct_code": "443911005",
                                "date_observed": "2022-09-13",
                                "value_as_string": "5",
                                "metadata": {"tag": "last"},
                            }
                        ],
                        "management_plan": {
                            "start_date": "2022-01-16",
                            "end_date": "2022-09-13",
                            "sct_code": "67866001",
                            "doses": [
                                {
                                    "medication_id": "12759201000001105",
                                    "dose_amount": 2.0,
                                    "routine_sct_code": "1761000175102",
                                }
                            ],
                            "actions": [{"action_sct_code": "12345"}],
                        },
                        "readings_plan": {
                            "start_date": "2022-01-16",
                            "end_date": "2022-09-13",
                            "sct_code": "54321",
                            "days_per_week_to_take_readings": 7,
                            "readings_per_day": 7,
                        },
                        "created": "2022-01-16T04:58:17.541Z",
                        "created_by": "static_clinician_gdm_standard_5",
                        "modified": "2022-01-16T04:58:17.541Z",
                        "modified_by": "static_clinician_gdm_standard_5",
                    }
                ],
                "visits": [{"visit_date": "2021-12-07T04:58:1"}],
            },
        }
        patient = Patient.new(**data)
        assert len(patient.record.notes) == 12
