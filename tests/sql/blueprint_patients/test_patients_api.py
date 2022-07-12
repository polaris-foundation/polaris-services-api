import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Union
from unittest.mock import Mock

import flask
import pytest
from flask.testing import FlaskClient
from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.helpers.error_handler import EntityNotFoundException
from pytest_mock import MockFixture

from dhos_services_api.blueprint_patients import (
    aggregation_controller,
    alerting_controller,
    mixed_controller,
    patient_controller,
)
from dhos_services_api.models.patient import Patient


@pytest.mark.usefixtures(
    "app", "mock_retrieve_jwt_claims", "mock_bearer_validation", "uses_sql_database"
)
class TestPatientsApi:
    @pytest.mark.usefixtures("mock_retrieve_jwt_claims", "gdm_jwt_clinician_uuid")
    def test_search_patients(self, mocker: MockFixture, client: FlaskClient) -> None:
        expected: Dict = {"uuid": "123456", "first_name": "Tom"}

        mock_method = mocker.patch.object(
            patient_controller, "search_patients", return_value=expected
        )
        response = client.get(
            "/dhos/v1/patient/search?q=tom&locs=L1&product_name=GDM",
            headers={"Authorization": "Bearer TOKEN"},
        )

        mock_method.assert_called_once_with(
            search_text="tom",
            locations=["L1"],
            product_name="GDM",
            active=True,
            modified_since=None,
            expanded=False,
        )
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"

    @pytest.mark.usefixtures("mock_retrieve_jwt_claims", "gdm_jwt_clinician_uuid")
    def test_get_patients_no_location(
        self, mocker: MockFixture, client: FlaskClient
    ) -> None:
        expected: Dict = {"uuid": "123456", "first_name": "Tom"}

        mock_method = mocker.patch.object(
            patient_controller, "search_patients", return_value=expected
        )
        response = client.get(
            "/dhos/v1/patient/search?q=tom&product_name=GDM",
            headers={"Authorization": "Bearer TOKEN"},
        )

        mock_method.assert_called_once_with(
            search_text="tom",
            locations=[],
            product_name="GDM",
            active=True,
            modified_since=None,
            expanded=False,
        )
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"

    @pytest.mark.usefixtures("mock_retrieve_jwt_claims", "gdm_jwt_clinician_uuid")
    def test_get_patients_empty_location(
        self, mocker: MockFixture, client: FlaskClient
    ) -> None:
        expected: Dict = {"uuid": "123456", "first_name": "Tom"}

        mock_method = mocker.patch.object(
            patient_controller, "search_patients", return_value=expected
        )
        response = client.get(
            "/dhos/v1/patient/search?q=tom&locs=&product_name=GDM",
            headers={"Authorization": "Bearer TOKEN"},
        )

        mock_method.assert_called_once_with(
            search_text="tom",
            locations=[""],
            product_name="GDM",
            active=True,
            modified_since=None,
            expanded=False,
        )
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"

    @pytest.mark.usefixtures("mock_retrieve_jwt_claims", "gdm_jwt_clinician_uuid")
    def test_get_patients_modified_since(
        self, mocker: MockFixture, client: FlaskClient
    ) -> None:
        expected: Dict = {"uuid": "123456", "first_name": "Tom"}

        mock_method = mocker.patch.object(
            patient_controller, "search_patients", return_value=expected
        )
        response = client.get(
            "/dhos/v1/patient/search?q=tom&locs=&product_name=GDM&modified_since=2000-01-01T01:01:01.123%2B01:00",  # `+` should be URL-encoded (%2B)
            headers={"Authorization": "Bearer TOKEN"},
        )

        mock_method.assert_called_once_with(
            search_text="tom",
            locations=[""],
            product_name="GDM",
            active=True,
            modified_since="2000-01-01T01:01:01.123+01:00",
            expanded=False,
        )
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"

    @pytest.mark.usefixtures("mock_retrieve_jwt_claims", "jwt_system")
    def test_open_gdm_patients(self, mocker: MockFixture, client: FlaskClient) -> None:
        expected = [
            {
                "readings_plans": [
                    {
                        "created": datetime.now().replace(tzinfo=timezone.utc),
                        "days_per_week_to_take_readings": 4,
                        "readings_per_day": 4,
                    }
                ],
                "uuid": generate_uuid(),
                "first_name": "Testy",
                "locations": "McTestface",
            }
        ]
        mock_method = mocker.patch.object(
            alerting_controller, "retrieve_open_gdm_patients", return_value=expected
        )
        response = client.post(
            "/dhos/v1/patient/open_gdm_patients",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert mock_method.call_count == 1
        assert response.json is not None
        assert len(response.json) == 1
        # Check timestamp is localised.
        assert response.json["patients"][0]["readings_plans"][0]["created"].endswith(
            "Z"
        )

    @pytest.mark.usefixtures("mock_retrieve_jwt_claims", "jwt_send_clinician_uuid")
    @pytest.mark.parametrize(
        "select,expected",
        [
            (
                [0, 1, 2, 3],
                {
                    "Alice",
                    "Bobby",
                    "Carol",
                    "Diane",
                },
            ),
            (
                [0, 3],
                {
                    "Alice",
                    "Diane",
                },
            ),
        ],
    )
    def test_get_patients_by_uuids_v2(
        self,
        client: FlaskClient,
        jwt_send_clinician_uuid: str,
        four_patient_uuids: List[str],
        select: List[int],
        expected: Set[str],
    ) -> None:
        ids = [four_patient_uuids[i] for i in select]
        response = client.post(
            f"/dhos/v2/patient/search",
            headers={"Authorization": "Bearer TOKEN"},
            json=ids,
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["total"] == len(expected)
        assert set(d["first_name"] for d in response.json["results"]) == expected

    @pytest.mark.usefixtures("mock_retrieve_jwt_claims")
    @pytest.mark.parametrize(
        "jwt_scopes,product_name",
        [
            (
                [
                    "write:gdm_patient_all",
                    "read:gdm_patient_all",
                ],
                "GDM",
            ),
            (
                [
                    "write:patient_all",
                    "read:patient_all",
                ],
                "NEW-PRODUCT",
            ),
            (
                [
                    "write:send_patient",
                    "read:send_patient",
                ],
                "SEND",
            ),
        ],
    )
    def test_create_location_clinician_patient(
        self,
        client: FlaskClient,
        jwt_gdm_clinician_uuid: str,
        jwt_scopes: List[str],
        product_name: str,
        gdm_location_uuid: str,
    ) -> None:
        patient = {
            "first_name": "Carol",
            "last_name": "Danvers",
            "phone_number": "07594203248",
            "allowed_to_text": True,
            "allowed_to_email": True,
            "dob": "1957-06-9",
            "hospital_number": "435y3948",
            "email_address": "charliemic@hotmail.co.uk",
            "dh_products": [
                {
                    "product_name": product_name,
                    "opened_date": "2018-06-22",
                    "accessibility_discussed": True,
                    "accessibility_discussed_with": jwt_gdm_clinician_uuid,
                    "accessibility_discussed_date": "2018-06-22",
                }
            ],
            "sex": "248152002",
            "height_in_mm": 1650,
            "weight_in_g": 71000,
            "accessibility_considerations": None,
            "record": {
                "pregnancies": [
                    {"estimated_delivery_date": datetime.today().strftime("%Y-%m-%d")}
                ],
                "diagnoses": [
                    {
                        "sct_code": "11687002",
                        "diagnosed": "2018-06-22",
                        "risk_factors": [],
                        "management_plan": {
                            "start_date": "2018-06-22",
                            "end_date": "2018-9-11",
                            "sct_code": "D0000007",
                            "doses": [],
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
            },
            "locations": [gdm_location_uuid],
        }
        url = f"/dhos/v1/patient?product_name={product_name}"
        post_response = client.open(
            url,
            method="POST",
            data=json.dumps(patient),
            content_type="application/json",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert (
            post_response.status_code == 200
        ), "Response body is : " + post_response.data.decode("utf-8")
        assert post_response.json is not None
        patient_uuid = post_response.json["uuid"]

        if product_name == "GDM":
            response = client.get(
                flask.url_for(
                    "patients_api.get_gdm_patients_by_location",
                    location_id=gdm_location_uuid,
                ),
                query_string={"diagnosis": "11687002"},
                headers={"Authorization": "Bearer TOKEN"},
            )
            assert response.status_code == 200 and response.json is not None

            assert response.json[0]["uuid"] == patient_uuid

        url = f"/dhos/v1/patient/{patient_uuid}?product_name={product_name}"
        response = client.get(url, headers={"Authorization": "Bearer TOKEN"})
        assert response.json is not None
        assert response.json["uuid"] == patient_uuid

    @pytest.mark.usefixtures("mock_retrieve_jwt_claims", "jwt_send_clinician_uuid")
    @pytest.mark.parametrize("jwt_scopes", [["read:send_patient"]])
    def test_get_send_patient_by_identifier(
        self,
        client: FlaskClient,
        jwt_scopes: List[str],
        patient: Patient,
    ) -> None:
        url = f"/dhos/v1/patient?product_name=SEND&identifier_type=mrn&identifier_value={patient.hospital_number}"
        response = client.get(url, headers={"Authorization": "Bearer TOKEN"})
        assert response.json is not None
        assert response.status_code == 200, f"Response body is : {response.json}"
        assert response.json[0]["first_name"] == "Carol"

    def test_missing_product_type_for_get_patients_by_uuid(
        self,
        client: FlaskClient,
        jwt_gdm_clinician_uuid: str,
        patient_uuid: str,
    ) -> None:
        url = f"/dhos/v1/patient/{patient_uuid}"
        response = client.get(url, headers={"Authorization": "Bearer TOKEN"})
        assert response.status_code in (403, 400)

    def test_missing_product_type_for_post_patient(
        self, client: FlaskClient, jwt_send_clinician_uuid: str
    ) -> None:
        url = f"/dhos/v1/patient"
        response = client.post(url, json={}, headers={"Authorization": "Bearer TOKEN"})
        assert response.status_code in (403, 400)

    def test_missing_product_type_for_validate_nhs_number(
        self, client: FlaskClient, jwt_gdm_clinician_uuid: str
    ) -> None:
        url = f"/dhos/v1/patient/validate/123"
        response = client.post(url, headers={"Authorization": "Bearer TOKEN"})
        assert response.status_code == 400

    def test_missing_product_type_for_validate_patient(
        self, client: FlaskClient, jwt_gdm_clinician_uuid: str
    ) -> None:
        url = f"/dhos/v1/patient/validate"
        response = client.post(url, json={}, headers={"Authorization": "Bearer TOKEN"})
        assert response.status_code == 400

    @pytest.fixture
    def mock_retrieve_patient_by_uuids(self, mocker: MockFixture) -> Any:
        return mocker.patch.object(patient_controller, "retrieve_patients_by_uuids")

    @pytest.mark.usefixtures("mock_retrieve_jwt_claims", "jwt_send_clinician_uuid")
    @pytest.mark.parametrize(
        "expected_status,expected_response_body,_json,controller_return_value",
        [
            (400, None, None, None),
            (400, None, {"key": "value"}, None),
            (404, None, ["unauthorised"], EntityNotFoundException()),
            (200, ["patient_list"], ["authorised"], ["patient_list"]),
        ],
    )
    def test_retrieve_patients_by_uuids(
        self,
        client: FlaskClient,
        jwt_send_clinician_uuid: str,
        mock_retrieve_patient_by_uuids: Mock,
        expected_status: int,
        expected_response_body: Dict,
        _json: Dict,
        controller_return_value: Union[Exception, List[str]],
    ) -> None:
        if isinstance(controller_return_value, Exception):
            mock_retrieve_patient_by_uuids.side_effect = controller_return_value
        else:
            mock_retrieve_patient_by_uuids.return_value = controller_return_value
        response = client.post(
            "/dhos/v1/patient_list?product_name=SEND",
            json=_json,
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == expected_status
        if expected_status == 200:
            assert response.json == expected_response_body

    @pytest.mark.usefixtures("mock_retrieve_jwt_claims", "jwt_system")
    @pytest.mark.parametrize(
        "expected_status,jwt_scopes,override_uuid,compact",
        [
            (200, "read:send_patient", None, False),
            (200, "read:send_patient", None, True),
            (200, "read:send_patient", None, None),
            (403, "read:gdm_patient_all", None, None),
            (404, "read:send_patient", "42f66697-b08a-45c3-ab7f-df62a53d3552", None),
        ],
    )
    def test_patient_by_record(
        self,
        client: FlaskClient,
        jwt_scopes: str,
        patient_uuid: str,
        patient_record_uuid: str,
        expected_status: int,
        override_uuid: str,
        compact: bool,
    ) -> None:
        record_id = override_uuid if override_uuid else patient_record_uuid
        response = client.get(
            flask.url_for(
                "patients_api.get_patient_by_record",
                record_id=record_id,
                compact=compact,
            ),
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == expected_status
        if expected_status == 200:
            assert response.json is not None
            assert response.json["uuid"] == patient_uuid
            # If we have compact format we don't get all of the fields.
            assert ("highest_education_level" in response.json) == (not compact)

    @pytest.mark.usefixtures("mock_retrieve_jwt_claims", "jwt_system")
    def test_record_first_medication(
        self, client: FlaskClient, patient_uuid: str
    ) -> None:
        url = f"/dhos/v1/patient/{patient_uuid}/first_medication"
        response = client.post(
            url,
            json={
                "first_medication_taken": "2 days ago",
                "first_medication_taken_recorded": "2020-01-01",
            },
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 204

    @pytest.mark.usefixtures("mock_retrieve_jwt_claims", "jwt_system")
    def test_get_patients_by_location_no_product_name(
        self,
        client: FlaskClient,
        location_uuid: str,
    ) -> None:
        response = client.get(
            f"/dhos/v2/location/{location_uuid}/patient",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 400

    def test_get_patients_abbreviated(
        self, client: FlaskClient, mocker: MockFixture, jwt_gdm_patient_uuid: str
    ) -> None:
        mock_get: Mock = mocker.patch.object(
            patient_controller,
            "get_patient_abbreviated",
            return_value={"uuid": jwt_gdm_patient_uuid},
        )
        with pytest.warns(DeprecationWarning):
            response = client.get(
                f"/dhos/v1/patient-abbreviated/{jwt_gdm_patient_uuid}",
                headers={"Authorization": "Bearer TOKEN"},
            )
        assert response.headers["Deprecation"] == "true"
        assert (
            response.headers["Link"]
            == '</dhos/v1/patient/<patient_uuid>>; rel="successor-version"'
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["uuid"] == jwt_gdm_patient_uuid
        assert mock_get.call_count == 1
        mock_get.assert_called_with(jwt_gdm_patient_uuid)

    def test_patch_patient(
        self, client: FlaskClient, mocker: MockFixture, jwt_system: str
    ) -> None:
        patient_uuid: str = generate_uuid()
        patient_update = {"first_name": "Laura"}
        mock_update: Mock = mocker.patch.object(
            patient_controller,
            "update_patient",
            return_value={"uuid": patient_uuid},
        )
        response = client.patch(
            f"/dhos/v1/patient/{patient_uuid}",
            json=patient_update,
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["uuid"] == patient_uuid
        assert mock_update.call_count == 1
        mock_update.assert_called_with(patient_uuid, patient_update)

    @pytest.mark.parametrize("jwt_scopes", ["write:gdm_patient_all"])
    def test_delete_from_patient(
        self, client: FlaskClient, mocker: MockFixture, jwt_gdm_clinician_uuid: str
    ) -> None:
        patient_uuid: str = generate_uuid()
        data_to_delete = {"record": {"diagnoses": [{"uuid": generate_uuid()}]}}
        mock_remove: Mock = mocker.patch.object(
            patient_controller,
            "remove_from_patient",
            return_value={"uuid": patient_uuid},
        )
        response = client.patch(
            f"/dhos/v1/patient/{patient_uuid}/delete",
            json=data_to_delete,
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["uuid"] == patient_uuid
        assert mock_remove.call_count == 1
        mock_remove.assert_called_with(
            patient_uuid=patient_uuid, fields_to_remove=data_to_delete
        )

    def test_post_patient_tos(
        self, client: FlaskClient, mocker: MockFixture, jwt_gdm_patient_uuid: str
    ) -> None:
        tos_uuid: str = generate_uuid()
        mock_create: Mock = mocker.patch.object(
            patient_controller,
            "create_patient_tos_v1",
            return_value={"uuid": tos_uuid},
        )
        terms_details = {
            "product_name": "GDM",
            "version": 1,
            "accepted_timestamp": "2020-01-01T00:00:00.000Z",
        }
        with pytest.warns(DeprecationWarning):
            response = client.post(
                f"/dhos/v1/patient/{jwt_gdm_patient_uuid}/terms_agreement",
                json=terms_details,
                headers={"Authorization": "Bearer TOKEN"},
            )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["uuid"] == tos_uuid
        assert mock_create.call_count == 1
        mock_create.assert_called_with(jwt_gdm_patient_uuid, terms_details)

    @pytest.mark.parametrize("jwt_scopes", ["write:gdm_patient_all"])
    def test_close_patient(
        self, client: FlaskClient, mocker: MockFixture, jwt_gdm_clinician_uuid: str
    ) -> None:
        patient_uuid: str = generate_uuid()
        product_uuid: str = generate_uuid()
        patient_update = {"closed_date": "2020-06-06"}
        mock_close: Mock = mocker.patch.object(
            patient_controller,
            "close_patient",
            return_value={"uuid": patient_uuid},
        )
        response = client.post(
            f"/dhos/v1/patient/{patient_uuid}/product/{product_uuid}/close",
            json=patient_update,
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["uuid"] == patient_uuid
        assert mock_close.call_count == 1
        mock_close.assert_called_with(patient_uuid, product_uuid, patient_update)

    @pytest.mark.parametrize("jwt_scopes", ["read:gdm_patient_all"])
    def test_get_aggregated_patients(
        self, client: FlaskClient, mocker: MockFixture, jwt_gdm_admin_uuid: str
    ) -> None:
        location_uuid: str = generate_uuid()
        patient_uuid: str = generate_uuid()
        mock_get: Mock = mocker.patch.object(
            aggregation_controller,
            "get_aggregated_patients",
            return_value=[{"uuid": patient_uuid}],
        )
        response = client.get(
            f"/dhos/v2/location/{location_uuid}/patient?product_name=GDM&active=true",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json[0]["uuid"] == patient_uuid
        assert mock_get.call_count == 1
        mock_get.assert_called_with(
            location_uuid=location_uuid, product_name="GDM", active=True
        )

    @pytest.mark.parametrize("jwt_scopes", ["write:gdm_patient_all"])
    @pytest.mark.parametrize("method,expected", [("post", True), ("delete", False)])
    def test_bookmark_patient(
        self,
        client: FlaskClient,
        mocker: MockFixture,
        method: str,
        expected: bool,
        jwt_gdm_clinician_uuid: str,
        gdm_location_uuid: str,
    ) -> None:
        patient_uuid: str = generate_uuid()
        mock_bookmark: Mock = mocker.patch.object(
            mixed_controller,
            "bookmark_patient",
            return_value={"uuid": patient_uuid},
        )
        response = client.open(
            f"/dhos/v1/location/{gdm_location_uuid}/patient/{patient_uuid}/bookmark",
            method=method,
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["uuid"] == patient_uuid
        assert mock_bookmark.call_count == 1
        mock_bookmark.assert_called_with(
            location_id=gdm_location_uuid,
            patient_id=patient_uuid,
            is_bookmarked=expected,
        )

    def test_validate_nhs_number(
        self, client: FlaskClient, mocker: MockFixture, jwt_gdm_clinician_uuid: str
    ) -> None:
        nhs_number = "1111111111"
        mock_validate: Mock = mocker.patch.object(
            patient_controller,
            "ensure_valid_nhs_number",
            return_value=True,
        )
        mock_ensure: Mock = mocker.patch.object(
            patient_controller,
            "ensure_unique_nhs_number",
            return_value=200,
        )
        response = client.post(
            f"/dhos/v1/patient/validate/{nhs_number}?product_name=GDM",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert mock_validate.call_count == 1
        mock_validate.assert_called_with(nhs_number=nhs_number)
        assert mock_ensure.call_count == 1
        mock_ensure.assert_called_with(nhs_number=nhs_number, product_name="GDM")

    def test_validate_patient_information(
        self, client: FlaskClient, mocker: MockFixture, jwt_gdm_clinician_uuid: str
    ) -> None:
        patient_details = {
            "hospital_number": "123876",
            "first_name": "Laura",
            "last_name": "Marling",
            "dob": "2020-05-05",
        }
        mock_validate: Mock = mocker.patch.object(
            patient_controller,
            "ensure_unique_patient_information",
            return_value=200,
        )
        response = client.post(
            f"/dhos/v1/patient/validate?product_name=GDM",
            json=patient_details,
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert mock_validate.call_count == 1
        mock_validate.assert_called_with(
            patient_details=patient_details, product_name="GDM"
        )

    @pytest.mark.parametrize(
        "patient_details",
        [
            {
                "blarg": "blorg",
            },
            {"hospital_number": False},
            {"hospital_number": 123456},
        ],
    )
    def test_validate_patient_invalid_request_400(
        self, client: FlaskClient, patient_details: Dict, jwt_gdm_clinician_uuid: str
    ) -> None:
        response = client.post(
            f"/dhos/v1/patient/validate?product_name=GDM",
            json=patient_details,
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "method,url,jwt_user_type,jwt_scopes",
        [
            (
                "get",
                "/dhos/v1/patient/dummy?product_name=GDM",
                "clinician",
                "read:gdm_patient_all",
            ),
            (
                "get",
                "/dhos/v1/patient-abbreviated/{uuid}",
                "patient",
                "read:gdm_patient_abbreviated",
            ),
            (
                "get",
                "/dhos/v1/location/dummy/gdm_patient",
                "clinician",
                "read:gdm_patient_all",
            ),
            (
                "get",
                "/dhos/v2/location/dummy/patient",
                "clinician",
                "read:gdm_patient_all",
            ),
            (
                "post",
                "/dhos/v1/location/dummy/patient/dummy/bookmark",
                "clinician",
                "write:gdm_patient_all",
            ),
            (
                "delete",
                "/dhos/v1/location/dummy/patient/dummy/bookmark",
                "clinician",
                "write:gdm_patient_all",
            ),
            (
                "post",
                "/dhos/v1/patient/validate/dummy",
                "clinician",
                "write:gdm_patient_all",
            ),
        ],
    )
    def test_json_body_present_400(
        self,
        client: FlaskClient,
        method: str,
        url: str,
        jwt_user_uuid: str,
    ) -> None:
        response = client.open(
            url.replace("{uuid}", jwt_user_uuid),
            method=method,
            headers={"Authorization": "Bearer TOKEN"},
            json={"some": "body"},
        )
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "method,url,jwt_user_type,jwt_scopes",
        [
            ("post", "/dhos/v1/patient_list", "clinician", "read:gdm_patient_all"),
            ("patch", "/dhos/v1/patient/dummy", "clinician", "write:gdm_patient_all"),
            (
                "patch",
                "/dhos/v1/patient/dummy/delete",
                "clinician",
                "write:gdm_patient_all",
            ),
            ("post", "/dhos/v1/patient", "clinician", "write:gdm_patient_all"),
            (
                "post",
                "/dhos/v1/patient/{uuid}/terms_agreement",
                "patient",
                "write:gdm_terms_agreement",
            ),
            (
                "post",
                "/dhos/v1/patient/dummy/product/dummy/close",
                "clinician",
                "write:gdm_patient_all",
            ),
            ("post", "/dhos/v1/patient/validate", "clinician", "write:gdm_patient_all"),
        ],
    )
    def test_json_body_not_present_400(
        self, client: FlaskClient, method: str, url: str, jwt_user_uuid: str
    ) -> None:
        response = client.open(
            url.replace("{uuid}", jwt_user_uuid),
            method=method,
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 400

    @pytest.mark.parametrize("jwt_scopes", ["write:gdm_patient_all"])
    def test_create_patient(
        self,
        client: FlaskClient,
        mocker: MockFixture,
        jwt_gdm_clinician_uuid: str,
        patient_uuid: str,
    ) -> None:
        # Arrange
        patient_details = {
            "accessibility_considerations": [],
            "allowed_to_text": True,
            "dh_products": [
                {
                    "accessibility_discussed": True,
                    "accessibility_discussed_date": "2019-04-29",
                    "accessibility_discussed_with": jwt_gdm_clinician_uuid,
                    "opened_date": "2019-04-29",
                    "product_name": "GDM",
                }
            ],
            "dob": "1992-04-23",
            "email_address": "dolly@email.com",
            "ethnicity": "185988007",
            "first_name": "Diane",
            "highest_education_level": "426769009",
            "hospital_number": "147777799",
            "last_name": "Smith",
            "locations": ["some_loc_uuid"],
            "nhs_number": "6875292351",
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
        }
        mock_create: Mock = mocker.patch.object(
            patient_controller,
            "create_patient",
            return_value={"uuid": patient_uuid, **patient_details},
        )
        # Act
        response = client.post(
            "/dhos/v1/patient?product_name=GDM",
            json=patient_details,
            headers={"Authorization": "Bearer TOKEN"},
        )
        # Assert
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["uuid"] == patient_uuid
        mock_create.assert_called_with(
            product_name="GDM",
            patient_details=patient_details,
        )

    @pytest.mark.usefixtures("mock_retrieve_jwt_claims", "gdm_jwt_clinician_uuid")
    def test_patient_uuids(self, mocker: MockFixture, client: FlaskClient) -> None:
        expected: List = ["patient_uuid_1", "patient_uuid_2"]

        mock_method = mocker.patch.object(
            patient_controller, "get_patient_uuids", return_value=expected
        )
        response = client.get(
            "/dhos/v1/patient_uuids?product_name=GDM",
            headers={"Authorization": "Bearer TOKEN"},
        )

        mock_method.assert_called_once()
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        assert response.json == expected
