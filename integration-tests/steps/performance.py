import codecs
import random
import string
import time
from datetime import date, datetime
from typing import Any, Dict, Generator, List, Tuple
from uuid import uuid4

import draymed
from behave import given, step, when
from behave.runner import Context
from clients import locations_api_client, services_api_client
from clients.neo4j_client import execute_cypher
from Cryptodome.Protocol.KDF import scrypt
from faker import Faker
from helpers.locations import (
    bay_factory,
    bed_factory,
    hospital_factory,
    slugify,
    ward_factory,
)
from helpers.sample_data import patient_data
from requests import Response
from she_logging import logger

HOSPITAL_SNOMED: str = draymed.codes.code_from_name("hospital", "location")
WARD_SNOMED: str = draymed.codes.code_from_name("ward", "location")
BAY_SNOMED: str = draymed.codes.code_from_name("bay", "location")
BED_SNOMED: str = draymed.codes.code_from_name("bed", "location")

fake = Faker()


def _location_fields(
    display_name: str, ods_code: str, uuid: str, location_type: str, clinician: str
) -> str:
    now = datetime.now().timestamp()
    return f"""{{
        created_by_: "{clinician}",
        ods_code: "{ods_code}",
        created: "{now}",
        modified: "{now}",
        active: TRUE,
        display_name: "{display_name}",
        uri: "http://snomed.codes",
        uuid: "{uuid}",
        location_type: "{location_type}",
        modified_by_: "{clinician}"}}"""


def _terms_agreement_fields(clinician_uuid: str, product_name: str) -> str:
    now = datetime.now().timestamp()
    return f"""{{
        uuid: "{str(uuid4())}",
        uri: "http://snomed.codes",
        created_by_: "{clinician_uuid}",
        created: "{now}",
        modified_by_: "{clinician_uuid}",
        modified: "{now}",
        product_name: "{product_name}",
        accepted_timestamp_: "{now}",
        accepted_timestamp_tz: 0}}"""


def _clinician_fields(clinician_uuid: str, product_name: str) -> str:
    now = datetime.now().timestamp()

    # Mock up a password.
    raw_password = clinician_uuid + "-password"
    salt = "".join(random.choices(string.ascii_uppercase, k=32))
    hash_bytes: bytes = scrypt(bytes(raw_password, "utf8"), bytes(salt, "utf8"), 256, 16384, 8, 1)  # type: ignore
    hash_str: str = codecs.encode(hash_bytes, "hex_codec").decode()

    return f"""{{
        uuid: "{clinician_uuid}",
        uri: "http://snomed.codes",
        created_by_: "{str(uuid4())}",
        created: "{now}",
        modified_by_: "{str(uuid4())}",
        modified: "{now}",
        first_name: "{fake.first_name()}",
        last_name: "{fake.last_name()}",
        phone_number: "{fake.phone_number()}", 
        nhs_smartcard_number: "{fake.random_number(digits=10)}", 
        send_entry_identifier: "{fake.random_number(digits=12)}",
        job_title: "Doctor",
        email_address: "{fake.unique.email()}",
        can_edit_ews: "{fake.boolean()}",
        professional_registration_number: "{fake.random_number(digits=10)}",
        agency_name: "Some agency",
        agency_staff_employee_number: "{fake.random_number(digits=10)}", 
        booking_reference: "{fake.random_number(digits=10)}",
        contract_expiry_eod_date_: "{fake.date_this_century(before_today = False, after_today=True)}",
        locations: [{", ".join('"' + str(uuid4()) + '"' for _ in range(random.randrange(5)))}],
        groups: ["{product_name} Clinician"],
        password_hash: "{hash_str}",
        password_salt: "{salt}",
        login_active: "{fake.boolean()}",
        bookmarks: [{", ".join('"' + str(uuid4()) + '"' for _ in range(random.randrange(5)))}],
        analytics_consent: "{fake.boolean()}",
        can_edit_encounter: "{fake.boolean()}"}}"""


def _product_fields(
    clinician_uuid: str, product_name: str = "SEND", opened_date: date = None
) -> str:
    uuid = str(uuid4())
    now = datetime.now().timestamp()
    if opened_date is None:
        opened_date = datetime.now().date()

    return f"""{{
        created_by_: "{clinician_uuid}",
        created: "{now}",
        modified: "{now}",
        opened_date: "{str(opened_date)}",
        product_name: "{product_name}",
        uuid: "{uuid}",
        modified_by_: "{clinician_uuid}"}}"""


