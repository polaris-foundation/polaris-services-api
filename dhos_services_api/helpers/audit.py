from typing import Any, Dict, Optional

from flask import g
from she_logging import logger

from dhos_services_api.helpers import publish


def _record_patient_event(event_type: str, event_data: Dict[str, Any]) -> None:
    clinician_uuid: Optional[str] = g.jwt_claims.get("clinician_id")

    if clinician_uuid is None:
        logger.info("User is not a clinician, skipping audit message")
        return

    event_data["clinician_id"] = clinician_uuid
    publish.audit_message(event_type=event_type, event_data=event_data)


def record_patient_viewed(patient_uuid: str) -> None:
    logger.debug(
        "Recording audit message for clinician viewing patient %s", patient_uuid
    )
    _record_patient_event(
        event_type="Patient information viewed",
        event_data={"patient_id": patient_uuid},
    )


def record_patient_updated(patient_uuid: str) -> None:
    logger.info(
        "Recording audit message for clinician updating patient %s", patient_uuid
    )
    _record_patient_event(
        event_type="Patient information updated",
        event_data={"patient_id": patient_uuid},
    )


def record_patient_archived(patient_uuid: str) -> None:
    logger.info(
        "Recording audit message for clinician archiving patient %s", patient_uuid
    )
    _record_patient_event(
        event_type="Patient information archived",
        event_data={"patient_id": patient_uuid},
    )


def record_patient_diabetes_type_changed(
    patient_uuid: str, new_type: str, old_type: str
) -> None:
    logger.info(
        "Recording audit message for clinician changing diabetes type for patient %s",
        patient_uuid,
    )
    event_data = {
        "patient_id": patient_uuid,
        "old_type": old_type,
        "new_type": new_type,
    }
    _record_patient_event(
        event_type="GDM Patient diabetes type changed", event_data=event_data
    )


def record_patient_not_monitored_anymore(patient_id: str, product_id: str) -> None:
    logger.info(
        "Recording audit message for clinician stopping monitoring patient %s for product %s",
        patient_id,
        product_id,
    )
    _record_patient_event(
        event_type="Stopped monitoring patient",
        event_data={"patient_id": patient_id, "product_id": product_id},
    )


def record_patient_monitored(patient_id: str, product_id: str) -> None:
    logger.info(
        "Recording audit message for clinician starting monitoring patient %s for product %s",
        patient_id,
        product_id,
    )
    _record_patient_event(
        event_type="Started monitoring patient",
        event_data={"patient_id": patient_id, "product_id": product_id},
    )
