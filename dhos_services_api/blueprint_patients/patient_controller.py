from __future__ import annotations

import copy
import re

from draymed.codes import code_from_name, list_category
from flask_batteries_included.helpers import schema, timestamp
from flask_batteries_included.helpers.error_handler import (
    DuplicateResourceException,
    EntityNotFoundException,
)
from flask_batteries_included.helpers.timestamp import (
    parse_iso8601_to_datetime_typesafe,
)
from flask_batteries_included.sqldb import db
from she_logging import logger
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Query, joinedload

from dhos_services_api import sqlmodels
from dhos_services_api.blueprint_patients.patient_controller_neo import (
    _publish_diabetes_type_changes,
)
from dhos_services_api.helpers import audit
from dhos_services_api.helpers.model_updates_sql import (
    recursive_delete,
    recursive_patch,
)
from dhos_services_api.sqlmodels import (
    DraysonHealthProduct,
    Patient,
    Pregnancy,
    Record,
    TermsAgreement,
    pydantic_models,
)
from dhos_services_api.sqlmodels.patient import (
    filter_patient_active_on_product,
    query_options_compact_patient_response,
    query_options_full_patient_response,
    query_options_patient_list,
)

DIABETES_CODES = list_category("diabetes_type").keys()
CLOSED_REASON_OTHER = code_from_name("otherReason", "closed_reason")
# This code was used by the Neo4J code but isn't used in the frontend. It may
# be possible to just remove it.
TERMINATION_OF_PREGNANCY = "386639001"

PREGNANCY_TERMINATION_CODES = {
    TERMINATION_OF_PREGNANCY,
    code_from_name("top", "outcome_for_baby"),
    code_from_name("topGt24", "outcome_for_baby"),
}


def get_patient(patient_uuid: str, product_name: str | None) -> dict:
    """
    :param patient_uuid: The uuid of the patient to retrieve
    :param product_name: Upper case string name of dh product. eg. "SEND" or "GDM"
    :return: The patient model instance in dict form
    """
    logger.debug("Getting patient with UUID %s", patient_uuid)
    query: Query = db.session.query(Patient).filter(Patient.uuid == patient_uuid)
    if product_name:
        query = query.filter(filter_patient_active_on_product(product_name))
    query = query.options(*query_options_full_patient_response()).order_by(Patient.uuid)
    patient = query.first()
    if patient is None:
        raise EntityNotFoundException(
            f"Patient not found with product {product_name} and uuid {patient_uuid}"
        )
    audit.record_patient_viewed(patient_uuid=patient_uuid)
    return pydantic_models.PatientResponse.from_orm(patient).dict()


def retrieve_patients_by_uuids(
    patient_uuids: list[str], product_name: str, compact: bool
) -> list[dict]:
    """
    :param patient_uuids: the UUIDs of the patients to retrieve
    :param product_name: the product the patients must be associated with
    :return: The patients as a list of dicts
    """
    query: Query = db.session.query(Patient).filter(Patient.uuid.in_(patient_uuids))
    query = query.filter(filter_patient_active_on_product(product_name))

    if compact:
        # N.B. Query options using subqueryload must be sorted on a unique field
        query = query.options(*query_options_compact_patient_response()).order_by(
            Patient.uuid
        )
    else:
        query = query.options(*query_options_full_patient_response()).order_by(
            Patient.uuid
        )

    patients: list[Patient] = query.all()

    # If at least one of the provided patient UUIDs did not result in a matching patient,
    # complain.
    requested_patient_uuids: set[str] = set(patient_uuids)
    if len(patients) < len(requested_patient_uuids):
        retrieved_patient_uuids: set[str] = set([p.uuid for p in patients])
        missing_uuids: set[str] = requested_patient_uuids - retrieved_patient_uuids
        raise EntityNotFoundException(
            f"Some '{product_name}' patients were not found: {missing_uuids}"
        )

    if compact:
        return [
            pydantic_models.CompactPatientResponse.from_orm(p).dict() for p in patients
        ]
    else:
        return [pydantic_models.PatientResponse.from_orm(p).dict() for p in patients]