def create_single_clinician(clinician_uuid: str, index: int, product_name: str) -> str:
    cypher = f"""(c{index}:Clinician{
        _clinician_fields(clinician_uuid=clinician_uuid, product_name=product_name)
    }), (p{index}:ClinicianProduct{
        _product_fields(clinician_uuid=clinician_uuid, product_name=product_name)
    }), (c{index})-[:ACTIVE_ON_PRODUCT]->(p{index}), (t{index}:TermsAgreement{
        _terms_agreement_fields(clinician_uuid=clinician_uuid, product_name=product_name)
    }), (c{index})-[:HAS_ACCEPTED]->(t{index}), (pat{index}:Patient{{uuid: "{str(uuid4())}"}}), (c{index})<-[:BOOKMARKED_BY]-(pat{index})"""
    return cypher


def create_single_location(
    index: int,
    clinician_uuid: str,
    display_name: str,
    ods_code: str,
    location_type: str,
    parentindex: int = None,
) -> str:
    uuid = str(uuid4())
    cypher = f"""(l{index}:Location{
        _location_fields(display_name, ods_code, uuid, location_type, clinician_uuid)
    }), (p{index}:LocationProduct{
        _product_fields(clinician_uuid)
    }), (l{index})-[:ACTIVE_ON_PRODUCT]->(p{index})"""
    if parentindex is not None:
        cypher += f""",(l{index})-[:CHILD_OF]->(l{parentindex})"""
    return cypher


@given(
    """(?P<hospitals>\d+) hospitals each with (?P<wards>\d+) wards each with (?P<bays>\d+) bays of (?P<beds>\d+) beds exists in neo4j"""
)
def bulk_create_locations(
    context: Context, hospitals: str, wards: str, bays: str, beds: str
) -> None:
    clinician_uuid = context.clinician_uuid
    context.hospital_count, context.ward_count, context.bay_count, context.bed_count = (
        int(hospitals),
        int(wards),
        int(bays),
        int(beds),
    )
    context.total_location_count = context.hospital_count * (
        context.ward_count * (context.bay_count * (context.bed_count + 1) + 1) + 1
    )
    locations = []
    index = 0
    for hospital in range(1, context.hospital_count + 1):
        hospital_index = index
        locations.append(
            create_single_location(
                hospital_index,
                clinician_uuid,
                display_name=f"Hospital {hospital}",
                ods_code=f"H{hospital}",
                location_type=HOSPITAL_SNOMED,
            )
        )
        index += 1
        for ward in range(1, context.ward_count + 1):
            ward_index = index
            locations.append(
                create_single_location(
                    index,
                    clinician_uuid,
                    display_name=f"Ward {hospital}-{ward}",
                    ods_code=f"W{hospital}-{ward}",
                    location_type=WARD_SNOMED,
                    parentindex=hospital_index,
                )
            )
            index += 1
            for bay in range(1, context.bay_count + 1):
                bay_index = index
                locations.append(
                    create_single_location(
                        index,
                        clinician_uuid,
                        display_name=f"Bay {hospital}-{ward}-{bay}",
                        ods_code=f"Y{hospital}-{ward}-{bay}",
                        location_type=BAY_SNOMED,
                        parentindex=ward_index,
                    )
                )
                index += 1
                for bed in range(1, context.bed_count + 1):
                    locations.append(
                        create_single_location(
                            index,
                            clinician_uuid,
                            display_name=f"Bed {hospital}-" f"{ward}-{bay}-{bed}",
                            ods_code=f"B{hospital}-{ward}-{bay}-{bed}",
                            location_type=BED_SNOMED,
                            parentindex=bay_index,
                        )
                    )
                    index += 1

        clauses = ",\n".join(locations)
        execute_cypher(context, f"CREATE {clauses} RETURN TRUE")
        locations = []


