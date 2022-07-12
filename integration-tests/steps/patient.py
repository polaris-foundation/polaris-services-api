from typing import Any, Dict, List

import dictdiffer
import draymed
import requests
from behave import given, step, then, use_fixture, when
from behave.runner import Context
from clients import locations_api_client, services_api_client, users_api_client
from clients.neo4j_client import clear_neo4j_database
from clients.rabbitmq_client import (
    assert_rabbitmq_message_queues_are_empty,
    create_rabbitmq_connection,
    create_rabbitmq_queues,
    get_rabbitmq_message,
)
from helpers.sample_data import minimal_patient_data, patient_data
from she_logging import logger

RABBITMQ_MESSAGES = {
    "AUDIT_MESSAGE": "dhos.34837004",
    "CLINICIAN_CREATED_MESSAGE": "dhos.D9000001",
    "CLINICIAN_UPDATED_MESSAGE": "dhos.D9000002",
    "EMAIL_NOTIFICATION_MESSAGE": "dhos.DM000017",
}
MESSAGE_NAMES = "|".join(RABBITMQ_MESSAGES)

CLOSE_REASON_CODES = {
    v["long"].upper().replace(" ", "_"): k
    for k, v in draymed.codes.list_category("closed_reason").items()
}


@given("RabbitMQ is running")
def rabbitmq_is_running(context: Context) -> None:
    if not hasattr(context, "rabbit_connection"):
        context.rabbit_connection = use_fixture(create_rabbitmq_connection, context)
        use_fixture(create_rabbitmq_queues, context, routing_keys=RABBITMQ_MESSAGES)


@given("the database is empty")
def database_empty(context: Context) -> None:
    use_fixture(services_api_client.drop_data, context)
    if not hasattr(context, "neo4j_session"):
        context.neo4j_session = use_fixture(clear_neo4j_database, context)


@given("the services API is running")
def services_api_is_running(context: Context) -> None:
    response = requests.get(url=f"{services_api_client.base_url}/running")
    assert response.status_code == 200


@given("a clinician exists")
def clinician_exists(context: Context) -> None:
    location_data = {
        "address_line_1": "Address",
        "postcode": "",
        "country": "",
        "location_type": "D0000009",
        "ods_code": "L20",
        "display_name": "Theme Hospital",
        "dh_products": [{"product_name": "GDM", "opened_date": "2000-01-01"}],
    }
    context.location_uuid = locations_api_client.post_location(context, location_data)[
        "uuid"
    ]

    clinician_data = {
        "first_name": "Sam",
        "last_name": "Tarly",
        "phone_number": "07123456770",
        "nhs_smartcard_number": "211213",
        "email_address": "sam@nhs.com",
        "job_title": "winner",
        "locations": [context.location_uuid],
        "groups": ["GDM Clinician"],
        "products": [{"product_name": "GDM", "opened_date": "2017-01-01"}],
    }

    context.clinician_uuid = users_api_client.post_clinician(context, clinician_data)

    # Eat the rabbit notification of a new clinician
    logger.info(f"Consuming {RABBITMQ_MESSAGES['CLINICIAN_CREATED_MESSAGE']} message")
    get_rabbitmq_message(context, RABBITMQ_MESSAGES["CLINICIAN_CREATED_MESSAGE"])


@step(
    "a(?:nother)? (?P<closed>\w+)?(?: with reason )?(?P<close_reason>\w+)?\s*(?P<product_name>\w+) patient exists"
)
def patient_exists(
    context: Context, closed: str, close_reason: str, product_name: str
) -> None:
    patient_json = patient_data(
        context,
        accessibility_discussed_with=context.clinician_uuid,
        location=context.location_uuid,
        allowed_to_text=False,
    )
    if closed == "closed":
        patient_json["dh_products"][0]["closed_date"] = patient_json["dh_products"][0][
            "opened_date"
        ]

    if close_reason is not None:
        patient_json["dh_products"][0]["closed_reason"] = CLOSE_REASON_CODES[
            close_reason
        ]
        patient_json["dh_products"][0]["closed_reason_other"] = "Test"

    patient_uuid: str = services_api_client.post_patient(
        context=context, patient=patient_json, product_name=product_name
    )
    context.patient_requests[patient_uuid] = patient_json
    context.patient_uuids.append(patient_uuid)
    # TODO: remove this when PLAT-694, PLAT-696, and PLAT-697 are complete
    context.patient_uuid = patient_uuid


