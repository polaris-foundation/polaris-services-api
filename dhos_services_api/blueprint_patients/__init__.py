from typing import Dict, List, Optional

import flask
from flask import Blueprint, Response, jsonify, make_response, request
from flask_batteries_included.helpers import schema
from flask_batteries_included.helpers.routes import deprecated_route
from flask_batteries_included.helpers.security import protected_route
from flask_batteries_included.helpers.security.endpoint_security import (
    and_,
    argument_present,
    key_present,
    match_keys,
    or_,
    scopes_present,
)
from she_logging import logger

from dhos_services_api.blueprint_patients import (
    aggregation_controller,
    alerting_controller,
    mixed_controller,
    patient_controller,
    pmcf_controller,
    search_controller,
)
from dhos_services_api.helpers.security import (
    current_user_is_specified_patient_or_any_gdm_clinician,
)
from dhos_services_api.models.patient import Patient

patients_blueprint = Blueprint("patients_api", __name__)


@patients_blueprint.route("/dhos/v1/patient_list", methods=["POST"])
@protected_route(
    or_(
        and_(
            scopes_present(required_scopes="read:send_patient"),
            argument_present("product_name", "SEND"),
        ),
        and_(
            argument_present("product_name", "GDM"),
            or_(
                scopes_present(required_scopes="read:gdm_patient_all"),
                scopes_present(required_scopes="read:gdm_patient"),
            ),
        ),
        scopes_present(required_scopes="read:patient_all"),
    )
)
def retrieve_patients_by_uuids(
    product_name: str, patient_uuids: List[str], compact: bool = False
) -> flask.Response:
    """
    ---
    post:
      summary: Retrieve patients by UUIDs
      description: Retrieve a list of patients using the UUIDs provided in the request body.
      tags: [patient]
      parameters:
        - name: product_name
          in: query
          required: true
          description: Product with which patients should be associated
          schema:
            type: string
            example: GDM
        - name: compact
          in: query
          required: false
          description: Whether to return patient in compact form
          schema:
            type: boolean
            default: false
      requestBody:
        description: List of patient UUIDs
        required: true
        content:
          application/json:
            schema:
              x-body-name: patient_uuids
              type: array
              items:
                type: string
                example: ff9279e6-7a70-4fbb-b532-eb8a602751ae
      responses:
        '200':
          description: List of patients
          content:
            application/json:
              schema:
                type: array
                items: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    return jsonify(
        patient_controller.retrieve_patients_by_uuids(
            patient_uuids, product_name, compact
        )
    )


@patients_blueprint.route("/dhos/v1/patient_list", methods=["GET"])
@protected_route(
    scopes_present(required_scopes="read:patient_all"),
)
def retrieve_patient_list(product_name: str, locs: str) -> flask.Response:
    """
    ---
    get:
      summary: Retrieve patient list
      description: Retrieve a list of patients by location and product
      tags: [patient]
      parameters:
        - name: product_name
          in: query
          required: true
          description: Product with which patients should be associated
          schema:
            type: string
            example: GDM
        - name: locs
          in: query
          required: false
          description: Filter patients to those associated with this comma-separated list of location UUIDs.
          schema:
            type: string
            example: 0480256a-4dd1-499b-b194-ec754ecfddf3
      responses:
        '200':
          description: List of patients
          content:
            application/json:
              schema:
                type: array
                items: PatientDiabetesResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    location_uuids: List[str] = locs.split(",") if locs is not None else []

    return jsonify(
        patient_controller.patient_list(
            product_name=product_name, location_uuids=location_uuids
        )
    )


@patients_blueprint.route("/dhos/v1/patient/<patient_id>", methods=["GET"])
@protected_route(
    or_(
        scopes_present(required_scopes="read:patient_all"),
        scopes_present(required_scopes="read:send_patient"),
        scopes_present(required_scopes="read:gdm_patient_all"),
        and_(
            scopes_present(required_scopes="read:gdm_patient"),
            current_user_is_specified_patient_or_any_gdm_clinician,
        ),
    )
)
def get_patient(
    patient_id: str, type: Optional[str] = None, product_name: Optional[str] = None
) -> flask.Response:
    """
    ---
    get:
      summary: Get patient by UUID
      description: Get patient with the provided UUID
      tags: [patient]
      parameters:
        - name: patient_id
          in: path
          required: true
          description: Patient UUID
          schema:
            type: string
            example: ff9279e6-7a70-4fbb-b532-eb8a602751ae
        - name: type
          in: query
          required: false
          description: Product name (deprecated - please use product_name instead)
          schema:
            type: string
            example: GDM
        - name: product_name
          in: query
          required: false
          description: Product name
          schema:
            type: string
            example: GDM
      responses:
        '200':
          description: Patient details
          content:
            application/json:
              schema: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if request.is_json:
        raise ValueError("Request should not contain a json body")

    # TODO: remove deprecated query parameter type once PLAT-100 is done.
    product_name = product_name or type

    response: Dict = patient_controller.get_patient(
        patient_uuid=patient_id, product_name=product_name
    )
    return jsonify(response)


@patients_blueprint.route("/dhos/v1/patient", methods=["GET"])
@protected_route(
    or_(
        and_(
            argument_present("product_name", "SEND"),
            scopes_present("read:send_patient"),
        ),
        and_(
            argument_present("product_name", "GDM"),
            or_(
                scopes_present(required_scopes="write:gdm_patient_all"),
                scopes_present(required_scopes="write:gdm_patient"),
            ),
        ),
    )
)
def get_patients_by_product_and_identifier(
    product_name: str, identifier_type: str, identifier_value: str
) -> flask.Response:
    """
    ---
    get:
      summary: Get patients by identifier
      description: Get patients by the identifier provided in the query parameters.
      tags: [patient]
      parameters:
        - name: product_name
          in: query
          required: true
          description: Product name
          schema:
            type: string
            example: SEND
        - name: identifier_type
          in: query
          required: true
          description: Type of identifier
          schema:
            type: string
            enum: ["NHS_NUMBER", "nhs_number", "MRN", "mrn", "HOSPITAL_NUMBER", "hospital_number"]
            example: nhs_number
        - name: identifier_value
          in: query
          required: true
          description: Value of identifier
          schema:
            type: string
            example: "1234567890"
      responses:
        '200':
          description: List of patients
          content:
            application/json:
              schema:
                type: array
                items: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    identifier_type = identifier_type.upper()
    return jsonify(
        mixed_controller.get_patients_by_product_and_identifer(
            product_name, identifier_type, identifier_value
        )
    )


