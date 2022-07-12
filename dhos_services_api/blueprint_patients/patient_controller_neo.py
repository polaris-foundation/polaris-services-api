import copy
import re
from collections import defaultdict
from string import Template
from typing import Dict, List, Optional, Set

import jsonpath_ng
from draymed.codes import list_category
from flask_batteries_included.helpers import schema
from flask_batteries_included.helpers.error_handler import (
    DuplicateResourceException,
    EntityNotFoundException,
)
from flask_batteries_included.helpers.timestamp import (
    parse_iso8601_to_datetime_typesafe,
)
from marshmallow import EXCLUDE
from she_logging import logger

from dhos_services_api.helpers import audit
from dhos_services_api.helpers.composite_queries import composite_query_builder
from dhos_services_api.helpers.model_updates import recursive_delete, recursive_patch
from dhos_services_api.helpers.neo_utils import get_node_or_404
from dhos_services_api.helpers.patient_validator import PatientValidator
from dhos_services_api.models.api_spec import PatientDiabetesResponse
from dhos_services_api.models.dose import Dose
from dhos_services_api.models.drayson_health_product import DraysonHealthProduct
from dhos_services_api.models.patient import Patient, SendPatient
from dhos_services_api.models.pregnancy import Pregnancy
from dhos_services_api.models.record import Record
from dhos_services_api.models.terms_agreement import TermsAgreement
from dhos_services_api.neodb import db

DIABETES_CODES = list(list_category("diabetes_type").keys())


def get_patient(patient_uuid: str, product_name: Optional[str]) -> Dict:
    """
    :param patient_uuid: The uuid of the patient to retrieve
    :param product_name: Upper case string name of dh product. eg. "SEND" or "GDM"
    :return: The patient model instance in dict form
    """
    logger.debug("Getting patient with UUID %s", patient_uuid)
    patient = get_node_or_404(Patient, uuid=patient_uuid)

    if product_name and not patient.has_product(product_name):
        raise EntityNotFoundException(
            f"Patient not found with product {product_name} and uuid {patient_uuid}"
        )

    audit.record_patient_viewed(patient_uuid=patient_uuid)

    return patient.to_dict()


def retrieve_patients_by_uuids(
    patient_uuids: List[str], product_name: str, compact: bool
) -> List[Dict]:
    """
    :param patient_uuids: the UUIDs of the patients to retrieve
    :param product_name: the product the patients must be associated with
    :return: The patients as a list of dicts
    """
    query_string: str = """
    MATCH (p:Patient)-[:ACTIVE_ON_PRODUCT]-(d:DraysonHealthProduct)
    WHERE p.uuid in {patient_uuids} 
    AND d.product_name = {product_name}
    return p;
    """

    results, meta = db.cypher_query(
        query_string, {"patient_uuids": patient_uuids, "product_name": product_name}
    )
    patients: List[Patient] = [Patient.inflate(row[0]) for row in results]

    # If at least one of the provided patient UUIDs did not result in a matching patient,
    # complain.
    requested_patient_uuids: Set[str] = set(patient_uuids)
    if len(patients) < len(requested_patient_uuids):
        retrieved_patient_uuids: Set[str] = set([p.uuid for p in patients])
        missing_uuids: Set[str] = requested_patient_uuids - retrieved_patient_uuids
        raise EntityNotFoundException(
            f"Some '{product_name}' patients were not found: {missing_uuids}"
        )

    if compact:
        return [p.to_compact_dict() for p in patients]
    else:
        return [p.to_dict() for p in patients]


def get_patient_abbreviated(patient_uuid: str) -> Dict:
    """
    :param patient_uuid:
    :return: The patient model as a dict, only containing location ID, diagnosis sct codes and plans
    """
    patient: Patient = get_node_or_404(Patient, uuid=patient_uuid)
    record: Record = patient.record.single()
    doses: List[Dose] = []
    diagnoses = sorted(record.diagnoses.all(), key=lambda x: x.created_, reverse=True)

    for diagnosis in diagnoses:
        doses += diagnosis.management_plan.single().doses  # use += to merge lists

    # Construct a minimal structure that matches the main one to represent what the apps need
    return {
        "uuid": patient.uuid,
        "locations": patient.locations,
        "record": {
            "diagnoses": [
                {"management_plan": {"doses": [dose.to_dict() for dose in doses]}}
            ]
        },
    }


