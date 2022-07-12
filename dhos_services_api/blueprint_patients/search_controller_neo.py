import re
from typing import Dict, List, Optional, Tuple, TypedDict

from flask_batteries_included.helpers.security.jwt import current_jwt_user

from dhos_services_api.models.api_spec import SearchPatient, SearchResultsResponse
from dhos_services_api.neodb import db


class PatientNode(TypedDict, total=False):
    uuid: str
    first_name: str
    last_name: str
    dob: str
    nhs_number: str
    hospital_number: str
    sex: str


SearchResult = Tuple[
    PatientNode,
    Optional[str],
]

SEARCH_RETURN = """
   RETURN DISTINCT p
"""


def search_patients_by_uuids(
    patient_uuids: List[str], q: Optional[str]
) -> SearchResultsResponse.Meta.Dict:
    results, total = _search_patients_by_uuids(patient_uuids=patient_uuids, q=q)
    return search_results(results, total)


def _search_patients_by_uuids(
    patient_uuids: List[str], q: Optional[str]
) -> Tuple[List[SearchResult], int]:
    results: List[SearchResult]
    meta: List[str]
    search_filter_query, params = build_query_search_terms(q)
    results, meta = db.cypher_query(
        (
            "MATCH (p:Patient) "
            "WHERE p.uuid in {patient_uuids} AND NOT (p)-[:CHILD_OF]->() "
            f"{search_filter_query} "
            "OPTIONAL MATCH (p)-[:BOOKMARKED_BY]->(c:Clinician {uuid:{current_clinician}}) "
            "RETURN p, c.uuid as bookmark"
        ),
        {
            "patient_uuids": patient_uuids,
            "current_clinician": current_jwt_user(),
            **params,
        },
    )
    return results, len(results)


def search_results(
    results: List[SearchResult], total: int
) -> SearchResultsResponse.Meta.Dict:
    # Build search results
    if not results:
        return {"total": 0, "results": []}

    search_results: List[SearchPatient.Meta.Dict] = [
        SearchPatient.Meta.Dict(
            patient_uuid=patient["uuid"],
            first_name=patient.get("first_name"),
            last_name=patient.get("last_name"),
            dob=patient.get("dob"),
            nhs_number=patient.get("nhs_number"),
            hospital_number=patient.get("hospital_number"),
            has_clinician_bookmark=bool(bookmark),
            sex=patient.get("sex"),
        )
        for (patient, bookmark) in results
    ]
    return {"total": total, "results": search_results}


def search_patients_by_term(
    q: str,
) -> SearchResultsResponse.Meta.Dict:
    results: List[SearchResult]
    total: int
    # If search is numeric search all Patients with encounters (open
    # as well as discharged) by MRN or NHS Number using an exact match
    # If search is non-numeric search patients
    # where first name or last name starts with the search phrase
    # case-insensitive
    results, total = search_all_patients(q=q)

    return search_results(results, total)


def search_all_patients(q: str) -> Tuple[List[SearchResult], int]:
    results: List[SearchResult]
    meta: List[str]
    search_filter_query, params = build_query_search_terms(q)
    results, meta = db.cypher_query(
        (
            "MATCH (p:Patient) "
            "WHERE NOT (p)-[:CHILD_OF]->() "
            f"{search_filter_query} "
            "OPTIONAL MATCH (p)-[:BOOKMARKED_BY]->(c:Clinician {uuid:{current_clinician}}) "
            "RETURN p, c.uuid as bookmark"
        ),
        {
            "current_clinician": current_jwt_user(),
            **params,
        },
    )
    return results, len(results)


def build_query_search_terms(search_term: Optional[str]) -> Tuple[str, Dict[str, str]]:
    if not search_term:
        return "", {}

    search_words = re.sub("\\W", " ", search_term).strip()
    search_terms: List[str] = [
        re.escape(s.strip()) for s in search_words.split() if s.strip()
    ]

    if not search_terms:
        return "AND false", {}

    search_filter = []
    if len(search_terms) == 1 and search_term.isdigit():
        search_filter += [
            "p.nhs_number={search_term}",
            "p.hospital_number={search_term}",
        ]
    else:
        search_filter += [
            f"(p.first_name+' '+p.last_name)=~{{search_re}}",
        ]

    if len(search_terms) > 1:
        search_filter += [f"(p.last_name+' '+p.first_name)=~{{search_re}}"]

    search_re = ".*\\b".join(search_terms)
    params = {
        "search_re": f"(?i).*\\b{search_re}.*",
        "search_term": search_term.strip(),
    }

    search_filter_query = " AND ((" + ") OR (".join(search_filter) + ")) "
    return search_filter_query, params
