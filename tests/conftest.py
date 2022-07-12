import contextlib
import datetime
import json
import os
import re
import signal
import socket
import sys
import time
import uuid
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    NoReturn,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)
from urllib.parse import urlparse

import flask
import kombu_batteries_included
import pytest
import sqlalchemy
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from flask import Flask, g
from flask_batteries_included.helpers import generate_uuid
from flask_sqlalchemy import SQLAlchemy
from marshmallow import RAISE, Schema
from mock import Mock
from pytest_mock import MockerFixture
from sqlalchemy.engine import Engine

from dhos_services_api.models.clinician import Clinician
from dhos_services_api.models.patient import Patient


def pytest_addoption(parser: Parser) -> None:
    parser.addoption(
        "--neo4j",
        action="store_true",
        default=False,
        help="run tests that require neo4j",
    )


def pytest_configure(config: Config) -> None:
    config.addinivalue_line("markers", "fast: Test does not require neo4j")
    config.addinivalue_line("markers", "neo4j: Test requires neo4j")

    for env_var, tox_var in [
        ("NEO4J_DB_PORT", "NEO4J_7687_TCP_PORT"),
        ("NEO4J_DB_BROWSER_PORT", "NEO4J_7474_TCP_PORT"),
        ("NEO$NEO4J_DB_BROWSER_PORT", "NEO4J_7474_TCP_PORT"),
        ("NEO4J_DB_URL", "NEO4J_HOST"),
        ("DATABASE_HOST", "POSTGRES_HOST"),
        ("DATABASE_PORT", "POSTGRES_5432_TCP_PORT"),
    ]:
        if tox_var in os.environ:
            os.environ[env_var] = os.environ[tox_var]

    # f-b-i will have already been imported at this point (by pytest-dhos), so we have to update
    # the configured database url. These need to be local imports.
    import neomodel.config

    from dhos_services_api.config import Configuration

    neomodel.config.DATABASE_URL = Configuration().NEO4J_DATABASE_URI

    import logging

    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if os.environ.get("SQLALCHEMY_ECHO") else logging.WARNING
    )


def pytest_report_header(config: Config) -> str:
    import neomodel.config

    db_config = (
        f"{os.environ['DATABASE_HOST']}:{os.environ['DATABASE_PORT']}"
        if os.environ.get("DATABASE_PORT")
        else "Sqlite"
    )
    return (
        f"NEO4J database url: {neomodel.config.DATABASE_URL}, "
        f"SQL database: {db_config}"
    )


def _wait_for_it(service: str, timeout: int = 30) -> None:
    url = urlparse(service, scheme="http")

    host = url.hostname
    port = url.port or (443 if url.scheme == "https" else 80)

    friendly_name = f"{host}:{port}"

    def _handle_timeout(signum: Any, frame: Any) -> NoReturn:
        print(f"timeout occurred after waiting {timeout} seconds for {friendly_name}")
        sys.exit(1)

    if timeout > 0:
        signal.signal(signal.SIGALRM, _handle_timeout)
        signal.alarm(timeout)
        print(f"waiting {timeout} seconds for {friendly_name}")
    else:
        print(f"waiting for {friendly_name} without a timeout")

    t1 = time.time()

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s = sock.connect_ex((host, port))
            if s == 0:
                seconds = round(time.time() - t1)
                print(f"{friendly_name} is available after {seconds} seconds")
                break
        except socket.gaierror:
            pass
        finally:
            time.sleep(1)

    signal.alarm(0)


def pytest_collection_modifyitems(config: Config, items: List) -> None:
    if config.getoption("--neo4j"):
        return

    skip_neo4j = pytest.mark.skip(reason="need --neo4j option to run")
    for item in items:
        if "neo4j" in item.keywords or "node_factory" in item.fixturenames:
            item.add_marker(skip_neo4j)


@pytest.fixture(scope="session", autouse=True)
def wait_for_neo4j(request: Any) -> None:
    if request.config.getoption("--neo4j"):
        # Wait for neo4j to have fully started
        host = os.getenv("NEO4J_DB_URL", "localhost")
        port = os.getenv("NEO4J_DB_BROWSER_PORT", "7474")
        _wait_for_it(f"//{host}:{port}", 30)


@pytest.fixture(scope="session")
def session_app(wait_for_neo4j: None) -> Flask:
    import dhos_services_api.app

    app: Flask = dhos_services_api.app.create_app(testing=True)

    return app


