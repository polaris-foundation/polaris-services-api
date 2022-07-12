from __future__ import annotations

import re

import sqlalchemy.sql.elements
from flask_batteries_included.sqldb import db
from sqlalchemy import or_
from sqlalchemy.orm import Query
from sqlalchemy.sql.elements import BooleanClauseList

from dhos_services_api.sqlmodels import Patient, pydantic_models


def search_patients_by_uuids(patient_uuids: list[str], q: str | None) -> dict:
    results: list[dict]
    query: Query = db.session.query(Patient).filter(
        Patient.uuid.in_(patient_uuids), Patient.child_of == None
    )
    query = query.filter(build_query_search_terms(q))
    results = [
        pydantic_models.SearchPatient.from_orm(result).dict() for result in query
    ]
    return {"total": len(results), "results": results}


def search_patients_by_term(
    q: str,
) -> dict:
    # If search is numeric search all Patients with encounters (open
    # as well as discharged) by MRN or NHS Number using an exact match
    # If search is non-numeric search patients
    # where first name or last name starts with the search phrase
    # case-insensitive
    results, total = search_all_patients(q=q)

    return {"total": total, "results": results}


def search_all_patients(q: str) -> tuple[list[dict], int]:
    results: list[dict]

    query: Query = db.session.query(Patient).filter(Patient.child_of == None)
    query = query.filter(build_query_search_terms(q))
    results = [
        pydantic_models.SearchPatient.from_orm(result).dict() for result in query
    ]
    return results, len(results)


def build_query_search_terms(
    search_term: str | None,
) -> BooleanClauseList:
    filters: list[object] = []

    if not search_term:
        return sqlalchemy.and_(sqlalchemy.true())

    search_words = re.sub("\\W", " ", search_term).strip()
    search_terms: list[str] = [
        re.escape(s.strip()) for s in search_words.split() if s.strip()
    ]

    if not search_terms:
        return sqlalchemy.and_(sqlalchemy.false())

    search_re = "(?i)" + r".*\m".join(search_terms)
    if len(search_terms) == 1 and search_term.isdigit():
        filters += [
            Patient.nhs_number == search_term,
            Patient.hospital_number == search_term,
        ]
    else:
        filters.append(
            (Patient.first_name + " " + Patient.last_name).op("~")(search_re)
        )

    if len(search_terms) > 1:
        filters.append(
            (Patient.last_name + " " + Patient.first_name).op("~")(search_re)
        )

    return or_(*filters)
