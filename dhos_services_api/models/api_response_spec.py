from marshmallow import EXCLUDE, Schema, fields

from dhos_services_api.models.api_spec import (
    BabyResponse,
    BaseProductSchema,
    DeliveryRequest,
    DiagnosisRequest,
    PatientRequest,
    PregnancyRequest,
)


class CompactIdentifier(Schema):
    uuid = fields.String(
        required=True,
        metadata={
            "description": "Universally unique identifier for object",
            "example": "2c4f1d24-2952-4d4e-b1d1-3637e33cc161",
        },
    )
    created = fields.DateTime(
        metadata={
            "description": "When the object was created",
            "example": "2017-09-23T08:29:19.123+00:00",
        }
    )


class CompactManagementPlanResponse(Schema):
    class Meta:
        description = "Management plan response"
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


class CompactDiagnosisResponse(CompactIdentifier, DiagnosisRequest):
    class Meta:
        description = "Diagnosis response"
        unknown = EXCLUDE
        ordered = True

    management_plan = fields.Nested(
        CompactManagementPlanResponse, required=False, allow_none=True
    )


class CompactDeliveryResponse(CompactIdentifier, DeliveryRequest):
    class Meta:
        description = "Delivery response"
        unknown = EXCLUDE
        ordered = True

    patient = fields.Nested(BabyResponse, required=False, allow_none=True)


class CompactPregnancyResponse(PregnancyRequest, CompactIdentifier):
    class Meta:
        description = "Pregnancy response"
        unknown = EXCLUDE
        ordered = True

    deliveries = fields.Nested(
        CompactDeliveryResponse, many=True, required=False, allow_none=True
    )


class CompactRecordResponse(CompactIdentifier):
    class Meta:
        description = "Compact Record response"
        unknown = EXCLUDE
        ordered = True

    diagnoses = fields.Nested(
        CompactDiagnosisResponse, many=True, required=True, allow_none=False
    )
    pregnancies = fields.Nested(
        CompactPregnancyResponse, many=True, required=True, allow_none=False
    )


class CompactDhProductResponse(BaseProductSchema):
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


class CompactPatientResponse(CompactIdentifier, PatientRequest):
    class Meta:
        description = "Compact Patient response"
        unknown = EXCLUDE
        ordered = True

    dob = fields.String(
        required=False,
        allow_none=True,
        description="Patient's date of birth in ISO8601 format",
        example="1978-05-06",
    )
    nhs_number = fields.String(
        required=False,
        allow_none=True,
        description="Patient's 10-digit NHS number",
        example="1111111111",
    )
    hospital_number = fields.String(
        required=True,
        description="Patient's hospital number (MRN)",
        example="232434",
        allow_none=True,
    )
    sex = fields.String(
        required=False,
        allow_none=True,
        description="SNOMED code for patient's sex",
        example="248152002",
    )
    record = fields.Nested(CompactRecordResponse, required=True)
    bookmarked = fields.Boolean(
        required=False,
        allow_none=True,
        description="Whether patient is bookmarked",
        example=False,
    )
    locations = fields.List(
        fields.String(),
        required=False,
        allow_none=True,
        description="UUIDs of locations with which patient is associated",
        example=["ea9fd397-6ff6-4b29-a4d2-c9d36bfa2737"],
    )
    dh_products = fields.Nested(
        CompactDhProductResponse, many=True, required=False, allow_none=True
    )
    fhir_resource_id = fields.String(
        required=False,
        allow_none=True,
        description="Patient's ID in a trustomer's FHIR EPR system (null if the patient is not presented there)",
        example="ea9fd397-6ff6-4b29-a4d2-c9d36bfa2737",
    )
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