@patients_blueprint.route("/dhos/v1/patient-abbreviated/<patient_id>", methods=["GET"])
@protected_route(
    and_(
        scopes_present(required_scopes="read:gdm_patient_abbreviated"),
        match_keys(patient_id="patient_id"),
    )
)
@deprecated_route(superseded_by="GET /dhos/v1/patient/<patient_uuid>")
def get_patient_abbreviated(patient_id: str) -> flask.Response:
    """
    ---
    get:
      summary: Get abbreviated patient by UUID
      description: >-
        Get abbreviated details for the patient with the provided UUID. This endpoint was
        designed to be used by mobile apps.
        Note: this endpoint is deprecated, please use GET /dhos/v1/patient/<patient_id>
      tags: [patient]
      parameters:
        - name: patient_id
          in: path
          required: true
          description: Patient UUID
          schema:
            type: string
            example: ff9279e6-7a70-4fbb-b532-eb8a602751ae
      responses:
        '200':
          description: Patient details
          content:
            application/json:
              schema: AbbreviatedPatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    # TODO: we can remove this endpoint once GDM-3440 is complete.
    if request.is_json:
        raise ValueError("Request should not contain a json body")

    response = patient_controller.get_patient_abbreviated(patient_id)
    return jsonify(response)


@patients_blueprint.route("/dhos/v1/patient/<patient_id>", methods=["PATCH"])
@protected_route(
    or_(
        scopes_present(required_scopes="write:send_patient_all"),
        scopes_present(required_scopes="write:gdm_patient_all"),
        scopes_present(required_scopes="write:gdm_patient"),
    )
)
def update_patient(patient_id: str, update_details: Dict) -> flask.Response:
    """
    ---
    patch:
      summary: Update patient
      description: >-
        Update the patient with the provided UUID using the details in the request body.
        Note: this endpoint uses recursive patch and can be used to update nested objects.
      tags: [patient]
      parameters:
        - name: patient_id
          in: path
          required: true
          description: Patient UUID
          schema:
            type: string
            example: ff9279e6-7a70-4fbb-b532-eb8a602751ae
      requestBody:
        description: Patient details to update
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PatientUpdateRequest'
              x-body-name: update_details
      responses:
        '200':
          description: Updated patient
          content:
            application/json:
              schema: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    response = patient_controller.update_patient(patient_id, update_details)
    return jsonify(response)


