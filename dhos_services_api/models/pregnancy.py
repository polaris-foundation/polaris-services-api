from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from flask_batteries_included.helpers import schema
from flask_batteries_included.helpers.timestamp import (
    parse_date_to_iso8601,
    parse_iso8601_to_date,
)
from neomodel import (
    ArrayProperty,
    BooleanProperty,
    DateProperty,
    IntegerProperty,
    RelationshipTo,
    StringProperty,
    StructuredNode,
)

import dhos_services_api.models.delivery
from dhos_services_api.helpers.responses import QueryResponse, response_to_dict
from dhos_services_api.neodb import NeomodelIdentifier

MAX_RETROACTIVE_EDD_PERIOD_IN_DAYS = 21
_MARKER: Any = object()


class Pregnancy(NeomodelIdentifier, StructuredNode):

    estimated_delivery_date_ = DateProperty(db_property="estimated_delivery_date")
    planned_delivery_place = StringProperty()
    length_of_postnatal_stay_in_days = IntegerProperty()
    colostrum_harvesting = BooleanProperty()
    expected_number_of_babies = IntegerProperty()
    pregnancy_complications = ArrayProperty(StringProperty(), default=[])

    induced = BooleanProperty()

    deliveries = RelationshipTo(".delivery.Delivery", "HAS_DELIVERY")

    height_at_booking_in_mm = IntegerProperty()
    weight_at_booking_in_g = IntegerProperty()

    weight_at_diagnosis_in_g = IntegerProperty()
    weight_at_36_weeks_in_g = IntegerProperty()

    delivery_place = StringProperty()
    delivery_place_other = StringProperty()

    first_medication_taken = StringProperty()
    first_medication_taken_recorded_ = DateProperty(
        db_property="first_medication_taken_recorded"
    )

    @property
    def first_medication_taken_recorded(self) -> Optional[Any]:
        return parse_date_to_iso8601(self.first_medication_taken_recorded_)

    @first_medication_taken_recorded.setter
    def first_medication_taken_recorded(self, value: Optional[str]) -> None:
        self.first_medication_taken_recorded_ = parse_iso8601_to_date(value)

    @property
    def estimated_delivery_date(self) -> Optional[str]:

        return parse_date_to_iso8601(self.estimated_delivery_date_)

    @estimated_delivery_date.setter
    def estimated_delivery_date(self, value: str) -> None:

        self.estimated_delivery_date_ = parse_iso8601_to_date(value)

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "Pregnancy":

        validation_date = timedelta(days=MAX_RETROACTIVE_EDD_PERIOD_IN_DAYS)
        earliest_allowed_edd = datetime.date(datetime.now() - validation_date)
        edd = parse_iso8601_to_date(kwargs.get("estimated_delivery_date"))

        if edd is None or earliest_allowed_edd > edd:
            raise ValueError("Estimated delivery date must be within 3 weeks of today")

        schema.post(json_in=kwargs, **cls.schema())

        deliveries = [
            dhos_services_api.models.delivery.Delivery.new(**delivery)
            for delivery in kwargs.pop("deliveries", [])
        ]
        obj = cls(*args, **kwargs)
        obj.save()

        for delivery in deliveries:
            delivery.save()
            obj.deliveries.connect(delivery)

        return obj

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "optional": {
                "length_of_postnatal_stay_in_days": int,
                "colostrum_harvesting": bool,
                "pregnancy_complications": [str],
                "induced": bool,
                "deliveries": [dict],
                "delivery_place": str,
                "delivery_place_other": str,
                "planned_delivery_place": str,
                "height_at_booking_in_mm": int,
                "weight_at_diagnosis_in_g": int,
                "weight_at_booking_in_g": int,
                "weight_at_36_weeks_in_g": int,
                "expected_number_of_babies": int,
                "first_medication_taken_recorded": str,
                "first_medication_taken": str,
            },
            "required": {"estimated_delivery_date": str},
            "updatable": {
                "length_of_postnatal_stay_in_days": int,
                "colostrum_harvesting": bool,
                "pregnancy_complications": [str],
                "induced": bool,
                "deliveries": [dict],
                "estimated_delivery_date": str,
                "planned_delivery_place": str,
                "height_at_booking_in_mm": int,
                "weight_at_diagnosis_in_g": int,
                "weight_at_booking_in_g": int,
                "weight_at_36_weeks_in_g": int,
                "delivery_place": str,
                "delivery_place_other": str,
                "expected_number_of_babies": int,
                "first_medication_taken_recorded": str,
                "first_medication_taken": str,
            },
        }

    def to_dict_no_relations(self, deliveries: Iterable[Dict] = ()) -> Dict:
        return {
            "estimated_delivery_date": self.estimated_delivery_date,
            "planned_delivery_place": self.planned_delivery_place,
            "length_of_postnatal_stay_in_days": self.length_of_postnatal_stay_in_days,
            "colostrum_harvesting": self.colostrum_harvesting,
            "expected_number_of_babies": self.expected_number_of_babies,
            "pregnancy_complications": self.pregnancy_complications,
            "induced": self.induced,
            "deliveries": sorted(deliveries, key=lambda x: x["created"]),
            "height_at_booking_in_mm": self.height_at_booking_in_mm,
            "weight_at_diagnosis_in_g": self.weight_at_diagnosis_in_g,
            "weight_at_booking_in_g": self.weight_at_booking_in_g,
            "weight_at_36_weeks_in_g": self.weight_at_36_weeks_in_g,
            "delivery_place": self.delivery_place,
            "delivery_place_other": self.delivery_place_other,
            "first_medication_taken_recorded": self.first_medication_taken_recorded,
            "first_medication_taken": self.first_medication_taken,
            **self.pack_identifier(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.to_dict_no_relations(
            deliveries=[delivery.to_dict() for delivery in self.deliveries]
        )

    def to_compact_dict(self, deliveries: List[Dict] = _MARKER) -> Dict:
        if deliveries is _MARKER:
            deliveries = [delivery.to_compact_dict() for delivery in self.deliveries]

        return {
            "estimated_delivery_date": self.estimated_delivery_date,
            "deliveries": sorted(
                deliveries,
                key=lambda x: x["created"],
            ),
            **self.compack_identifier(),
        }

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        """Inflate from a response that may include include dicts for related nodes
        then convert to a dict. Any related nodes must be included in the dict or
        they are ignored.
        """
        return response_to_dict(
            cls,
            response,
            primary="pregnancy",
            multiple={"deliveries": dhos_services_api.models.delivery.Delivery},
            method=method,
        )
