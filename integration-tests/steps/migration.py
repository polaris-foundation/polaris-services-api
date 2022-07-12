import base64
from typing import Any, Dict, List

import dictdiffer
from behave import given, step, when
from behave.runner import Context
from clients import (
    locations_api_client,
    neo4j_client,
    rabbitmq_client,
    services_api_client,
    users_api_client,
)
from clients.locations_api_client import reset_locations_api
from clients.ssh_client import run_on_dhos_services
from clients.users_api_client import get_all_clinicians, reset_users_api
from neo4j import StatementResult
from steps.patient import RABBITMQ_MESSAGES


@given("the locations database is empty")
def reset_locations_db(context: Context) -> None:
    reset_locations_api(context)


@given("the users database is empty")
def reset_users_db(context: Context) -> None:
    reset_users_api(context)


@step("we migrate the clinicians")
def migrate_clinicians(context: Context) -> None:
    output = run_on_dhos_services(
        "flask migrate clinicians",
    )
    clinician_count = context.clinician_count
    for msg in [
        "Migrating clinician data to users API",
        f"Retrieved {clinician_count} clinicians from NEO4J",
        f"Bulk uploading {clinician_count} clinicians",
        f"Created {clinician_count} clinicians",
        "Migration completed",
    ]:
        assert msg in output, f"{msg} not in {output}"

    assert "exception" not in output.lower(), f"Exception: {output}"


@step("we migrate the patients")
def migrate_patients(context: Context) -> None:
    output = run_on_dhos_services(
        "flask migrate patients",
    )
    patient_count = context.patient_count
    print(f"\n\n{output}\n\n")
    # Expect twice the patient_count below because each patient has a baby, which is another patient under the hood.
    for msg in [
        "Migrating patient data to Postgresql",
        f"Bulk uploading {patient_count*2} Patients",
        f"Created {patient_count*2} new Patients",
        "Migration completed",
    ]:
        assert msg in output, f"{msg} not in {output}"

    assert "exception" not in output.lower(), f"Exception: {output}"


@when("we fetch the location hierarchy from locations API")
def fetch_location_api_hierarchy(context: Context) -> None:
    context.hierarchy = locations_api_client.get_all_locations(
        context=context,
        product_name="SEND",
        location_types="225746001|22232009",
        compact=True,
        active=True,
        children=True,
    )


@when("we fetch the clinicians from users API")
def fetch_clinicians(context: Context) -> None:
    context.migrated_clinicians = get_all_clinicians(
        context=context, compact=True, expanded=False
    )


@when("we fetch the patients from services API \(postgres\)")
def fetch_patients_postgres(context: Context) -> None:
    context.migrated_patients = services_api_client.retrieve_patients_by_uuids(
        context=context, uuids=context.original_patient_uuids, product_name="GDM"
    )


@step("we received all of the expected locations from locations API")
def check_location_hierarchy(context: Context) -> None:
    hierarchy: Dict[str, Dict[str, Any]] = context.hierarchy
    expected_count = context.hospital_count * (context.ward_count + 1)
    assert (
        len(hierarchy) == expected_count
    ), f"Expected {expected_count} locations, got {len(hierarchy)}"
    for location in hierarchy.values():
        location_type = location["location_type"]
        assert location_type in ["225746001", "22232009"]
        if location_type == "22232009":
            # Hospital
            assert location["parent"] is None
            assert len(location["children"]) == context.ward_count * (
                context.bay_count * (context.bed_count + 1) + 1
            )
        else:
            # Ward
            parent = hierarchy[location["parent"]["uuid"]]
            expected_parent = {
                k: parent[k]
                for k in (
                    "uuid",
                    "parent",
                    "location_type",
                    "ods_code",
                    "display_name",
                )
            }

            assert location["parent"] == expected_parent
            assert len(location["children"]) == context.bay_count * (
                context.bed_count + 1
            )


