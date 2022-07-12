from typing import Any, Dict, List, Optional

import draymed
from flask_batteries_included.helpers.error_handler import EntityNotFoundException

from dhos_services_api.models.patient import Patient
from dhos_services_api.neodb import db

WARD_LOCATION_TYPE = draymed.codes.code_from_name(name="ward", category="location")

ADD_BOOKMARK_QUERY = """
    MATCH (patient:Patient)
    WHERE patient.uuid={p_uuid} and {location_id} IN patient.locations
    SET patient.bookmarked_at_locations = FILTER(
      loc IN patient.bookmarked_at_locations WHERE loc <> {location_id})  + [{location_id}],
      patient.has_been_bookmarked = true
    RETURN patient
"""

REMOVE_BOOKMARK_QUERY = """
    MATCH (patient:Patient)
    WHERE patient.uuid={p_uuid} and {location_id} IN patient.locations
    SET patient.bookmarked_at_locations = FILTER(
      loc IN patient.bookmarked_at_locations WHERE loc <> {location_id})
    RETURN patient
"""


def get_gdm_patients_by_location(
    location_uuid: str,
    current: Optional[bool] = None,
    diagnosis: Optional[str] = None,
    include_all: Optional[bool] = None,
) -> list:

    if diagnosis:
        query_sections = [
            "MATCH (p:Patient)-[:ACTIVE_ON_PRODUCT]-(dh:DraysonHealthProduct {product_name: 'GDM'})"
            ", (p)-[:HAS_RECORD]-(r:Record)-[:HAS_DIAGNOSIS]-(g:Diagnosis)",
            " OPTIONAL MATCH (r)-[:HAS_PREGNANCY]-(pg:Pregnancy)",
        ]
    else:
        query_sections = [
            "MATCH (p:Patient)-[:ACTIVE_ON_PRODUCT]-(dh:DraysonHealthProduct {product_name: 'GDM'})",
            " OPTIONAL MATCH (p)-[:HAS_RECORD]-(r:Record)",
            " OPTIONAL MATCH (r)-[:HAS_DIAGNOSIS]-(g:Diagnosis)",
            " OPTIONAL MATCH (r)-[:HAS_PREGNANCY]-(pg:Pregnancy)",
        ]

    predicates: List[str] = ["ANY(loc IN p.locations WHERE loc={location_id})"]
    pregnancies_uuid: List[str] = []

    # active patients at location
    if current is True:
        predicates.append("dh.closed_date IS NULL")
    # inactive patients at location
    elif current is False:
        predicates.append("dh.closed_date IS NOT NULL")

        # Hide patients created in error unless we specifically ask for them all.
        if not include_all:
            predicates.append(
                f"(dh.closed_reason IS NULL OR dh.closed_reason <> 'D0000034')"
            )

    if diagnosis is not None:
        predicates.append("(g.sct_code={diagnosis} OR g.diagnosis_other={diagnosis})")

    condition = ""
    if predicates:
        condition = " WHERE " + "\nAND ".join(predicates) + " "

    query_sections[0] += condition
    query_base = "\n".join(query_sections)

    full_query = [
        query_base,
        "RETURN p, r, collect(dh) as dh, collect(g) as g, collect(pg) as pg",
    ]

    query = "\n".join(filter(None, full_query))

    results, meta = db.cypher_query(
        query,
        {
            "location_id": location_uuid,
            "diagnosis": diagnosis,
        },
    )
    # Get all deliveries for each pregnancy
    patients = []
    for (
        res_patient,
        res_record,
        res_products,
        res_diagnoses,
        res_pregnancies,
    ) in results:
        record: Optional[Dict[str, Any]] = None
        if res_record:
            diagnoses = [
                {
                    "diagnosed": returned_diagnosis.get("diagnosed_"),
                    "sct_code": returned_diagnosis.get("sct_code"),
                    "uuid": returned_diagnosis.get("uuid"),
                }
                for returned_diagnosis in res_diagnoses
            ]

            pregnancies = []
            for pregnancy in res_pregnancies:
                pregnancy_uuid = pregnancy.get("uuid")
                pregnancies_uuid.append(pregnancy_uuid)
                p = {
                    "estimated_delivery_date": pregnancy.get("estimated_delivery_date"),
                    "uuid": pregnancy_uuid,
                }
                pregnancies.append(p)

            record = {
                "uuid": res_record.get("uuid"),
                "diagnoses": diagnoses,
                "pregnancies": pregnancies,
            }

        dh_products = [
            {
                "closed_date": dh_product.get("closed_date"),
                "closed_reason": dh_product.get("closed_reason"),
                "closed_reason_other": dh_product.get("closed_reason_other"),
                "opened_date": dh_product.get("opened_date"),
                "product_name": dh_product.get("product_name"),
                "uuid": dh_product.get("uuid"),
            }
            for dh_product in res_products
        ]

        patient = {
            "dob": res_patient.get("dob"),
            "nhs_number": res_patient.get("nhs_number"),
            "hospital_number": res_patient.get("hospital_number"),
            "sex": res_patient.get("sex"),
            "record": record,
            "bookmarked": bool(res_patient.get("bookmarked_at_locations")),
            "dh_products": dh_products,
            "first_name": res_patient.get("first_name"),
            "last_name": res_patient.get("last_name"),
            "uuid": res_patient.get("uuid"),
        }

        patients.append(patient)

    if pregnancies_uuid:
        pgs, delivery_uuids = get_deliveries_from_pregnancies(pregnancies_uuid)

        if delivery_uuids:
            babies = get_babies_from_deliveries(delivery_uuids)
        else:
            babies = {}

        for idx, p in enumerate(patients):
            pregnancies = patients[idx]["record"]["pregnancies"]
            for num, preg in enumerate(p["record"].get("pregnancies")):
                pregnancies[num]["deliveries"] = pgs.get(preg["uuid"], [])
                for baby, delivery in enumerate(pregnancies[num]["deliveries"]):
                    pregnancies[num]["deliveries"][baby]["patient"] = babies.get(
                        delivery["uuid"]
                    )
    return patients