def get_patient_by_record_uuid(record_id: str, compact: bool) -> Dict:
    """
    :param record_id: uuid of the patient record
    :param compact: Return a full patient dictionary or a compact version
    :return: The top level patient model instance in dict form
    """

    query = """
    MATCH (r:Record {uuid:{record_id}})<-[:HAS_RECORD]-(p:Patient)
    WHERE NOT (p)-[:CHILD_OF]->()
    return p
    UNION MATCH (r:Record {uuid:{record_id}})<-[:HAS_RECORD]-(pc:Patient)-[:CHILD_OF *1..]-(p:Patient)
    WHERE NOT (p)-[:CHILD_OF]->()
    return p
    """
    results, meta = db.cypher_query(query, {"record_id": record_id})
    if not results:
        raise EntityNotFoundException(
            f"No patient found for record {record_id} not found"
        )

    patient = Patient.inflate(results[0][0])
    if compact:
        return patient.to_compact_dict()
    else:
        return patient.to_dict()


@db.write_transaction
def create_patient(product_name: str, patient_details: Dict) -> Dict:
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

    if product_name == "SEND":
        patient = SendPatient.new(**patient_details)
    else:
        patient = Patient.new(**patient_details)

    patient.save()

    return patient.to_dict()


@db.write_transaction
def update_patient(patient_uuid: str, patient_details: Dict) -> Dict:
    """
    Updates a patient using the recursive patch method.
    """
    patient: Patient = get_node_or_404(Patient, uuid=patient_uuid)
    nhs_number: Optional[str] = patient_details.get("nhs_number", None)
    if nhs_number:
        ensure_valid_nhs_number(nhs_number)

    existing_diagnosis_map: Dict[str, str] = {
        d.uuid: d.sct_code for d in patient.record.single().diagnoses.all()
    }

    # Perform the patch. Deepcopy the patient_details input as it get mutated but we need the original later.
    recursive_patch(patient, copy.deepcopy(patient_details))

    # Publish an audit message saying who updated the patient.
    audit.record_patient_updated(patient_uuid=patient_uuid)

    # If a GDM patient's diabetes type has changed, publish an audit message specifically for that.
    if patient.has_product(product_name="GDM"):
        _publish_diabetes_type_changes(
            patient_uuid, patient_details, existing_diagnosis_map
        )

    patient.save()
    return patient.to_dict()


def _publish_diabetes_type_changes(
    patient_id: str, patient_details: Dict, existing_diagnosis_map: Dict[str, str]
) -> None:
    for match in jsonpath_ng.parse("$.record.diagnoses[*]").find(patient_details):
        updated_diagnosis: Dict = match.value
        if "sct_code" not in updated_diagnosis or "uuid" not in updated_diagnosis:
            continue
        new_diabetes_type_sct: str = updated_diagnosis["sct_code"]
        old_diabetes_type_sct: str = existing_diagnosis_map[updated_diagnosis["uuid"]]
        if new_diabetes_type_sct != old_diabetes_type_sct:
            audit.record_patient_diabetes_type_changed(
                patient_uuid=patient_id,
                new_type=new_diabetes_type_sct,
                old_type=old_diabetes_type_sct,
            )


@db.write_transaction
def remove_from_patient(patient_uuid: str, fields_to_remove: Dict) -> Dict:
    patient: Patient = get_node_or_404(Patient, uuid=patient_uuid)
    recursive_delete(patient, fields_to_remove)
    patient.save()
    return patient.to_dict()


@db.write_transaction
def close_patient(
    patient_uuid: str,
    product_uuid: str,
    patient_details: Dict,
) -> Dict:
    patient: Patient = get_node_or_404(Patient, uuid=patient_uuid)
    product: Optional[DraysonHealthProduct] = next(
        (x for x in patient.dh_products if x.uuid == product_uuid), None
    )
    if product is None:
        raise EntityNotFoundException(f"Product with UUID {product_uuid} not found")

    closed_date: Optional[str] = patient_details.pop("closed_date", None)
    if closed_date is None:
        raise KeyError("A closed date is required in order to close a record")

    closed_reason = patient_details.pop("closed_reason", None)
    closed_reason_other = patient_details.pop("closed_reason_other", None)

    product_name: str = product.product_name.upper()
    if product_name == "GDM":
        _close_gdm_patient_validation(closed_reason, closed_reason_other, patient)
    elif product_name == "DBM":
        _close_dbm_patient_validation(closed_reason, closed_reason_other, patient)
    else:
        raise ValueError(f"You cannot close {product_name} patients")

    product.close(closed_date, closed_reason, closed_reason_other)

    patient_data = patient.to_dict()
    audit.record_patient_archived(patient_uuid=patient_uuid)
    return patient_data


