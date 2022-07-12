"""Common fixtures for tests using SQL models"""
from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Callable, ContextManager, Generator, Iterator, Optional

import pytest
import sqlalchemy
from flask_batteries_included.sqldb import db
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Session

from dhos_services_api.sqlmodels import Patient


@pytest.fixture
def uses_sql_database(_db: SQLAlchemy) -> None:
    _db.session.commit()
    _db.drop_all()
    _db.create_all()


class DBStatementCounter(object):
    def __init__(self, limit: int = None) -> None:
        self.clauses: list[sqlalchemy.sql.ClauseElement] = []
        self.limit = limit

    @property
    def count(self) -> int:
        return len(self.clauses)

    def callback(
        self,
        conn: sqlalchemy.engine.Connection,
        clauseelement: sqlalchemy.sql.ClauseElement,
        multiparams: list[dict],
        params: dict,
        execution_options: dict,
    ) -> None:
        if isinstance(clauseelement, sqlalchemy.sql.elements.SavepointClause):
            return

        self.clauses.append(clauseelement)
        if self.limit:
            if len(self.clauses) > self.limit:
                clauses = [str(clause) for clause in self.clauses]
                print(clauses)
            assert (
                len(self.clauses) <= self.limit
            ), f"Too many SQL statements (limit was {self.limit})"


@contextlib.contextmanager
def db_statement_counter(
    limit: int = None, session: Session = None
) -> Iterator[DBStatementCounter]:
    if session is None:
        session = db.session
    counter = DBStatementCounter(limit=limit)
    cb = counter.callback
    sqlalchemy.event.listen(db.engine, "before_execute", cb)
    try:
        yield counter
    finally:
        sqlalchemy.event.remove(db.engine, "before_execute", cb)


@pytest.fixture
def statement_counter() -> Callable[
    [int | None, Session | None], ContextManager[DBStatementCounter]
]:
    return db_statement_counter