@step("a minimal (?P<product_name>\w+) patient exists")
def mininal_patient_exists(context: Context, product_name: str) -> None:
    patient_json = minimal_patient_data(
        context,
        accessibility_discussed_with=None,
        location=context.location_uuid,
        allowed_to_text=False,
    )
    patient_uuid: str = services_api_client.post_patient(
        context=context, patient=patient_json, product_name=product_name
    )
    context.patient_requests[patient_uuid] = patient_json
    context.patient_uuids.append(patient_uuid)
    # TODO: remove this when PLAT-694, PLAT-696, and PLAT-697 are complete
    context.patient_uuid = patient_uuid


@when("a new patient is posted successfully")
def new_patient_is_posted(context: Context) -> None:
    patient_json = patient_data(
        context,
        accessibility_discussed_with=context.clinician_uuid,
        location=context.location_uuid,
    )
    patient_uuid: str = services_api_client.post_patient(
        context=context, patient=patient_json, product_name="GDM"
    )
    context.patient_requests[patient_uuid] = patient_json
    context.patient_uuids.append(patient_uuid)
    # TODO: remove this when PLAT-694, PLAT-696, and PLAT-697 are complete
    context.patient_uuid = patient_uuid


@when("I view the patient")
def view_patient(context: Context) -> None:
    if not isinstance(context.patient_uuids, list):
        raise ValueError("context.patient_uuids is not a list")
    patient = services_api_client.get_patient(
        context=context, patient_uuid=context.patient_uuids[-1], product_name="GDM"
    )
    assert patient["uuid"] == context.patient_uuids[-1]


@then("the patient is saved in the database")
def patient_is_saved_in_database(context: Context) -> None:
    if not isinstance(context.patient_uuids, list):
        raise ValueError("context.patient_uuids is not a list")
    patient = services_api_client.get_patient(
        context=context, patient_uuid=context.patient_uuids[-1], product_name="GDM"
    )
    assert patient["uuid"] == context.patient_uuids[-1]
    assert patient["hospital_number"] == "a1b2c3d4e5f6"
    assert (
        patient["record"]["diagnoses"][0]["observable_entities"][0]["value_as_string"]
        == "A value"
    )


@step(f"a (?P<message_name>\w+) message is published to RabbitMQ")
def message_published_to_rabbitmq(context: Context, message_name: str) -> None:
    get_rabbitmq_message(context, RABBITMQ_MESSAGES[message_name])


@step("the RabbitMQ queues are empty")
def step_impl(context: Context) -> None:
    assert_rabbitmq_message_queues_are_empty(context)


# calls /dhos/v2/location/{location_id}/patient
@step("the (?P<product_name>\w+) patient is found in the list of patients")
def assert_patient_is_in_patient_list(context: Context, product_name: str) -> None:
    if not isinstance(context.patient_uuids, list):
        raise ValueError("context.patient_uuids is not a list")
    full_patient_body: Dict[str, Any] = services_api_client.get_patient(
        context=context,
        patient_uuid=context.patient_uuids[-1],
        product_name=product_name,
    )
    # getting full patient body from API produces an AUDIT_MESSAGE, read it
    get_rabbitmq_message(context, RABBITMQ_MESSAGES["AUDIT_MESSAGE"])
    if not isinstance(context.patient_uuids, list):
        raise ValueError("context.patient_uuids is not a list")
    patients: List[Dict] = [
        p for p in context.patient_list if p["uuid"] == context.patient_uuids[-1]
    ]
    assert len(patients) == 1

    # remove fields where difference is expected
    # FIXME: PLAT-707 raised for `clinician_bookmark`
    if "clinician_bookmark" in patients[0]:
        del patients[0]["clinician_bookmark"]
    if "clinician_bookmark" in full_patient_body:
        del full_patient_body["clinician_bookmark"]

    diffs = "\n".join(
        f"{op} {location} {ab!r}"
        for op, location, ab in dictdiffer.diff(patients[0], full_patient_body)
    )

    assert full_patient_body == patients[0], f"\nDifferences: {diffs}"


