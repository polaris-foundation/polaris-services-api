from typing import Dict, List, Optional

import draymed
from flask_batteries_included.helpers.error_handler import EntityNotFoundException
from flask_batteries_included.sqldb import db
from sqlalchemy import and_, any_, or_

from dhos_services_api.sqlmodels import (
    Diagnosis,
    DraysonHealthProduct,
    Record,
    pydantic_models,
)
from dhos_services_api.sqlmodels.patient import (
    Patient,
    query_options_compact_patient_response,
    query_top_level_patients,
)

WARD_LOCATION_TYPE = draymed.codes.code_from_name(name="ward", category="location")


def get_gdm_patients_by_location(
    location_uuid: str,
    current: Optional[bool] = None,
    diagnosis: Optional[str] = None,
    include_all: Optional[bool] = None,
) -> list[dict]:
    query = db.session.query(Patient)
    query = query.filter(location_uuid == any_(Patient.locations))

    product_filter = DraysonHealthProduct.patient_id == Patient.uuid
    if current is True:
        # active patients at location
        product_filter = and_(product_filter, DraysonHealthProduct.closed_date == None)
    elif current is False:
        # inactive patients at location
        product_filter = and_(product_filter, DraysonHealthProduct.closed_date != None)
        if not include_all:
            # Hide patients created in error unless we specifically ask for them all.
            product_filter = and_(
                product_filter,
                or_(
                    DraysonHealthProduct.closed_reason == None,
                    DraysonHealthProduct.closed_reason != "D0000034",
                ),
            )

    query = query.join(DraysonHealthProduct, product_filter)

    if diagnosis:
        query = (
            query.join(Patient.record)
            .join(Record.diagnoses)
            .filter(
                or_(
                    Diagnosis.sct_code == diagnosis,
                    Diagnosis.diagnosis_other == diagnosis,
                ),
            )
        )

    query = query.options(*query_options_compact_patient_response()).order_by(
        Patient.uuid
    )
    return [
        pydantic_models.CompactPatientResponse.from_orm(patient).dict()
        for patient in query
    ]


def bookmark_patient(location_id: str, patient_id: str, is_bookmarked: bool) -> Dict:
    if not isinstance(is_bookmarked, bool):
        raise ValueError("Incorrect value supplied")

    query = db.session.query(Patient).filter(
        Patient.uuid == patient_id, location_id == any_(Patient.locations)
    )
    patient = query.first()
    if patient is None:
        raise EntityNotFoundException(
            f"Patient with id {patient_id} not found at location {location_id}"
        )

    if is_bookmarked:
        patient.has_been_bookmarked = True
        patient.bookmarked_at_locations = [
            loc for loc in patient.bookmarked_at_locations if loc != location_id
        ] + [location_id]
    else:
        patient.bookmarked_at_locations = [
            loc for loc in patient.bookmarked_at_locations if loc != location_id
        ]

    result = pydantic_models.PatientResponse.from_orm(patient).dict()
    db.session.add(patient)
    db.session.commit()
    return result


def get_patients_by_product_and_identifer(
    product_name: str, identifier_type: str, identifier_value: str
) -> List[Dict]:

    base_query = db.session.query(Patient.uuid).join(
        DraysonHealthProduct,
        and_(
            DraysonHealthProduct.patient_id == Patient.uuid,
            DraysonHealthProduct.product_name == product_name,
        ),
    )

    if identifier_type.upper() == "NHS_NUMBER":
        base_query = base_query.filter(
            Patient.nhs_number == identifier_value,
        )
    elif identifier_type.upper() in ["MRN", "HOSPITAL_NUMBER"]:
        base_query = base_query.filter(
            Patient.hospital_number == identifier_value,
        )
    else:
        # We can't get here due to previous validation.
        raise ValueError()

    # Filter only top level parent patient records
    query = query_top_level_patients(base_query)

    return [
        pydantic_models.PatientResponse.from_orm(patient).dict() for patient in query
    ]
