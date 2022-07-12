from typing import Any, List, Optional, TypedDict

import draymed
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flask_batteries_included.helpers.apispec import (
    FlaskBatteriesPlugin,
    Identifier,
    initialise_apispec,
    openapi_schema,
)
from marshmallow import EXCLUDE, Schema, ValidationError, fields, validate

dhos_services_api_spec: APISpec = APISpec(
    version="1.2.2",
    openapi_version="3.0.3",
    title="DHOS Services API",
    info={
        "description": "The DHOS Services API is responsible for storing and retrieving information "
        "about patients, clinicians and locations."
    },
    plugins=[FlaskPlugin(), MarshmallowPlugin(), FlaskBatteriesPlugin()],
)

initialise_apispec(dhos_services_api_spec)


def validate_identifier(data: Any) -> None:
    if isinstance(data, str):
        return
    if isinstance(data, dict):
        if (
            isinstance(data.get("uuid"), str)
            and isinstance(data.get("first_name"), str)
            and isinstance(data.get("last_name"), str)
        ):
            return
    raise ValidationError("Invalid identifier field")


class ExpandableIdentifier(Schema):
    """
    TODO: We need this because of the horrible clinician UUID -> dict expansion that happens in this service.
    When this expansion logic is moved to the GDM BFF, we can get rid of this class and use Identifier instead.
    """

    class Meta:
        unknown = EXCLUDE
        ordered = True

    uuid = fields.String(
        required=True,
        description="Universally unique identifier for object",
        example="2c4f1d24-2952-4d4e-b1d1-3637e33cc161",
    )
    created = fields.String(
        description="When the object was created",
        example="2017-09-23T08:29:19.123+00:00",
    )
    modified = fields.String(
        description="When the object was modified",
        example="2017-09-23T08:29:19.123+00:00",
    )
    created_by = fields.Field(
        required=False,
        allow_none=True,
        validate=validate_identifier,
        description="UUID or object describing the user that created the object",
    )
    modified_by = fields.Field(
        required=False,
        allow_none=True,
        validate=validate_identifier,
        description="UUID or object describing the user that modified the object",
    )


class LocationProductRequest(Schema):
    class Meta:
        ordered = True

    product_name = fields.String(
        required=True, description="The product name", example="GDM"
    )
    opened_date = fields.String(
        required=True,
        description="ISO8601 date for when product was opened for the location",
        example="2020-01-01",
    )
    closed_date = fields.String(
        required=False,
        allow_none=True,
        description="ISO8601 date for when product was closed for the location",
        example="2020-05-01",
    )


class LocationProductResponse(Identifier, LocationProductRequest):
    class Meta:
        ordered = True


class LocationCommonOptionalFields(Schema):
    class Meta:
        ordered = True

    bookmarked_patients = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="List of bookmarked patient UUIDs",
        example=["4556cdf3-b60f-486c-bba8-7b1c222fe02a"],
    )

    active = fields.Boolean(
        required=False,
        allow_none=True,
        description="Whether the location is active",
        example=True,
    )
    address_line_1 = fields.String(
        required=False,
        allow_none=True,
        description="First line of location address",
        example="21 Spring Lane",
    )
    address_line_2 = fields.String(
        required=False,
        allow_none=True,
        description="Second line of location address",
        example="Villageville",
    )
    address_line_3 = fields.String(
        required=False,
        allow_none=True,
        description="Third line of location address",
        example="Townton",
    )
    address_line_4 = fields.String(
        required=False,
        allow_none=True,
        description="Fourth line of location address",
        example="Cityland",
    )
    postcode = fields.String(
        required=False,
        allow_none=True,
        description="Location address postcode",
        example="OX1 1AA",
    )
    country = fields.String(
        required=False,
        allow_none=True,
        description="Location address country",
        example="United Kingdom",
    )
    locality = fields.String(
        required=False,
        allow_none=True,
        description="Location address locality",
        example="Oxfordshire",
    )
    region = fields.String(
        required=False,
        allow_none=True,
        description="Location address region",
        example="South East",
    )
    score_system_default = fields.String(
        required=False,
        allow_none=True,
        description="Default early warning score system for this location",
        validate=validate.OneOf(["news2", "meows"]),
    )


class LocationCommonRequiredFields(Schema):
    class Meta:
        ordered = True

    location_type = fields.String(
        required=True,
        description="Location type code",
        example=draymed.codes.code_from_name(name="hospital", category="location"),
    )
    ods_code = fields.String(
        required=True,
        description="ODS code used by the EPR to refer to the location",
        example="JW1-34",
    )
    display_name = fields.String(
        required=True,
        description="Name used to display the location in product UIs",
        example="John Radcliffe Hospital",
    )


@openapi_schema(dhos_services_api_spec)
class LocationRequest(LocationCommonOptionalFields, LocationCommonRequiredFields):
    class Meta:
        description = "Location request"
        unknown = EXCLUDE
        ordered = True

    uuid = fields.String(description="Location UUID", required=False, allow_none=False)

    dh_products = fields.List(
        fields.Nested(LocationProductRequest),
        required=True,
        description="Products with which location should be associated",
    )

    parents = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="List of parent location UUIDs",
        example=["eb42ee95-6aa6-46b7-9c3e-0e96526747a6"],
    )

    parent_ods_code = fields.String(
        required=False,
        allow_none=True,
        description="ODS code used by EPR to refer to the location's parent",
        example="ABC-123",
    )


@openapi_schema(dhos_services_api_spec)
class LocationResponse(
    Identifier, LocationCommonOptionalFields, LocationCommonRequiredFields
):
    class Meta:
        description = "Location response"
        unknown = EXCLUDE
        ordered = True

    dh_products = fields.List(
        fields.Nested(LocationProductResponse),
        required=False,
        description="Products with which location is associated",
    )
    clinician_bookmark = fields.Boolean(
        required=False,
        allow_none=True,
        description="Whether the current user (determined by JWT) has bookmarked the location",
        example=False,
    )
    parents = fields.List(
        fields.Nested("self"),
        required=False,
        allow_none=True,
        description="Parent locations",
    )
    children = fields.List(
        fields.String(),
        required=False,
        description="UUIDs of child locations associated with this location",
    )
    bookmarked = fields.List(
        fields.String(),
        required=False,
        description="UUIDs of bookmarked patients in this location",
    )


@openapi_schema(dhos_services_api_spec)
class LocationUpdateRequest(LocationCommonOptionalFields):
    class Meta:
        description = "Location update request"
        unknown = EXCLUDE
        ordered = True

    location_type = fields.String(
        required=False,
        allow_none=True,
        description="Location type code",
        example=draymed.codes.code_from_name(name="hospital", category="location"),
    )

    parent_locations = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="List of parent location UUIDs",
        example=["eb42ee95-6aa6-46b7-9c3e-0e96526747a6"],
    )

    dh_products = fields.List(
        fields.Nested(LocationProductRequest),
        required=False,
        allow_none=True,
        description="Products with which location should be associated",
    )


@openapi_schema(dhos_services_api_spec)
class LocationDeleteRequest(Schema):
    class Meta:
        description = "Location delete request"
        unknown = EXCLUDE
        ordered = True

    parent_locations = fields.List(
        fields.String(),
        required=True,
        description="List of parent location UUIDs",
        example=["eb42ee95-6aa6-46b7-9c3e-0e96526747a6"],
    )


