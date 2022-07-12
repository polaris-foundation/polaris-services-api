import datetime
from typing import Any, Dict, List, Optional, Union

from flask_batteries_included.helpers.timestamp import (
    parse_date_to_iso8601,
    parse_iso8601_to_date,
)
from neomodel import (
    ArrayProperty,
    BooleanProperty,
    DateProperty,
    IntegerProperty,
    One,
    RelationshipTo,
    StringProperty,
    StructuredNode,
    ZeroOrMore,
    ZeroOrOne,
)

import dhos_services_api.models.record
from dhos_services_api.helpers.neo_utils import get_node_or_404
from dhos_services_api.helpers.responses import (
    QueryResponse,
    response_to_dict,
    validate_identity,
)
from dhos_services_api.models.drayson_health_product import DraysonHealthProduct
from dhos_services_api.models.mixins.user import UserMixin
from dhos_services_api.models.personal_address import PersonalAddress
from dhos_services_api.models.record import Record
from dhos_services_api.models.terms_agreement import TermsAgreement
from dhos_services_api.neodb import NeomodelIdentifier

_MARKER: Any = object()


def _latest_terms_agreement(terms_aggreements: List[TermsAgreement]) -> Optional[Dict]:
    if not terms_aggreements:
        return None

    sorted_terms = sorted(
        terms_aggreements,
        key=lambda x: (
            getattr(x, "patient_notice_version") or -1,
            getattr(x, "tou_version") or -1,
            getattr(x, "version") or -1,
        ),
        reverse=True,
    )
    return sorted_terms[0].to_dict()


