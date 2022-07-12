from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from dhos_services_api.helpers import security


@pytest.mark.usefixtures("app")
class TestSecurity:
    def test_current_user_is_specified_patient_success(
        self, mocker: MockerFixture, gdm_patient_uuid: str, jwt_gdm_patient_uuid: str
    ) -> None:
        mock_request: Mock = mocker.patch("dhos_services_api.helpers.security.request")
        mock_request.view_args = {"patient_id": gdm_patient_uuid, "product_name": "GDM"}
        result = security.current_user_is_specified_patient_or_any_gdm_clinician(
            jwt_claims={
                "patient_id": gdm_patient_uuid,
            },
            claims_map={},
        )
        assert result is True

    def test_current_user_is_specified_patient_failure(
        self, mocker: MockerFixture, gdm_patient_uuid: str, jwt_gdm_patient_uuid: str
    ) -> None:
        mock_request: Mock = mocker.patch("dhos_services_api.helpers.security.request")
        mock_request.view_args = {
            "patient_id": "OTHER_PATIENT_UUID",
            "product_name": "GDM",
        }
        result = security.current_user_is_specified_patient_or_any_gdm_clinician(
            jwt_claims={
                "patient_id": gdm_patient_uuid,
            },
            claims_map={},
        )
        assert result is False

    def test_current_user_is_specified_clinician_success(
        self, mocker: MockerFixture, gdm_patient_uuid: str, jwt_gdm_clinician_uuid: str
    ) -> None:
        mock_request: Mock = mocker.patch("dhos_services_api.helpers.security.request")
        mock_request.view_args = {"patient_id": gdm_patient_uuid}
        mock_request.args = {
            "product_name": "GDM",
        }
        result = security.current_user_is_specified_patient_or_any_gdm_clinician(
            jwt_claims={
                "clinician_id": jwt_gdm_clinician_uuid,
            },
            claims_map={},
        )
        assert result is True

    def test_current_user_is_specified_clinician_fail(
        self, mocker: MockerFixture, gdm_patient_uuid: str, jwt_gdm_clinician_uuid: str
    ) -> None:
        mock_request: Mock = mocker.patch("dhos_services_api.helpers.security.request")
        mock_request.view_args = {
            "patient_id": gdm_patient_uuid,
            "product_name": "SEND",
        }
        result = security.current_user_is_specified_patient_or_any_gdm_clinician(
            jwt_claims={
                "clinician_id": jwt_gdm_clinician_uuid,
            },
            claims_map={},
        )
        assert result is False