class BaseProductSchema(Schema):
    class Meta:
        description = "Product"
        unknown = EXCLUDE
        ordered = True

    product_name = fields.String(
        required=True,
        description="Product name",
        example="SEND",
    )
    opened_date = fields.String(
        required=True,
        description="Opened date",
        example="2018-01-01",
    )
    closed_date = fields.String(
        required=False,
        allow_none=True,
        description="Closed date",
        example="2018-06-01",
    )
    closed_reason = fields.String(
        required=False,
        allow_none=True,
        description="Closed reason",
        example="Some reason",
    )
    closed_reason_other = fields.String(
        required=False,
        allow_none=True,
        description="Closed reason other",
        example="Some other reason",
    )
    accessibility_discussed = fields.Boolean(
        required=False,
        allow_none=True,
        description="Whether accessibility was discussed",
        example=True,
    )
    accessibility_discussed_date = fields.String(
        required=False,
        allow_none=True,
        description="When was accessibility discussed",
        example="2019-10-07",
    )


class ClinicianProductSchema(BaseProductSchema):
    class Meta:
        description = "Clinician product"
        unknown = EXCLUDE
        ordered = True

    accessibility_discussed_with = fields.String(
        required=False,
        allow_none=True,
        description="UUID of Clinician that discussed accessibility requirements",
        example="2ae1e5f0-2e64-405b-a5e2-96d38a688df1",
    )


class ClinicianCommonOptionalFields(Schema):
    class Meta:
        ordered = True

    bookmarks = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="List of bookmarked location UUIDs",
        example=["2ae1e5f0-2e64-405b-a5e2-96d38a688df1"],
    )

    bookmarked_patients = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="List of bookmarked patient UUIDs",
        example=["eb42ee95-6aa6-46b7-9c3e-0e96526747a6"],
    )

    can_edit_ews = fields.Boolean(
        required=False,
        allow_none=True,
        description="Whether the clinician is allowed to change a patient's early warning score in SEND",
        example=True,
    )

    can_edit_encounter = fields.Boolean(
        required=False,
        allow_none=True,
        description="Whether the clinician is allowed to change a patient's early warning score in SEND",
        example=True,
    )

    contract_expiry_eod_date = fields.Date(
        required=False,
        allow_none=True,
        description="Contract expiry date",
        example="2020-12-31",
    )

    professional_registration_number = fields.String(
        required=False,
        allow_none=True,
        description="Professional registration number",
        example="321",
    )

    agency_name = fields.String(
        required=False, allow_none=True, description="Agency name", example="XYZ Ltd"
    )

    agency_staff_employee_number = fields.String(
        required=False,
        allow_none=True,
        description="Agency staff employee number",
        example="321",
    )

    email_address = fields.String(
        required=False,
        allow_none=True,
        description="e-mail address",
        example="abc@xyz.com",
    )

    booking_reference = fields.String(
        required=False, allow_none=True, description="Booking reference", example="4321"
    )

    analytics_consent = fields.Boolean(
        required=False,
        allow_none=True,
        description="Indicates if the user has given consent to analytics",
        example=True,
    )

    send_entry_identifier = fields.String(
        required=False,
        allow_none=True,
        description="Identifier used by clinician to log into SEND entry",
        example="321",
    )

    login_active = fields.Boolean(
        required=False,
        allow_none=True,
        description="Whether the clinician is allowed to log in",
        example=True,
    )


class ClinicianAllFieldsAsOptional(ClinicianCommonOptionalFields):
    class Meta:
        ordered = True

    first_name = fields.String(
        required=False, allow_none=True, description="First name", example="John"
    )

    last_name = fields.String(
        required=False, allow_none=True, description="last name", example="Roberts"
    )

    phone_number = fields.String(
        required=False,
        allow_none=True,
        description="Phone number",
        example="01234098765",
    )

    job_title = fields.String(
        required=False, allow_none=True, description="Job title", example="Doctor"
    )

    nhs_smartcard_number = fields.String(
        required=False,
        allow_none=True,
        description="NHS Smartcard number",
        example="012345",
    )

    locations = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="List of UUIDs of locations with which the clinician is associated",
        example=["eb42ee95-6aa6-46b7-9c3e-0e96526747a6"],
    )

    groups = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="List of user groups assigned to",
        example=["SEND Clinician"],
    )

    products = fields.Nested(
        ClinicianProductSchema,
        many=True,
        required=False,
        allow_none=True,
        description="Products with which the clinician should be associated",
        example=[{"product_name": "SEND", "opened_date": "2019-06-01"}],
    )


@openapi_schema(dhos_services_api_spec)
class ClinicianCreateRequest(ClinicianCommonOptionalFields):
    class Meta:
        description = "Clinician create request"
        unknown = EXCLUDE
        ordered = True

    first_name = fields.String(required=True, description="First name", example="John")

    last_name = fields.String(
        required=True,
        description="last name",
        example="Roberts",
    )

    phone_number = fields.String(
        required=True,
        description="Phone number",
        example="01234098765",
    )

    job_title = fields.String(required=True, description="Job title", example="Doctor")

    nhs_smartcard_number = fields.String(
        required=True,
        description="NHS Smartcard number",
        example="012345",
    )

    locations = fields.List(
        fields.String(),
        required=True,
        description="List of UUIDs of locations with which the clinician is associated",
        example=["eb42ee95-6aa6-46b7-9c3e-0e96526747a6"],
    )

    groups = fields.List(
        fields.String(),
        required=True,
        description="List of user groups assigned to",
        example=["SEND Clinician"],
    )

    products = fields.List(
        fields.Nested(ClinicianProductSchema),
        required=True,
        description="Products with which the clinician should be associated",
        example=[{"product_name": "SEND", "opened_date": "2019-06-01"}],
    )


@openapi_schema(dhos_services_api_spec)
class ClinicianTermsRequest(Schema):
    class Meta:
        description = "Create Clinician Terms of Service request"
        unknown = EXCLUDE
        ordered = True

    product_name = fields.String(
        required=True,
        description="Product name",
        example="SEND",
    )
    version = fields.Integer(required=True, description="Product version", example=12)
    accepted_timestamp = fields.String(
        required=False,
        allow_none=True,
        description="Accepted at timestamp",
        example="2019-01-01T12:01:01.000Z",
    )


@openapi_schema(dhos_services_api_spec)
class ClinicianTermsResponse(ClinicianTermsRequest, ExpandableIdentifier):
    class Meta:
        description = "Create Clinician Terms of Service response"
        unknown = EXCLUDE
        ordered = True


@openapi_schema(dhos_services_api_spec)
class ClinicianUpdateRequest(ClinicianAllFieldsAsOptional):
    class Meta:
        description = "Clinician update request"
        unknown = EXCLUDE
        ordered = True


@openapi_schema(dhos_services_api_spec)
class ClinicianPasswordUpdateRequest(Schema):
    class Meta:
        description = "Clinician password update request"
        unknown = EXCLUDE
        ordered = True

    password = fields.String(required=True, description="Password", example="abc*_123")


@openapi_schema(dhos_services_api_spec)
class ClinicianRemoveRequest(ClinicianAllFieldsAsOptional):
    class Meta:
        description = "Clinician remove request"
        unknown = EXCLUDE
        ordered = True


@openapi_schema(dhos_services_api_spec)
class ClinicianResponse(ClinicianAllFieldsAsOptional, ExpandableIdentifier):
    class Meta:
        description = "Clinician response"
        unknown = EXCLUDE
        ordered = True

    terms_agreement = fields.Dict(
        required=False, allow_none=True, description="Latest terms agreement"
    )


@openapi_schema(dhos_services_api_spec)
class CliniciansResponse(Schema):
    class Meta:
        description = "Clinicians response"
        unknown = EXCLUDE
        ordered = True

    results = fields.Nested(
        ClinicianResponse, required=True, allow_none=False, many=True
    )
    total = fields.Integer(
        required=True,
        allow_none=False,
        description="Total clinicians in the database matching the request",
    )