def get_patient_abbreviated(patient_uuid: str) -> dict:
    """
    :param patient_uuid:
    :return: The patient model as a dict, only containing location ID, diagnosis sct codes and plans
    """
    record_opt = joinedload(Patient.record)
    diagnoses_opt = record_opt.subqueryload(sqlmodels.Record.diagnoses)
    management_plan_opt = diagnoses_opt.subqueryload(
        sqlmodels.Diagnosis.management_plan
    )
    management_plan_doses_opt = management_plan_opt.subqueryload(
        sqlmodels.ManagementPlan.doses
    ).joinedload(sqlmodels.Dose.changes)

    patient: Patient = (
        db.session.query(Patient)
        .filter(Patient.uuid == patient_uuid)
        .options(
            record_opt,
            diagnoses_opt,
            management_plan_opt,
            management_plan_doses_opt,
        )
        .first()
    )
    record: Record = patient.record
    doses = [
        dose
        for diagnosis in record.diagnoses
        for dose in diagnosis.management_plan.doses
    ]

    # Construct a minimal structure that matches the main one to represent what the apps need
    return {
        "uuid": patient.uuid,
        "locations": patient.locations,
        "record": {
            "diagnoses": [
                {
                    "management_plan": {
                        "doses": [
                            pydantic_models.DoseResponse.from_orm(dose).dict()
                            for dose in doses
                        ]
                    }
                }
            ]
        },
    }


def get_patient_by_record_uuid(record_id: str, compact: bool) -> dict:
    """
    :param record_id: uuid of the patient record
    :param compact: Return a full patient dictionary or a compact version
    :return: The top level patient model instance in dict form
    """
    query: Query = (
        db.session.query(Patient).join(Patient.record).filter(Record.uuid == record_id)
    )
    response = query.first()
    if response is None:
        raise EntityNotFoundException(
            f"No patient found for record {record_id} not found"
        )
    else:
        patient: Patient = response

    while (parent := patient.child_of) is not None:
        patient = parent

    if compact:
        return pydantic_models.CompactPatientResponse.from_orm(patient).dict()
    else:
        return pydantic_models.PatientResponse.from_orm(patient).dict()


def create_patient(product_name: str, patient_details: dict) -> dict:
    if product_name == "SEND":
        if patient_details.get("dod"):
            schema.post(json_in=patient_details, **Patient.send_dod_schema())
        else:
            schema.post(json_in=patient_details, **Patient.send_schema())

        ensure_unique_patient_information(patient_details, product_name)
    else:
        schema.post(json_in=patient_details, **Patient.gdm_schema())
        # don't call validate_patient_information here:
        # allows GDM clinicians to create patients with duplicate details (they are still warned on FE)

    nhs_number = patient_details.get("nhs_number", None)
    if nhs_number:
        ensure_valid_nhs_number(nhs_number)
        ensure_unique_nhs_number(nhs_number, product_name)

    patient = Patient.new(**patient_details)
    db.session.commit()

    return pydantic_models.PatientResponse.from_orm(patient).dict()


def update_patient(patient_uuid: str, patient_details: dict) -> dict:
    """
    Updates a patient using the recursive patch method.
    """
    patient: Patient = db.session.get(Patient, patient_uuid)
    nhs_number: str | None = patient_details.get("nhs_number", None)
    if nhs_number:
        ensure_valid_nhs_number(nhs_number)

    existing_diagnosis_map: dict[str, str] = {
        d.uuid: d.sct_code for d in patient.record.diagnoses
    }

    # Perform the patch. Deepcopy the patient_details input as it get mutated but we need the original later.
    with db.session.no_autoflush:
        recursive_patch(patient, copy.deepcopy(patient_details))

    # Publish an audit message saying who updated the patient.
    audit.record_patient_updated(patient_uuid=patient_uuid)

    # If a GDM patient's diabetes type has changed, publish an audit message specifically for that.
    if patient.has_product(product_name="GDM"):
        _publish_diabetes_type_changes(
            patient_uuid, patient_details, existing_diagnosis_map
        )

    db.session.commit()
    return pydantic_models.PatientResponse.from_orm(patient).dict()


def remove_from_patient(patient_uuid: str, fields_to_remove: dict) -> dict:
    patient: Patient = db.session.get(Patient, patient_uuid)
    recursive_delete(patient, fields_to_remove)
    return pydantic_models.PatientResponse.from_orm(patient).dict()