@pytest.fixture(scope="session")
def _db(session_app: Flask) -> Generator[SQLAlchemy, None, None]:
    """
    Provide the transactional fixtures with access to the database via a Flask-SQLAlchemy
    database connection.
    """
    from flask_batteries_included.sqldb import db

    yield db


@pytest.fixture
def alembic_engine(app_context: None, _db: SQLAlchemy) -> Generator[Engine, None, None]:
    _db.drop_all()
    _db.session.execute(sqlalchemy.text("DROP TABLE IF EXISTS alembic_version"))
    _db.session.commit()
    yield _db.engine


@pytest.fixture
def app(session_app: Flask, _db: SQLAlchemy) -> Generator[Flask, None, None]:
    with session_app.app_context():
        _db.drop_all()
        _db.create_all()

        g.jwt_claims = {}
        g.jwt_scopes = []

        yield session_app


@pytest.fixture
def mock_retrieve_jwt_claims(app: Flask, mocker: MockerFixture) -> Mock:
    from flask_batteries_included.helpers.security import _ProtectedRoute

    def mock_claims(self: Any, verify: bool = True) -> Tuple:
        return g.jwt_claims, g.jwt_scopes

    app.config["IGNORE_JWT_VALIDATION"] = False

    return mocker.patch.object(_ProtectedRoute, "_retrieve_jwt_claims", mock_claims)


@pytest.fixture
def clean_up_neo4j_after_test() -> Generator[None, None, None]:
    # Yield nothing, then after the test run the cleanup query.
    from dhos_services_api.neodb import db

    yield
    db.cypher_query("MATCH (n) DETACH DELETE n")


@pytest.fixture
def app_context(app: Flask) -> Generator[None, None, None]:
    with app.app_context():
        yield


@pytest.fixture
def mock_publish(mocker: MockerFixture) -> Mock:
    return mocker.patch.object(kombu_batteries_included, "publish_message")


@pytest.fixture
def jwt_user_type() -> str:
    "parametrize to 'clinician', 'patient', or None as appropriate"
    return "clinician"


@pytest.fixture
def patient_context() -> Callable:
    """Dummy fixture needed for jwt_user_uuid fixture."""

    class Patient:
        uuid: str

    @contextlib.contextmanager
    def make_patient(*args: object, **kw: object) -> Generator[Patient, None, None]:

        patient = Patient()
        patient.uuid = generate_uuid()
        yield patient

    return make_patient


@pytest.fixture
def jwt_user_uuid(
    app_context: None,
    jwt_send_clinician_uuid: str,
    patient: Patient,
    jwt_user_type: str,
    jwt_scopes: List[str],
    mocker: MockerFixture,
) -> str:
    """Use this fixture for parametrized tests setting the jwt_user_type fixture to select different
    account types for requests."""

    if jwt_user_type == "clinician":
        mocker.patch.object(g, "jwt_claims", {"clinician_id": jwt_send_clinician_uuid})
        return jwt_send_clinician_uuid

    elif jwt_user_type == "patient":
        mocker.patch.object(g, "jwt_claims", {"patient_id": patient.uuid})
        if jwt_scopes is None:
            mocker.patch.object(g, "jwt_scopes", "")
        else:
            if isinstance(jwt_scopes, str):
                jwt_scopes = jwt_scopes.split(",")
            mocker.patch.object(g, "jwt_scopes", jwt_scopes)
        return patient.uuid

    else:
        mocker.patch.object(g, "jwt_claims", {})
        if isinstance(jwt_scopes, str):
            jwt_scopes = jwt_scopes.split(",")
        mocker.patch.object(g, "jwt_scopes", jwt_scopes)

        return "dummy"


@pytest.fixture
def jwt_gdm_patient_uuid(
    mocker: MockerFixture,
    patient: Patient,
    jwt_scopes: Union[str, List[str], None],
) -> str:
    mocker.patch.object(g, "jwt_claims", {"patient_id": patient.uuid})
    if jwt_scopes is None:
        jwt_scopes = [
            "read:gdm_patient_abbreviated",
            "read:gdm_message",
            "write:gdm_message",
            "read:gdm_bg_reading",
            "write:gdm_bg_reading",
            "read:gdm_medication",
            "read:gdm_question",
            "read:gdm_answer",
            "write:gdm_answer",
            "read:gdm_trustomer",
            "read:gdm_telemetry",
            "write:gdm_telemetry",
            "write:gdm_terms_agreement",
        ]

    if isinstance(jwt_scopes, str):
        jwt_scopes = jwt_scopes.split(",")
    mocker.patch.object(g, "jwt_scopes", jwt_scopes)
    return patient.uuid