class ClinicianLocations(Schema):
    class Meta:
        ordered = True

    name = fields.String(
        description="Name used to display the location for product",
        example="John Radcliffe Hospital",
    )
    id = fields.String(
        description="Location UUID",
        example="eb42ee95-6aa6-46b7-9c3e-0e96526747a6",
    )
    products = fields.List(
        fields.Nested(ClinicianProductSchema),
        description="Products with which the clinician should be associated",
        example=[{"product_name": "SEND", "opened_date": "2019-06-01"}],
    )


@openapi_schema(dhos_services_api_spec)
class ClinicianLoginResponse(Schema):
    class Meta:
        description = "Create Clinician Terms of Service response"
        unknown = EXCLUDE
        ordered = True

    job_title = fields.String(description="Job title", required=True, example="Doctor")

    email_address = fields.String(
        description="e-mail address",
        example="abc@xyz.com",
        required=True,
        allow_none=True,
    )

    locations = fields.List(
        fields.Nested(ClinicianLocations),
        description="Locations with which the clinician should be associated",
        required=True,
    )

    user_id = fields.String(
        description="User UUID of clinician",
        required=True,
        example="eb42ee95-6aa6-46b7-9c3e-0e96526747a6",
    )

    groups = fields.List(
        fields.String(),
        description="List of user groups assigned to",
        required=True,
        example=["SEND Clinician"],
    )

    products = fields.List(
        fields.Nested(ClinicianProductSchema),
        description="Products with which the clinician should be associated",
        required=True,
        example=[{"product_name": "SEND", "opened_date": "2019-06-01"}],
    )

    can_edit_ews = fields.Boolean(
        description="Whether the clinician is allowed to change a patient's SpO2 scale in SEND",
        required=True,
        example=True,
        allow_none=True,
    )

    can_edit_encounter = fields.Boolean(
        description="Whether the clinician is allowed to modify an encounter",
        required=False,
        example=True,
        allow_none=True,
    )


@openapi_schema(dhos_services_api_spec)
class SearchPatient(Schema):
    class Meta:
        title = "Search result for a single patient"
        unknown = EXCLUDE
        ordered = True

        class Dict(TypedDict, total=False):
            patient_uuid: str
            first_name: Optional[str]
            last_name: Optional[str]
            dob: Optional[str]
            nhs_number: Optional[str]
            hospital_number: Optional[str]
            sex: Optional[str]
            has_clinician_bookmark: bool

    patient_uuid = fields.String(required=True)
    first_name = fields.String(required=True, allow_none=True)
    last_name = fields.String(required=True, allow_none=True)
    dob = fields.Date(required=True, allow_none=True)
    nhs_number = fields.String(required=True, allow_none=True)
    hospital_number = fields.String(required=True, allow_none=True)
    sex = fields.String(required=True, allow_none=True)
    has_clinician_bookmark = fields.Boolean(required=True, default=False)


@openapi_schema(dhos_services_api_spec)
class SearchResultsResponse(Schema):
    class Meta:
        title = "Search result"
        unknown = EXCLUDE
        ordered = True

        class Dict(TypedDict):
            total: int
            results: List[SearchPatient.Meta.Dict]

    total = fields.Integer(example=2)
    results = fields.Nested(SearchPatient, many=True)


class AddressRequest(Schema):
    class Meta:
        description = "Address request"
        unknown = EXCLUDE
        ordered = True

    address_line_1 = fields.String(
        required=False,
        allow_none=True,
        description="First line of address",
        example="Flat 14",
    )
    address_line_2 = fields.String(
        required=False,
        allow_none=True,
        description="Second line of address",
        example="11 Spring Close",
    )
    address_line_3 = fields.String(
        required=False,
        allow_none=True,
        description="Third line of address",
        example="Summerville",
    )
    address_line_4 = fields.String(
        required=False,
        allow_none=True,
        description="Fourth line of address",
        example="Autumn City",
    )
    locality = fields.String(
        required=False,
        allow_none=True,
        description="Locality of address",
        example="Wintershire",
    )
    region = fields.String(
        required=False,
        allow_none=True,
        description="Region of address",
        example="England",
    )
    postcode = fields.String(
        required=False,
        allow_none=True,
        description="Postcode of address",
        example="A11 111",
    )
    country = fields.String(
        required=False,
        allow_none=True,
        description="Country of address",
        example="United Kingdom",
    )
    lived_from = fields.String(
        required=False,
        allow_none=True,
        description="ISO8601 date for start of residence",
        example="2017-09-01",
    )
    lived_until = fields.String(
        required=False,
        allow_none=True,
        description="ISO8601 date for end of residence",
        example="2019-03-23",
    )


class AddressResponse(Identifier, AddressRequest):
    class Meta:
        description = "Address response"
        unknown = EXCLUDE
        ordered = True


class NoteSchema(Schema):
    class Meta:
        description = "Note"
        unknown = EXCLUDE
        ordered = True

    content = fields.String(
        required=True,
        description="Contents of the note",
        example="Patient is a delight",
    )


class NoteRequest(NoteSchema):
    class Meta:
        description = "Note request"
        unknown = EXCLUDE
        ordered = True

    clinician_uuid = fields.String(
        required=True,
        description="Clinician UUID",
        example="48378ca6-d28b-424a-9408-f8e00b9af657",
    )


class NoteResponse(Identifier, NoteSchema):
    class Meta:
        description = "Note response"
        unknown = EXCLUDE
        ordered = True

    clinician_uuid = fields.String(
        required=True,
        description="Clinician UUID",
        example="48378ca6-d28b-424a-9408-f8e00b9af657",
    )


class NoteUpdateRequest(NoteRequest):
    class Meta:
        description = "Note update request"
        unknown = EXCLUDE
        ordered = True

    # Same as NoteRequest but without required fields.
    content = fields.String(
        required=False,
        description="Contents of the note",
        example="Patient is a delight",
    )
    clinician_uuid = fields.String(
        required=False,
        description="Clinician UUID",
        example="48378ca6-d28b-424a-9408-f8e00b9af657",
    )


class ObservableEntityRequest(Schema):
    class Meta:
        description = "Observable entity request"
        unknown = EXCLUDE
        ordered = True

    sct_code = fields.String(
        required=True,
        description="SNOMED code for the observable entity",
        example="443911005",
    )
    date_observed = fields.String(
        required=True,
        description="ISO8601 date for the observable entity",
        example="2020-01-01",
    )
    value_as_string = fields.String(
        required=False,
        description="Observable entity value",
        example="11",
        allow_none=True,
    )
    metadata = fields.Dict(
        required=False,
        allow_none=True,
        description="Metadata related to the observable entity",
        example={
            "0hr": 50,
            "1hr": 100,
            "2hr": 75,
            "3hr": None,
        },
    )


class ObservableEntityResponse(Identifier, ObservableEntityRequest):
    class Meta:
        description = "Observable entity response"
        unknown = EXCLUDE
        ordered = True

    value_as_string = fields.String(
        required=True,
        description="Observable entity value",
        example="11",
        allow_none=True,
    )
    metadata = fields.Dict(
        required=True,
        allow_none=True,
        description="Metadata related to the observable entity",
        example={
            "0hr": 50,
            "1hr": 100,
            "2hr": 75,
            "3hr": None,
        },
    )


class ObservableEntityUpdateRequest(ObservableEntityRequest):
    class Meta:
        description = "Observable entity update request"
        unknown = EXCLUDE
        ordered = True

    # Same as ObservableEntityRequest but without required fields.
    sct_code = fields.String(
        required=False,
        description="SNOMED code for the observable entity",
        example="443911005",
    )
    date_observed = fields.String(
        required=False,
        description="ISO8601 date for the observable entity",
        example="2020-01-01",
    )
    value_as_string = fields.String(
        allow_none=True,
        required=False,
        description="Observable entity value",
        example="11",
    )