def _close_gdm_patient_validation(
    closed_reason: str | None, closed_reason_other: str | None, patient: Patient
) -> None:
    if (
        closed_reason == CLOSED_REASON_OTHER and closed_reason_other is None
    ):  # Other code
        raise KeyError("sct code for closed reason is 'other' but no reason provided")

    if closed_reason is not None:
        return

    for pregnancy in patient.record.pregnancies:
        if pregnancy.height_at_booking_in_mm is None:
            raise KeyError("height_at_booking_in_mm is required to close a record")
        if pregnancy.weight_at_booking_in_g is None:
            raise KeyError("weight_at_booking_in_g is required to close a record")
        if pregnancy.length_of_postnatal_stay_in_days is None:
            raise KeyError(
                "length_of_postnatal_stay_in_days is required to close a record"
            )
        if pregnancy.induced is None:
            raise KeyError("induced is required to close a record")

        for delivery in pregnancy.deliveries:

            if (
                delivery.birth_outcome not in PREGNANCY_TERMINATION_CODES
                and delivery.birth_weight_in_grams is None
            ):
                raise KeyError("birth_weight_in_grams is required to close a record")

            if delivery.birth_outcome is None:
                raise KeyError("birth_outcome is required to close a record")
            if delivery.outcome_for_baby is None:
                raise KeyError("outcome_for_baby is required to close a record")

            if (
                delivery.birth_outcome not in PREGNANCY_TERMINATION_CODES
                and not delivery.neonatal_complications
                and delivery.neonatal_complications_other is None
            ):
                raise KeyError("neonatal_complications is required to close a record")
            if (
                delivery.birth_outcome not in PREGNANCY_TERMINATION_CODES
                and delivery.admitted_to_special_baby_care_unit is None
            ):
                raise KeyError(
                    "admitted_to_special_baby_care_unit is required to close a record"
                )
            if (
                delivery.admitted_to_special_baby_care_unit is True
                and delivery.length_of_postnatal_stay_for_baby is None
            ):
                raise KeyError(
                    "length_of_postnatal_stay_for_baby is required to close a record"
                )
            if (
                delivery.birth_outcome not in PREGNANCY_TERMINATION_CODES
                and delivery.patient.dob is None
            ):
                raise KeyError("baby dob is required to close a record")
            if (
                delivery.birth_outcome in PREGNANCY_TERMINATION_CODES
                and delivery.date_of_termination is None
            ):
                raise KeyError("date_of_termination is required to close a record")
            if (
                delivery.birth_outcome not in PREGNANCY_TERMINATION_CODES
                and delivery.date_of_termination is not None
            ):
                raise KeyError(
                    "date_of_termination is not required to close this record"
                )

    diagnosis: sqlmodels.Diagnosis
    for diagnosis in patient.record.diagnoses:
        if diagnosis.sct_code not in DIABETES_CODES:
            continue

        if diagnosis.diagnosed is None:
            raise KeyError("diagnosed (date) is required to close a record")
        if not diagnosis.diagnosis_tool and diagnosis.diagnosis_tool_other is None:
            raise KeyError("diagnosis_tool is required to close a record")
        if not diagnosis.risk_factors:
            raise KeyError("risk_factors is required to close a record")

        plan = diagnosis.readings_plan
        if plan.readings_per_day is None:
            raise KeyError("readings_per_day is required to close a record")
        if plan.days_per_week_to_take_readings is None:
            raise KeyError(
                "days_per_week_to_take_readings is required to close a record"
            )


def close_patient(
    patient_uuid: str,
    product_uuid: str,
    patient_details: dict,
) -> dict:
    product: DraysonHealthProduct = (
        db.session.query(DraysonHealthProduct)
        .filter(
            DraysonHealthProduct.patient_id == patient_uuid,
            DraysonHealthProduct.uuid == product_uuid,
        )
        .first()
    )

    if product is None:
        raise EntityNotFoundException(f"Product with UUID {product_uuid} not found")

    patient: Patient = product.patient

    closed_date: str | None = patient_details.pop("closed_date", None)
    if closed_date is None:
        raise KeyError("A closed date is required in order to close a record")

    closed_reason = patient_details.pop("closed_reason", None)
    closed_reason_other = patient_details.pop("closed_reason_other", None)

    product_name: str = product.product_name.upper()
    if product_name == "GDM":
        _close_gdm_patient_validation(closed_reason, closed_reason_other, patient)
    elif product_name == "DBM":
        pass
    else:
        raise ValueError(f"You cannot close {product_name} patients")

    product.close(closed_date, closed_reason, closed_reason_other)
    db.session.commit()

    audit.record_patient_archived(patient_uuid=patient_uuid)
    return pydantic_models.PatientResponse.from_orm(patient).dict()