def _close_dbm_patient_validation(
    closed_reason: Optional[str], closed_reason_other: Optional[str], patient: Patient
) -> None:
    """DBM does not currently have additional validation when closing patients"""


def _close_gdm_patient_validation(
    closed_reason: Optional[str], closed_reason_other: Optional[str], patient: Patient
) -> None:
    if closed_reason is None:
        for pregnancy in patient.record.single().pregnancies:
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
                    delivery.birth_outcome != "386639001"
                    and delivery.birth_weight_in_grams is None
                ):
                    raise KeyError(
                        "birth_weight_in_grams is required to close a record"
                    )

                if delivery.birth_outcome is None:
                    raise KeyError("birth_outcome is required to close a record")
                if delivery.outcome_for_baby is None:
                    raise KeyError("outcome_for_baby is required to close a record")

                if (
                    delivery.birth_outcome != "386639001"
                    and not delivery.neonatal_complications
                    and delivery.neonatal_complications_other is None
                ):
                    raise KeyError(
                        "neonatal_complications is required to close a record"
                    )
                if (
                    delivery.birth_outcome != "386639001"
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
                    delivery.birth_outcome != "386639001"
                    and delivery.patient.single().dob is None
                ):
                    raise KeyError("baby dob is required to close a record")
                if (
                    delivery.birth_outcome == "386639001"
                    and delivery.date_of_termination is None
                ):
                    raise KeyError("date_of_termination is required to close a record")
                if (
                    delivery.birth_outcome != "386639001"
                    and delivery.date_of_termination is not None
                ):
                    raise KeyError(
                        "date_of_termination is not required to close this record"
                    )

        for diagnosis in patient.record.single().diagnoses.filter(
            sct_code__in=DIABETES_CODES
        ):
            if diagnosis.diagnosed is None:
                raise KeyError("diagnosed (date) is required to close a record")
            if not diagnosis.diagnosis_tool and diagnosis.diagnosis_tool_other is None:
                raise KeyError("diagnosis_tool is required to close a record")
            if not diagnosis.risk_factors:
                raise KeyError("risk_factors is required to close a record")

            plan = diagnosis.readings_plan.single()
            if plan.readings_per_day is None:
                raise KeyError("readings_per_day is required to close a record")
            if plan.days_per_week_to_take_readings is None:
                raise KeyError(
                    "days_per_week_to_take_readings is required to close a record"
                )

    elif closed_reason == "D0000028" and closed_reason_other is None:  # Other code
        raise KeyError("sct code for closed reason is 'other' but no reason provided")


@db.write_transaction
def create_patient_tos(patient_uuid: str, terms_details: Dict) -> Dict:
    patient: Patient = get_node_or_404(Patient, uuid=patient_uuid)
    tos: TermsAgreement = TermsAgreement.new(**terms_details)
    patient.terms_agreement.connect(tos)
    tos.save()
    patient.save()
    return tos.to_dict()


@db.write_transaction
def create_patient_tos_v2(patient_uuid: str, terms_details: Dict) -> Dict:
    patient: Patient = get_node_or_404(Patient, uuid=patient_uuid)
    tos: TermsAgreement = TermsAgreement.new_v2(**terms_details)
    patient.terms_agreement.connect(tos)
    tos.save()
    patient.save()
    return tos.to_dict()


def ensure_unique_patient_information(patient_details: Dict, product_name: str) -> None:
    validator = PatientValidator(patient_details)

    if validator.exists_by_hospital_num(product_name):
        raise DuplicateResourceException(
            f"a {product_name} patient already exists with that hospital number"
        )

    if validator.exists_by_details(product_name):
        raise DuplicateResourceException(
            f"a {product_name} patient already exists with those details"
        )


def ensure_unique_nhs_number(nhs_number: str, product_name: str) -> None:
    """
    Raises a DuplicateResourceException (HTTP 409) if the NHS number is already known.
    """
    if PatientValidator.exists_by_nhs_number(nhs_number, product_name):
        raise DuplicateResourceException(
            f"a {product_name} patient already exists with that NHS number"
        )


