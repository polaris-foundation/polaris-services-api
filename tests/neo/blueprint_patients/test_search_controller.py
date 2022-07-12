from typing import Dict, List, Set, Tuple

import pytest
from _pytest.fixtures import FixtureRequest
from marshmallow import RAISE

from dhos_services_api.blueprint_patients import search_controller_neo
from dhos_services_api.models.api_spec import SearchResultsResponse


@pytest.mark.usefixtures("app", "clean_up_neo4j_after_test")
class TestController:
    @pytest.fixture
    def patient_uuid_subset(
        self, request: FixtureRequest, four_patient_uuids: List[str]
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
    ) -> None:
        result: SearchResultsResponse.Meta.Dict = (
            search_controller_neo.search_patients_by_uuids(
                patient_uuids=patient_uuid_subset, q=q
            )
        )
        SearchResultsResponse().load(result, many=False, partial=False, unknown=RAISE)
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
    ) -> None:
        result: SearchResultsResponse.Meta.Dict = (
            search_controller_neo.search_patients_by_term(q=q)
        )
        SearchResultsResponse().load(result, many=False, partial=False, unknown=RAISE)
        assert result["total"] == expected_total
        assert len(result["results"]) == len(expected)
        assert {p["first_name"] for p in result["results"]} == expected

    @pytest.mark.parametrize(
        "search_term,expected",
        [
            (
                "Smith",
                (
                    " AND (((p.first_name+' '+p.last_name)=~{search_re})) ",
                    {
                        "search_term": "Smith",
                        "search_re": "(?i).*\\bSmith.*",
                    },
                ),
            ),
            (
                "adrian, jones",
                (
                    " AND (((p.first_name+' '+p.last_name)=~{search_re}) OR ((p.last_name+' '+p.first_name)=~{"
                    "search_re})) ",
                    {
                        "search_term": "adrian, jones",
                        "search_re": "(?i).*\\badrian.*\\bjones.*",
                    },
                ),
            ),
            (
                "eloise ratke-littel",
                (
                    " AND (((p.first_name+' '+p.last_name)=~{search_re}) OR ((p.last_name+' '+p.first_name)=~{"
                    "search_re})) ",
                    {
                        "search_term": "eloise ratke-littel",
                        "search_re": "(?i).*\\beloise.*\\bratke.*\\blittel.*",
                    },
                ),
            ),
            (
                ";&;",
                ("AND false", {}),
            ),
            (
                "123456",
                (
                    " AND ((p.nhs_number={search_term}) OR (p.hospital_number={search_term})) ",
                    {"search_re": "(?i).*\\b123456.*", "search_term": "123456"},
                ),
            ),
        ],
    )
    def test_build_query_search_terms(
        self, search_term: str, expected: Tuple[str, Dict]
    ) -> None:
        result: tuple = search_controller_neo.build_query_search_terms(
            search_term=search_term
        )
        assert result == expected
