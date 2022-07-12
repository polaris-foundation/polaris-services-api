from datetime import datetime
from typing import Callable

import pytest
from marshmallow import RAISE
from neomodel import db
from pytest_mock import MockerFixture

from dhos_services_api.blueprint_patients import mixed_controller_neo
from dhos_services_api.models.api_spec import PatientResponse


@pytest.mark.usefixtures("mock_retrieve_jwt_claims", "clean_up_neo4j_after_test")
class TestMixedController:
    @pytest.fixture
    def patient_child_children(self) -> None:
        query = """
            CREATE
             (l1:Location {uuid:'L1', active:true, location_type:'test3'}),
             (l3:Location {uuid:'L3', active:true, location_type:'test2'}),
             (lp1:Location {uuid:'LP1', active:true, location_type:'test1'}),
             (lpr1:LocationProduct {product_name:'SEND'}),
             (lpr3:LocationProduct {product_name:'SEND'}),
             (p1:Patient {uuid:'P1', hospital_number:'MRN1', first_name:'Peter', last_name:'Griffin'}),
             (p2:Patient {uuid:'P2', hospital_number:'MRN2', first_name:'Lois', last_name:'Griffin'}),
             (p3:Patient {uuid:'P3', hospital_number:'MRN3', first_name:'Brian', last_name:'Griffin'}),
             (l3)-[:ACTIVE_ON_PRODUCT]->(lpr3),
             (lpr1)<-[:ACTIVE_ON_PRODUCT]-(lp1),
             (lp1)<-[:CHILD_OF]-(l1),
             (lp1)<-[:CHILD_OF]-(l3),
             (p1)-[:HAS_RECORD]->(pr1:Record {uuid:'R1'}),
             (p1)-[:ACTIVE_ON_PRODUCT]->(dh1:DraysonHealthProduct {uuid:'DH1', product_name:'SEND'}),
             (pr1)-[:HAS_HISTORY]->(h1:History),
             (p2)-[:CHILD_OF]->(p1),
             (pr2:Record {uuid:'R2'}),
             (pr2)-[:HAS_HISTORY]->(h2:History),
             (p3)-[:HAS_RECORD]->(pr3:Record {uuid:'R3'}),
             (p3)-[:CHILD_OF]->(p2),
             (p3)-[:ACTIVE_ON_PRODUCT]->(dh3:DraysonHealthProduct {uuid:'DH3', product_name:'SEND'}),
             (pr3)-[:HAS_HISTORY]->(h3:History)
            """
        results, meta = db.cypher_query(query)

    def test_get_patient_by_product_and_identifer(
        self, patient_child_children: MockerFixture
    ) -> None:
        expected = "P1"
        result = mixed_controller_neo.get_patients_by_product_and_identifer(
            product_name="SEND", identifier_type="mrn", identifier_value="MRN3"
        )
        assert expected == result[0]["uuid"]
        for patient in result:
            PatientResponse().load(patient, unknown=RAISE)
        PatientResponse().load(result, many=True, unknown=RAISE)

    def test_bookmark_patient(
        self, gdm_patient_uuid: str, gdm_location_uuid: str
    ) -> None:
        bookmarked_patient = mixed_controller_neo.bookmark_patient(
            patient_id=gdm_patient_uuid,
            location_id=gdm_location_uuid,
            is_bookmarked=True,
        )
        unbookmarked_patient = mixed_controller_neo.bookmark_patient(
            patient_id=gdm_patient_uuid,
            location_id=gdm_location_uuid,
            is_bookmarked=False,
        )
        assert bookmarked_patient["bookmarked"] is True
        assert bookmarked_patient["has_been_bookmarked"] is True

        assert unbookmarked_patient["bookmarked"] is False
        assert unbookmarked_patient["has_been_bookmarked"] is True

        PatientResponse().load(bookmarked_patient, unknown=RAISE)
        PatientResponse().load(unbookmarked_patient, unknown=RAISE)

    def test_get_babies_from_deliveries(
        self, node_factory: Callable, relation_factory: Callable
    ) -> None:
        delivery_uuid: str = node_factory("Delivery")
        baby_uuid: str = node_factory("Baby", dob=datetime.now())
        relation_factory("IS_PATIENT", delivery_uuid, baby_uuid)
        result = mixed_controller_neo.get_babies_from_deliveries(
            delivery_uuids=[delivery_uuid]
        )
        assert len(result) == 1
        assert delivery_uuid in result
        assert result[delivery_uuid]["uuid"] == baby_uuid

    def test_get_deliveries_from_pregnancies(
        self, node_factory: Callable, relation_factory: Callable
    ) -> None:
        pregnancy_uuid: str = node_factory("Pregnancy")
        delivery_uuid: str = node_factory("Delivery")
        relation_factory("HAS_DELIVERY", pregnancy_uuid, delivery_uuid)
        result = mixed_controller_neo.get_deliveries_from_pregnancies(
            pregnancies_uuid=[pregnancy_uuid]
        )
        pregnancies = result[0]
        delivery_uuids = result[1]
        assert len(pregnancies.keys()) == 1
        assert pregnancies[pregnancy_uuid] == [{"uuid": delivery_uuid}]
        assert delivery_uuids == [delivery_uuid]