class NonMedicationActionRequest(Schema):
    class Meta:
        description = "Non medication action request"
        unknown = EXCLUDE
        ordered = True

    action_sct_code = fields.String(
        required=True, description="SNOMED code for the action", example="281090004"
    )


class NonMedicationActionResponse(Identifier, NonMedicationActionRequest):
    class Meta:
        description = "Non medication action"
        unknown = EXCLUDE
        ordered = True


class DoseRequest(Schema):
    class Meta:
        description = "Dose"
        unknown = EXCLUDE
        ordered = True

    medication_id = fields.String(
        required=True,
        description="UUID of the medication",
        example="bbc1a393-818f-417a-a6e5-76f9338a6a1c",
    )
    dose_amount = fields.Float(
        required=True, description="Amount of the medication", example=1.5
    )
    routine_sct_code = fields.String(
        required=False,
        allow_none=True,
        description="SNOMED code for the dose",
        example="12345",
    )


class DoseChangeSchema(Identifier, DoseRequest):
    class Meta:
        description = "Dose change"
        unknown = EXCLUDE
        ordered = True


class DoseResponse(DoseRequest):
    class Meta:
        description = "Dose response"
        unknown = EXCLUDE
        ordered = True

    changes = fields.Nested(
        DoseChangeSchema, many=True, required=False, allow_none=True
    )


class DoseUpdateRequest(DoseRequest):
    class Meta:
        description = "Dose update request"
        unknown = EXCLUDE
        ordered = True

    # Like DoseRequest but without required fields.
    medication_id = fields.String(
        required=False,
        description="UUID of the medication",
        example="bbc1a393-818f-417a-a6e5-76f9338a6a1c",
    )
    dose_amount = fields.Float(
        required=False, description="Amount of the medication", example=1.5
    )


class DoseHistorySchema(Identifier):
    class Meta:
        description = "Dose history"
        unknown = EXCLUDE
        ordered = True

    clinician_uuid = fields.String(
        required=False,
        allow_none=True,
        description="Clinician UUID",
        example="48378ca6-d28b-424a-9408-f8e00b9af657",
    )
    dose = fields.Nested(DoseResponse, required=False, allow_none=True)
    action = fields.String(
        required=False,
        allow_none=True,
        description="Description of the change",
        example="Reduction by 2 units",
    )


class ManagementPlanRequest(Schema):
    class Meta:
        description = "Management plan request"
        unknown = EXCLUDE
        ordered = True

    sct_code = fields.String(
        required=True,
        description="SNOMED code for the management plan type",
        example="386359008",
    )
    start_date = fields.String(
        required=False,
        allow_none=True,
        description="ISO8601 date when plan started",
        example="2020-01-01",
    )
    end_date = fields.String(
        required=False,
        allow_none=True,
        description="ISO8601 date when plan ended",
        example="2020-05-01",
    )
    actions = fields.Nested(
        NonMedicationActionRequest, many=True, required=False, allow_none=True
    )
    doses = fields.Nested(DoseRequest, many=True, required=False, allow_none=True)


class ManagementPlanResponse(Identifier, ManagementPlanRequest):
    class Meta:
        description = "Management plan response"
        unknown = EXCLUDE
        ordered = True

    plan_history = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="SNOMED codes for previous management plan types",
        example=["67866001"],
    )
    actions = fields.Nested(
        NonMedicationActionResponse, many=True, required=False, allow_none=True
    )
    doses = fields.Nested(DoseResponse, many=True, required=False, allow_none=True)
    dose_history = fields.Nested(
        DoseHistorySchema, many=True, required=False, allow_none=True
    )


class ManagementPlanUpdateRequest(ManagementPlanRequest):
    class Meta:
        description = "Management plan update request"
        unknown = EXCLUDE
        ordered = True

    # Same as ManagementPlanRequest but without required fields.
    sct_code = fields.String(
        required=False,
        description="SNOMED code for the management plan type",
        example="386359008",
    )
    doses = fields.Nested(DoseUpdateRequest, many=True, required=False, allow_none=True)


class ReadingsPlanChangeSchema(Identifier):
    class Meta:
        description = "Readings plan change"
        unknown = EXCLUDE
        ordered = True

    days_per_week_to_take_readings = fields.Integer(
        required=False,
        allow_none=True,
        description="Days per week patient is expected to take readings",
        example=5,
    )
    readings_per_day = fields.Integer(
        required=False,
        allow_none=True,
        description="Number of readings per day patient is expected to take",
        example=4,
    )


class ReadingsPlanRequest(Schema):
    class Meta:
        description = "Readings plan request"
        unknown = EXCLUDE
        ordered = True

    sct_code = fields.String(
        required=True,
        description="SNOMED code for the readings plan type",
        example="33747003",
    )
    start_date = fields.String(
        required=True,
        description="ISO8601 date when plan started",
        example="2020-01-01",
    )
    days_per_week_to_take_readings = fields.Integer(
        required=True,
        description="Days per week patient is expected to take readings",
        example=5,
    )
    readings_per_day = fields.Integer(
        required=True,
        description="Number of readings per day patient is expected to take",
        example=4,
    )
    end_date = fields.String(
        required=False,
        allow_none=True,
        description="ISO8601 date when plan ended",
        example="2020-05-01",
    )


class ReadingsPlanResponse(Identifier, ReadingsPlanRequest):
    class Meta:
        description = "Readings plan response"
        unknown = EXCLUDE
        ordered = True

    changes = fields.Nested(
        ReadingsPlanChangeSchema, many=True, required=True, allow_none=False
    )


class ReadingsPlanUpdateRequest(ReadingsPlanRequest):
    class Meta:
        description = "Readings plan update request"
        unknown = EXCLUDE
        ordered = True

    # Same as ReadingsPlanRequest but without required fields.
    sct_code = fields.String(
        required=False,
        description="SNOMED code for the readings plan type",
        example="33747003",
    )
    start_date = fields.String(
        required=False,
        description="ISO8601 date when plan started",
        example="2020-01-01",
    )
    days_per_week_to_take_readings = fields.Integer(
        required=False,
        description="Days per week patient is expected to take readings",
        example=5,
    )
    readings_per_day = fields.Integer(
        required=False,
        description="Number of readings per day patient is expected to take",
        example=4,
    )


class DiagnosisRequest(Schema):
    class Meta:
        description = "Diagnosis request"
        unknown = EXCLUDE
        ordered = True

    sct_code = fields.String(
        required=True, description="SNOMED code for the diagnosis", example="11687002"
    )
    diagnosis_other = fields.String(
        required=False,
        allow_none=True,
        description="Freetext field for diagnosis description",
        example="Diabetes type 4",
    )
    diagnosed = fields.String(
        required=False,
        allow_none=True,
        description="ISO8601 date of diagnosis",
        example="2020-01-01",
    )
    resolved = fields.String(
        required=False,
        allow_none=True,
        description="ISO8601 date of resolution",
        example="2020-01-01",
    )
    episode = fields.Integer(required=False, allow_none=True, example=1)
    presented = fields.String(
        required=False,
        allow_none=True,
        description="ISO8601 date of presentation",
        example="2020-01-01",
    )
    diagnosis_tool = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="List of SNOMED code for the diagnosis tools",
        example=["D0000011"],
    )
    diagnosis_tool_other = fields.String(
        required=False,
        allow_none=True,
        description="Freetext field for the diagnosis tool",
        example="My own intuition",
    )
    risk_factors = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="List of SNOMED code for risk factors",
        example=["199228009"],
    )
    observable_entities = fields.Nested(
        ObservableEntityRequest, many=True, required=False, allow_none=True
    )
    management_plan = fields.Nested(
        ManagementPlanRequest, required=False, allow_none=True
    )
    readings_plan = fields.Nested(ReadingsPlanRequest, required=False, allow_none=True)