@patients_blueprint.route("/dhos/v1/patient/<patient_id>/delete", methods=["PATCH"])
@protected_route(
    or_(
        scopes_present(required_scopes="write:gdm_patient_all"),
        scopes_present(required_scopes="write:gdm_patient"),
    )
)
def remove_from_patient(patient_id: str, fields_to_remove: Dict) -> flask.Response:
    """
    ---
    patch:
      summary: Remove details from patient
      description: >-
        Remove the details in the request body from the patient with the provided UUID.
        Note that this endpoint does not remove the patient itself.
      tags: [patient]
      parameters:
        - name: patient_id
          in: path
          required: true
          description: Patient UUID
          schema:
            type: string
            example: ff9279e6-7a70-4fbb-b532-eb8a602751ae
      requestBody:
        description: >-
          Details to remove from patient:
          This endpoint can only delete individual items from a collection such as a list or tuple.
          It will ignore a single key-value pair e.g. { "phone_number" : "01234999999" }.
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PatientUpdateRequest'
              x-body-name: fields_to_remove
      responses:
        '200':
          description: Updated patient
          content:
            application/json:
              schema: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    response: Dict = patient_controller.remove_from_patient(
        patient_uuid=patient_id, fields_to_remove=fields_to_remove
    )
    return jsonify(response)


@patients_blueprint.route("/dhos/v1/patient", methods=["POST"])
@protected_route(
    or_(
        scopes_present(required_scopes="write:patient_all"),
        and_(
            scopes_present(required_scopes="write:send_patient"),
            or_(
                argument_present("product_name", "SEND"),
                argument_present("type", "SEND"),
            ),
        ),
        and_(
            or_(
                argument_present("product_name", "GDM"), argument_present("type", "GDM")
            ),
            or_(
                scopes_present(required_scopes="write:gdm_patient_all"),
                scopes_present(required_scopes="write:gdm_patient"),
            ),
        ),
    )
)
def create_patient(
    patient_details: Dict,
    product_name: Optional[str] = None,
    type: Optional[str] = None,
) -> flask.Response:
    """
    ---
    post:
      summary: Create patient
      description: Create a patient using the details provided in the request body.
      tags: [patient]
      parameters:
        - name: type
          in: query
          required: false
          description: Product name (deprecated - please use product_name instead)
          schema:
            type: string
            example: GDM
        - name: product_name
          in: query
          required: false
          description: Product name
          schema:
            type: string
            example: GDM
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PatientUpdateRequest'
              x-body-name: patient_details
      responses:
        '200':
          description: New patient
          content:
            application/json:
              schema: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    # TODO: remove deprecated query parameter type once PLAT-100 is done.
    product_name = product_name or type
    if product_name is None:
        raise ValueError("Missing required query parameter 'product_name'")

    response: Dict = patient_controller.create_patient(
        product_name=product_name, patient_details=patient_details
    )
    return jsonify(response)


@patients_blueprint.route(
    "/dhos/v1/patient/<patient_id>/terms_agreement", methods=["POST"]
)
@protected_route(
    and_(
        scopes_present(required_scopes="write:gdm_terms_agreement"),
        or_(match_keys(patient_id="patient_id"), key_present("system_id")),
    )
)
@deprecated_route(superseded_by="POST /dhos/v2/patient/<patient_id>/terms_agreement")
def create_patient_tos(patient_id: str, terms_details: Dict) -> flask.Response:
    """
    ---
    post:
      summary: Create patient terms of service agreement
      description: Create a new patient terms of service agreement using the details provided in the request body.
      tags: [patient]
      parameters:
        - name: patient_id
          in: path
          required: true
          description: Patient UUID
          schema:
            type: string
            example: ff9279e6-7a70-4fbb-b532-eb8a602751ae
      requestBody:
        description: Terms of service agreement details
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PatientTermsRequest'
              x-body-name: terms_details
      responses:
        '200':
          description: New terms of service agreement
          content:
            application/json:
              schema: PatientTermsResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    # TODO: remove endpoint once there are no older applications using this
    response: Dict = patient_controller.create_patient_tos_v1(patient_id, terms_details)
    return jsonify(response)


@patients_blueprint.route(
    "/dhos/v2/patient/<patient_id>/terms_agreement", methods=["POST"]
)
@protected_route(
    and_(
        scopes_present(required_scopes="write:gdm_terms_agreement"),
        or_(match_keys(patient_id="patient_id"), key_present("system_id")),
    )
)
def create_patient_tos_v2(patient_id: str, terms_details: Dict) -> flask.Response:
    """
    ---
    post:
      summary: Create patient terms of service agreement
      description: Create a new patient terms of service agreement using the details provided in the request body.
      tags: [patient]
      parameters:
        - name: patient_id
          in: path
          required: true
          description: Patient UUID
          schema:
            type: string
            example: ff9279e6-7a70-4fbb-b532-eb8a602751ae
      requestBody:
        description: Terms of service agreement details
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PatientTermsRequestV2'
              x-body-name: terms_details
      responses:
        '200':
          description: New terms of service agreement
          content:
            application/json:
              schema: PatientTermsResponseV2
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    response: Dict = patient_controller.create_patient_tos_v2(patient_id, terms_details)
    return jsonify(response)


@patients_blueprint.route(
    "/dhos/v1/patient/<patient_id>/product/<product_id>/close", methods=["POST"]
)
@protected_route(
    or_(
        scopes_present(required_scopes="write:gdm_patient_all"),
        scopes_present(required_scopes="write:gdm_patient"),
    )
)
def close_patient(
    patient_id: str, product_id: str, patient_details: Dict
) -> flask.Response:
    """
    ---
    post:
      summary: Close (archive) patient
      description: >-
        Close (archive) a product and patient with the provided UUIDs using the details
        provided in the request body. Note: you can only archive a GDM product.
      tags: [patient]
      parameters:
        - name: patient_id
          in: path
          required: true
          description: Patient UUID
          schema:
            type: string
            example: ff9279e6-7a70-4fbb-b532-eb8a602751ae
        - name: product_id
          in: path
          required: true
          description: Product UUID
          schema:
            type: string
            example: 95b90947-fb5d-4445-bfb1-e2b1078d5057
      requestBody:
        description: Patient details
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ClosePatientRequest'
              x-body-name: patient_details
      responses:
        '200':
          description: Closed patient
          content:
            application/json:
              schema: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    response: Dict = patient_controller.close_patient(
        patient_id, product_id, patient_details
    )
    return jsonify(response)


@patients_blueprint.route("/dhos/v1/patient/open_gdm_patients", methods=["POST"])
@protected_route(scopes_present(required_scopes="write:gdm_alert"))
def retrieve_open_gdm_patients() -> flask.Response:
    """
    ---
    post:
      summary: Retrieve activity alerting information
      description: >-
        Retrieve activity alerting information for open GDM patients. Responds with details of all open
        GDM patients that had their GDM product opened more than 7 days ago.
      tags: [patient]
      responses:
        '200':
          description: Closed patient
          content:
            application/json:
              schema:
                type: array
                items: ActivityAlertingPatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    patients = alerting_controller.retrieve_open_gdm_patients()
    return jsonify({"patients": patients})