@pytest.fixture
def clinician_context(
    app: Flask, location_uuid: str, gdm_location_uuid: str
) -> Callable:
    @contextlib.contextmanager
    def make_clinician(
        first_name: str,
        last_name: str,
        nhs_smartcard_number: str,
        product_name: str = "SEND",
        expiry: Optional[str] = None,
        login_active: Optional[bool] = None,
    ) -> Generator[Clinician, None, None]:
        pass

        clinician: Dict[str, Any] = {
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": "07654123123",
            "nhs_smartcard_number": nhs_smartcard_number,
            "email_address": f"{first_name.lower()}.{last_name.lower()}@test.com",
            "job_title": "somejob",
            "locations": [
                location_uuid if product_name == "SEND" else gdm_location_uuid
            ],
            "groups": ["GDMClinician"],
            "products": [
                {
                    "product_name": product_name,
                    "opened_date": datetime.datetime.today().strftime("%Y-%m-%d"),
                }
            ],
        }
        if expiry is not None:
            clinician["contract_expiry_eod_date"] = expiry

        if login_active is not None:
            clinician["login_active"] = login_active

        with app.app_context():
            g.jwt_claims = {"system_id": "dhos-robot"}
            c: Clinician = Clinician.new(**clinician)
            c.save()
        yield c
        c.delete()

    return make_clinician


@pytest.fixture
def patient(patient_context: Callable) -> Generator[Patient, None, None]:
    with patient_context("Carol") as patient:
        yield patient


@pytest.fixture
def patient_uuid(patient: Patient) -> str:
    return patient.uuid


@pytest.fixture
def diabetes_patient_product() -> str:
    """Override this fixture to get test patients for products similar to GDM but with a different product"""
    return "GDM"


@pytest.fixture
def gdm_patient_uuid(
    patient_context: Callable, gdm_location_uuid: str, diabetes_patient_product: str
) -> Generator[str, None, None]:
    with patient_context(
        "Carol", product=diabetes_patient_product, location_uuid=gdm_location_uuid
    ) as patient:
        yield patient.uuid


@pytest.fixture
def four_patient_uuids(patient_context: Callable) -> Generator[List[str], None, None]:
    with patient_context(
        "Alice", last_name="Jones", hospital_number="123alice"
    ) as alice, patient_context(
        "Bobby", last_name="McCullough-Durgan", hospital_number="123bobby"
    ) as bobby, patient_context(
        "Carol", last_name="McCullough-Durgan", hospital_number="123carol"
    ) as carol, patient_context(
        "Diane", last_name="Burford", hospital_number="123diane"
    ) as diane:
        yield [alice.uuid, bobby.uuid, carol.uuid, diane.uuid]


@pytest.fixture
def ward_uuids(location_factory: Callable, location_uuid: str) -> List[str]:
    apple = location_factory("Apple", parent=location_uuid)
    orange = location_factory("Orange", parent=location_uuid)
    lemon = location_factory("Lemon", parent=location_uuid)
    lime = location_factory("Lime", parent=location_uuid)
    return [apple, orange, lemon, lime]


@pytest.fixture
def gdm_jwt_clinician_uuid(
    app_context: flask.ctx.AppContext, jwt_scopes: Union[List, str, None]
) -> str:
    """Use this fixture to make requests as a GDM clinician"""
    from flask import g

    clinician_uuid = str(uuid.uuid4())
    g.jwt_claims = {
        "clinician_id": clinician_uuid,
    }

    if jwt_scopes is None:
        g.jwt_scopes = [
            "read:gdm_clinician_all",
            "write:gdm_clinician_all",
            "read:gdm_patient_all",
            "write:gdm_patient_all",
        ]

    else:
        if isinstance(jwt_scopes, str):
            jwt_scopes = jwt_scopes.split(",")
        g.jwt_scopes = jwt_scopes
    return clinician_uuid


@pytest.fixture
def location_uuid() -> str:
    """Default location for SEND tests 'Tester Hospital'"""
    return generate_uuid()


@pytest.fixture
def gdm_location_uuid() -> str:
    """Default location for GDM tests 'GdmTest Hospital'"""
    return generate_uuid()