def merge_schemas(
    x: Dict[str, Dict[str, Any]], y: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:

    merged = x.copy()
    merged["optional"].update(y["optional"])
    merged["required"].update(y["required"])
    merged["updatable"].update(y["updatable"])

    return merged


class Patient(NeomodelIdentifier, UserMixin, StructuredNode):
    # Identity
    dob_ = DateProperty(db_property="dob")
    dod_ = DateProperty(db_property="dod")

    nhs_number = StringProperty()
    hospital_number = StringProperty()

    # Contact permissions
    allowed_to_text = BooleanProperty()
    allowed_to_email = BooleanProperty()

    # Contact
    email_address = StringProperty()
    personal_addresses = RelationshipTo(
        ".personal_address.PersonalAddress", "HAS_PERSONAL_ADDRESS"
    )

    # Demographics
    ethnicity = StringProperty()
    ethnicity_other = StringProperty()

    # Sex SNOMED codes
    sex = StringProperty()

    height_in_mm = IntegerProperty()
    weight_in_g = IntegerProperty()

    highest_education_level = StringProperty()
    highest_education_level_other = StringProperty()

    # Notes
    accessibility_considerations = ArrayProperty(StringProperty(), default=[])
    accessibility_considerations_other = StringProperty()

    other_notes = StringProperty()  # TODO: seriously?
    locations: List[str] = ArrayProperty(StringProperty(), default=[])
    bookmarked_at_locations: List[str] = ArrayProperty(StringProperty(), default=[])
    has_been_bookmarked = BooleanProperty(default=False)

    # Related notes
    record = RelationshipTo(".record.Record", "HAS_RECORD", cardinality=One)

    # Products patient is attached to
    dh_products = RelationshipTo(DraysonHealthProduct, "ACTIVE_ON_PRODUCT")

    terms_agreement = RelationshipTo(
        ".terms_agreement.TermsAgreement", "HAS_ACCEPTED", cardinality=ZeroOrMore
    )

    child_of = RelationshipTo(".patient.Patient", "CHILD_OF", cardinality=ZeroOrOne)
    fhir_resource_id = StringProperty()

    @classmethod
    def patient_validate_schema(cls) -> Dict:
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
    def shared_schema(cls) -> Dict[str, Dict[str, Any]]:
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
    def gdm_exclusive_schema(cls) -> Dict[str, Dict[str, Any]]:
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
    def gdm_schema(cls) -> Dict[str, Dict[str, Any]]:
        return merge_schemas(cls.shared_schema(), cls.gdm_exclusive_schema())

    @classmethod
    def send_dod_exclusive_schema(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "optional": {
                "dod": str,
            },
            "required": {},
            "updatable": {},
        }

    @classmethod
    def send_dod_schema(cls) -> Dict[str, Dict[str, Any]]:
        return merge_schemas(cls.send_schema(), cls.send_dod_exclusive_schema())

    @classmethod
    def send_exclusive_schema(cls) -> Dict[str, Dict[str, Any]]:
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
    def send_schema(cls) -> Dict[str, Dict[str, Any]]:
        return merge_schemas(cls.shared_schema(), cls.send_exclusive_schema())

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> Union["Baby", "Patient", "SendPatient"]:

        if (
            "accessibility_considerations" in kwargs
            and not kwargs["accessibility_considerations"]
        ):
            kwargs["accessibility_considerations"] = []

        products = [
            DraysonHealthProduct.new(**prod) for prod in kwargs.pop("dh_products", [])
        ]
        personal_addresses = [
            PersonalAddress.new(**addr) for addr in kwargs.pop("personal_addresses", [])
        ]

        record = dhos_services_api.models.record.Record.new(**kwargs.pop("record", {}))

        dob = kwargs.get("dob", None)

        if dob:
            dob_dt = parse_iso8601_to_date(dob)
            on_gdm = len(list(filter(lambda x: x.product_name == "GDM", products))) > 0
            if dob_dt is None or (
                on_gdm
                and datetime.date.today() - datetime.timedelta(days=365.25 * 16)
                < dob_dt
            ):
                raise ValueError("patient must be over 16 years old")

        child_of = kwargs.pop("child_of", None)

        obj = cls(*args, **kwargs)
        obj.save()

        # connect record to patient
        obj.record.connect(record)

        # connect dh products to patient
        for product in products:
            product.save()
            obj.dh_products.connect(product)

        # connect personal addresses to patient
        for address in personal_addresses:
            address.save()
            obj.personal_addresses.connect(address)

        if child_of:
            parent_patient = get_node_or_404(Patient, uuid=child_of)
            obj.child_of.connect(parent_patient)

        return obj

    def on_patch(self, _json: Dict[str, Any] = None, *args: Any, **kwargs: Any) -> None:

        if _json is None:
            return

        super(Patient, self).on_patch(_json, **kwargs)

        if _json.get("highest_education_level", None) != "365460000":
            _json.pop("highest_education_level_other", None)
            self.highest_education_level_other = None

        if _json.get("ethnicity", None) != "186023009":
            _json.pop("ethnicity_other", None)
            self.ethnicity_other = None
        else:
            self.ethnicity_other = _json.pop("ethnicity_other", "")

        if "D0000032" not in _json.get("accessibility_considerations", []):
            _json.pop("accessibility_considerations_other", None)
            self.accessibility_considerations_other = None

    @property
    def dob(self) -> Optional[str]:
        return parse_date_to_iso8601(self.dob_)

    @dob.setter
    def dob(self, value: Optional[str]) -> None:
        self.dob_ = parse_iso8601_to_date(value)

    @property
    def dod(self) -> Optional[str]:
        return parse_date_to_iso8601(self.dod_)

    @dod.setter
    def dod(self, value: Optional[str]) -> None:
        self.dod_ = parse_iso8601_to_date(value)

    @property
    def bookmarked(self) -> bool:
        return len(self.bookmarked_at_locations) > 0

    # 'active_only=True' returns True if patient is active on product
    def has_product(self, product_name: str, active_only: bool = False) -> bool:
        for product in self.dh_products:
            if product.product_name == product_name:
                if active_only:
                    if product.closed_date is None:
                        return True
                else:
                    return True
        return False

    def to_dict_no_relations(
        self,
        personal_addresses: List[Dict] = None,
        record: Dict = None,
        dh_products: List[Dict] = None,
        bookmarked: bool = None,
        terms_agreement: List[Dict] = None,
    ) -> Dict:

        result: Dict = {
            "allowed_to_text": self.allowed_to_text,
            "allowed_to_email": self.allowed_to_email,
            "dob": self.dob,
            "dod": self.dod,
            "nhs_number": self.nhs_number,
            "hospital_number": self.hospital_number,
            "email_address": self.email_address,
            "personal_addresses": personal_addresses,
            "ethnicity": self.ethnicity,
            "ethnicity_other": self.ethnicity_other,
            "sex": self.sex,
            "height_in_mm": self.height_in_mm,
            "weight_in_g": self.weight_in_g,
            "highest_education_level": self.highest_education_level,
            "highest_education_level_other": self.highest_education_level_other,
            "accessibility_considerations": self.accessibility_considerations,
            "accessibility_considerations_other": self.accessibility_considerations_other,
            "other_notes": self.other_notes,
            "record": record,
            "locations": self.locations,
            "bookmarked": bookmarked,
            "has_been_bookmarked": self.has_been_bookmarked,
            "dh_products": dh_products,
            "terms_agreement": terms_agreement,
            "fhir_resource_id": self.fhir_resource_id,
            **self.pack_user(),
            **self.pack_identifier(),
        }
        return result

    def to_dict(self) -> Dict[str, Any]:

        return {
            "allowed_to_text": self.allowed_to_text,
            "allowed_to_email": self.allowed_to_email,
            "dob": self.dob,
            "dod": self.dod,
            "nhs_number": self.nhs_number,
            "hospital_number": self.hospital_number,
            "email_address": self.email_address,
            "personal_addresses": [addr.to_dict() for addr in self.personal_addresses],
            "ethnicity": self.ethnicity,
            "ethnicity_other": self.ethnicity_other,
            "sex": self.sex,
            "height_in_mm": self.height_in_mm,
            "weight_in_g": self.weight_in_g,
            "highest_education_level": self.highest_education_level,
            "highest_education_level_other": self.highest_education_level_other,
            "accessibility_considerations": self.accessibility_considerations,
            "accessibility_considerations_other": self.accessibility_considerations_other,
            "other_notes": self.other_notes,
            "record": self.record.single().to_dict(),
            "locations": self.locations,
            "bookmarked": bool(self.bookmarked),
            "has_been_bookmarked": self.has_been_bookmarked,
            "dh_products": [prod.to_dict() for prod in self.dh_products],
            "terms_agreement": _latest_terms_agreement(self.terms_agreement.all()),
            "fhir_resource_id": self.fhir_resource_id,
            **self.pack_user(),
            **self.pack_identifier(),
        }

    def to_compact_dict(
        self,
        personal_addresses: List[Dict] = None,
        record: Optional[Dict] = _MARKER,
        dh_products: Optional[List[Dict]] = _MARKER,
        bookmarked: Optional[bool] = _MARKER,
        terms_agreement: List[Dict] = None,
    ) -> Dict:
        if dh_products is _MARKER:
            dh_products = [prod.to_compact_dict() for prod in self.dh_products]

        if bookmarked is _MARKER:
            bookmarked = bool(self.bookmarked)

        if record is _MARKER:
            record = self.record.single().to_compact_dict()

        return {
            "dob": self.dob,
            "nhs_number": self.nhs_number,
            "hospital_number": self.hospital_number,
            "sex": self.sex,
            "record": record,
            "bookmarked": bookmarked,
            "dh_products": dh_products,
            "locations": self.locations,
            "fhir_resource_id": self.fhir_resource_id,
            **self.compack_user(),
            **self.compack_identifier(),
        }

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        return response_to_dict(
            cls,
            response,
            primary="patient",
            single={"record": Record},
            multiple={
                "personal_addresses": PersonalAddress,
                "dh_products": DraysonHealthProduct,
            },
            custom={"bookmarked": validate_identity},
            method=method,
        )

    @classmethod
    def convert_response_to_compact_dict(cls, response: QueryResponse) -> Dict:
        return response_to_dict(
            cls,
            response,
            primary="patient",
            single={"record": Record},
            multiple={"dh_products": DraysonHealthProduct},
            custom={"bookmarked": validate_identity},
            method="to_compact_dict",
        )


class Baby(Patient):
    @classmethod
    def gdm_schema(cls) -> Dict:
        return {
            "optional": {
                "first_name": str,
                "last_name": str,
                "ethnicity_other": str,
                "highest_education_level_other": str,
                "accessibility_considerations": str,
                "other_notes": str,
                "phone_number": str,
                "dob": str,
                "nhs_number": str,
                "hospital_number": str,
                "allowed_to_text": bool,
                "allowed_to_email": bool,
                "email_address": str,
                "personal_addresses": [dict],
                "ethnicity": str,
                "sex": str,
                "highest_education_level": str,
                "record": dict,
                "locations": [str],
                "dh_products": [dict],
            },
            "required": {},
            "updatable": {
                "first_name": str,
                "last_name": str,
                "phone_number": str,
                "dob": str,
                "nhs_number": str,
                "hospital_number": str,
                "allowed_to_text": bool,
                "email_address": str,
                "personal_addresses": [dict],
                "ethnicity": str,
                "sex": str,
                "highest_education_level": str,
                "record": dict,
                "locations": [str],
                "dh_products": [dict],
                "ethnicity_other": str,
                "highest_education_level_other": str,
                "accessibility_considerations": str,
                "other_notes": str,
            },
        }

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "sex": self.sex,
            "dob": self.dob,
            **self.pack_user(),
            **self.pack_identifier(),
        }

    def to_dict_no_relations(
        self,
        personal_addresses: List[Dict] = None,
        record: Dict = None,
        dh_products: List[Dict] = None,
        bookmarked: bool = None,
        terms_agreement: List[Dict] = None,
    ) -> Dict:
        return self.to_dict()

    def to_compact_dict(
        self,
        personal_addresses: List[Dict] = None,
        record: Optional[Dict] = _MARKER,
        dh_products: Optional[List[Dict]] = _MARKER,
        bookmarked: Optional[bool] = _MARKER,
        terms_agreement: List[Dict] = None,
    ) -> Dict:
        return {"dob": self.dob, **self.compack_identifier()}

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        return response_to_dict(cls, response, primary="baby", method=method)


class SendPatient(Patient):
    nhs_number = StringProperty(unique_index=True, required=False)
    hospital_number = StringProperty(unique_index=True, required=False)