def create_patient_tos_v1(patient_uuid: str, terms_details: dict) -> dict:
    tos: TermsAgreement = TermsAgreement.new(patient_id=patient_uuid, **terms_details)
    db.session.commit()
    return pydantic_models.PatientTermsResponseV1.from_orm(tos).dict()


def create_patient_tos_v2(patient_uuid: str, terms_details: dict) -> dict:
    tos: TermsAgreement = TermsAgreement.new(patient_id=patient_uuid, **terms_details)
    db.session.commit()
    return pydantic_models.PatientTermsResponseV2.from_orm(tos).dict()


WHITELIST = {
    "allowed_to_text",
    "first_name",
    "last_name",
    "phone_number",
    "nhs_number",
    "email_address",
    "ethnicity",
    "sex",
    "dod",
    "highest_education_level",
    "other_notes",
    "uuid",
    "allowed_to_email",
    "ethnicity_other",
    "highest_education_level_other",
    "accessibility_considerations_other",
    "dob",
}


def ensure_unique_patient_information(patient_details: dict, product_name: str) -> None:
    hospital_number = patient_details.get("hospital_number", None)
    dob = timestamp.parse_iso8601_to_date(patient_details.get("dob", None))

    if hospital_number:
        query: Query = (
            db.session.query(Patient.uuid)
            .filter(Patient.hospital_number == hospital_number)
            .join(Patient.dh_products)
            .filter(
                DraysonHealthProduct.product_name == product_name,
                DraysonHealthProduct.closed_date == None,
            )
        )

        if query.first():
            raise DuplicateResourceException(
                f"a {product_name} patient already exists with that hospital number"
            )

    if dob:
        fields = {
            k: patient_details[k]
            for k in patient_details.keys() & WHITELIST
            if not isinstance(patient_details[k], (list, dict))
        }

        if "dod" in fields:
            fields["dod"] = timestamp.parse_iso8601_to_date_typesafe(fields["dod"])

        query = (
            db.session.query(Patient.uuid)
            .filter(*[getattr(Patient, k) == v for k, v in fields.items()])
            .filter(
                Patient.dh_products.any(
                    and_(
                        DraysonHealthProduct.closed_date == None,
                        DraysonHealthProduct.product_name == product_name,
                    )
                )
            )
        )

        if query.first():
            raise DuplicateResourceException(
                f"a {product_name} patient already exists with those details"
            )


def ensure_unique_nhs_number(nhs_number: str, product_name: str) -> None:
    """
    Raises a DuplicateResourceException (HTTP 409) if the NHS number is already known.
    """
    query: Query = db.session.query(Patient.uuid).filter(
        Patient.nhs_number == nhs_number,
        Patient.dh_products.any(
            and_(
                DraysonHealthProduct.closed_date == None,
                DraysonHealthProduct.product_name == product_name,
            )
        ),
    )

    if query.first() != None:
        raise DuplicateResourceException(
            f"a {product_name} patient already exists with that NHS number"
        )


def ensure_valid_nhs_number(nhs_number: str) -> bool:
    """
    Validates an NHS number, raising a ValueError if invalid (leading to an HTTP 400 if not handled).
    An NHS number must be 10 digits, where the last digit is a check digit using the modulo 11 algorithm
    (see https://datadictionary.nhs.uk/attributes/nhs_number.html).
    """
    if not re.match(r"^\d{10}$", nhs_number):
        raise ValueError(f"NHS number '{nhs_number}' does not match expected format")

    total: int = sum((10 - i) * int(nhs_number[i]) for i in range(9))
    remainder: int = total % 11
    expected_check_digit: int = 0 if remainder == 0 else 11 - remainder
    actual_check_digit = int(nhs_number[-1])
    if expected_check_digit != actual_check_digit:
        logger.info(
            "Expected check digit is '%d', actual is '%d'",
            expected_check_digit,
            actual_check_digit,
        )
        raise ValueError(f"NHS number '{nhs_number}' is invalid")

    return True


