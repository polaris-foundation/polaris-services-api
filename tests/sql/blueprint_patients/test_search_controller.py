"""Patient search using SQL models"""
from typing import Callable, List, Set, Type, cast

import pytest
from _pytest.fixtures import FixtureRequest
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Dialect
from sqlalchemy.sql.elements import BooleanClauseList

from dhos_services_api.blueprint_patients import search_controller
from dhos_services_api.models.api_spec import SearchResultsResponse

POSTGRESQL_DIALECT = cast(Type[Dialect], postgresql.dialect)()


@pytest.mark.usefixtures("app", "uses_sql_database")
class TestController:
    @pytest.fixture
    def patient_uuid_subset(
        self, request: FixtureRequest, four_patient_uuids: List[str], _db: SQLAlchemy
    ) -> List[str]:
        names = ("Alice", "Bobby", "Carol", "Diane")
        param = getattr(request, "param", None)
        if param is None:
            return four_patient_uuids
        return [
            uuid
            for uuid, first_name in zip(four_patient_uuids, names)
            if first_name in param
        ]

    @pytest.mark.parametrize(
        "q,patient_uuid_subset,expected_total,expected",
        [
            (
                None,
                ("Alice", "Bobby", "Carol", "Diane"),
                4,
                {"Alice", "Bobby", "Carol", "Diane"},
            ),
            (
                None,
                ("Alice", "Carol"),
                2,
                {"Alice", "Carol"},
            ),
            (
                None,
                (),
                0,
                set(),
            ),
            (
                "Jones",
                ("Alice", "Bobby", "Carol", "Diane"),
                1,
                {
                    "Alice",
                },
            ),
            ("Dur", ("Alice", "Bobby", "Carol", "Diane"), 2, {"Bobby", "Carol"}),
            ("Mcc", ("Alice", "Bobby", "Carol", "Diane"), 2, {"Bobby", "Carol"}),
            ("Mcc Dur", ("Alice", "Bobby", "Carol", "Diane"), 2, {"Bobby", "Carol"}),
            ("D", ("Alice", "Bobby", "Carol", "Diane"), 3, {"Bobby", "Carol", "Diane"}),
            ("D B", ("Alice", "Bobby", "Carol", "Diane"), 2, {"Bobby", "Diane"}),
        ],
        indirect=["patient_uuid_subset"],
    )
    def test_search_patients_by_uuid(
        self,
        patient_uuid_subset: List[str],
        q: str,
        expected: Set[str],
        expected_total: int,
        assert_valid_schema: Callable,
        statement_counter: Callable,
    ) -> None:
        with statement_counter(limit=100):
            result: dict = search_controller.search_patients_by_uuids(
                patient_uuids=patient_uuid_subset, q=q
            )
        assert_valid_schema(SearchResultsResponse, result)
        assert result["total"] == expected_total
        assert len(result["results"]) == len(expected)
        assert {p["first_name"] for p in result["results"]} == expected

    @pytest.mark.parametrize(
        "q,expected_total,expected",
        [
            (None, 4, {"Alice", "Bobby", "Carol", "Diane"}),
            (
                "Jones",
                1,
                {
                    "Alice",
                },
            ),
            ("Dur", 2, {"Bobby", "Carol"}),
            ("Mcc", 2, {"Bobby", "Carol"}),
            ("Mcc Dur", 2, {"Bobby", "Carol"}),
            ("D", 3, {"Bobby", "Carol", "Diane"}),
            ("D B", 2, {"Bobby", "Diane"}),
        ],
    )
    def test_search_patients_by_term(
        self,
        four_patient_uuids: List[str],
        q: str,
        expected: Set[str],
        expected_total: int,
        assert_valid_schema: Callable,
        statement_counter: Callable,
    ) -> None:
        with statement_counter(limit=1):
            result: dict = search_controller.search_patients_by_term(q=q)
        assert_valid_schema(SearchResultsResponse, result)
        assert result["total"] == expected_total
        assert len(result["results"]) == len(expected)
        assert {p["first_name"] for p in result["results"]} == expected

    @pytest.mark.parametrize(
        "search_term,expected",
        [
            (
                "Smith",
                "patient.first_name || ' ' || patient.last_name ~ '(?i)Smith'",
            ),
            (
                "adrian, jones",
                "(patient.first_name || ' ' || patient.last_name ~ '(?i)adrian.*\\\\mjones') OR (patient.last_name || ' ' || patient.first_name ~ '(?i)adrian.*\\\\mjones')",
            ),
            (
                "eloise ratke-littel",
                "(patient.first_name || ' ' || patient.last_name ~ '(?i)eloise.*\\\\mratke.*\\\\mlittel') OR (patient.last_name || ' ' || patient.first_name ~ '(?i)eloise.*\\\\mratke.*\\\\mlittel')",
            ),
            (
                ";&;",
                "false",
            ),
            (
                "123456",
                "patient.nhs_number = '123456' OR patient.hospital_number = '123456'",
            ),
        ],
    )
    def test_build_query_search_terms(
        self, _db: SQLAlchemy, search_term: str, expected: str
    ) -> None:
        condition: BooleanClauseList = search_controller.build_query_search_terms(
            search_term=search_term
        )
        statement = str(
            condition.compile(
                compile_kwargs={"literal_binds": True}, dialect=POSTGRESQL_DIALECT
            )
        )
        assert statement == expected