@deprecated_route(superseded_by="GET /dhos/v2/location/<location_id>/patient")
@patients_blueprint.route(
    "/dhos/v1/location/<location_id>/gdm_patient", methods=["GET"]
)
@protected_route(
    or_(
        scopes_present(required_scopes="read:gdm_patient_all"),
        scopes_present(required_scopes="read:gdm_patient"),
    )
)
def get_gdm_patients_by_location(
    location_id: str,
    location_active: Optional[bool] = None,
    current: Optional[bool] = None,
    include_all: Optional[bool] = None,
    diagnosis: Optional[str] = None,
) -> flask.Response:
    """
    ---
    get:
      summary: Get GDM patients by location
      description: Get GDM patients associated with the location UUID provided in the request.
      tags: [patient]
      parameters:
        - name: location_id
          in: path
          required: true
          description: Location UUID
          schema:
            type: string
            example: 0480256a-4dd1-499b-b194-ec754ecfddf3
        - name: location_active
          in: query
          required: false
          deprecated: true
          description: >-
            Filter patients to those associated with locations that are active (true) or inactive (false).
            If not provided, no filter is applied.
          schema:
            type: boolean
            example: true
        - name: current
          in: query
          required: false
          description: Filter patients to active (true) or inactive (false). If not provided, no filter is applied.
          schema:
            type: boolean
            example: true
        - name: include_all
          in: query
          required: false
          description: Whether to include patients marked as having been created in error
          schema:
            type: boolean
            example: true
        - name: diagnosis
          in: query
          required: false
          description: Filter patients to those with a diagnosis matching this SNOMED code.
          schema:
            type: string
            example: '11687002'
      responses:
        '200':
          description: List of patients
          content:
            application/json:
              schema:
                type: array
                items: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if request.is_json:
        raise ValueError("Request should not contain a json body")

    if location_active is not None:
        logger.warning("location_active parameter is no longer supported")

    response: List[Dict] = mixed_controller.get_gdm_patients_by_location(
        location_uuid=location_id,
        current=current,
        diagnosis=diagnosis,
        include_all=include_all,
    )

    return jsonify(response)


@patients_blueprint.route("/dhos/v2/location/<location_id>/patient", methods=["GET"])
@protected_route(
    or_(
        scopes_present(required_scopes="read:gdm_patient_all"),
        scopes_present(required_scopes="read:gdm_patient"),
    )
)
def get_aggregated_patients(
    location_id: str, product_name: str, active: Optional[bool] = None
) -> flask.Response:
    """
    ---
    get:
      summary: Get patients by location
      description: Get patients associated with the location with the provided UUID.
      tags: [patient]
      parameters:
        - name: location_id
          in: path
          required: true
          description: Location UUID
          schema:
            type: string
            example: 0480256a-4dd1-499b-b194-ec754ecfddf3
        - name: product_name
          in: query
          required: true
          description: Product name
          schema:
            type: string
            example: GDM
        - name: active
          in: query
          required: false
          description: Filter patients to active (true) or inactive (false). If not provided, no filter is applied.
          schema:
            type: boolean
            example: true
      responses:
        '200':
          description: Patient details
          content:
            application/json:
              schema:
                type: array
                items: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if request.is_json:
        raise ValueError("Request should not contain a json body")

    response: List[Dict] = aggregation_controller.get_aggregated_patients(
        location_uuid=location_id, product_name=product_name.upper(), active=active
    )
    return jsonify(response)