def ensure_valid_nhs_number(nhs_number: str) -> bool:
    """
    Validates an NHS number, raising a ValueError if invalid (leading to an HTTP 400 if not handled).
    An NHS number must be 10 digits, where the last digit is a check digit using the modulo 11 algorithm
    (see https://datadictionary.nhs.uk/attributes/nhs_number.html).
    """
    is_correct_format = re.match(r"^[0-9]{10}$", nhs_number) is not None
    if not is_correct_format:
        raise ValueError(f"NHS number '{nhs_number}' does not match expected format")
    digits = [int(d) for d in nhs_number]
    total = sum((10 - i) * digit for i, digit in enumerate(digits[:9]))
    expected_check_digit = 11 - (total % 11)
    actual_check_digit = digits[-1]
    if expected_check_digit == 10:
        logger.info("Got invalid check digit '10'")
        raise ValueError(f"NHS number '{nhs_number}' is invalid")
    if expected_check_digit == 11 and actual_check_digit != 0:
        logger.info("Expected check digit is '0', actual is '%d'", actual_check_digit)
        raise ValueError(f"NHS number '{nhs_number}' is invalid")
    if expected_check_digit < 10 and expected_check_digit != actual_check_digit:
        logger.info(
            "Expected check digit is '%d', actual is '%d'",
            expected_check_digit,
            actual_check_digit,
        )
        raise ValueError(f"NHS number '{nhs_number}' is invalid")
    return True


PATIENT_SEARCH_QUERY = Template(
    composite_query_builder(
        "patient",
        Patient,
        "MATCH (patient:Patient)\n"
        "WHERE NOT (patient)-[:CHILD_OF]->() AND (${patient_constraint}) AND (${location_constraint}) AND (${modified_since_constraint})\n"
        "WITH patient\n"
        "    MATCH (patient)-[:ACTIVE_ON_PRODUCT]->(dh_products:DraysonHealthProduct)\n"
        "    WHERE (${product_constraint})\n"
        "WITH patient, collect(dh_products) as dh_products\n",
        ignore_nodes={
            "Clinician",
            "DraysonHealthProduct",
            "DoseHistory",
            "Dose",
            "DoseChange",
            "History",
            "Location",
            "NonMedicationAction",
            "Note",
            "PersonalAddress",
            "ReadingsPlan",
            "ObservableEntity",
            "TermsAgreement",
            "Visit",
        },
        special_relations={"CHILD_OF": None},
        extra_fields=["dh_products"],
    )
)


def search_patients(
    locations: List[str],
    product_name: str,
    search_text: Optional[str],
    active: bool = True,
    modified_since: Optional[str] = None,
    expanded: bool = False,
) -> List[Dict]:
    active_flag = "NULL" if active else "NOT NULL"

    patient_constraint = (
        _build_conditions(search_text) if search_text is not None else "true"
    )
    escaped_text = "" if search_text is None else re.escape(search_text)
    search_pattern = f"(?i)^{escaped_text}.*"

    location_constraint = (
        "FILTER(loc IN patient.locations WHERE loc IN {locations})"
        if locations
        else "true"
    )
    product_constraint = (
        f"dh_products.closed_date IS {active_flag} AND dh_products.product_name={{product_name}}"
        if product_name
        else "true"
    )

    modified_since_parsed: Optional[float] = None
    modified_since_constraint: str = "true"

    if modified_since:
        modified_since_constraint = "patient.modified >= {modified_since}"
        modified_since_parsed = parse_iso8601_to_datetime_typesafe(
            modified_since
        ).timestamp()

    query = PATIENT_SEARCH_QUERY.substitute(
        {
            "patient_constraint": patient_constraint,
            "location_constraint": location_constraint,
            "product_constraint": product_constraint,
            "modified_since_constraint": modified_since_constraint,
        }
    )
    results, meta = db.cypher_query(
        query,
        {
            "search_text": search_text,
            "search_pattern": search_pattern,
            "locations": locations,
            "product_name": product_name,
            "modified_since": modified_since_parsed,
        },
    )
    method = "to_dict_no_relations" if expanded else "to_compact_dict"
    patients: List[Dict] = [
        Patient.convert_response_to_dict(patient, method=method)
        for (patient,) in results
    ]
    return patients