# calls /dhos/v1/location/{location_id}/gdm_patient
@step(
    "the (?P<ordinal>\d+)?\w*\s*patient is found in the list of GDM patients for location"
)
def assert_patient_is_in_gdm_patient_list(context: Context, ordinal: str) -> None:
    if not isinstance(context.patient_uuids, list):
        raise ValueError("context.patient_uuids is not a list")

    if not ordinal:
        # we want the last created patient
        patient_uuid: str = context.patient_uuids[-1]
    else:
        patient_uuid = context.patient_uuids[int(ordinal) - 1]
    patients: List[Dict] = [
        p for p in context.patient_list if p["uuid"] == patient_uuid
    ]
    assert len(patients) == 1

    # patient found by this endpoint has only some fields from the full patient record
    for field in ["nhs_number", "hospital_number", "first_name", "last_name", "sex"]:
        assert context.patient_requests[patient_uuid][field] == patients[0][field]
    assert (
        context.patient_requests[patient_uuid]["record"]["diagnoses"][0]["sct_code"]
        == patients[0]["record"]["diagnoses"][0]["sct_code"]
    )
    assert (
        context.patient_requests[patient_uuid]["record"]["diagnoses"][0]["diagnosed"]
        == patients[0]["record"]["diagnoses"][0]["diagnosed"]
    )
    assert (
        context.patient_requests[patient_uuid]["record"]["pregnancies"][0][
            "estimated_delivery_date"
        ]
        == patients[0]["record"]["pregnancies"][0]["estimated_delivery_date"]
    )


# calls /dhos/v1/location/{location_id}/gdm_patient
@step(
    "the (?P<ordinal>\d+)?\w*\s*patient is not found in the list of GDM patients for location"
)
def assert_patient_is_not_in_gdm_patient_list(context: Context, ordinal: str) -> None:
    if not isinstance(context.patient_uuids, list):
        raise ValueError("context.patient_uuids is not a list")
    if not ordinal:
        # we want the last created patient
        patient_uuid: str = context.patient_uuids[-1]
    else:
        patient_uuid = context.patient_uuids[int(ordinal) - 1]
    patient_uuids: List[Dict] = [p["uuid"] for p in context.patient_list]
    assert patient_uuid not in patient_uuids


@step("I update the patient")
def update_patient(context: Context) -> None:
    data: Dict = {
        "record": {
            "diagnoses": [
                {
                    "diagnosed": "2021-05-29",
                    "presented": "2021-05-29",
                    "diagnosis_tool": ["D0000012", "D0000013", "D0000018"],
                    "diagnosis_tool_other": "",
                    "uuid": context.patient_response["record"]["diagnoses"][0]["uuid"],
                    "observable_entities": [
                        {
                            "sct_code": "113076002",
                            "date_observed": "2021-02-05",
                            "value_as_string": "50",
                            "metadata": {"1hr": "5.5"},
                            "uuid": context.patient_response["record"]["diagnoses"][0][
                                "observable_entities"
                            ][0]["uuid"],
                        }
                    ],
                }
            ]
        }
    }

    services_api_client.patch_patient(
        context, patient_uuid=context.patient_uuid, data=data, product_name="GDM"
    )


@step("a request for patient UUIDs returns list of UUIDs")
def patient_list_uuids(context: Context) -> None:
    response = services_api_client.get_patient_uuids(context, product_name="GDM")
    assert response == [context.patient_uuid]


@step("a request for the patient list returns the patient")
def patient_list(context: Context) -> None:
    response = services_api_client.get_patient_list(
        context, product_name="GDM", locs=[context.location_uuid]
    )
    assert "readings_plan" in response[0]["record"]["diagnoses"][0]
    assert response[0]["dh_products"][0]["monitored_by_clinician"] is True
    assert response[0]["uuid"] == context.patient_uuid
