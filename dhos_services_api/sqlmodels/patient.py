from __future__ import annotations

import functools
from typing import Any, Sequence

from flask_batteries_included.sqldb import db
from sqlalchemy import and_, true
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Load, Query, aliased, joinedload, subqueryload

from dhos_services_api import sqlmodels
from dhos_services_api.sqlmodels import DraysonHealthProduct
from dhos_services_api.sqlmodels.mixins import (
    ModelIdentifier,
    ValidationSchema,
    construct_children,
    construct_single_child,
)

_MARKER: Any = object()


def merge_schemas(x: ValidationSchema, y: ValidationSchema) -> ValidationSchema:
    merged = x.copy()

    merged["optional"].update(y["optional"])
    merged["required"].update(y["required"])
    merged["updatable"].update(y["updatable"])

    return merged


class Patient(ModelIdentifier, db.Model):
    __tablename__ = "patient"
    patient_type = db.Column(db.String)
    __mapper_args__ = {
        "polymorphic_on": patient_type,
        "polymorphic_identity": "patient",
    }
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    phone_number = db.Column(db.String, nullable=True)

    dob = db.Column(db.Date, nullable=True)
    dod = db.Column(db.Date, nullable=True)
    nhs_number = db.Column(db.String, nullable=True)
    hospital_number = db.Column(db.String, nullable=True)

    # Contact permissions
    allowed_to_text = db.Column(db.Boolean)
    allowed_to_email = db.Column(db.Boolean)

    # Contact
    email_address = db.Column(db.String, nullable=True)
    personal_addresses = db.relationship(
        "PersonalAddress", cascade="all, delete-orphan"
    )

    # Demographics
    ethnicity = db.Column(db.String, nullable=True)
    ethnicity_other = db.Column(db.String, nullable=True)

    # Sex SNOMED codes
    sex = db.Column(db.String, nullable=True)

    height_in_mm = db.Column(db.Integer, nullable=True)
    weight_in_g = db.Column(db.Integer, nullable=True)

    highest_education_level = db.Column(db.String, nullable=True)
    highest_education_level_other = db.Column(db.String, nullable=True)

    # Notes
    accessibility_considerations: list[str] = db.Column(
        db.JSON, default=[], nullable=False
    )
    accessibility_considerations_other = db.Column(db.String, nullable=True)

    other_notes = db.Column(db.String, nullable=True)
    locations = db.Column(postgresql.ARRAY(db.String), default=[])
    bookmarked_at_locations = db.Column(postgresql.ARRAY(db.String), default=[])
    has_been_bookmarked = db.Column(db.Boolean, default=False)

    @property
    def bookmarked(self) -> bool:
        return len(self.bookmarked_at_locations) > 0

    # Related notes
    record_id = db.Column(
        db.String, db.ForeignKey("record.uuid", ondelete="CASCADE"), nullable=True
    )
    record = db.relationship(
        "Record",
        back_populates="patient",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    # Note: Verify this has moved entirely to dhos-users-api
    # clinician_bookmarks = RelationshipTo(".clinician.Clinician", "BOOKMARKED_BY")

    # Products patient is attached to
    dh_products = db.relationship(
        "DraysonHealthProduct", backref="patient", cascade="all, delete-orphan"
    )

    terms_agreement = db.relationship(
        "TermsAgreement",
        cascade="all, delete-orphan",
        order_by="func.coalesce(TermsAgreement.patient_notice_version,0).desc(),"
        "func.coalesce(TermsAgreement.tou_version,0).desc(),"
        "func.coalesce(TermsAgreement.version,0).desc()",
    )

    parent_patient_id = db.Column(
        db.String, db.ForeignKey("patient.uuid", ondelete="SET NULL")
    )
    child_of = db.relationship("Patient", remote_side="Patient.uuid", uselist=False)

    fhir_resource_id = db.Column(db.String, nullable=True)

    __table_args__ = (
        db.Index(
            "nhs_number_unique_index",
            "nhs_number",
            unique=True,
            postgresql_where=and_(nhs_number != None, patient_type == "send"),
        ),
        db.Index(
            "hospital_number_unique_index",
            "hospital_number",
            unique=True,
            postgresql_where=and_(hospital_number != None, patient_type == "send"),
        ),
    )

    @property
    def patient_uuid(self) -> str:
        return self.uuid

    @classmethod
    def new(
        cls,
        *,
        record: dict | sqlmodels.Record | None = None,
        dh_products: Sequence[dict[str, object] | sqlmodels.DraysonHealthProduct]
        | None = None,
        personal_addresses: Sequence[dict[str, object] | sqlmodels.PersonalAddress]
        | None = None,
        accessibility_considerations: list[str] | None = None,
        **kw: Any,
    ) -> "Patient":
        with db.session.no_autoflush:
            self = cls(
                record=construct_single_child(record, sqlmodels.Record),
                dh_products=construct_children(
                    dh_products, sqlmodels.DraysonHealthProduct
                ),
                personal_addresses=construct_children(
                    personal_addresses, sqlmodels.PersonalAddress
                ),
                accessibility_considerations=accessibility_considerations or [],
                **kw,
            )
            db.session.add(self)

        return self

    @classmethod
    def patient_validate_schema(cls) -> ValidationSchema:
        # ** This is used by the /patient/validate endpoint **
        # TODO this probably needs a better place to live...
        return {
            "required": {},
            "optional": {
                "hospital_number": str,
                "first_name": str,
                "last_name": str,
                "dob": str,
            },
            "updatable": {},
        }

    @classmethod
    def shared_schema(cls) -> ValidationSchema:
        return {
            "optional": {
                "allowed_to_email": bool,
                "ethnicity_other": str,
                "highest_education_level": str,
                "highest_education_level_other": str,
                "accessibility_considerations": [str],
                "accessibility_considerations_other": str,
                "personal_addresses": [dict],
                "ethnicity": str,
                "nhs_number": str,
                "other_notes": str,
                "height_in_mm": int,
                "weight_in_g": int,
            },
            "required": {
                "first_name": str,
                "last_name": str,
                "hospital_number": str,
                "record": dict,
            },
            "updatable": {
                "first_name": str,
                "last_name": str,
                "phone_number": str,
                "dob": str,
                "dod": str,
                "nhs_number": str,
                "hospital_number": str,
                "allowed_to_text": bool,
                "allowed_to_email": bool,
                "email_address": str,
                "personal_addresses": [dict],
                "ethnicity": str,
                "sex": str,
                "height_in_mm": int,
                "weight_in_g": int,
                "highest_education_level": str,
                "highest_education_level_other": str,
                "record": dict,
                "locations": [str],
                "dh_products": [dict],
                "ethnicity_other": str,
                "accessibility_considerations": [str],
                "accessibility_considerations_other": str,
                "other_notes": str,
            },
        }

    @classmethod
    def gdm_exclusive_schema(cls) -> ValidationSchema:
        return {
            "optional": {"dod": str, "fhir_resource_id": str},
            "required": {
                "phone_number": str,
                "dob": str,
                "allowed_to_text": bool,
                "email_address": str,
                "sex": str,
                "locations": [str],
                "dh_products": [dict],
            },
            "updatable": {"fhir_resource_id": str},
        }

    @classmethod
    def gdm_schema(cls) -> ValidationSchema:
        return merge_schemas(cls.shared_schema(), cls.gdm_exclusive_schema())

    @classmethod
    def send_dod_exclusive_schema(cls) -> ValidationSchema:
        return {
            "optional": {
                "dod": str,
            },
            "required": {},
            "updatable": {},
        }

    @classmethod
    def send_dod_schema(cls) -> ValidationSchema:
        return merge_schemas(cls.send_schema(), cls.send_dod_exclusive_schema())

    @classmethod
    def send_exclusive_schema(cls) -> ValidationSchema:
        return {
            "optional": {
                "phone_number": str,
                "dob": str,
                "hospital_number": str,
                "allowed_to_text": bool,
                "email_address": str,
                "sex": str,
                "locations": [str],
                "dh_products": [dict],
                "child_of": str,
            },
            "required": {},
            "updatable": {},
        }

    @classmethod
    def send_schema(cls) -> ValidationSchema:
        return merge_schemas(cls.shared_schema(), cls.send_exclusive_schema())

    @property
    def _latest_terms_agreement(self) -> "sqlmodels.TermsAgreement | None":
        """
        terms_agreement is sorted descending with nulls at end so just return the first
        element or None if no elements.
        """
        terms_agreements = self.terms_agreement[:1]
        if not terms_agreements:
            return None
        return terms_agreements[0]

    def recursive_patch(
        self,
        *,
        record: dict | None = None,
        personal_addresses: list[dict] | None = None,
        dh_products: list[dict] | None = None,
        **kwargs: object,
    ) -> None:
        super().recursive_patch(**kwargs)
        if record:
            sqlmodels.Record.patch_or_add(
                self.record, record, {"patient_id": self.uuid}
            )
        if personal_addresses:
            sqlmodels.PersonalAddress.patch_related_objects(
                related_column=sqlmodels.PersonalAddress.patient_id,
                parent_id=self.uuid,
                patch_data=personal_addresses,
            )
        if dh_products:
            sqlmodels.DraysonHealthProduct.patch_related_objects(
                related_column=sqlmodels.DraysonHealthProduct.patient_id,
                parent_id=self.uuid,
                patch_data=dh_products,
            )

    # 'active_only=True' returns True if patient is active on product
    def has_product(self, product_name: str, active_only: bool = False) -> bool:
        for product in self.dh_products:
            if product.product_name == product_name and (
                product.closed_date is None or not active_only
            ):
                return True
        return False


class Baby(Patient):
    __mapper_args__ = {
        "polymorphic_identity": "baby",
    }


class SendPatient(Patient):
    __mapper_args__ = {
        "polymorphic_identity": "send",
    }


@functools.cache
def query_options_full_patient_response() -> list[Load]:
    """Preload response data for a query that returns a PatientResponse"""
    record = joinedload(Patient.record)
    notes = record.subqueryload(sqlmodels.Record.notes)
    diagnoses = record.subqueryload(sqlmodels.Record.diagnoses)
    observable_entities = diagnoses.subqueryload(
        sqlmodels.Diagnosis.observable_entities
    )
    management_plan = diagnoses.subqueryload(sqlmodels.Diagnosis.management_plan)
    management_plan_actions = management_plan.subqueryload(
        sqlmodels.ManagementPlan.actions
    )
    management_plan_doses = management_plan.subqueryload(
        sqlmodels.ManagementPlan.doses
    ).joinedload(sqlmodels.Dose.changes)
    management_plan_dose_history = (
        management_plan.subqueryload(sqlmodels.ManagementPlan.dose_history)
        .joinedload(sqlmodels.DoseHistory.dose)
        .joinedload(sqlmodels.Dose.changes)
    )
    readings_plan_with_changes = diagnoses.subqueryload(
        sqlmodels.Diagnosis.readings_plan
    ).joinedload(sqlmodels.ReadingsPlan.changes)
    pregnancies = record.subqueryload(sqlmodels.Record.pregnancies)
    deliveries = pregnancies.subqueryload(sqlmodels.Pregnancy.deliveries).joinedload(
        sqlmodels.Delivery.patient
    )
    visits = record.subqueryload(sqlmodels.Record.visits)
    history = record.joinedload(sqlmodels.Record.history)

    dh_products = subqueryload(Patient.dh_products).joinedload(
        sqlmodels.DraysonHealthProduct.changes
    )
    addresses = subqueryload(Patient.personal_addresses)
    terms_agreement = subqueryload(Patient.terms_agreement)

    options: list[Load] = [
        notes,
        diagnoses,
        observable_entities,
        management_plan,
        management_plan_actions,
        management_plan_doses,
        management_plan_dose_history,
        readings_plan_with_changes,
        pregnancies,
        deliveries,
        visits,
        history,
        dh_products,
        addresses,
        terms_agreement,
    ]
    return options


@functools.cache
def query_options_compact_patient_response() -> list[Load]:
    """Preload response data for a query that returns a CompactPatientResponse"""
    record = joinedload(Patient.record)
    diagnoses = record.subqueryload(sqlmodels.Record.diagnoses)
    management_plan = diagnoses.subqueryload(sqlmodels.Diagnosis.management_plan)
    pregnancies = record.subqueryload(sqlmodels.Record.pregnancies)
    deliveries = pregnancies.subqueryload(sqlmodels.Pregnancy.deliveries).joinedload(
        sqlmodels.Delivery.patient
    )
    dh_products = subqueryload(Patient.dh_products)
    options: list[Load] = [
        record,
        diagnoses,
        management_plan,
        pregnancies,
        deliveries,
        dh_products,
    ]
    return options


@functools.cache
def query_options_patient_list() -> list[Load]:
    """Preload response data for a query that returns a PatientDiabetesResponse"""
    record = joinedload(Patient.record)
    diagnoses = record.subqueryload(sqlmodels.Record.diagnoses)
    readings_plan_with_changes = diagnoses.subqueryload(
        sqlmodels.Diagnosis.readings_plan
    ).joinedload(sqlmodels.ReadingsPlan.changes)
    dh_products = subqueryload(Patient.dh_products)

    options: list[Load] = [record, diagnoses, readings_plan_with_changes, dh_products]
    return options


def query_top_level_patients(query: Query) -> Query:
    """
    Given an existing query for patients matching a condition,
    return a query for the top level patients which matched the query directly
    or where a child matched the query.
    """
    cte = query.cte("base")
    hierarchy = (
        db.session.query(
            cte.c.uuid.label("uuid"),
            Patient.parent_patient_id.label("parent_patient_id"),
        ).join(Patient, Patient.uuid == cte.c.uuid)
    ).cte(name="hierarchy", recursive=True)

    child = aliased(hierarchy, name="c")
    parent = aliased(Patient, name="p")
    hierarchy = hierarchy.union_all(
        db.session.query(parent.uuid, parent.parent_patient_id).filter(
            child.c.parent_patient_id == parent.uuid
        )
    )
    parents = (
        db.session.query(hierarchy.c.uuid).filter(hierarchy.c.parent_patient_id == None)
    ).subquery(name="parents")

    parent_query = db.session.query(Patient).join(
        parents, Patient.uuid == parents.c.uuid
    )
    return parent_query


def filter_patient_active_on_product(
    product_name: str, active_only: bool = False
) -> Any:
    return Patient.dh_products.any(
        and_(
            DraysonHealthProduct.product_name == product_name,
            DraysonHealthProduct.closed_date == None if active_only else true(),
        )
    )