@patients_blueprint.route(
    "/dhos/v1/location/<location_id>/patient/<patient_id>/bookmark", methods=["POST"]
)
@protected_route(
    or_(
        scopes_present(required_scopes="write:gdm_patient_all"),
        scopes_present(required_scopes="write:gdm_patient"),
    )
)
def bookmark_patient(location_id: str, patient_id: str) -> flask.Response:
    """
    ---
    post:
      summary: Create a location-patient bookmark
      description: Create a bookmark between the location and patient with the provided UUIDs.
      tags: [patient]
      parameters:
        - name: location_id
          in: path
          required: true
          description: Location UUID
          schema:
            type: string
            example: 99f86b12-0112-42be-a0bb-fbe8e65c6b2f
        - name: patient_id
          in: path
          required: true
          description: Patient UUID
          schema:
            type: string
            example: ff9279e6-7a70-4fbb-b532-eb8a602751ae
      responses:
        '200':
          description: Updated patient
          content:
            application/json:
              schema: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if request.is_json:
        raise ValueError("Request should not contain a json body")

    response: Dict = mixed_controller.bookmark_patient(
        location_id=location_id, patient_id=patient_id, is_bookmarked=True
    )
    return jsonify(response)


@patients_blueprint.route(
    "/dhos/v1/location/<location_id>/patient/<patient_id>/bookmark", methods=["DELETE"]
)
@protected_route(
    or_(
        scopes_present(required_scopes="write:gdm_patient_all"),
        scopes_present(required_scopes="write:gdm_patient"),
    )
)
def remove_bookmark(location_id: str, patient_id: str) -> flask.Response:
    """
    ---
    delete:
      summary: Delete a location-patient bookmark
      description: Delete a bookmark between the location and patient with the provided UUIDs.
      tags: [patient]
      parameters:
        - name: location_id
          in: path
          required: true
          description: Location UUID
          schema:
            type: string
            example: 99f86b12-0112-42be-a0bb-fbe8e65c6b2f
        - name: patient_id
          in: path
          required: true
          description: Patient UUID
          schema:
            type: string
            example: ff9279e6-7a70-4fbb-b532-eb8a602751ae
      responses:
        '200':
          description: Updated patient
          content:
            application/json:
              schema: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if request.is_json:
        raise ValueError("Request should not contain a json body")

    response: Dict = mixed_controller.bookmark_patient(
        location_id=location_id, patient_id=patient_id, is_bookmarked=False
    )
    return jsonify(response)


@patients_blueprint.route("/dhos/v1/patient/validate/<nhs_number>", methods=["POST"])
@protected_route(
    or_(
        scopes_present(required_scopes="write:gdm_patient_all"),
        scopes_present(required_scopes="write:gdm_patient"),
    )
)
def validate_patient_nhs_number(
    nhs_number: str, type: Optional[str] = None, product_name: Optional[str] = None
) -> flask.Response:
    """
    ---
    post:
      summary: Validate NHS number
      description: Validate an NHS number and ensure it is not already known to the platform.
      tags: [patient]
      parameters:
        - name: nhs_number
          in: path
          required: true
          description: NHS number to validate
          schema:
            type: string
            example: '1111111111'
        - name: type
          in: query
          required: false
          description: Product name (deprecated - please use product_name instead)
          schema:
            type: string
            example: GDM
        - name: product_name
          in: query
          required: false
          description: Product name
          schema:
            type: string
            example: GDM
      responses:
        '200':
          description: NHS number is valid and unique
        '400':
          description: NHS number is invalid
        '409':
          description: NHS number is known to the system
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if request.is_json:
        raise ValueError("Request should not contain a json body")

    # TODO: remove deprecated query parameter type once PLAT-100 is done.
    product_name = product_name or type
    if product_name is None:
        raise ValueError("Missing required query parameter 'product_name'")

    patient_controller.ensure_valid_nhs_number(nhs_number=nhs_number)
    patient_controller.ensure_unique_nhs_number(
        nhs_number=nhs_number, product_name=product_name
    )
    return make_response("", 200)


@patients_blueprint.route("/dhos/v1/patient/validate", methods=["POST"])
@protected_route(
    or_(
        scopes_present(required_scopes="write:gdm_patient_all"),
        scopes_present(required_scopes="write:gdm_patient"),
    )
)
def validate_patient_information(
    patient_identifiers: Dict,
    type: Optional[str] = None,
    product_name: Optional[str] = None,
) -> flask.Response:
    """
    ---
    post:
      summary: Validate patient information
      description: >-
        Validate patient information, ensuring a patient isn't already known to the platform. Checks a
        patient's hospital number (MRN) isn't already known, and checks the combination of (first name,
        last name, date of birth) isn't already known.
      tags: [patient]
      parameters:
        - name: type
          in: query
          required: false
          description: Product name (deprecated - please use product_name instead)
          schema:
            type: string
            example: GDM
        - name: product_name
          in: query
          required: false
          description: Product name
          schema:
            type: string
            example: GDM
      requestBody:
        description: Patient details
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ValidatePatientRequest'
              x-body-name: patient_identifiers
      responses:
        '200':
          description: Patient is unique
        '409':
          description: Patient is known to the system
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    # TODO: remove deprecated query parameter type once PLAT-100 is done.
    product_name = product_name or type
    if product_name is None:
        raise ValueError("Missing required query parameter 'product_name'")

    schema.post(**Patient.patient_validate_schema(), **patient_identifiers)
    patient_controller.ensure_unique_patient_information(
        patient_details=patient_identifiers, product_name=product_name
    )
    return make_response("", 200)


