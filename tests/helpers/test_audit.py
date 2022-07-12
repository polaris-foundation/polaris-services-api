import uuid

import kombu_batteries_included
import pytest
from mock import Mock
from pytest_mock import MockerFixture

from dhos_services_api.helpers import audit


@pytest.mark.usefixtures("app", "jwt_user_uuid")
class TestAudit:
    @pytest.fixture
    def mock_publish_audit(self, mocker: MockerFixture) -> Mock:
        return mocker.patch.object(kombu_batteries_included, "publish_message")

    def test_record_patient_viewed(
        self, mock_publish_audit: Mock, jwt_user_uuid: str
    ) -> None:
        patient_uuid = str(uuid.uuid4())
        audit.record_patient_viewed(patient_uuid=patient_uuid)
        expected = {
            "event_type": "Patient information viewed",
            "event_data": {
                "patient_id": patient_uuid,
                "clinician_id": jwt_user_uuid,
            },
        }
        mock_publish_audit.assert_called_with(
            routing_key="dhos.34837004", body=expected
        )

    def test_record_patient_updated(
        self, mock_publish_audit: Mock, jwt_user_uuid: str
    ) -> None:
        patient_uuid = str(uuid.uuid4())
        audit.record_patient_updated(patient_uuid=patient_uuid)
        expected = {
            "event_type": "Patient information updated",
            "event_data": {
                "patient_id": patient_uuid,
                "clinician_id": jwt_user_uuid,
            },
        }
        mock_publish_audit.assert_called_with(
            routing_key="dhos.34837004", body=expected
        )

    def test_record_patient_archived(
        self, mock_publish_audit: Mock, jwt_user_uuid: str
    ) -> None:
        patient_uuid = str(uuid.uuid4())
        audit.record_patient_archived(patient_uuid=patient_uuid)
        expected = {
            "event_type": "Patient information archived",
            "event_data": {
                "patient_id": patient_uuid,
                "clinician_id": jwt_user_uuid,
            },
        }
        mock_publish_audit.assert_called_with(
            routing_key="dhos.34837004", body=expected
        )

    def test_record_patient_diabetes_type_changed(
        self, mock_publish_audit: Mock, jwt_user_uuid: str
    ) -> None:
        patient_uuid = str(uuid.uuid4())
        new_type = "new_type"
        old_type = "old_type"
        audit.record_patient_diabetes_type_changed(
            patient_uuid=patient_uuid, new_type=new_type, old_type=old_type
        )
        expected = {
            "event_type": "GDM Patient diabetes type changed",
            "event_data": {
                "patient_id": patient_uuid,
                "old_type": old_type,
                "new_type": new_type,
                "clinician_id": jwt_user_uuid,
            },
        }
        mock_publish_audit.assert_called_with(
            routing_key="dhos.34837004", body=expected
        )