@step("we received all of the expected clinicians from users API")
def check_clinicians_migrated(context: Context) -> None:
    migrated_clinicians: List[Dict[str, Any]] = context.migrated_clinicians
    expected_count = context.clinician_count
    assert (
        len(migrated_clinicians) == expected_count
    ), f"Expected {expected_count} clinicians, got {len(migrated_clinicians)}"
    assert {c["uuid"] for c in migrated_clinicians} == set(
        context.original_clinician_uuids
    )
    for clinician in migrated_clinicians:
        for field in [
            "created",
            "created_by",
            "modified_by",
            "modified",
            "first_name",
            "last_name",
        ]:
            assert clinician[field] is not None


@step("we received all of the expected patients from services API")
def check_patients_migrated(context: Context) -> None:
    migrated_patients: List[Dict[str, Any]] = context.migrated_patients
    expected_count = context.patient_count
    assert (
        len(migrated_patients) == expected_count
    ), f"Expected {expected_count} patients, got {len(migrated_patients)}"
    assert {p["uuid"] for p in migrated_patients} == set(context.original_patient_uuids)
    for patient in migrated_patients:
        for field in [
            "created",
            "created_by",
            "modified_by",
            "modified",
            "first_name",
            "last_name",
        ]:
            assert patient[field] is not None


@step("the migrated clinicians have the same details as the originals")
def verify_clinician_details_identical(context: Context) -> None:
    cypher_query = """MATCH (c:Clinician) RETURN 
        c.uuid AS uuid, 
        c.first_name AS first_name, 
        c.email_address AS email_address
    """
    results: StatementResult = neo4j_client.execute_cypher(context, cypher_query)
    neo4j_clinician_details: Dict[str, Dict] = {
        record["uuid"]: {
            "first_name": record["first_name"],
            "email_address": record["email_address"],
        }
        for record in results
    }
    after_clinicians: Dict[str, Dict] = users_api_client.retrieve_clinicians_by_uuids(
        context=context, uuids=context.original_clinician_uuids
    )
    for c_uuid in context.original_clinician_uuids:
        assert (
            neo4j_clinician_details[c_uuid]["first_name"]
            == after_clinicians[c_uuid]["first_name"]
        )
        assert (
            neo4j_clinician_details[c_uuid]["email_address"]
            == after_clinicians[c_uuid]["email_address"]
        )


@step("the migrated patients have the same details as the originals")
def verify_patient_details_identical(context: Context) -> None:
    before_patients: List[Dict] = services_api_client.retrieve_patients_by_uuids_neo4j(
        context=context, uuids=context.original_patient_uuids, product_name="GDM"
    )
    after_patients: List[Dict] = context.migrated_patients
    before_patients_map = {p["uuid"]: p for p in before_patients}
    after_patients_map = {p["uuid"]: p for p in after_patients}

    for c_uuid in context.original_patient_uuids:
        expected = before_patients_map[c_uuid]
        actual = after_patients_map[c_uuid]

        diffs = "\n".join(
            f"{op} {location} {a!r} -> {b!r}"
            for op, location, (a, b) in dictdiffer.diff(expected, actual)
        )
        assert expected == actual, f"\nDifferences: {diffs}"


@step("the migrated clinicians can log in via the Users API")
def verify_clinician_login(context: Context) -> None:
    clinician_details_map: Dict[
        str, Dict
    ] = users_api_client.retrieve_clinicians_by_uuids(
        context=context, uuids=context.original_clinician_uuids
    )
    for c_uuid in context.original_clinician_uuids:
        username = clinician_details_map[c_uuid]["email_address"]
        password = (
            c_uuid + "-password"
        )  # Set when the clinician was created earlier in the test
        auth_header_raw = username + ":" + password
        auth_header = str(base64.b64encode(auth_header_raw.encode("utf-8")), "utf-8")
        users_api_login_details = users_api_client.clinician_login(
            context=context, basic_auth_value=auth_header
        )
        assert users_api_login_details["user_id"] == c_uuid
        # Check audit message was published
        rabbitmq_client.get_rabbitmq_message(
            context, RABBITMQ_MESSAGES["AUDIT_MESSAGE"]
        )
