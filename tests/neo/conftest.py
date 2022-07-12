import contextlib
import datetime
import time
from typing import Any, Callable, Dict, Generator, List, Optional
from uuid import uuid4

import draymed
import pytest
from flask import Flask
from neomodel import db
from neomodel import db as neo_db

from dhos_services_api.models import Patient


@pytest.fixture
def patient_context(app: Flask, location_uuid: str, clinician: str) -> Callable:
    from dhos_services_api.models.patient import Patient, SendPatient

    @contextlib.contextmanager
    def make_patient(
        first_name: str,
        product: str = "SEND",
        last_name: str = "Patient",
        nhs_number: Optional[str] = None,
        hospital_number: str = "435y9999",
        location_uuid: str = location_uuid,
        opened_date: str = "2018-06-22",
        diagnosis_code: str = "11687002",
    ) -> Generator[Patient, None, None]:
        email_address = (f"{first_name}.patient@mail.com",)

        patient = {
            "first_name": first_name.title(),
            "last_name": last_name,
            "phone_number": "07594203248",
            "allowed_to_text": True,
            "allowed_to_email": True,
            "dob": "1957-06-9",
            "hospital_number": hospital_number,
            "nhs_number": nhs_number,
            "email_address": email_address,
            "dh_products": [
                {
                    "product_name": product,
                    "opened_date": opened_date,
                    "accessibility_discussed": True,
                    "accessibility_discussed_with": clinician,
                    "accessibility_discussed_date": opened_date,
                }
            ],
            "sex": "248152002",
            "accessibility_considerations": None,
            "record": {
                "pregnancies": [
                    {
                        "estimated_delivery_date": datetime.datetime.today().strftime(
                            "%Y-%m-%d"
                        )
                    }
                ],
                "diagnoses": [
                    {
                        "sct_code": diagnosis_code,
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
            "locations": [location_uuid],
        }
        with app.app_context():
            cls = SendPatient if product == "SEND" else Patient
            p: Patient = cls.new(**patient)
            p.save()
        yield p
        p.delete()

    return make_patient


@pytest.fixture
def diagnosis_uuid(patient: Patient) -> str:
    return patient.record.get().diagnoses.get().uuid


@pytest.fixture
def patient_record_uuid(patient: Patient) -> str:
    return patient.record[0].uuid


@pytest.fixture
def neo4j_clear_database() -> Generator[None, None, None]:
    """Clear the database after the test."""
    from dhos_services_api.neodb import db

    yield
    db.cypher_query("MATCH(n) DETACH DELETE(n)")


@pytest.fixture
def patient_with_delivery_uuid(
    gdm_patient_uuid: str,
    location_uuid: str,
    gdm_clinician: Dict,
    diabetes_patient_product: str,
    jwt_system: str,
) -> str:
    from dhos_services_api.blueprint_patients import patient_controller_neo

    patient = patient_controller_neo.get_patient(
        patient_uuid=gdm_patient_uuid, product_name=diabetes_patient_product
    )
    pregnancy_id = patient["record"]["pregnancies"][0]["uuid"]
    update_data = {
        "personal_addresses": [
            {
                "address_line_1": "42 Some Street",
                "address_line_2": "",
                "address_line_3": "",
                "address_line_4": "",
                "locality": "Oxford",
                "region": "Oxfordshire",
                "postcode": "OX3 5TF",
                "country": "England",
                "lived_from": "1970-01-01",
                "lived_until": "1970-01-01",
            }
        ],
        "record": {
            "notes": [
                {
                    "content": "Will need to monitor patient closely",
                    "clinician_uuid": gdm_clinician,
                }
            ],
            "history": {"gravidity": 1, "parity": 1},
            "pregnancies": [
                {
                    "uuid": pregnancy_id,
                    "height_at_booking_in_mm": 1230,
                    "weight_at_booking_in_g": 78000,
                    "length_of_postnatal_stay_in_days": 2,
                    "induced": True,
                    "deliveries": [
                        {
                            "neonatal_complications": ["123456", "123456"],
                            "patient": {"first_name": "Paul", "last_name": "Smith"},
                        }
                    ],
                }
            ],
            "diagnoses": [
                {
                    "sct_code": "1234567890",
                    "diagnosis_other": "Some diagnosis with no snomed code",
                    "diagnosed": "1970-01-01",
                    "episode": 1,
                    "presented": "1970-01-01",
                    "diagnosis_tool": ["1234567890"],
                    "diagnosis_tool_other": "some tool",
                    "risk_factors": ["1234567890"],
                    "observable_entities": [
                        {
                            "sct_code": "123456789",
                            "date_observed": "1970-01-01",
                            "value_as_string": "A value",
                        },
                    ],
                    "management_plan": {
                        "start_date": "1970-01-01",
                        "end_date": "1970-01-01",
                        "sct_code": "386359008",
                        "doses": [
                            {
                                "medication_id": "99b1668c-26f1-4aec-88ca-597d3a20d977",
                                "dose_amount": 1.5,
                                "routine_sct_code": "12345",
                            }
                        ],
                        "actions": [{"action_sct_code": "12345"}],
                    },
                    "readings_plan": {
                        "start_date": "1970-01-01",
                        "end_date": "1970-01-01",
                        "sct_code": "33747003",
                        "days_per_week_to_take_readings": 7,
                        "readings_per_day": 4,
                    },
                }
            ],
            "visits": [
                {
                    "visit_date": "2018-01-11T15:01:01.146Z",
                    "summary": "Talked about GDM",
                    "location": location_uuid,
                    "clinician_uuid": gdm_clinician,
                    "diagnoses": [],
                }
            ],
        },
    }
    patient = patient_controller_neo.update_patient(
        patient_uuid=gdm_patient_uuid, patient_details=update_data
    )
    return patient["uuid"]


@pytest.fixture
def two_gdm_patients_one_with_children() -> None:
    query = """
        CREATE
         (p1:Patient {
            uuid:'P1',
            hospital_number:'MRN1',
            nhs_number:'8888888888',
            first_name: 'Jane',
            last_name: 'Grey Dudley',
            locations: ['L1']}),
         (p2:Patient {uuid:'P2', hospital_number:'MRN2'}),
         (p3:Patient {uuid:'P3', hospital_number:'MRN3', locations: ['L3']}),
         (p4:Patient {
            uuid:'P4',
            hospital_number:'9998887771',
            first_name: 'Jane Grey',
            last_name: 'Dudley',
            locations: ['L4']}),
         (p1)-[:HAS_RECORD]->(pr1:Record {uuid:'R1'}),
         (p1)-[:ACTIVE_ON_PRODUCT]->(dh1:DraysonHealthProduct {uuid:'DH1', product_name:'GDM'}),
         (pr1)-[:HAS_DIAGNOSIS]->(dg1:Diagnosis {uuid:'DG1', sct_code: '11687002'}),
         (dg1)-[:HAS_MANAGEMENT_PLAN]->(mp1:ManagementPlan {
           uuid:'MP1', sct_code: '67866001', start_date: '2019-08-26', end_date: '2020-01-01'
         }),
         (p3)-[:CHILD_OF]->(p2)-[:CHILD_OF]->(p1),
         (p3)-[:HAS_RECORD]->(pr3:Record {uuid:'R3'}),
         (p3)-[:ACTIVE_ON_PRODUCT]->(dh3:DraysonHealthProduct {uuid:'DH3', product_name:'GDM'}),
         (p4)-[:HAS_RECORD]->(pr4:Record {uuid:'R4'}),
         (p4)-[:ACTIVE_ON_PRODUCT]->(dh4:DraysonHealthProduct {uuid:'DH4', product_name:'GDM'}),
         (pr4)-[:HAS_PREGNANCY]->(pregnancy1:Pregnancy {uuid:'Pr1', estimated_delivery_date:'2020-06-04'}),
         (pr4)-[:HAS_DIAGNOSIS]->(dg4:Diagnosis {uuid:'DG4', sct_code: '11687002'})
        """
    results, meta = db.cypher_query(query)


@pytest.fixture
def one_send_patient() -> None:
    query = """
        CREATE
         (p6:Patient {
            uuid:'P6',
            hospital_number:'MRN6',
            nhs_number:'8888888888',
            first_name: 'Jane',
            last_name: 'Grey Dudley',
            locations: ['L1']}),
         (p6)-[:HAS_RECORD]->(pr1:Record {uuid:'R6'}),
         (p6)-[:ACTIVE_ON_PRODUCT]->(dh1:DraysonHealthProduct {uuid:'DH1S', product_name:'SEND'})
        """
    results, meta = db.cypher_query(query)


@pytest.fixture
def closed_gdm_patient() -> None:
    query = """
        CREATE
         (p5:Patient {uuid:'P5', locations: ['L5']}),
         (dh5:DraysonHealthProduct {uuid:'DH5', product_name:'GDM', closed_date: '2020-01-01', monitored_by_clinician: false}),
         (p5)-[:HAS_RECORD]->(pr5:Record {uuid:'R5'}),
         (p5)-[:ACTIVE_ON_PRODUCT]->(dh5),
         (dh5)-[:HAS_CHANGE]->(dhpc51:DraysonHealthProductChange {uuid:'DHPC51', event:'stop monitoring'}),
         (dh5)-[:HAS_CHANGE]->(dhpc52:DraysonHealthProductChange {uuid:'DHPC52', event:'archive'})
         """
    results, meta = db.cypher_query(query)


@pytest.fixture
def not_monitored_gdm_patient() -> None:
    query = """
        CREATE
         (p8:Patient {uuid:'P8', locations: ['L8']}),
         (dh8:DraysonHealthProduct {uuid:'DH8', product_name:'GDM', monitored_by_clinician: false}),
         (p8)-[:HAS_RECORD]->(pr8:Record {uuid:'R8'}),
         (p8)-[:ACTIVE_ON_PRODUCT]->(dh8),
         (dh8)-[:HAS_CHANGE]->(dhpc81:DraysonHealthProductChange {uuid:'DHPC81', event:'stop monitoring'}),
         (pr8)-[:HAS_HISTORY]->(prh8:History {uuid:'RH8'})
         """
    results, meta = db.cypher_query(query)


@pytest.fixture
def monitored_gdm_patient() -> None:
    query = """
        CREATE
         (p9:Patient {uuid:'P9', locations: ['L9']}),
         (dh9:DraysonHealthProduct {uuid:'DH9', product_name:'GDM', monitored_by_clinician: true}),
         (p9)-[:HAS_RECORD]->(pr9:Record {uuid:'R9'}),
         (p9)-[:ACTIVE_ON_PRODUCT]->(dh9),
         (dh9)-[:HAS_CHANGE]->(dhpc91:DraysonHealthProductChange {uuid:'DHPC91', event:'stop monitoring'}),
         (dh9)-[:HAS_CHANGE]->(dhpc92:DraysonHealthProductChange {uuid:'DHPC92', event:'start monitoring'}),
         (pr9)-[:HAS_HISTORY]->(prh9:History {uuid:'RH9'})
         """
    results, meta = db.cypher_query(query)


@pytest.fixture
def gdm_patients_modified() -> None:
    query = """
        CREATE
        (p6:Patient {
            uuid: 'P6',
            hospital_number: 'MRN6',
            nhs_number: '66666666',
            first_name: 'Leonard',
            last_name: 'Shepard',
            locations: ['L1'],
            modified: 1262304000.0
            }
        ),
        (p6)-[:HAS_RECORD]->(pr6:Record {uuid:'R6'}),
        (p6)-[:ACTIVE_ON_PRODUCT]->(dh6:DraysonHealthProduct {uuid:'DH6', product_name:'GDM'}),
        (p7:Patient {
            uuid: 'P7',
            hospital_number: 'MRN7',
            nhs_number: '7777777',
            first_name: 'Albert',
            last_name: 'Einstein',
            locations: ['L2'],
            modified: 946598400.0
            }
        ),
        (p7)-[:HAS_RECORD]->(pr7:Record {uuid:'R7'}),
        (p7)-[:ACTIVE_ON_PRODUCT]->(dh7:DraysonHealthProduct {uuid:'DH7', product_name:'GDM'})
         """
    results, meta = db.cypher_query(query)


@pytest.fixture
def node_factory(neo4j_teardown_node: Any) -> Callable:
    """Fixture providing a factory to create an arbitrary neo4j node.
    The node will be automatically deleted at the end of the test.
    Usage: node_factory(node_name, **fields) -> uuid
    """

    def make_node(node_name: str, **fields: Any) -> str:
        if "uuid " not in fields:
            fields["uuid"] = str(uuid4())

        field_cypher = ",\n".join(f"{k}:{{{k}}}" for k in fields)
        cypher = f"""CREATE (n:{node_name}{{{field_cypher}}}) RETURN n.uuid"""
        results, meta = neo_db.cypher_query(cypher, fields)
        uuid = results[0][0]
        neo4j_teardown_node(uuid)
        return uuid

    return make_node


@pytest.fixture
def relation_factory() -> Callable:
    """Fixture providing a factory to create an arbitrary neo4j relation.
    Usage: relation_factory(relation_name, from_uuid, to_uuid)
    """

    def create_relation(relation_name: str, from_uuid: str, to_uuid: str) -> None:
        cypher = f"""MATCH (from_node),(to_node)
            WHERE from_node.uuid = {{from_uuid}} AND to_node.uuid = {{to_uuid}}
            CREATE (from_node)-[r:{relation_name}]->(to_node)
            RETURN type(r)"""

        neo_db.cypher_query(cypher, dict(from_uuid=from_uuid, to_uuid=to_uuid))

    return create_relation


@pytest.fixture
def neo4j_teardown_node() -> Generator[Callable, None, None]:
    """Fixture providing a function that marks neo4j nodes to be cleaned up at the end of the test
    neo4j_teardown_node(uuid1, [uuid2, ...])
    """
    nodes = set()

    def teardown(*uuids: List[str]) -> None:
        for uuid in uuids:
            nodes.add(uuid)

    yield teardown

    neo_db.cypher_query(
        "MATCH (n) WHERE n.uuid in {nodes} DETACH DELETE n", dict(nodes=list(nodes))
    )


@pytest.fixture
def location_factory(
    neo4j_teardown_node: Any, node_factory: Callable, relation_factory: Callable
) -> Callable:
    """Fixture providing a factory to create locations.
    Usage: location_factory(name, parent=None, product_name='SEND', **fields) -> uuid
    If parent is None the display name is "{name} Hospital", otherwise it is
    "{name} Ward" and the ods_code is set to a ward.
    All fields may be overridden with additional keyword parameters.
    """

    def make_location(
        name: str,
        parent: Optional[str] = None,
        product_name: str = "SEND",
        **fields: Any,
    ) -> str:
        create_time = time.time()
        fields = {
            "address_line_1": "Address",
            "postcode": "",
            "country": "",
            "location_type": draymed.codes.code_from_name("ward", category="location")
            if parent
            else "",
            "ods_code": name,
            "display_name": f"{name} {'Ward' if parent else 'Hospital'}",
            "active": True,
            "created_by_": "dhos-robot",
            "created": create_time,
            "modified_by_": "dhos-robot",
            "modified": create_time,
            **fields,
        }
        location_uuid = node_factory("Location", **fields)

        if parent:
            relation_factory("CHILD_OF", location_uuid, parent)

        location_product_uuid = node_factory(
            "LocationProduct",
            created_by_=fields["created_by_"],
            created=fields["created"],
            modified_by_=fields["modified_by_"],
            modified=fields["modified"],
            opened_date="2000-01-01",
            uri="http://snomed.codes",
            product_name=product_name,
        )

        relation_factory("ACTIVE_ON_PRODUCT", location_uuid, location_product_uuid)

        return location_uuid

    return make_location


@pytest.fixture
def location_uuid(location_factory: Callable) -> Callable:
    """Default location for SEND tests 'Tester Hospital'"""
    return location_factory("Tester")


@pytest.fixture
def gdm_location_uuid(location_factory: Callable) -> Callable:
    """Default location for GDM tests 'GdmTest Hospital'"""
    return location_factory("Tester", product_name="GDM")


@pytest.fixture
def clinician_factory(
    node_factory: Callable,
    relation_factory: Callable,
    location_uuid: str,
    gdm_location_uuid: str,
) -> Callable:
    """Fixture providing a factory to create clinicians.
    Usage: clinician_factory(first_name, last_name, nhs_smartcard, product_name='SEND',
         expiry=None, login_active=None, **fields) -> uuid
    All fields may be overridden with additional keyword parameters.
    """

    def make_clinician(
        first_name: str,
        last_name: str,
        nhs_smartcard_number: str,
        product_name: str = "SEND",
        expiry: Optional[str] = None,
        login_active: Optional[bool] = None,
        **fields: Any,
    ) -> Callable:

        if product_name == "SEND":
            location = location_uuid
        else:
            location = gdm_location_uuid

        create_time = time.time()

        fields = {
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": "07654123123",
            "nhs_smartcard_number": nhs_smartcard_number,
            "email_address": f"{first_name.lower()}.{last_name.lower()}@test.com",
            "job_title": "somejob",
            "contract_expiry_eod_date": expiry,
            "login_active": login_active,
            "locations": [location],
            "created_by_": "dhos-robot",
            "created": create_time,
            "modified_by_": "dhos-robot",
            "modified": create_time,
            **fields,
        }
        clinician_uuid = node_factory("Clinician", **fields)

        clinician_product_uuid = node_factory(
            "ClinicianProduct",
            created_by_="dhos-robot",
            created=fields["created"],
            modified_by_=fields["modified_by_"],
            modified=fields["modified"],
            opened_date="2000-01-01",
            product_name=product_name,
        )
        relation_factory("ACTIVE_ON_PRODUCT", clinician_uuid, clinician_product_uuid)

        return clinician_uuid

    return make_clinician


@pytest.fixture
def clinician(clinician_factory: Callable) -> Callable:
    """SEND clinician fixture: Jane Deer"""
    return clinician_factory("Jane", "Deer", "211214")


@pytest.fixture
def gdm_clinician(clinician_factory: Callable) -> Callable:
    """GDM clinician fixture: Lou Rabbit"""
    return clinician_factory("Lou", "Rabbit", "456987", product_name="GDM")


@pytest.fixture
def clinician2_uuid(clinician_factory: Callable) -> Callable:
    """SEND clinician fixture: Kate Wildcat"""
    return clinician_factory("Kate", "Wildcat", "211215")


@pytest.fixture
def clinician_temp_uuid(clinician_factory: Callable) -> Callable:
    """SEND temporary clinician fixture: Lou Armadillo"""
    return clinician_factory("Lou", "Armadillo", "211216", expiry="2019-03-12")