@pytest.fixture
def patient_context(_db: SQLAlchemy, location_uuid: str, clinician: str) -> Callable:
    from dhos_services_api.sqlmodels.patient import Patient, SendPatient

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
        email_address = f"{first_name}.patient@mail.com"

        patient: dict = {
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
                    {"estimated_delivery_date": datetime.today().strftime("%Y-%m-%d")}
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
        cls = SendPatient if product == "SEND" else Patient
        p: Patient = cls.new(**patient)
        db.session.commit()
        yield p

    return make_patient


@pytest.fixture
def diagnosis_uuid(patient: Patient) -> str:
    return patient.record.diagnoses[0].uuid


@pytest.fixture
def patient_record_uuid(patient: Patient) -> str:
    return patient.record.uuid


@pytest.fixture
def patient_with_delivery_uuid(
    gdm_patient_uuid: str,
    location_uuid: str,
    gdm_clinician: dict,
    diabetes_patient_product: str,
    jwt_system: str,
) -> str:
    from dhos_services_api.blueprint_patients import patient_controller

    patient = patient_controller.get_patient(
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
                            },
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
    patient = patient_controller.update_patient(
        patient_uuid=gdm_patient_uuid, patient_details=update_data
    )
    return patient["uuid"]


@pytest.fixture
def two_gdm_patients_one_with_children() -> None:
    p1 = Patient.new(
        uuid="P1",
        hospital_number="MRN1",
        nhs_number="8888888888",
        first_name="Jane",
        last_name="Grey Dudley",
        locations=["L1"],
        record={
            "uuid": "R1",
            "diagnoses": [
                {
                    "uuid": "DG1",
                    "sct_code": "11687002",
                    "management_plan": {
                        "uuid": "MP1",
                        "sct_code": "67866001",
                        "start_date": "2019-08-26",
                        "end_date": "2020-01-01",
                    },
                }
            ],
        },
        dh_products=[{"uuid": "DH1", "product_name": "GDM"}],
    )
    db.session.commit()
    p2 = Patient.new(uuid="P2", hospital_number="MRN2", parent_patient_id="P1")
    db.session.commit()
    p3 = Patient.new(
        uuid="P3",
        hospital_number="MRN3",
        locations=["L3"],
        parent_patient_id="P2",
        record={"uuid": "R3"},
        dh_products=[{"uuid": "DH3", "product_name": "GDM"}],
    )
    db.session.commit()
    p4 = Patient.new(
        uuid="P4",
        hospital_number="9998887771",
        first_name="Jane Grey",
        last_name="Dudley",
        locations=["L4"],
        record={
            "uuid": "R4",
            "pregnancies": [{"uuid": "Pr1", "estimated_delivery_date": "2020-06-04"}],
            "diagnoses": [{"uuid": "DG4", "sct_code": "11687002"}],
        },
        dh_products=[{"uuid": "DH4", "product_name": "GDM"}],
    )
    db.session.commit()


@pytest.fixture
def one_send_patient() -> None:
    p6 = Patient.new(
        uuid="P6",
        hospital_number="MRN6",
        nhs_number="8888888888",
        first_name="Jane",
        last_name="Grey Dudley",
        locations=["L1"],
        record={"uuid": "R6"},
        dh_products=[{"uuid": "DH1S", "product_name": "SEND"}],
    )
    db.session.commit()


@pytest.fixture
def closed_gdm_patient() -> None:
    p5 = Patient.new(
        uuid="P5",
        locations=["L5"],
        hospital_number="MRN5",
        dh_products=[
            {
                "uuid": "DH5",
                "product_name": "GDM",
                "closed_date": "2020-01-01",
                "monitored_by_clinician": False,
                "changes": [
                    {"uuid": "DHPC51", "event": "stop monitoring"},
                    {"uuid": "DHPC52", "event": "archive"},
                ],
            }
        ],
        record={"uuid": "R5"},
    )
    db.session.commit()


@pytest.fixture
def not_monitored_gdm_patient() -> None:
    p8 = Patient.new(
        uuid="P8",
        locations=["L8"],
        dh_products=[
            {
                "uuid": "DH8",
                "product_name": "GDM",
                "monitored_by_clinician": False,
                "changes": [{"uuid": "DHPC81", "event": "stop monitoring"}],
            }
        ],
        record={"uuid": "R8", "history": {"uuid": "RH8"}},
    )
    db.session.commit()


@pytest.fixture
def monitored_gdm_patient() -> None:
    p9 = Patient.new(
        uuid="P9",
        locations=["L9"],
        dh_products=[
            {
                "uuid": "DH9",
                "product_name": "GDM",
                "monitored_by_clinician": True,
                "changes": [
                    {"uuid": "DHPC91", "event": "stop monitoring"},
                    {"uuid": "DHPC92", "event": "start monitoring"},
                ],
            }
        ],
        record={"uuid": "R9", "history": {"uuid": "RH9"}},
    )
    db.session.commit()


@pytest.fixture
def gdm_patients_modified() -> None:
    p6 = Patient.new(
        uuid="P6",
        hospital_number="MRN6",
        nhs_number="66666666",
        first_name="Leonard",
        last_name="Shepard",
        locations=["L1"],
        modified=datetime.fromtimestamp(1262304000.0),
        record={"uuid": "R6"},
        dh_products=[{"uuid": "DH6", "product_name": "GDM"}],
    )
    p7 = Patient.new(
        uuid="P7",
        hospital_number="MRN7",
        nhs_number="7777777",
        first_name="Albert",
        last_name="Einstein",
        locations=["L2"],
        modified=datetime.fromtimestamp(946598400.0),
        record={"uuid": "R7"},
        dh_products=[{"uuid": "DH7", "product_name": "GDM"}],
    )
    db.session.commit()


@pytest.fixture
def wildcard_identifier(any_datetime: datetime, any_uuid: str) -> dict:
    return {
        "created": any_datetime,
        "created_by": "unknown",
        "modified": any_datetime,
        "modified_by": "unknown",
        "uuid": any_uuid,
    }