@patients_blueprint.route("/dhos/v1/patient/record/<record_id>", methods=["GET"])
@protected_route(scopes_present(required_scopes="read:send_patient"))
def get_patient_by_record(record_id: str, compact: bool = False) -> flask.Response:
    """
    ---
    get:
      summary: Get patient by record UUID
      description: Get patient with the provided record UUID
      tags: [patient]
      parameters:
        - name: record_id
          in: path
          required: true
          description: Patient record UUID
          schema:
            type: string
            example: 29297b3c-1e51-4526-9d70-9f8b2b0c879f
        - name: compact
          in: query
          required: false
          description: Whether to return patient in compact form
          schema:
            type: boolean
            default: false
      responses:
        '200':
          description: Patient details
          content:
            application/json:
              schema: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    return jsonify(patient_controller.get_patient_by_record_uuid(record_id, compact))


@patients_blueprint.route("/dhos/v1/patient/search", methods=["GET"])
@protected_route(
    or_(
        scopes_present(required_scopes="read:gdm_patient_all"),
        scopes_present(required_scopes="read:gdm_patient"),
        scopes_present(required_scopes="read:patient_all"),
    )
)
def search_patients(
    product_name: str,
    active: bool = True,
    q: Optional[str] = None,
    locs: Optional[str] = None,
    modified_since: Optional[str] = None,
    expanded: bool = False,
) -> flask.Response:
    """
    ---
    get:
      summary: Search for patients
      description: >-
        Search for patients by query and filters. The search query is optional, and will be used to
        check patient name (including partial matches), full NHS number, and full hospital number (MRN).
        Note: this search is limited to non-SEND patients.
      tags: [patient]
      parameters:
        - name: q
          in: query
          required: false
          description: Search query
          schema:
            type: string
            example: Jones
        - name: product_name
          in: query
          required: true
          description: Product name
          schema:
            type: string
            example: GDM
        - name: active
          in: query
          required: false
          description: Filter patients to active (true) or inactive (false).
          schema:
            type: boolean
            default: true
        - name: locs
          in: query
          required: false
          description: Filter patients to those associated with this comma-separated list of location UUIDs.
          schema:
            type: string
            example: 0480256a-4dd1-499b-b194-ec754ecfddf3
        - name: modified_since
          in: query
          required: false
          description: Filter patients to those modified since this datetime. Note, if timezone is used, a `+` symbol should be passed as an URL-encoded character, i.e. `%2B`
          schema:
            type: string
            format: date-time
            example: 2000-01-01T01:01:01.123%2B01:00
        - name: expanded
          in: query
          required: false
          description: Return a fully expanded model.
          schema:
            type: boolean
            default: false
      responses:
        '200':
          description: List of patients
          content:
            application/json:
              schema:
                type: array
                items: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    location_uuids: List[str] = locs.split(",") if locs is not None else []
    return jsonify(
        patient_controller.search_patients(
            search_text=q,
            locations=location_uuids,
            product_name=product_name,
            active=active,
            modified_since=modified_since,
            expanded=expanded,
        )
    )


@patients_blueprint.route(
    "/dhos/v1/patient/<patient_id>/first_medication", methods=["POST"]
)
@protected_route(
    or_(
        and_(
            scopes_present(required_scopes="write:gdm_bg_reading"),
            match_keys(patient_id="patient_id"),
        ),
        scopes_present(required_scopes="write:gdm_patient_all"),
    )
)
def record_first_medication(patient_id: str, first_medication: Dict) -> flask.Response:
    """
    ---
    post:
      summary: Record patient's first medication
      description: >-
        Record a patient has taken medication for the first time.
        Note: only works for GDM patients.
      tags: [patient]
      parameters:
        - name: patient_id
          in: path
          required: true
          description: Patient UUID
          schema:
            type: string
            example: ff9279e6-7a70-4fbb-b532-eb8a602751ae
      requestBody:
        description: First medication details
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/FirstMedicationRequest'
              x-body-name: first_medication
      responses:
        '204':
          description: First medication recorded
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    patient_controller.record_first_medication(
        patient_id=patient_id,
        first_medication_taken=first_medication["first_medication_taken"],
        first_medication_taken_recorded=first_medication[
            "first_medication_taken_recorded"
        ],
    )
    return make_response("", 204)


@patients_blueprint.route("/dhos/v2/patient/search", methods=["POST"])
@protected_route(scopes_present(required_scopes="read:send_encounter"))
def search_patients_by_uuids_v2(
    patient_ids: List[str], q: Optional[str] = None
) -> Response:
    """---
    post:
      summary: Get patient search info matching specified patient UUIDs
      description: >-
        Retrieve patients using the patients UUIDs provided in the
        request body, and the filters provided in the request parameters.

        (For GDM patient search use the v1 endpoint instead)
      tags: [search]
      parameters:
        - name: q
          in: query
          required: false
          description: The search term
          schema:
            type: string
            example: 'jones'
      requestBody:
        description: List of patient UUIDs
        required: true
        content:
          application/json:
            schema:
              x-body-name: patient_ids
              type: array
              items:
                type: string
                example: '2126393f-c86b-4bf2-9f68-42bb03a7b68a'
      responses:
        '200':
          description: Search results
          content:
            application/json:
              schema: SearchResultsResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    return jsonify(
        search_controller.search_patients_by_uuids(patient_uuids=patient_ids, q=q)
    )