@pytest.fixture
def clinician() -> str:
    """SEND clinician fixture: Jane Deer"""
    return generate_uuid()


@pytest.fixture
def gdm_clinician() -> str:
    """GDM clinician fixture: Lou Rabbit"""
    return generate_uuid()


@pytest.fixture
def clinician2_uuid() -> str:
    """SEND clinician fixture: Kate Wildcat"""
    return generate_uuid()


@pytest.fixture
def clinician_temp_uuid() -> str:
    """SEND temporary clinician fixture: Lou Armadillo"""
    return generate_uuid()


@pytest.fixture
def mock_bearer_validation(mocker: MockerFixture) -> Mock:
    from jose import jwt

    mocked = mocker.patch.object(jwt, "get_unverified_claims")
    mocked.return_value = {
        "sub": "1234567890",
        "name": "John Doe",
        "iat": 1_516_239_022,
        "iss": "http://localhost/",
    }
    return mocked


def sanitize_json(data: Any, ignored: Set) -> Any:
    """Sanitize a json-able object (e.g. list or dict) for comparisons.
    Remove the ignored fields from a dict, recurse into dict or list.
    """
    if isinstance(data, dict):
        return {
            k: sanitize_json(v, ignored) for k, v in data.items() if k not in ignored
        }
    elif isinstance(data, list):
        return [sanitize_json(v, ignored) for v in data]
    else:
        return data


def remove_dates(
    data: Union[List, Dict, str, int, float]
) -> Union[List, Dict, str, int, float]:
    """Clean up returned data to remove dates that aren't constant"""
    if isinstance(data, List):
        return [remove_dates(item) for item in data]
    if isinstance(data, Dict):
        return {
            k: remove_dates(data[k])
            for k in data
            if k not in ("created", "opened_date", "modified")
        }
    return data


class _Anything:
    def __init__(
        self, _type: Optional[Type] = None, regex: Optional[str] = None
    ) -> None:
        self._type = _type
        self._regex = f"^{regex}$"
        self._pattern = regex

    def __eq__(self, other: Any) -> bool:
        print(f"{self}=={repr(other)}")
        if self._type is not None:
            return isinstance(other, self._type)
        if self._regex is not None and isinstance(other, str):
            return re.match(self._regex, other) is not None
        return True

    def __repr__(self) -> str:
        if self._pattern:
            match = f" matching {self._pattern}"
        else:
            match = ""
        if self._type is not None:
            return f"<Any {str(self._type.__name__)}{match}>"
        else:
            return f"<Anything{match}>"


@pytest.fixture
def any() -> _Anything:
    return _Anything()


@pytest.fixture
def any_string() -> _Anything:
    return _Anything(str)


@pytest.fixture
def any_datetime() -> _Anything:
    return _Anything(datetime.datetime)


@pytest.fixture
def any_date() -> _Anything:
    return _Anything(datetime.date)


@pytest.fixture
def any_datetime_string() -> _Anything:
    return _Anything(str, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}.*")


@pytest.fixture
def any_date_string() -> _Anything:
    return _Anything(str, r"\d{4}-\d{2}-\d{2}")


@pytest.fixture
def any_name() -> _Anything:
    return _Anything(str, regex=r"\w+")


@pytest.fixture
def any_phone() -> _Anything:
    return _Anything(str, regex=r"[\d\(\)\-\+]+")


@pytest.fixture
def any_smartcard() -> _Anything:
    return _Anything(str, regex=r"\@\d+")


@pytest.fixture
def any_digits() -> _Anything:
    return _Anything(str, regex=r"\d+")


@pytest.fixture
def any_uuid() -> _Anything:
    return _Anything(
        str,
        regex=r"[[:xdigit:]]{8}-[[:xdigit:]]{4}-[[:xdigit:]]{4}-[[:xdigit:]]{4]-[[:xdigit:]]{12}",
    )


@pytest.fixture
def assert_valid_schema(
    app: Flask,
) -> Callable[[Type[Schema], Union[Dict, List], bool], None]:
    def verify_schema(
        schema: Type[Schema], value: Union[Dict, List], many: bool = False
    ) -> None:
        # Roundtrip through JSON to convert datetime values to strings.
        serialised = json.loads(json.dumps(value, cls=app.json_encoder))
        schema().load(serialised, many=many, unknown=RAISE)

    return verify_schema
