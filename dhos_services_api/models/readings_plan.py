from typing import Any, Dict, Iterable, Sequence

from flask_batteries_included.helpers import schema
from neomodel import IntegerProperty, RelationshipTo, StructuredNode

from dhos_services_api.helpers.responses import QueryResponse, response_to_dict
from dhos_services_api.models.mixins.plan import PlanMixin
from dhos_services_api.neodb import NeomodelIdentifier


class ReadingsPlan(NeomodelIdentifier, PlanMixin, StructuredNode):

    days_per_week_to_take_readings = IntegerProperty()
    readings_per_day = IntegerProperty()

    changes = RelationshipTo(".readings_plan.ReadingsPlanChange", "HAS_CHANGE")

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "ReadingsPlan":
        schema.post(json_in=kwargs, **cls.schema())

        obj = cls(*args, **kwargs)
        obj.save()

        days_per_week_to_take_readings: int = kwargs["days_per_week_to_take_readings"]
        readings_per_day: int = kwargs["readings_per_day"]

        obj.on_patch(
            {
                "days_per_week_to_take_readings": days_per_week_to_take_readings,
                "readings_per_day": readings_per_day,
            },
            include_no_changes=True,
        )

        return obj

    def on_patch(
        self,
        _json: Dict[str, int] = None,
        include_no_changes: bool = None,
        *args: Any,
        **kwargs: Any
    ) -> None:

        if _json is None:
            return

        days_per_week_to_take_readings = _json.pop(
            "days_per_week_to_take_readings", self.days_per_week_to_take_readings
        )
        if (
            days_per_week_to_take_readings == self.days_per_week_to_take_readings
            and not include_no_changes
        ):
            new_days_per_week_to_take_readings = None
        else:
            new_days_per_week_to_take_readings = days_per_week_to_take_readings

        readings_per_day = _json.pop("readings_per_day", self.readings_per_day)
        if readings_per_day == self.readings_per_day and not include_no_changes:
            new_readings_per_day = None
        else:
            new_readings_per_day = readings_per_day

        if new_days_per_week_to_take_readings is not None:
            self.days_per_week_to_take_readings = new_days_per_week_to_take_readings

        if new_readings_per_day is not None:
            self.readings_per_day = new_readings_per_day

        node = ReadingsPlanChange.new()
        node.days_per_week_to_take_readings = new_days_per_week_to_take_readings
        node.readings_per_day = new_readings_per_day
        node.save()

        self.changes.connect(node)

        super(ReadingsPlan, self).on_patch()
        self.save()

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, type]]:
        return {
            "optional": {
                "days_per_week_to_take_readings": int,
                "readings_per_day": int,
                "start_date": str,
                "end_date": str,
            },
            "required": {"sct_code": str},
            "updatable": {
                "days_per_week_to_take_readings": int,
                "readings_per_day": int,
                "start_date": str,
                "end_date": str,
                "sct_code": str,
            },
        }

    def to_dict_no_relations(self, changes: Iterable[Dict] = ()) -> Dict:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "sct_code": self.sct_code,
            "days_per_week_to_take_readings": self.days_per_week_to_take_readings,
            "readings_per_day": self.readings_per_day,
            "changes": sorted(changes, key=lambda x: x["created"]),
            **self.pack_identifier(),
        }

    def to_dict(self) -> Dict[str, Any]:
        changes: Sequence[ReadingsPlanChange] = self.changes
        return self.to_dict_no_relations(
            changes=(change.to_dict() for change in changes)
        )

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        return response_to_dict(
            cls,
            response,
            primary="readings_plan",
            multiple={"changes": ReadingsPlanChange},
            method=method,
        )


class ReadingsPlanChange(NeomodelIdentifier, StructuredNode):

    days_per_week_to_take_readings = IntegerProperty()
    readings_per_day = IntegerProperty()

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "ReadingsPlanChange":
        schema.post(json_in=kwargs, **cls.schema())
        return cls(*args, **kwargs)

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, type]]:
        return {
            "optional": {
                "days_per_week_to_take_readings": int,
                "readings_per_day": int,
            },
            "required": {},
            "updatable": {},
        }

    @property
    def created_by(self) -> str:
        return self.created_by_

    @created_by.setter
    def created_by(self, v: str) -> None:
        self.created_by_ = v

    @property
    def modified_by(self) -> str:
        return self.modified_by_

    @modified_by.setter
    def modified_by(self, v: str) -> None:
        self.modified_by_ = v

    def to_dict(self) -> Dict:
        return {
            "days_per_week_to_take_readings": self.days_per_week_to_take_readings,
            "readings_per_day": self.readings_per_day,
            **self.pack_identifier(),
        }

    to_dict_no_relations = to_dict

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        return response_to_dict(cls, response, primary="changes", method=method)