def _build_conditions(search_text: str) -> str:
    conditions: List = [
        "toLower(patient.hospital_number)=toLower({search_text})",
        "patient.nhs_number={search_text}",
        "(patient.first_name + ' ' + patient.last_name)=~{search_pattern}",
        "(patient.last_name + ' ' + patient.first_name)=~{search_pattern}",
    ]

    condition = " OR ".join(conditions)
    return condition


def patient_list(product_name: str, location_uuids: List[str]) -> List[Dict]:
    query = composite_query_builder(
        "patient",
        Patient,
        "MATCH (patient:Patient)\n"
        "WHERE NOT (patient)-[:CHILD_OF]->()\n"
        "AND FILTER(loc IN patient.locations WHERE loc IN {location_uuids})\n"
        "WITH patient\n"
        "    MATCH (patient)-[:ACTIVE_ON_PRODUCT]->(dh_products:DraysonHealthProduct)\n"
        "    WHERE dh_products.product_name={product_name} \n"
        "WITH patient, collect(dh_products) as dh_products\n",
        ignore_nodes={
            "Clinician",
            "DraysonHealthProduct",
            "DoseHistory",
            "Dose",
            "DoseChange",
            "History",
            "Location",
            "NonMedicationAction",
            "Note",
            "PersonalAddress",
            "Pregnancy",
            "ObservableEntity",
            "TermsAgreement",
            "Visit",
        },
        special_relations={"CHILD_OF": None},
        extra_fields=["dh_products"],
    )
    results, meta = db.cypher_query(
        query,
        {
            "location_uuids": location_uuids,
            "product_name": product_name,
        },
    )
    patients: List[Dict] = [
        Patient.convert_response_to_dict(patient, method="to_dict_no_relations")
        for (patient,) in results
    ]
    return [PatientDiabetesResponse().load(p, unknown=EXCLUDE) for p in patients]


@db.write_transaction
def record_first_medication(
    patient_id: str, first_medication_taken: str, first_medication_taken_recorded: str
) -> None:
    """
    :param first_medication_taken: Relative time of when medication first taken e.g. 5 days ago
    :param first_medication_taken_recorded: The date which first_medication_taken is relative to e.g. 2019-12-31
    :return: None
    """
    patient: Patient = get_node_or_404(Patient, uuid=patient_id)
    latest_pregnancy: Optional[Pregnancy] = (
        patient.record.single().pregnancies.order_by("-created_").first_or_none()
    )
    if latest_pregnancy is None:
        raise ValueError("expected pregnancy data not found")
    latest_pregnancy.first_medication_taken = first_medication_taken
    latest_pregnancy.first_medication_taken_recorded = first_medication_taken_recorded
    latest_pregnancy.save()


def get_bookmarks_for_locations(location_uuids: Set[str]) -> Dict[str, List[str]]:
    """Returns a map of location uuid -> [patient_uuid, ...]"""
    query = """
    MATCH (p:Patient)
    WHERE p.bookmarked_at_locations IS NOT NULL AND SIZE(p.bookmarked_at_locations) > 0
    RETURN p.uuid, p.bookmarked_at_locations
    """
    results, meta = db.cypher_query(query)
    location_patient_map: Dict[str, List[str]] = defaultdict(list)
    for patient_uuid, bookmarked_loc_uuids in results:
        for loc_uuid in bookmarked_loc_uuids:
            if loc_uuid in location_uuids:
                location_patient_map[loc_uuid].append(patient_uuid)
    return location_patient_map


@db.write_transaction
def set_patient_monitored_by_clinician(
    patient_id: str, product_id: str, monitored_by_clinician: bool
) -> Dict:
    patient: Patient = get_node_or_404(Patient, uuid=patient_id)
    product: Optional[DraysonHealthProduct] = next(
        (x for x in patient.dh_products if x.uuid == product_id), None
    )
    if product is None or product.closed_date:
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

    return patient.to_dict()


def get_patient_uuids(product_name: str) -> List[str]:
    query: str = """
        MATCH 
            (p:Patient)-[:ACTIVE_ON_PRODUCT]-(d:DraysonHealthProduct)
        WHERE 
            NOT (p)-[:CHILD_OF]->() 
            AND NOT p:Baby 
            AND d.product_name = {product_name}
        RETURN p.uuid
    """
    results, meta = db.cypher_query(
        query,
        {
            "product_name": product_name,
        },
    )
    return [uuid[0] for uuid in results]
