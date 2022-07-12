from typing import Dict, List, Optional

from dhos_services_api.helpers.composite_queries import composite_query_builder
from dhos_services_api.models.patient import Patient
from dhos_services_api.neodb import db


def _build_aggregation_query(active: Optional[bool] = None) -> str:
    base_query = (
        "MATCH (patient:Patient)"
        " -[:ACTIVE_ON_PRODUCT]-(dh:DraysonHealthProduct {product_name: {product_name}})\n"
        "WHERE {location_id} IN patient.locations\n"
    )

    if active is True:
        base_query += " AND dh.closed_date IS NULL\n"
    elif active is False:
        base_query += " AND dh.closed_date IS NOT NULL\n"

    base_query += " WITH patient, collect(dh) as dh_products, ({location_id} in patient.bookmarked_at_locations) as bookmarked\n"
    return composite_query_builder(
        "patient",
        Patient,
        base_query,
        terminal_nodes={"Clinician", "Location"},
        ignore_nodes={"TermsAgreement"},
        special_relations={
            "ACTIVE_ON_PRODUCT": None,
            "BOOKMARKED_BY": None,
            "AT_LOCATION": "head(collect({var_name}.uuid))",
            "RELATES_TO_DIAGNOSIS": "collect({var_name}.uuid)",
        },
        extra_fields=["dh_products", "bookmarked"],
    )


def get_aggregated_patients(
    location_uuid: str, product_name: str, active: Optional[bool] = None
) -> List[Dict]:
    params = {"location_id": location_uuid, "product_name": product_name.upper()}

    query: str = _build_aggregation_query(active=active)
    results, meta = db.cypher_query(query, params)

    patients: List[Dict] = [
        Patient.convert_response_to_dict(patient, method="to_dict_no_relations")
        for (patient,) in results
    ]
    return patients