class DiagnosisResponse(Identifier, DiagnosisRequest):
    class Meta:
        description = "Diagnosis response"
        unknown = EXCLUDE
        ordered = True

    observable_entities = fields.Nested(
        ObservableEntityResponse, many=True, required=True, allow_none=False
    )
    management_plan = fields.Nested(
        ManagementPlanResponse, required=False, allow_none=True
    )
    readings_plan = fields.Nested(ReadingsPlanResponse, required=False, allow_none=True)


class DiagnosisUpdateRequest(DiagnosisRequest):
    class Meta:
        description = "Diagnosis update request"
        unknown = EXCLUDE
        ordered = True

    # Same as DiagnosisSchema but without required fields.
    sct_code = fields.String(
        required=False,
        allow_none=True,
        description="SNOMED code for the diagnosis",
        example="11687002",
    )
    observable_entities = fields.Nested(
        ObservableEntityUpdateRequest, many=True, required=False, allow_none=True
    )
    management_plan = fields.Nested(
        ManagementPlanUpdateRequest, required=False, allow_none=True
    )
    readings_plan = fields.Nested(
        ReadingsPlanUpdateRequest, required=False, allow_none=True
    )


class BabyRequest(Schema):
    class Meta:
        description = "Baby request"
        unknown = EXCLUDE
        ordered = True

    sex = fields.String(
        required=False,
        allow_none=True,
        description="SNOMED code for baby's sex",
        example="248152002",
    )
    first_name = fields.String(
        required=False, allow_none=True, description="Baby's first name", example="Joan"
    )
    last_name = fields.String(
        required=False,
        allow_none=True,
        description="Baby's last name",
        example="Speedwell",
    )
    dob = fields.String(
        required=False,
        allow_none=True,
        description="Baby's date of birth in ISO8601 format",
        example="1978-05-06",
    )
    phone_number = fields.String(
        required=False,
        allow_none=True,
        description="Baby's phone number",
        example="07777777777",
    )


class BabyResponse(Identifier, BabyRequest):
    class Meta:
        description = "Baby"
        unknown = EXCLUDE
        ordered = True


class DeliveryRequest(Schema):
    class Meta:
        description = "Delivery request"
        unknown = EXCLUDE
        ordered = True

    birth_outcome = fields.String(
        required=False,
        allow_none=True,
        description="SNOMED code for birth outcome",
        example="48782003",
    )
    outcome_for_baby = fields.String(
        required=False,
        allow_none=True,
        description="SNOMED code for outcome for baby",
        example="169826009",
    )
    neonatal_complications = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="List of SNOMED codes for neonatal complications",
        example=["52767006"],
    )
    neonatal_complications_other = fields.String(
        required=False,
        allow_none=True,
        description="Freetext field for other neonatal complications",
        example="Baby is too cute",
    )
    admitted_to_special_baby_care_unit = fields.Boolean(
        required=False,
        allow_none=True,
        description="Whether the patient was admitted to special baby care unit",
        example=False,
    )
    birth_weight_in_grams = fields.Integer(
        required=False, allow_none=True, description="Birth weight (g)", example=2000
    )
    length_of_postnatal_stay_for_baby = fields.Integer(
        required=False,
        allow_none=True,
        description="Length of postnatal stay for baby in days",
        example=3,
    )
    apgar_1_minute = fields.Integer(
        required=False,
        allow_none=True,
        description="APGAR score 1 minute after birth",
        example=9,
    )
    apgar_5_minute = fields.Integer(
        required=False,
        allow_none=True,
        description="APGAR score 5 minutes after birth",
        example=10,
    )
    feeding_method = fields.String(
        required=False,
        allow_none=True,
        description="SNOMED code for feeding method",
        example="226789007",
    )
    date_of_termination = fields.String(
        required=False,
        allow_none=True,
        description="ISO8601 date of termination",
        example="2020-01-01",
    )
    patient = fields.Nested(BabyRequest, required=False, allow_none=True)


class DeliveryResponse(Identifier, DeliveryRequest):
    class Meta:
        description = "Delivery response"
        unknown = EXCLUDE
        ordered = True

    patient = fields.Nested(BabyResponse, required=False, allow_none=True)


class DeliveryUpdateRequest(DeliveryRequest):
    class Meta:
        description = "Delivery update request"
        unknown = EXCLUDE
        ordered = True

    # Same as DeliveryRequest but without the required fields.
    patient = fields.Nested(BabyRequest, required=False, allow_none=True)


class PregnancyRequest(Schema):
    class Meta:
        description = "Pregnancy request"
        unknown = EXCLUDE
        ordered = True

    estimated_delivery_date = fields.String(
        required=True,
        description="ISO8601 date of expected delivery",
        example="2020-01-01",
    )
    planned_delivery_place = fields.String(
        required=False,
        allow_none=True,
        description="SNOMED code for planned delivery place",
        example="310586008",
    )
    length_of_postnatal_stay_in_days = fields.Integer(
        required=False,
        allow_none=True,
        description="Length of postnatal stay in days",
        example=3,
    )
    colostrum_harvesting = fields.Boolean(
        required=False,
        allow_none=True,
        description="Whether colostrum harvesting occurred",
        example=True,
    )
    expected_number_of_babies = fields.Integer(
        required=False,
        allow_none=True,
        description="Expected number of babies",
        example=1,
    )
    pregnancy_complications = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="List of SNOMED codes for any pregnancy complications",
        example=["48194001"],
    )
    induced = fields.Boolean(
        required=False,
        allow_none=True,
        description="Whether pregnancy was induced",
        example=False,
    )
    deliveries = fields.Nested(
        DeliveryRequest, many=True, required=False, allow_none=True
    )
    height_at_booking_in_mm = fields.Integer(
        required=False,
        allow_none=True,
        description="Height (mm) at booking",
        example=1600,
    )
    weight_at_diagnosis_in_g = fields.Integer(
        required=False,
        allow_none=True,
        description="Weight (g) at diagnosis",
        example=6000,
    )
    weight_at_booking_in_g = fields.Integer(
        required=False,
        allow_none=True,
        description="Weight (g) at booking",
        example=6000,
    )
    weight_at_36_weeks_in_g = fields.Integer(
        required=False,
        allow_none=True,
        description="Weight (g) at 36 weeks' gestation",
        example=6200,
    )
    delivery_place = fields.String(
        required=False,
        allow_none=True,
        description="SNOMED code for actual delivery place",
        example="D0000009",
    )
    delivery_place_other = fields.String(
        required=False,
        allow_none=True,
        description="Freetext field for actual delivery place",
        example="At home",
    )
    first_medication_taken_recorded = fields.String(
        required=False,
        allow_none=True,
        description="ISO8601 date for when medication was first taken",
        example="2020-01-01",
    )
    first_medication_taken = fields.String(
        required=False,
        allow_none=True,
        description="Description of when medication was first taken",
        example="5 days ago",
    )


class PregnancyUpdateRequest(PregnancyRequest):
    class Meta:
        description = "Pregnancy update request"
        unknown = EXCLUDE
        ordered = True

    # Same as PregnancyRequest but without required fields.
    estimated_delivery_date = fields.String(
        required=False,
        description="ISO8601 date of expected delivery",
        example="2020-01-01",
    )
    deliveries = fields.Nested(
        DeliveryUpdateRequest, many=True, required=False, allow_none=True
    )


class PregnancyResponse(PregnancyRequest, Identifier):
    class Meta:
        description = "Pregnancy response"
        unknown = EXCLUDE
        ordered = True

    deliveries = fields.Nested(
        DeliveryResponse, many=True, required=False, allow_none=True
    )