def get_babies_from_deliveries(delivery_uuids: list) -> dict:
    query = """
        MATCH (d:Delivery)-[:IS_PATIENT]-(b:Baby)
        WHERE d.uuid in {delivery_uuids}
        RETURN d.uuid, b
    """
    results, meta = db.cypher_query(query, {"delivery_uuids": delivery_uuids})
    babies = {}
    for row in results:
        babies[row[0]] = {"uuid": row[1].get("uuid"), "dob": row[1].get("dob")}

    return babies


def get_deliveries_from_pregnancies(pregnancies_uuid: List[str]) -> tuple:
    query = """
        MATCH (p:Pregnancy)-[:HAS_DELIVERY]-(d:Delivery)
        WHERE p.uuid in {pregnancies_uuid}
        RETURN p.uuid, collect(d)
    """
    results, meta = db.cypher_query(query, {"pregnancies_uuid": pregnancies_uuid})
    pgs = {}
    delivery_uuids = []
    for row in results:
        deliveries = []
        if row[1]:
            for delivery in row[1]:
                delivery_uuid = delivery.get("uuid")
                delivery_uuids.append(delivery_uuid)
                deliveries.append({"uuid": delivery_uuid})
            pgs[row[0]] = deliveries
    return pgs, delivery_uuids


@db.write_transaction
def bookmark_patient(location_id: str, patient_id: str, is_bookmarked: bool) -> Dict:

    if not isinstance(is_bookmarked, bool):
        raise ValueError("Incorrect value supplied")

    query = ADD_BOOKMARK_QUERY if is_bookmarked else REMOVE_BOOKMARK_QUERY

    results, meta = db.cypher_query(
        query,
        {"location_id": location_id, "p_uuid": patient_id},
    )

    try:
        patient = results[0][0]
        patient = Patient.inflate(patient)

        return patient.to_dict()

    except IndexError:
        raise EntityNotFoundException(
            f"Patient with id {patient_id} not found at location {location_id}"
        )


def get_patients_by_product_and_identifer(
    product_name: str, identifier_type: str, identifier_value: str
) -> List[Dict]:

    # Filter only top level parent patient records
    if identifier_type.upper() == "NHS_NUMBER":
        condition = (
            "nhs_number={identifier_value} AND NOT (p)-[:CHILD_OF]->() return p "
        )
    elif identifier_type.upper() in ["MRN", "HOSPITAL_NUMBER"]:
        condition = (
            "hospital_number={identifier_value} AND NOT (p)-[:CHILD_OF]->() return p "
        )
    else:
        # We can't get here due to previous validation.
        raise ValueError()

    # Match parent patient (p) from child patient (pc) by above filter
    query = (
        """MATCH (d:DraysonHealthProduct {product_name: {product_name}})
    -[:ACTIVE_ON_PRODUCT]-(pc:Patient)-[:CHILD_OF *1..]->(p:Patient)
    WHERE pc."""
        + condition
    )

    # Union match to de-duplicate results selecting patient (p) by above filter
    query += (
        """UNION MATCH (d:DraysonHealthProduct {product_name: {product_name}})
    -[:ACTIVE_ON_PRODUCT]-(p:Patient)
    WHERE p."""
        + condition
    )

    results, meta = db.cypher_query(
        query,
        {"identifier_value": identifier_value, "product_name": product_name.upper()},
    )
    return [Patient.inflate(row[0]).to_dict() for row in results]