@given("""(?P<num_clinicians>\d+) clinicians exist in neo4j""")
def bulk_create_clinicians(context: Context, num_clinicians: str) -> None:
    context.clinician_count = int(num_clinicians)
    context.original_clinician_uuids = []
    cypher_clauses: List[str] = []
    index = 0
    for clinician in range(1, context.clinician_count + 1):
        clinician_uuid = str(uuid4())
        context.original_clinician_uuids.append(clinician_uuid)
        cypher_clauses.append(
            create_single_clinician(
                clinician_uuid=clinician_uuid,
                index=index,
                product_name=random.choice(["SEND", "GDM", "DBM"]),
            )
        )
        index += 1
    cypher_statement = ",\n".join(cypher_clauses)
    execute_cypher(context, f"CREATE {cypher_statement} RETURN TRUE")


@given("""(?P<num_patients>\d+) patients exist in neo4j""")
def bulk_create_patients(context: Context, num_patients: str) -> None:
    context.patient_count = int(num_patients)
    context.original_patient_uuids = []
    for i in range(1, context.patient_count + 1):
        logger.info("Creating patient %d of %d", i, context.patient_count)
        patient_json = patient_data(
            context,
            accessibility_discussed_with="static-clinician-uuid",
            location="static-location-uuid",
        )
        patient_uuid = services_api_client.post_patient_neo4j(
            context=context, patient=patient_json, product_name="GDM"
        )
        context.original_patient_uuids.append(patient_uuid)


def names(category: str, count: str) -> Generator[Tuple[str, int, str], None, None]:
    for c in range(int(count)):
        name = f"{category} {c+1}"
        ods_code = slugify(name)
        yield name, c + 1, ods_code


@given(
    """(?P<hospitals>\d+) hospitals each with (?P<wards>\d+) wards each with (?P<bays>\d+) bays """
    """of (?P<beds>\d+) beds exists in postgres"""
)
def bulk_create_locations_postgres(
    context: Context, hospitals: str, wards: str, bays: str, beds: str
) -> None:
    context.hospital_count, context.ward_count, context.bay_count, context.bed_count = (
        int(hospitals),
        int(wards),
        int(bays),
        int(beds),
    )
    locations = []
    for hospital, hospital_index, hospital_ods_code in names("Hospital", hospitals):
        hospital_uuid = str(uuid4())
        locations.append(
            hospital_factory(hospital, ods_code=hospital_ods_code, uuid=hospital_uuid)
        )
        for ward, ward_index, ward_ods_code in names(f"H{hospital_index} Ward", wards):
            ward_uuid = str(uuid4())
            locations.append(
                ward_factory(
                    ward, ods_code=ward_ods_code, parent=hospital_uuid, uuid=ward_uuid
                )
            )
            for bay, bay_index, bay_ods_code in names(
                f"H{hospital_index}W{ward_index} Bay", bays
            ):
                bay_uuid = str(uuid4())
                locations.append(
                    bay_factory(
                        bay, ods_code=bay_ods_code, parent=ward_uuid, uuid=bay_uuid
                    )
                )
                for bed, bed_index, bed_ods_code in names(
                    f"H{hospital_index}W{ward_index}B{bay_index} Bed", beds
                ):
                    locations.append(
                        bed_factory(bed, ods_code=bed_ods_code, parent=bay_uuid)
                    )
    response: Response = locations_api_client.post_many_locations(context, locations)
    context.create_location_response = response
    assert response.status_code == 200


@given("we are timing this step")
def timing_step(context: Context) -> None:
    context.start_time = time.time()


@step("it took less than (?P<max_time>\d+(?:.\d*)?) second(?:s)? to complete")
def it_took_less_than(context: Context, max_time: str) -> None:
    limit = float(max_time)

    end_time = time.time()
    print(f"Step actually took {end_time - context.start_time:.1f} seconds")
    assert (
        end_time - context.start_time < limit
    ), f"Max time for test exceeded {max_time} seconds took {end_time - context.start_time:.1f}"


@when("we fetch the location hierarchy")
def fetch_location_hierarchy(context: Context) -> None:
    context.hierarchy = locations_api_client.get_all_locations(
        context=context,
        product_name="SEND",
        location_types="225746001|22232009",
        compact=True,
        active=True,
        children=True,
    )


@step("we received all of the expected locations")
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
            assert not location["parent"]
            assert len(location["children"]) == context.ward_count * (
                context.bay_count * (context.bed_count + 1) + 1
            )
        else:
            # Ward
            assert location["parent"]
            assert len(location["children"]) == context.bay_count * (
                context.bed_count + 1
            )