class VisitSchema(Schema):
    class Meta:
        description = "Visit"
        unknown = EXCLUDE
        ordered = True

    visit_date = fields.String(
        required=True, description="ISO8601 date of visit", example="2020-01-01"
    )
    location = fields.String(
        required=True,
        description="UUID of location where visit occurred",
        example="ccc602d9-eef1-4e48-b012-8312274bcab1",
    )
    summary = fields.String(
        required=False,
        allow_none=True,
        description="Freetext summary of visit",
        example="Patient was healthy",
    )
    diagnoses = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="List of diagnosis UUIDs relevant to the visit",
        example=["485d3d40-7c70-4b60-a3f3-f79ae1f55ff9"],
    )


class VisitRequest(VisitSchema):
    class Meta:
        description = "Visit request"
        unknown = EXCLUDE
        ordered = True

    clinician_uuid = fields.String(
        required=True,
        description="UUID of clinician with whom visit occurred",
        example="963410f7-d92e-4b0a-9be1-f141df2a9d35",
    )


class VisitResponse(Identifier, VisitSchema):
    class Meta:
        description = "Visit response"
        unknown = EXCLUDE
        ordered = True

    clinician_uuid = fields.String(
        required=True,
        description="UUID of clinician with whom visit occurred",
        example="963410f7-d92e-4b0a-9be1-f141df2a9d35",
    )


class VisitUpdateRequest(VisitRequest):
    class Meta:
        description = "Visit update request"
        unknown = EXCLUDE
        ordered = True

    # Same as VisitRequest but without required fields.
    visit_date = fields.String(
        required=False, description="ISO8601 date of visit", example="2020-01-01"
    )
    location = fields.String(
        required=False,
        description="UUID of location where visit occurred",
        example="ccc602d9-eef1-4e48-b012-8312274bcab1",
    )
    clinician_uuid = fields.String(
        required=False,
        description="UUID of clinician with whom visit occurred",
        example="963410f7-d92e-4b0a-9be1-f141df2a9d35",
    )


class RecordHistoryRequest(Schema):
    class Meta:
        description = "Record history request"
        unknown = EXCLUDE
        ordered = True

    parity = fields.Integer(
        required=False,
        allow_none=True,
        description="Gestational parity (number of pregnancies carried beyond 20 weeks)",
        example=2,
    )
    gravidity = fields.Integer(
        required=False,
        allow_none=True,
        description="Gestational gravidity (number of pregnancies)",
        example=2,
    )


class RecordHistoryResponse(Identifier, RecordHistoryRequest):
    class Meta:
        description = "Record history response"
        unknown = EXCLUDE
        ordered = True


class RecordRequest(Schema):
    class Meta:
        description = "Record request"
        unknown = EXCLUDE
        ordered = True

    notes = fields.Nested(NoteRequest, many=True, required=False, allow_none=True)
    diagnoses = fields.Nested(
        DiagnosisRequest, many=True, required=False, allow_none=True
    )
    pregnancies = fields.Nested(
        PregnancyRequest, many=True, required=False, allow_none=True
    )
    visits = fields.Nested(VisitRequest, many=True, required=False, allow_none=True)
    history = fields.Nested(RecordHistoryRequest, required=False, allow_none=True)


class RecordUpdateRequest(RecordRequest):
    class Meta:
        description = "Record update request"
        unknown = EXCLUDE
        ordered = True

    notes = fields.Nested(NoteUpdateRequest, many=True, required=False, allow_none=True)
    diagnoses = fields.Nested(
        DiagnosisUpdateRequest, many=True, required=False, allow_none=True
    )
    pregnancies = fields.Nested(
        PregnancyUpdateRequest, many=True, required=False, allow_none=True
    )
    visits = fields.Nested(
        VisitUpdateRequest, many=True, required=False, allow_none=True
    )
    history = fields.Nested(RecordHistoryRequest, required=False, allow_none=True)


class RecordResponse(RecordRequest, Identifier):
    class Meta:
        description = "Record response"
        unknown = EXCLUDE
        ordered = True

    notes = fields.Nested(NoteResponse, many=True, required=True, allow_none=False)
    diagnoses = fields.Nested(
        DiagnosisResponse, many=True, required=True, allow_none=False
    )
    pregnancies = fields.Nested(
        PregnancyResponse, many=True, required=True, allow_none=False
    )
    visits = fields.Nested(VisitResponse, many=True, required=True, allow_none=False)
    history = fields.Nested(RecordHistoryResponse, required=True, allow_none=True)


@openapi_schema(dhos_services_api_spec)
class PatientTermsRequest(Schema):
    class Meta:
        description = "Patient terms agreement request"
        unknown = EXCLUDE
        ordered = True

    product_name = fields.String(
        required=True,
        description="Product whose terms have been agreed to",
        example="GDM",
    )
    version = fields.Integer(
        required=True, description="Version number of terms agreed to", example=3
    )
    accepted_timestamp = fields.String(
        required=False,
        description="ISO8601 timestamp of acceptance",
        example="2020-01-01T00:00:00.000Z",
    )


class PatientTermsResponse(Identifier, PatientTermsRequest):
    class Meta:
        description = "Patient terms agreement response"
        unknown = EXCLUDE
        ordered = True


@openapi_schema(dhos_services_api_spec)
class PatientTermsRequestV2(Schema):
    class Meta:
        description = "Patient terms agreement request"
        unknown = EXCLUDE
        ordered = True

    product_name = fields.String(
        required=True,
        description="Product whose terms have been agreed to",
        example="GDM",
    )
    tou_version = fields.Integer(
        required=True, description="Version number of TOU terms agreed to", example=3
    )
    tou_accepted_timestamp = fields.String(
        required=False,
        description="ISO8601 timestamp of acceptance",
        example="2020-01-01T00:00:00.000Z",
    )
    patient_notice_version = fields.Integer(
        required=True, description="Version number of PN terms agreed to", example=3
    )
    patient_notice_accepted_timestamp = fields.String(
        required=False,
        description="ISO8601 timestamp of acceptance",
        example="2020-01-01T00:00:00.000Z",
    )


@openapi_schema(dhos_services_api_spec)
class PatientTermsResponseV2(Identifier, PatientTermsRequestV2):
    class Meta:
        description = "Patient terms agreement response"
        unknown = EXCLUDE
        ordered = True


class PatientTermsUpdateRequest(PatientTermsRequest):
    class Meta:
        description = "Patient terms agreement update request"
        unknown = EXCLUDE
        ordered = True

    # Same as TermsAgreementRequest but without required fields.
    product_name = fields.String(
        required=False,
        description="Product whose terms have been agreed to",
        example="GDM",
    )
    version = fields.Integer(
        required=False, description="Version number of terms agreed to", example=3
    )


class DhProductChangeResponse(Identifier):
    class Meta:
        description = "Product change"
        unknown = EXCLUDE
        ordered = True

    event = fields.String(
        required=True,
        allow_none=False,
        description="Event resulting in a change",
        example="archive",
    )


class DhProductRequest(BaseProductSchema):
    class Meta:
        description = "Drayson health product request"
        unknown = EXCLUDE
        ordered = True

    accessibility_discussed_with = fields.String(
        required=False,
        allow_none=True,
        description="UUID of the clinician with whom accessibility was discussed",
        example="6158fca0-b805-4d4a-9592-654fc1001a94",
    )


class DhProductResponse(Identifier, BaseProductSchema):
    class Meta:
        description = "Drayson health product response"
        unknown = EXCLUDE
        ordered = True

    accessibility_discussed_with = fields.String(required=False, allow_none=True)
    monitored_by_clinician = fields.Boolean(required=True, allow_none=False)
    changes = fields.Nested(
        DhProductChangeResponse, many=True, required=False, allow_none=False
    )


