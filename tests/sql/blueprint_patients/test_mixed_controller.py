from typing import Callable

import pytest
from flask_sqlalchemy import SQLAlchemy

from dhos_services_api.blueprint_patients import mixed_controller
from dhos_services_api.models.api_spec import PatientResponse
from dhos_services_api.sqlmodels import DraysonHealthProduct, History, Patient, Record


@pytest.mark.usefixtures("mock_retrieve_jwt_claims", "uses_sql_database", "app")
class TestMixedController:
    @pytest.fixture
    def patient_child_children(self, _db: SQLAlchemy) -> None:
        p1: Patient = Patient.new(
            uuid="P1",
            hospital_number="MRN1",
            first_name="Peter",
            last_name="Griffin",
            record=Record.new(uuid="R1", history=History.new()),
            dh_products=[DraysonHealthProduct.new(uuid="DH1", product_name="SEND")],
        )
        p2: Patient = Patient.new(
            uuid="P2",
            hospital_number="MRN2",
            first_name="Lois",
            last_name="Griffin",
            child_of=p1,
            record=Record.new(uuid="R2", history=History.new()),
            dh_products=[DraysonHealthProduct.new(uuid="DH2", product_name="SEND")],
        )
        p3: Patient = Patient.new(
            uuid="P3",
            hospital_number="MRN3",
            first_name="Brian",
            last_name="Griffin",
            child_of=p2,
            record=Record.new(uuid="R3", history=History.new()),
            dh_products=[DraysonHealthProduct.new(uuid="DH3", product_name="SEND")],
        )
        _db.session.commit()

    @pytest.mark.parametrize("mrn", ["MRN3", "MRN2", "MRN1"])
    def test_get_patient_by_product_and_identifer(
        self, patient_child_children: None, assert_valid_schema: Callable, mrn: str
    ) -> None:
        expected = "P1"
        result = mixed_controller.get_patients_by_product_and_identifer(
            product_name="SEND", identifier_type="mrn", identifier_value=mrn
        )
        assert expected == result[0]["uuid"]
        assert_valid_schema(PatientResponse, result, many=True)

    def test_bookmark_patient(
        self,
        gdm_patient_uuid: str,
        gdm_location_uuid: str,
        assert_valid_schema: Callable,
    ) -> None:
        bookmarked_patient = mixed_controller.bookmark_patient(
            patient_id=gdm_patient_uuid,
            location_id=gdm_location_uuid,
            is_bookmarked=True,
        )
        unbookmarked_patient = mixed_controller.bookmark_patient(
            patient_id=gdm_patient_uuid,
            location_id=gdm_location_uuid,
            is_bookmarked=False,
        )
        assert bookmarked_patient["bookmarked"] is True
        assert bookmarked_patient["has_been_bookmarked"] is True

        assert unbookmarked_patient["bookmarked"] is False
        assert unbookmarked_patient["has_been_bookmarked"] is True

        assert_valid_schema(PatientResponse, bookmarked_patient, many=False)
        assert_valid_schema(PatientResponse, unbookmarked_patient, many=False)