@patients_blueprint.route("/dhos/v2/patient/search", methods=["GET"])
@protected_route(scopes_present(required_scopes="read:send_encounter"))
def search_patients_by_term(q: str) -> Response:
    """---
    get:
      summary: Search for patients by search term
      description: >-
        Search for patient by search term. Allows searching by MRN, NHS number,
        first name or last name
        (For GDM patient search use the v1 endpoint instead)
      tags: [search]
      parameters:
        - name: q
          in: query
          required: true
          description: The search term
          schema:
            type: string
            example: Jones
      responses:
        '200':
          description: Search results
          content:
            application/json:
              schema: SearchResultsResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    return jsonify(search_controller.search_patients_by_term(q=q))


@patients_blueprint.route(
    "/dhos/v1/patient/<patient_id>/product/<product_id>/stop_monitoring",
    methods=["POST"],
)
@protected_route(
    or_(
        scopes_present(required_scopes="write:gdm_patient_all"),
        scopes_present(required_scopes="write:patient_all"),
        scopes_present(required_scopes="write:gdm_patient"),
        scopes_present(required_scopes="write:patient"),
    )
)
def stop_monitoring_patient(patient_id: str, product_id: str) -> flask.Response:
    """
    ---
    post:
      summary: Stop monitoring patient
      description: |-
        Stop monitoring a patient within a product with the provided UUIDs by
            setting `Product.monitored_by_clinician` flag to `False`.
        DBm: marking a product as not monitored prevents user from sending
            readings.
        GDm: Has no effect.
        Send: Has no effect.
      tags: [patient]
      parameters:
        - name: patient_id
          in: path
          required: true
          description: Patient UUID
          schema:
            type: string
            example: ff9279e6-7a70-4fbb-b532-eb8a602751ae
        - name: product_id
          in: path
          required: true
          description: Product UUID
          schema:
            type: string
            example: 95b90947-fb5d-4445-bfb1-e2b1078d5057
      responses:
        '200':
          description: Patient
          content:
            application/json:
              schema: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    response: Dict = patient_controller.set_patient_monitored_by_clinician(
        patient_id, product_id, monitored_by_clinician=False
    )
    return jsonify(response)


@patients_blueprint.route(
    "/dhos/v1/patient/<patient_id>/product/<product_id>/start_monitoring",
    methods=["POST"],
)
@protected_route(
    or_(
        scopes_present(required_scopes="write:gdm_patient_all"),
        scopes_present(required_scopes="write:patient_all"),
        scopes_present(required_scopes="write:gdm_patient"),
        scopes_present(required_scopes="write:patient"),
    )
)
def start_monitoring_patient(patient_id: str, product_id: str) -> flask.Response:
    """
    ---
    post:
      summary: Start monitoring patient
      description: |-
        Start monitoring a patient within a product with the provided UUIDs by
            setting `Product.monitored_by_clinician` flag to `True`.
        DBm: marking a product as monitored allows user to send readings.
        GDm: Has no effect.
        Send: Has no effect.
      tags: [patient]
      parameters:
        - name: patient_id
          in: path
          required: true
          description: Patient UUID
          schema:
            type: string
            example: ff9279e6-7a70-4fbb-b532-eb8a602751ae
        - name: product_id
          in: path
          required: true
          description: Product UUID
          schema:
            type: string
            example: 95b90947-fb5d-4445-bfb1-e2b1078d5057
      responses:
        '200':
          description: Patient
          content:
            application/json:
              schema: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    response: Dict = patient_controller.set_patient_monitored_by_clinician(
        patient_id, product_id, monitored_by_clinician=True
    )
    return jsonify(response)


@patients_blueprint.route("/dhos/v1/patient_uuids", methods=["GET"])
@protected_route(
    or_(
        scopes_present(required_scopes="read:gdm_patient_all"),
        scopes_present(required_scopes="read:patient_all"),
    )
)
def patient_uuids(product_name: str) -> flask.Response:
    """
    ---
    get:
      summary: Get list of patient UUIDs
      tags: [patient]
      parameters:
        - name: product_name
          in: query
          required: true
          description: Product name
          schema:
            type: string
            example: GDM
      responses:
        '200':
          description: List of UUIDs
          content:
            application/json:
              schema:
                type: array
                items:
                  type: string
                  example: ff9279e6-7a70-4fbb-b532-eb8a602751ae
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    response: List[str] = patient_controller.get_patient_uuids(product_name)
    return jsonify(response)


