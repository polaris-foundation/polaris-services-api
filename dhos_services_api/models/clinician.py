import codecs
import itertools
import string
from typing import Any, Dict, List, Optional

from Cryptodome.Protocol.KDF import scrypt
from Cryptodome.Random import random as crr
from flask_batteries_included.helpers.timestamp import (
    parse_date_to_iso8601,
    parse_iso8601_to_date,
)
from neomodel import (
    ArrayProperty,
    BooleanProperty,
    DateProperty,
    EmailProperty,
    OneOrMore,
    RelationshipFrom,
    RelationshipTo,
    StringProperty,
    StructuredNode,
    ZeroOrMore,
)
from she_logging import logger

from dhos_services_api.helpers.responses import QueryResponse, response_to_dict
from dhos_services_api.models.drayson_health_product import ClinicianProduct
from dhos_services_api.models.mixins.user import UserMixin
from dhos_services_api.neodb import NeomodelIdentifier


class Clinician(NeomodelIdentifier, UserMixin, StructuredNode):

    nhs_smartcard_number = StringProperty()
    send_entry_identifier = StringProperty()
    job_title = StringProperty()
    email_address = EmailProperty()
    can_edit_ews = BooleanProperty(default=False)

    professional_registration_number = StringProperty()
    agency_name = StringProperty()
    agency_staff_employee_number = StringProperty()
    booking_reference = StringProperty()

    contract_expiry_eod_date_ = DateProperty(db_property="contract_expiry_eod_date")

    locations: List[str] = ArrayProperty(StringProperty(), default=[])
    products = RelationshipTo(
        ClinicianProduct, "ACTIVE_ON_PRODUCT", cardinality=OneOrMore
    )

    terms_agreement = RelationshipTo(
        ".terms_agreement.TermsAgreement", "HAS_ACCEPTED", cardinality=ZeroOrMore
    )

    groups = ArrayProperty(StringProperty(), default=[])

    password_hash = StringProperty()
    password_salt = StringProperty()

    login_active = BooleanProperty(default=True)

    bookmarks: List[str] = ArrayProperty(StringProperty(), default=[])
    bookmarked_patients = RelationshipFrom(".patient.Patient", "BOOKMARKED_BY")

    analytics_consent = BooleanProperty()
    can_edit_encounter = BooleanProperty()

    @property
    def contract_expiry_eod_date(self) -> Optional[str]:
        return parse_date_to_iso8601(self.contract_expiry_eod_date_)

    @contract_expiry_eod_date.setter
    def contract_expiry_eod_date(self, v: Optional[str]) -> None:
        self.contract_expiry_eod_date_ = parse_iso8601_to_date(v)

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "Clinician":

        products = kwargs.pop("products", [])

        obj = cls(*args, **kwargs)
        obj.save()

        for product in products:
            product = ClinicianProduct.new(**product)
            product.save()
            obj.products.connect(product)

        return obj

    @classmethod
    def schema(cls) -> Dict:
        return {
            "optional": {
                "login_active": bool,
                "contract_expiry_eod_date": str,
                "send_entry_identifier": str,
                "bookmarks": [str],
                "bookmarked_patients": [str],
                "can_edit_ews": bool,
                "can_edit_encounter": bool,
                "professional_registration_number": str,
                "agency_name": str,
                "agency_staff_employee_number": str,
                "email_address": str,
                "booking_reference": str,
                "analytics_consent": bool,
            },
            "required": {
                "first_name": str,
                "last_name": str,
                "phone_number": str,
                "job_title": str,
                "nhs_smartcard_number": str,
                "locations": [str],
                "groups": [str],
                "products": [dict],
            },
            "updatable": {
                "first_name": str,
                "last_name": str,
                "job_title": str,
                "login_active": bool,
                "contract_expiry_eod_date": str,
                "phone_number": str,
                "nhs_smartcard_number": str,
                "send_entry_identifier": str,
                "email_address": str,
                "locations": [str],
                "groups": [str],
                "products": [dict],
                "bookmarks": [str],
                "can_edit_ews": bool,
                "can_edit_encounter": bool,
                "professional_registration_number": str,
                "agency_name": str,
                "agency_staff_employee_number": str,
                "booking_reference": str,
                "analytics_consent": bool,
            },
        }

    def _latest_terms_agreement_by_product(self) -> Dict[str, Dict]:
        """
        Returns a dictionary mapping product name to TermsAgreement (as a dict).
        For each product the TermsAgreement that is used is the one with the highest
        version number.

        Only products where the clinician has agreed to terms are included in the dict.
        """
        tos = itertools.groupby(
            sorted(
                self.terms_agreement.all(),
                key=lambda x: (x.product_name, x.version),
                reverse=True,
            ),
            key=lambda x: x.product_name,
        )
        return {k: next(g).to_dict() for k, g in tos}

    def generate_secure_random_string(self, length: int = 10) -> str:
        if length < 3:
            raise ValueError("Cannot generate a secure random string of length < 3")
        return "".join(
            [
                str(crr.choice(string.ascii_uppercase + string.digits))
                for _ in range(length)
            ]
        )

    def generate_password_hash(self, password: str) -> str:
        if not self.password_salt:
            raise RuntimeError("Password_salt does not exist")
        code_bytes = bytes(password, "utf8")
        salt_bytes = bytes(self.password_salt, "utf8")
        _hash: bytes = scrypt(code_bytes, salt_bytes, 256, 16384, 8, 1)  # type: ignore
        return codecs.encode(_hash, "hex_codec").decode()

    def set_password(self, password: str) -> None:
        self.password_salt = self.generate_secure_random_string(32)
        self.password_hash = self.generate_password_hash(password)

    def validate_password(self, password: str) -> bool:
        if not self.password_salt or not self.password_hash:
            logger.warning(
                "Login for clinician %s attempted prior to password generation",
                self.uuid,
            )
            return False

        if self.generate_password_hash(password) == self.password_hash:
            return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        analytics_consent = {}
        if self.analytics_consent is not None:
            analytics_consent = {"analytics_consent": self.analytics_consent}

        return {
            "job_title": self.job_title,
            "send_entry_identifier": self.send_entry_identifier,
            "nhs_smartcard_number": self.nhs_smartcard_number,
            "professional_registration_number": self.professional_registration_number,
            "agency_name": self.agency_name,
            "agency_staff_employee_number": self.agency_staff_employee_number,
            "email_address": self.email_address,
            "locations": self.locations,
            "bookmarks": self.bookmarks,
            "bookmarked_patients": [p.uuid for p in self.bookmarked_patients],
            "terms_agreement": self._latest_terms_agreement_by_product(),
            "login_active": self.login_active,
            "groups": self.groups,
            "products": [p.to_dict() for p in self.products],
            "can_edit_ews": self.can_edit_ews,
            "can_edit_encounter": self.can_edit_encounter,
            "contract_expiry_eod_date": self.contract_expiry_eod_date,
            **analytics_consent,
            **self.pack_identifier(),
            **self.pack_user(),
        }

    def to_compact_dict(self) -> Dict[str, str]:
        return {
            "job_title": self.job_title,
            "email_address": self.email_address,
            "first_name": self.first_name,
            "last_name": self.last_name,
            **self.compack_identifier(),
        }

    def to_dict_no_relations(self) -> Dict:
        return self.to_compact_dict()

    def to_auth_dict(self) -> Dict[str, Any]:
        return {
            "job_title": self.job_title,
            "send_entry_identifier": self.send_entry_identifier,
            "locations": self.locations,
            "login_active": self.login_active,
            "contract_expiry_eod_date": self.contract_expiry_eod_date,
            "groups": self.groups,
            "products": [p.to_dict() for p in self.products],
            **self.pack_identifier(),
        }

    def to_login_dict(self) -> Dict[str, Any]:

        return {
            "job_title": self.job_title,
            "email_address": self.email_address,
            "user_id": self.uuid,
            "groups": self.groups,
            "products": [p.to_dict() for p in self.products if p.closed_date is None],
            "can_edit_ews": self.can_edit_ews,
            "can_edit_encounter": self.can_edit_encounter,
        }

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        """Inflate from a response that may include include dicts for related nodes
        then convert to a dict. Any related nodes must be included in the dict or
        they are ignored.
        """
        return response_to_dict(cls, response, primary="clinician", method=method)
