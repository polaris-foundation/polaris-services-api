from random import randint
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pytest
from pytest_mock import MockerFixture

from dhos_services_api.helpers.composite_queries import composite_query_builder
from dhos_services_api.models.dose import Dose, DoseChange
from dhos_services_api.models.management_plan import DoseHistory, ManagementPlan
from tests.conftest import sanitize_json


@pytest.mark.usefixtures("clean_up_neo4j_after_test")
class TestAggregation:
    @pytest.fixture
    def readings_plan_factory(
        self, node_factory: Callable, relation_factory: Callable
    ) -> Callable:
        def factory(
            days_per_week_to_take_readings: Optional[int] = 4,
            readings_per_day: Optional[int] = 6,
            start_date: Optional[str] = "2019-01-01",
            end_date: Optional[str] = None,
            changes: List[Tuple[int, int]] = None,
        ) -> Callable:
            readings_plan = node_factory(
                "ReadingsPlan",
                sct_code="33747003",
                start_date=start_date,
                end_date=end_date,
                days_per_week_to_take_readings=days_per_week_to_take_readings,
                readings_per_day=readings_per_day,
            )
            if changes:
                for dpw, rpd in changes:
                    readings_plan_change = node_factory(
                        "ReadingsPlanChange",
                        days_per_week_to_take_readings=dpw,
                        readings_per_day=rpd,
                    )
                    relation_factory("HAS_CHANGE", readings_plan, readings_plan_change)
            return readings_plan

        return factory

    @pytest.fixture
    def dose_history_factory(
        self, node_factory: Callable, relation_factory: Callable, dose_factory: Callable
    ) -> Callable:
        def factory(
            dose: Union[str, Dict, None] = None,
            action: Optional[str] = None,
            clinician: Optional[str] = None,
        ) -> Callable:
            dose_history = node_factory("DoseHistory", action=action)
            if dose:
                if isinstance(dose, dict):
                    dose = dose_factory(**dose)
                relation_factory("RELATES_TO_DOSE", dose_history, dose)
            if clinician:
                relation_factory("CHANGED_BY", dose_history, clinician)
            return dose_history

        return factory

    @pytest.fixture
    def dose_factory(
        self, node_factory: Callable, relation_factory: Callable
    ) -> Callable:
        def factory(
            medication_id: str,
            dose_amount: float,
            routine_sct_code: Optional[str] = None,
            dose_changes: Optional[List[Tuple[str, float, str]]] = None,
        ) -> str:
            dose = node_factory(
                "Dose",
                medication_id=medication_id,
                dose_amount=dose_amount,
                routine_sct_code=routine_sct_code,
            )
            if dose_changes:
                for med, amount, code in dose_changes:
                    dose_change = node_factory(
                        "DoseChange",
                        medication_id=med,
                        dose_amount=amount,
                        routine_sct_code=code,
                    )
                    relation_factory("HAS_CHANGE", dose, dose_change)
            return dose

        return factory

    @pytest.fixture
    def action_factory(self, node_factory: Callable) -> Callable:
        def factory(action_sct_code: str) -> Callable:
            return node_factory("NonMedicationAction", action_sct_code=action_sct_code)

        return factory

    @pytest.fixture
    def management_plan_factory(
        self,
        node_factory: Callable,
        relation_factory: Callable,
        dose_factory: Callable,
        action_factory: Callable,
        dose_history_factory: Callable,
    ) -> Callable[[str, List[Dict], List[Dict], List[Dict]], str]:
        def factory(
            start_date: str,
            doses: List[Dict],
            actions: List[Dict],
            dose_history: List[Dict],
        ) -> str:
            management_plan = node_factory(
                "ManagementPlan", sct_code="D0000008", start_date=start_date
            )
            if doses:
                for d in doses:
                    dose = dose_factory(**d)
                    relation_factory("HAS_DOSE", management_plan, dose)

                for a in actions:
                    action = action_factory(**a)
                    relation_factory("HAS_ACTION", management_plan, action)

                for dh in dose_history:
                    dose_history = dose_history_factory(**dh)
                    relation_factory("HAD_DOSE", management_plan, dose_history)
            return management_plan

        return factory

    @pytest.fixture
    def gdm_patient(self, node_factory: Callable, relation_factory: Callable) -> None:
        patient = node_factory(
            "Patient",
            first_name="Edgar",
            nhs_number=str(randint(1_000_000, 10_000_000)),
        )
        record = node_factory("Record")

    @pytest.fixture
    def plan_uuid(self, management_plan_factory: Callable) -> str:
        uuid = management_plan_factory(
            start_date="2018-01-31",
            doses=[
                {
                    "medication_id": "109081006",
                    "dose_amount": 2,
                    "routine_sct_code": "1771000175105",
                }
            ],
            actions=[{"action_sct_code": "12345"}, {"action_sct_code": "67890"}],
            dose_history=[
                {
                    "dose": {
                        "medication_id": "9512801000001102",
                        "dose_amount": 33.0,
                        "routine_sct_code": "1771000175105",
                        "dose_changes": [("9512801000001102", 25.0, "1771000175105")],
                    },
                    "action": "insert",
                }
            ],
        )
        return uuid

    @pytest.mark.parametrize(
        "label,node,expected",
        [
            ("d", DoseChange, """MATCH (d:DoseChange)\nRETURN d"""),
            (
                "d",
                Dose,
                "MATCH (d:Dose)\n"
                "OPTIONAL MATCH (d)-[:HAS_CHANGE]->(changes:DoseChange)\n"
                "WITH d, collect(changes) AS changes\n"
                "RETURN { dose:d, changes:changes } AS d",
            ),
            (
                "dh",
                DoseHistory,
                "MATCH (dh:DoseHistory)\n"
                "OPTIONAL MATCH (dh)-[:RELATES_TO_DOSE]->(dose:Dose)\n"
                "OPTIONAL MATCH (dose)-[:HAS_CHANGE]->(changes:DoseChange)\n"
                "WITH dh, dose, collect(changes) AS changes\n"
                "WITH dh, CASE WHEN dose IS NOT NULL THEN { dose:dose, changes:changes } END AS dose\n"
                "WITH dh, collect(dose) AS dose\n"
                "RETURN { dose_history:dh, dose:dose } AS dh",
            ),
        ],
    )
    def test_query_builder(self, label: str, node: Any, expected: str) -> None:
        query = composite_query_builder(
            label, node, f"MATCH ({label}:{node.__label__})"
        )
        assert query == expected

    @pytest.mark.parametrize(
        "labels,node,base_query,expected",
        [
            (
                ["dh", "clinician_id"],
                DoseHistory,
                "MATCH (dh:DoseHistory)-[:CHANGED_BY]->(clinician:Clinician)\n"
                "WITH dh, collect(clinician.uuid) as clinician_id",
                "MATCH (dh:DoseHistory)-[:CHANGED_BY]->(clinician:Clinician)\n"
                "WITH dh, collect(clinician.uuid) as clinician_id\n"
                "OPTIONAL MATCH (dh)-[:RELATES_TO_DOSE]->(dose:Dose)\n"
                "OPTIONAL MATCH (dose)-[:HAS_CHANGE]->(changes:DoseChange)\n"
                "WITH dh, clinician_id, dose, collect(changes) AS changes\n"
                "WITH dh, clinician_id, CASE WHEN dose IS NOT NULL THEN { dose:dose, changes:changes } END AS dose\n"
                "WITH dh, clinician_id, collect(dose) AS dose\n"
                "RETURN { dose_history:dh, clinician_id:clinician_id, dose:dose } AS dh",
            )
        ],
    )
    def test_query_extra_results(
        self, labels: List[str], node: Any, base_query: str, expected: str
    ) -> None:
        query = composite_query_builder(
            labels[0],
            node,
            base_query,
            ignore_nodes={"TermsAgreement", "Patient", "Clinician"},
            extra_fields=labels[1:],
        )
        assert query == expected

    @pytest.mark.neo4j
    def test_no_history(self) -> None:
        histories = DoseHistory.nodes.all()
        assert len(histories) == 0

    @pytest.mark.neo4j
    def test_dose_history(self, jwt_system: str, plan_uuid: str) -> None:
        from dhos_services_api.neodb import db

        ignored_fields = {"created", "created_by", "modified", "modified_by"}

        histories = DoseHistory.nodes.all()
        assert len(histories) == 1

        simple_dict = sanitize_json(histories[0].to_dict(), ignored=ignored_fields)
        query = composite_query_builder("x", DoseHistory, f"MATCH (x:DoseHistory)")
        results, meta = db.cypher_query(query, {})
        full_dict = sanitize_json(
            DoseHistory.convert_response_to_dict(
                results[0][0], method="to_dict_no_relations"
            ),
            ignored=ignored_fields,
        )
        assert full_dict == simple_dict

    @pytest.mark.neo4j
    def test_management_plan(
        self,
        management_plan_factory: Callable,
        jwt_system: str,
        plan_uuid: str,
        mocker: MockerFixture,
    ) -> None:
        from dhos_services_api.neodb import db

        ignored_fields = {"created", "created_by", "modified", "modified_by"}

        wrapped_cypher_query = mocker.patch.object(
            db, "cypher_query", wraps=db.cypher_query
        )
        cypher_call_count = 0

        def call_count() -> int:
            nonlocal cypher_call_count
            new_calls = wrapped_cypher_query.call_count - cypher_call_count
            cypher_call_count = wrapped_cypher_query.call_count
            return new_calls

        plan = ManagementPlan.nodes.get(uuid=plan_uuid)
        assert call_count() == 1

        simple_dict = plan.to_dict()
        assert call_count() == 6

        simple_dict = sanitize_json(simple_dict, ignored=ignored_fields)
        assert set(action["action_sct_code"] for action in simple_dict["actions"]) == {
            "12345",
            "67890",
        }
        assert simple_dict["dose_history"][0]["action"] == "insert"
        assert (
            simple_dict["dose_history"][0]["dose"]["changes"][0]["dose_amount"] == 25.0
        )
        assert simple_dict["doses"][0]["changes"] == []
        assert simple_dict["doses"][0]["dose_amount"] == 2
        assert simple_dict["start_date"] == "2018-01-31"

        cypher = composite_query_builder(
            "m", ManagementPlan, "MATCH (m:ManagementPlan { uuid: {plan_uuid}})"
        )
        results, meta = db.cypher_query(cypher, {"plan_uuid": plan_uuid})
        assert len(results) == 1
        assert call_count() == 1

        full_dict = sanitize_json(
            ManagementPlan.convert_response_to_dict(
                results[0][0], method="to_dict_no_relations"
            ),
            ignored=ignored_fields,
        )
        assert call_count() == 0
        assert full_dict == simple_dict