@patients_blueprint.route("/dhos/v1/neo4j_patient_list", methods=["POST"])
@protected_route(scopes_present(required_scopes="read:patient_all"))
@deprecated_route()
def retrieve_patients_by_uuids_neo() -> Response:
    """
    ---
    post:
      summary: Retrieve patients by UUIDs (neo4j - do not use in production)
      description: Retrieve a list of patients using the UUIDs provided in the request body.
      tags: [patient]
      parameters:
        - name: product_name
          in: query
          required: true
          description: Product with which patients should be associated
          schema:
            type: string
            example: GDM
        - name: compact
          in: query
          required: false
          description: Whether to return patient in compact form
          schema:
            type: boolean
            default: false
      requestBody:
        description: List of patient UUIDs
        required: true
        content:
          application/json:
            schema:
              x-body-name: patient_uuids
              type: array
              items:
                type: string
                example: ff9279e6-7a70-4fbb-b532-eb8a602751ae
      responses:
        '200':
          description: List of patients
          content:
            application/json:
              schema:
                type: array
                items: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    product_name: str = request.args["product_name"]
    patient_uuids: List[str] = request.get_json() or []
    compact: bool = bool(request.args.get("compact", False))
    from dhos_services_api.blueprint_patients import patient_controller_neo

    return jsonify(
        patient_controller_neo.retrieve_patients_by_uuids(
            patient_uuids, product_name, compact
        )
    )


@patients_blueprint.route("/dhos/v1/neo4j_patient", methods=["POST"])
@protected_route(
    or_(
        scopes_present(required_scopes="write:patient_all"),
        and_(
            scopes_present(required_scopes="write:send_patient"),
            or_(
                argument_present("product_name", "SEND"),
                argument_present("type", "SEND"),
            ),
        ),
        and_(
            or_(
                argument_present("product_name", "GDM"), argument_present("type", "GDM")
            ),
            or_(
                scopes_present(required_scopes="write:gdm_patient_all"),
                scopes_present(required_scopes="write:gdm_patient"),
            ),
        ),
    )
)
@deprecated_route()
def create_patient_neo() -> Response:
    """
    ---
    post:
      summary: Create patient (neo4j - do not use in production)
      description: Create a patient using the details provided in the request body.
      tags: [patient]
      parameters:
        - name: product_name
          in: query
          required: false
          description: Product name
          schema:
            type: string
            example: GDM
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PatientUpdateRequest'
              x-body-name: patient_details
      responses:
        '200':
          description: New patient
          content:
            application/json:
              schema: PatientResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    patient_details: dict = request.get_json() or {}
    product_name: str = request.args["product_name"]

    if not product_name:
        raise ValueError("Missing required query parameter 'product_name'")

    from dhos_services_api.blueprint_patients import patient_controller_neo

    response: dict = patient_controller_neo.create_patient(
        product_name=product_name, patient_details=patient_details
    )
    return jsonify(response)


@patients_blueprint.route("/dhos/v1/weekly_active_patients", methods=["GET"])
@protected_route(
    or_(
        scopes_present(required_scopes="read:gdm_patient_all"),
        scopes_present(required_scopes="read:patient_all"),
    )
)
def weekly_active_patients(
    product_name: str, start_date: Optional[str] = None, end_date: Optional[str] = None
) -> flask.Response:
    """
    ---
    get:
      summary: Get a year-week count of active patients
      description: |-
        Patients are considered active if their DraysonHealthProduct has is
        open before or during the week and is closed during or after the week
      tags: [patient]
      parameters:
        - name: product_name
          in: query
          required: true
          description: Product name
          schema:
            type: string
            example: GDM
        - name: start_date
          in: query
          required: false
          description: Earliest date for active patients to be returned
          schema:
            type: string
            format: date
            example: '2020-01-01'
        - name: end_date
          in: query
          required: false
          description: Latest date for active patients to be returned
          schema:
            type: string
            format: date
            example: '2020-07-01'
      responses:
        '200':
          description: Active patient counts by week
          content:
            application/json:
              schema:
                type: array
                items: ActiveWeeklyPatientCountResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if product_name != "GDM":
        raise ValueError(f"{product_name} is not currently supported.")

    response: List[Dict[str, str]] = pmcf_controller.get_active_patient_count(
        product_name=product_name, start_date=start_date, end_date=end_date
    )
    return jsonify(response)


@patients_blueprint.route("/dhos/v1/daily_created_patients", methods=["GET"])
@protected_route(
    or_(
        scopes_present(required_scopes="read:gdm_patient_all"),
        scopes_present(required_scopes="read:patient_all"),
    )
)
def daily_created_patients(
    product_name: str, start_date: Optional[str] = None, end_date: Optional[str] = None
) -> flask.Response:
    """
    ---
    get:
      summary: Get daily created patients
      description: |-
        Get daily created patients based on their DraysonHealthProduct
        opened_date by product_name
      tags: [patient]
      parameters:
        - name: product_name
          in: query
          required: true
          description: Product name
          schema:
            type: string
            example: GDM
        - name: start_date
          in: query
          required: false
          description: Earliest date for created patients to be returned
          schema:
            type: string
            format: date
            example: '2020-01-01'
        - name: end_date
          in: query
          required: false
          description: Latest date for created patients to be returned
          schema:
            type: string
            format: date
            example: '2020-07-01'
      responses:
        '200':
          description: Daily patient counts
          content:
            application/json:
              schema:
                type: array
                items: DailyCreatedPatientCountsResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    response: List[Dict[str, str]] = pmcf_controller.get_created_patient_count(
        product_name=product_name, start_date=start_date, end_date=end_date
    )
    return jsonify(response)