class DhDiabetesProductResponse(Identifier, BaseProductSchema):
    class Meta:
        description = "Drayson health product response"
        unknown = EXCLUDE
        ordered = True

    monitored_by_clinician = fields.Boolean(required=True, allow_none=False)


class DhProductUpdateRequest(DhProductRequest):
    class Meta:
        description = "Drayson health product update request"
        unknown = EXCLUDE
        ordered = True

    # Like DhProductRequest but without required fields.
    product_name = fields.String(
        required=False,
        description="Product name",
        example="SEND",
    )
    opened_date = fields.String(
        required=False,
        description="Opened date",
        example="2018-01-01",
    )


@openapi_schema(dhos_services_api_spec)
class PatientRequest(Schema):
    class Meta:
        description = "Patient request"
        unknown = EXCLUDE
        ordered = True

    first_name = fields.String(
        required=True, description="Patient's first name", example="Joan"
    )
    last_name = fields.String(
        required=True, description="Patient's last name", example="Speedwell"
    )
    hospital_number = fields.String(
        required=True, description="Patient's hospital number (MRN)", example="232434"
    )
    record = fields.Nested(RecordRequest, required=True)
    phone_number = fields.String(
        required=False,
        allow_none=True,
        description="Patient's phone number",
        example="07777777777",
    )
    allowed_to_text = fields.Boolean(
        required=False,
        allow_none=True,
        description="Whether SMS messages can be sent to the patient",
        example=True,
    )
    allowed_to_email = fields.Boolean(
        required=False,
        allow_none=True,
        description="Whether emails can be sent to the patient",
        example=True,
    )
    dob = fields.String(
        required=False,
        allow_none=True,
        description="Patient's date of birth in ISO8601 format",
        example="1978-05-06",
    )
    dod = fields.String(
        required=False,
        allow_none=True,
        description="Patient's date of death in ISO8601 format",
        example="2020-01-01",
    )
    nhs_number = fields.String(
        required=False,
        allow_none=True,
        description="Patient's 10-digit NHS number",
        example="1111111111",
    )
    email_address = fields.String(
        required=False,
        allow_none=True,
        description="Patient's email address",
        example="joan.speedwell@mail.com",
    )
    ethnicity = fields.String(
        required=False,
        allow_none=True,
        description="SNOMED code for patient's ethnicity",
        example="186019001",
    )
    ethnicity_other = fields.String(
        required=False,
        allow_none=True,
        description="Freetext field for for patient's ethnicity",
        example="Extraterrestrial",
    )
    sex = fields.String(
        required=False,
        allow_none=True,
        description="SNOMED code for patient's sex",
        example="248152002",
    )
    height_in_mm = fields.Integer(
        required=False,
        allow_none=True,
        description="Height (mm)",
        example=1600,
    )
    weight_in_g = fields.Integer(
        required=False,
        allow_none=True,
        description="Weight (g)",
        example=6000,
    )
    highest_education_level = fields.String(
        required=False,
        allow_none=True,
        description="SNOMED code for patient's highest education level",
        example="224297003",
    )
    highest_education_level_other = fields.String(
        required=False,
        allow_none=True,
        description="Freetext field for patient's highest education level",
        example="Arch-chancellor, Unseen University",
    )
    accessibility_considerations = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="List of SNOMED code for patient's accessibility considerations",
        example=["105597003"],
    )
    accessibility_considerations_other = fields.String(
        required=False,
        allow_none=True,
        description="Freetext field for patient's accessibility considerations",
        example="Patient has no ribs",
    )
    other_notes = fields.String(
        required=False,
        allow_none=True,
        description="Freeteext field for patient notes",
        example="Patient is delightful",
    )
    locations = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="UUIDs of locations with which patient is associated",
        example=["ea9fd397-6ff6-4b29-a4d2-c9d36bfa2737"],
    )
    personal_addresses = fields.Nested(
        AddressRequest, many=True, required=False, allow_none=True
    )
    dh_products = fields.Nested(
        DhProductRequest, many=True, required=False, allow_none=True
    )
    fhir_resource_id = fields.String(
        required=False,
        allow_none=True,
        description="Patient's ID in a trustomer's FHIR EPR system (null if the patient is not presented there)",
        example="ea9fd397-6ff6-4b29-a4d2-c9d36bfa2737",
    )


@openapi_schema(dhos_services_api_spec)
class PatientUpdateRequest(PatientRequest):
    class Meta:
        description = "Patient update request"
        unknown = EXCLUDE
        ordered = True

    # Same as PatientRequest but no fields are required.
    first_name = fields.String(
        required=False, description="Patient's first name", example="Joan"
    )
    last_name = fields.String(
        required=False, description="Patient's last name", example="Speedwell"
    )
    hospital_number = fields.String(
        required=False, description="Patient's hospital number (MRN)", example="232434"
    )
    record = fields.Nested(RecordUpdateRequest, required=False)
    personal_addresses = fields.Nested(
        AddressRequest, many=True, required=False, allow_none=True
    )
    dh_products = fields.Nested(
        DhProductUpdateRequest, many=True, required=False, allow_none=True
    )


@openapi_schema(dhos_services_api_spec)
class PatientResponse(Identifier, PatientRequest):
    class Meta:
        description = "Patient response"
        unknown = EXCLUDE
        ordered = True

    first_name = fields.String(
        required=True,
        allow_none=True,
        description="Patient's first name",
        example="Joan",
    )
    last_name = fields.String(
        required=True,
        allow_none=True,
        description="Patient's last name",
        example="Speedwell",
    )

    hospital_number = fields.String(
        required=True,
        description="Patient's hospital number (MRN)",
        example="232434",
        allow_none=True,
    )

    record = fields.Nested(RecordResponse, required=True)

    personal_addresses = fields.Nested(
        AddressResponse, many=True, required=True, allow_none=False
    )
    dh_products = fields.Nested(
        DhProductResponse, many=True, required=True, allow_none=False
    )
    terms_agreement = fields.Nested(
        PatientTermsResponse, required=False, allow_none=True
    )
    bookmarked = fields.Boolean(
        required=False,
        allow_none=True,
        description="Whether patient is bookmarked",
        example=False,
    )
    has_been_bookmarked = fields.Boolean(
        required=False,
        allow_none=True,
        description="Whether patient has ever been bookmarked",
        example=True,
    )
    clinician_bookmark = fields.Boolean(
        required=False,
        allow_none=True,
        description="Whether patient is bookmarked by a clinician",
        example=True,
    )


@openapi_schema(dhos_services_api_spec)
class AbbreviatedManagementPlanResponse(Schema):
    class Meta:
        description = "Abbreviated Management plan response"
        unknown = EXCLUDE
        ordered = True

    doses = fields.Nested(DoseResponse, many=True, required=True, allow_none=False)


@openapi_schema(dhos_services_api_spec)
class AbbreviatedDiagnosisResponse(Schema):
    class Meta:
        description = "Abbreviated Diagnosis response"
        unknown = EXCLUDE
        ordered = True

    management_plan = fields.Nested(
        AbbreviatedManagementPlanResponse, required=True, allow_none=False
    )


@openapi_schema(dhos_services_api_spec)
class AbbreviatedRecordResponse(Schema):
    class Meta:
        description = "Abbreviated Record response"
        unknown = EXCLUDE
        ordered = True

    diagnoses = fields.Nested(
        AbbreviatedDiagnosisResponse, many=True, required=True, allow_none=False
    )


