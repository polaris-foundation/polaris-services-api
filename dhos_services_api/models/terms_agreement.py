from datetime import datetime
from typing import Any, Dict, Union

from flask_batteries_included.helpers import schema, timestamp
from neomodel import DateTimeProperty, IntegerProperty, StringProperty, StructuredNode

from dhos_services_api.neodb import NeomodelIdentifier


class TermsAgreement(NeomodelIdentifier, StructuredNode):

    product_name = StringProperty()
    version = IntegerProperty()
    accepted_timestamp_ = DateTimeProperty()
    accepted_timestamp_tz = IntegerProperty()

    tou_version = IntegerProperty()
    tou_accepted_timestamp_ = DateTimeProperty()
    tou_accepted_timestamp_tz = IntegerProperty()

    patient_notice_version = IntegerProperty()
    patient_notice_accepted_timestamp_ = DateTimeProperty()
    patient_notice_accepted_timestamp_tz = IntegerProperty()

    expand_clinician_created_modified = False

    @property
    def accepted_timestamp(self) -> datetime:
        return timestamp.join_timestamp(
            self.accepted_timestamp_, self.accepted_timestamp_tz
        )

    @accepted_timestamp.setter
    def accepted_timestamp(self, value: Union[datetime, str, None]) -> None:
        if not value:
            self.accepted_timestamp_ = None
            self.accepted_timestamp_tz = None
        elif isinstance(value, datetime):
            self.accepted_timestamp_ = value
            self.accepted_timestamp_tz = 0
        else:
            (
                self.accepted_timestamp_,
                self.accepted_timestamp_tz,
            ) = timestamp.split_timestamp(value)

    @property
    def tou_accepted_timestamp(self) -> datetime:
        return timestamp.join_timestamp(
            self.tou_accepted_timestamp_, self.tou_accepted_timestamp_tz
        )

    @tou_accepted_timestamp.setter
    def tou_accepted_timestamp(self, value: Union[datetime, str, None]) -> None:
        if not value:
            self.tou_accepted_timestamp_ = None
            self.tou_accepted_timestamp_tz = None
        elif isinstance(value, datetime):
            self.tou_accepted_timestamp_ = value
            self.tou_accepted_timestamp_tz = 0
        else:
            (
                self.tou_accepted_timestamp_,
                self.tou_accepted_timestamp_tz,
            ) = timestamp.split_timestamp(value)

    @property
    def patient_notice_accepted_timestamp(self) -> datetime:
        return timestamp.join_timestamp(
            self.patient_notice_accepted_timestamp_,
            self.patient_notice_accepted_timestamp_tz,
        )

    @patient_notice_accepted_timestamp.setter
    def patient_notice_accepted_timestamp(
        self, value: Union[datetime, str, None]
    ) -> None:
        if not value:
            self.patient_notice_accepted_timestamp_ = None
            self.patient_notice_accepted_timestamp_tz = None
        elif isinstance(value, datetime):
            self.patient_notice_accepted_timestamp_ = value
            self.patient_notice_accepted_timestamp_tz = 0
        else:
            (
                self.patient_notice_accepted_timestamp_,
                self.patient_notice_accepted_timestamp_tz,
            ) = timestamp.split_timestamp(value)

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "TermsAgreement":

        schema.post(json_in=kwargs, **cls.schema())

        if kwargs.get("accepted_timestamp", None) is None:
            kwargs["accepted_timestamp"] = datetime.utcnow()

        obj = cls(*args, **kwargs)
        obj.save()

        return obj

    @classmethod
    def new_v2(cls, *args: Any, **kwargs: Any) -> "TermsAgreement":

        schema.post(json_in=kwargs, **cls.schema())

        if kwargs.get("tou_accepted_timestamp", None) is None:
            kwargs["tou_accepted_timestamp"] = datetime.utcnow()

        if kwargs.get("patient_notice_accepted_timestamp", None) is None:
            kwargs["patient_notice_accepted_timestamp"] = datetime.utcnow()

        obj = cls(*args, **kwargs)
        obj.save()

        return obj

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, type]]:
        return {
            "optional": {
                "version": int,
                "accepted_timestamp": str,
                "tou_version": int,
                "tou_accepted_timestamp": str,
                "patient_notice_version": int,
                "patient_notice_accepted_timestamp": str,
            },
            "required": {
                "product_name": str,
            },
            "updatable": {},
        }

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "product_name": self.product_name,
            **self.pack_identifier(),
        }
        if self.version:
            result.update(
                {
                    "version": self.version,
                    "accepted_timestamp": self.accepted_timestamp.isoformat(
                        timespec="milliseconds"
                    ),
                }
            )

        if self.tou_version:
            result.update(
                {
                    "tou_version": self.tou_version,
                    "tou_accepted_timestamp": self.tou_accepted_timestamp.isoformat(
                        timespec="milliseconds"
                    ),
                }
            )

        if self.patient_notice_version:
            result.update(
                {
                    "patient_notice_version": self.patient_notice_version,
                    "patient_notice_accepted_timestamp": self.patient_notice_accepted_timestamp.isoformat(
                        timespec="milliseconds"
                    ),
                }
            )

        return result