def search_patients(
    locations: list[str],
    product_name: str,
    search_text: str | None,
    active: bool = True,
    modified_since: str | None = None,
    expanded: bool = False,
) -> list[dict]:
    query = db.session.query(Patient).filter(Patient.parent_patient_id == None)

    if search_text is not None:
        search_pattern = f"{search_text}%"
        query = query.filter(
            or_(
                func.lower(Patient.hospital_number) == search_text.lower(),
                Patient.nhs_number == search_text,
                (Patient.first_name + " " + Patient.last_name).ilike(search_pattern),
                (Patient.last_name + " " + Patient.first_name).ilike(search_pattern),
            )
        )

    if locations:
        query = query.filter(Patient.locations.overlap(locations))

    if product_name:
        active_flag = (
            (DraysonHealthProduct.closed_date == None)
            if active
            else (DraysonHealthProduct.closed_date != None)
        )
        query = query.filter(
            Patient.dh_products.any(
                and_(active_flag, DraysonHealthProduct.product_name == product_name)
            )
        )

    if modified_since:
        query = query.filter(
            Patient.modified >= parse_iso8601_to_datetime_typesafe(modified_since)
        )

    if expanded:
        # N.B. Query options using subqueryload must be sorted on a unique field
        query = query.options(*query_options_full_patient_response()).order_by(
            Patient.uuid
        )
        return [pydantic_models.PatientSearchResponse.from_orm(p).dict() for p in query]
    else:
        # N.B. Query options using subqueryload must be sorted on a unique field
        query = query.options(*query_options_compact_patient_response()).order_by(
            Patient.uuid
        )
        return [
            pydantic_models.CompactPatientResponse.from_orm(p).dict() for p in query
        ]


def patient_list(product_name: str, location_uuids: list[str]) -> list[dict]:
    query = db.session.query(Patient)
    query = query.filter(
        Patient.parent_patient_id == None,
        filter_patient_active_on_product(product_name),
        Patient.locations.overlap(location_uuids),
    )
    # Ensure all related records are pulled in either with join or as separate subqueries

    # N.B. Query options using subqueryload must be sorted on a unique field
    query = query.options(*query_options_patient_list()).order_by(Patient.uuid)

    return [
        pydantic_models.PatientDiabetesResponse.from_orm(p).dict(exclude_defaults=True)
        for p in query
    ]


def record_first_medication(
    patient_id: str, first_medication_taken: str, first_medication_taken_recorded: str
) -> None:
    """
    :param first_medication_taken: Relative time of when medication first taken e.g. 5 days ago
    :param first_medication_taken_recorded: The date which first_medication_taken is relative to e.g. 2019-12-31
    :return: None
    """
    patient: Patient = db.session.get(Patient, patient_id)
    pregnancies = patient.record.pregnancies
    if not pregnancies:
        raise ValueError("expected pregnancy data not found")

    latest_pregnancy: Pregnancy = patient.record.pregnancies[0]
    latest_pregnancy.first_medication_taken = first_medication_taken
    latest_pregnancy.first_medication_taken_recorded = first_medication_taken_recorded
    db.session.add(latest_pregnancy)
    db.session.commit()


def set_patient_monitored_by_clinician(
    patient_id: str, product_id: str, monitored_by_clinician: bool
) -> dict:
    product: DraysonHealthProduct = (
        db.session.query(DraysonHealthProduct)
        .filter(
            DraysonHealthProduct.uuid == product_id,
            DraysonHealthProduct.closed_date == None,
            DraysonHealthProduct.patient_id == patient_id,
        )
        .options(joinedload(DraysonHealthProduct.patient))
        .first()
    )
    if product is None:
        raise EntityNotFoundException(f"Product with UUID {product_id} not found")

    if product.monitored_by_clinician is monitored_by_clinician:
        raise ValueError(
            f"Patient with UUID {patient_id} is already {'' if monitored_by_clinician else 'not '}monitored for product with UUID {product_id}"
        )

    if monitored_by_clinician:
        product.start_monitoring()
        audit.record_patient_monitored(patient_id=patient_id, product_id=product_id)
    else:
        product.stop_monitoring()
        audit.record_patient_not_monitored_anymore(
            patient_id=patient_id, product_id=product_id
        )

    return pydantic_models.PatientResponse.from_orm(product.patient).dict(
        exclude_defaults=True
    )


def get_patient_uuids(product_name: str) -> list[str]:
    query = db.session.scalars(
        select(Patient.uuid).filter(
            Patient.parent_patient_id == None,
            Patient.patient_type != "baby",
            filter_patient_active_on_product(product_name),
        )
    )
    return query.all()