@openapi_schema(dhos_services_api_spec)
class AbbreviatedPatientResponse(Schema):
    class Meta:
        description = "Abbreviated patient response"
        unknown = EXCLUDE
        ordered = True

    uuid = fields.String(
        required=True,
        description="Universally unique identifier for object",
        example="2c4f1d24-2952-4d4e-b1d1-3637e33cc161",
    )
    locations = fields.List(
        fields.String(),
        required=True,
        allow_none=False,
        description="UUIDs of locations with which patient is associated",
        example=["ea9fd397-6ff6-4b29-a4d2-c9d36bfa2737"],
    )
    # This field is only used in one deprecated endpoint and is a subset of RecordSchema.
    # Rather than sinking time into documenting it, we should make the BFF use the main
    # GET patient endpoint and strip out fields the app doesn't need.
    # TODO: remove this schema once GDM-3440 is complete.
    record = fields.Nested(
        AbbreviatedRecordResponse,
        required=True,
        description="Abbreviated patient record",
    )


@openapi_schema(dhos_services_api_spec)
class ClosePatientRequest(Schema):
    class Meta:
        description = "Close patient request"
        unknown = EXCLUDE
        ordered = True

    closed_date = fields.String(
        required=True,
        description="ISO8601 date for when patient was closed",
        example="2017-09-01",
    )
    closed_reason = fields.String(
        required=False,
        allow_none=True,
        description="SNOMED code for reason for closing patient",
        example="289256000",
    )
    closed_reason_other = fields.String(
        required=False,
        allow_none=True,
        description="Freetext field for reason for closing patient",
        example="Patient created in error",
    )


class SimpleReadingsPlanSchema(Schema):
    class Meta:
        description = "Simple readings plan"
        unknown = EXCLUDE
        ordered = True

    created = fields.String(
        required=True,
        description="ISO8601 timestamp of acceptance",
        example="2020-01-01T00:00:00.000Z",
    )
    days_per_week_to_take_readings = fields.Integer(
        required=True,
        description="Days per week patient is expected to take readings",
        example=5,
    )
    readings_per_day = fields.Integer(
        required=True,
        description="Number of readings per day patient is expected to take",
        example=4,
    )


@openapi_schema(dhos_services_api_spec)
class ActivityAlertingPatientResponse(Schema):
    class Meta:
        description = "Activity alerting patient response"
        unknown = EXCLUDE
        ordered = True

    uuid = fields.String(
        required=True,
        description="Universally unique identifier for object",
        example="2c4f1d24-2952-4d4e-b1d1-3637e33cc161",
    )
    first_name = fields.String(
        required=True, description="Patient's first name", example="Joan"
    )
    locations = fields.List(
        fields.String(),
        required=True,
        description="UUIDs of locations with which patient is associated",
        example=["ea9fd397-6ff6-4b29-a4d2-c9d36bfa2737"],
    )
    readings_plans = fields.Nested(SimpleReadingsPlanSchema, many=True, required=True)


@openapi_schema(dhos_services_api_spec)
class ValidatePatientRequest(Schema):
    class Meta:
        description = "Validate patient request"
        unknown = EXCLUDE
        ordered = True

    first_name = fields.String(
        required=False,
        allow_none=True,
        description="Patient's first name",
        example="Joan",
    )
    last_name = fields.String(
        required=False,
        allow_none=True,
        description="Patient's last name",
        example="Speedwell",
    )
    hospital_number = fields.String(
        required=False,
        allow_none=True,
        description="Patient's hospital number (MRN)",
        example="232434",
    )
    dob = fields.String(
        required=False,
        allow_none=True,
        description="Patient's date of birth in ISO8601 format",
        example="1978-05-06",
    )


@openapi_schema(dhos_services_api_spec)
class FirstMedicationRequest(Schema):
    class Meta:
        description = "First medication request"
        unknown = EXCLUDE
        ordered = True

    first_medication_taken = fields.String(
        required=True,
        description="Patient's description of when the first medication was taken",
        example="3 days ago",
    )
    first_medication_taken_recorded = fields.String(
        required=True,
        description="ISO8601 date for the time at which the patient reported having first taken medication",
        example="2020-01-01",
    )


class DiabetesDiagnosisRequest(Schema):
    class Meta:
        description = "Diagnosis request"
        unknown = EXCLUDE
        ordered = True

    sct_code = fields.String(
        required=True, description="SNOMED code for the diagnosis", example="11687002"
    )
    diagnosis_other = fields.String(
        required=False,
        allow_none=True,
        description="Freetext field for diagnosis description",
        example="Diabetes type 4",
    )
    readings_plan = fields.Nested(ReadingsPlanRequest, required=False, allow_none=True)


class DiabetesRecordRequest(Schema):
    class Meta:
        description = "Diabetes Record request"
        unknown = EXCLUDE
        ordered = True

    diagnoses = fields.Nested(
        DiabetesDiagnosisRequest, many=True, required=False, allow_none=True
    )


class DiabetesDiagnosisResponse(Schema):
    class Meta:
        description = "Diagnosis request"
        unknown = EXCLUDE
        ordered = True

    sct_code = fields.String(
        required=True, description="SNOMED code for the diagnosis", example="11687002"
    )
    diagnosis_other = fields.String(
        required=False,
        allow_none=True,
        description="Freetext field for diagnosis description",
        example="Diabetes type 4",
    )
    readings_plan = fields.Nested(ReadingsPlanResponse, required=True, allow_none=True)


class DiabetesRecordResponse(Schema):
    class Meta:
        description = "Diabetes Record response"
        unknown = EXCLUDE
        ordered = True

    diagnoses = fields.Nested(
        DiabetesDiagnosisResponse, many=True, required=True, allow_none=False
    )


@openapi_schema(dhos_services_api_spec)
class PatientDiabetesResponse(Identifier):
    class Meta:
        description = "Patient diabetes request"
        unknown = EXCLUDE
        ordered = True

    first_name = fields.String(
        required=True,
        description="Patient's first name",
        example="Joan",
        allow_none=True,
    )
    last_name = fields.String(
        required=True,
        description="Patient's last name",
        example="Speedwell",
        allow_none=True,
    )
    hospital_number = fields.String(
        required=True, description="Patient's hospital number (MRN)", example="232434"
    )
    record = fields.Nested(DiabetesRecordResponse, required=True)
    dh_products = fields.Nested(
        DhDiabetesProductResponse, many=True, required=True, allow_none=False
    )
    dob = fields.String(
        required=False,
        allow_none=True,
        description="Patient's date of birth in ISO8601 format",
        example="1978-05-06",
    )
    dod = fields.String(
        required=False,
        allow_none=True,
        description="Patient's date of death in ISO8601 format",
        example="2020-01-01",
    )
    nhs_number = fields.String(
        required=False,
        allow_none=True,
        description="Patient's 10-digit NHS number",
        example="1111111111",
    )
    sex = fields.String(
        required=False,
        allow_none=True,
        description="SNOMED code for patient's sex",
        example="248152002",
    )
    locations = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="UUIDs of locations with which patient is associated",
        example=["ea9fd397-6ff6-4b29-a4d2-c9d36bfa2737"],
    )


@openapi_schema(dhos_services_api_spec)
class ActiveWeeklyPatientCountResponse(Schema):
    class Meta:
        description = "Active patient counts by week"
        unknown = EXCLUDE
        ordered = True

    year_week = fields.String(
        required=True,
        allow_none=True,
        description="The year and week that the data covers",
        example="2021-1",
    )
    count = fields.Integer(
        required=True,
        allow_none=True,
        description="Count of active patients",
        example=100,
    )


@openapi_schema(dhos_services_api_spec)
class DailyCreatedPatientCountsResponse(Schema):
    class Meta:
        description = "Daily created patient counts"
        unknown = EXCLUDE
        ordered = True

    date = fields.String(
        required=True,
        allow_none=True,
        description="The day data covers",
        example="2021-01-25",
    )
    count = fields.Integer(
        required=True,
        allow_none=True,
        description="Count of daily created patients",
        example=100,
    )
