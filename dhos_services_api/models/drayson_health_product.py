from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union

import lazy_import
from flask import abort
from flask_batteries_included.helpers import schema
from flask_batteries_included.helpers.timestamp import (
    parse_date_to_iso8601,
    parse_iso8601_to_date,
)
from neomodel import (
    BooleanProperty,
    DateProperty,
    RelationshipDefinition,
    RelationshipTo,
    StringProperty,
    StructuredNode,
)

from dhos_services_api.helpers.responses import QueryResponse, response_to_dict
from dhos_services_api.neodb import NeomodelIdentifier, db

clinician_module = lazy_import.lazy_module(
    "dhos_services_api.models.clinician", level="leaf"
)

patient_module = lazy_import.lazy_module(
    "dhos_services_api.models.patient", level="leaf"
)


class DraysonHealthProductChangeEvent(Enum):
    ARCHIVE = "archive"
    STOP_MONITORING = "stop monitoring"
    START_MONITORING = "start monitoring"
    # UNARCHIVE = "unarchive"  NOT IMPLEMENTED YET


class BaseProduct(NeomodelIdentifier):
    product_name = StringProperty()
    opened_date_ = DateProperty(default=datetime.now().date, db_property="opened_date")
    closed_date_ = DateProperty(default=None, db_property="closed_date")

    @property
    def opened_date(self) -> Optional[str]:

        if self.opened_date_ is None:
            return None

        return parse_date_to_iso8601(self.opened_date_)

    @opened_date.setter
    def opened_date(self, value: str) -> None:

        if value is None:
            return

        self.opened_date_ = parse_iso8601_to_date(value)

    @property
    def closed_date(self) -> Optional[Any]:

        if self.closed_date_ is None:
            return None
        return parse_date_to_iso8601(self.closed_date_)

    @closed_date.setter
    def closed_date(self, value: Optional[Any]) -> None:

        if value is None:
            return
        self.closed_date_ = parse_iso8601_to_date(value)

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

    def pack_base_product(self) -> Union[Dict[str, Optional[str]], Dict[str, str]]:

        return {
            "product_name": self.product_name,
            "opened_date": self.opened_date,
            "closed_date": self.closed_date,
            **self.pack_identifier(),
        }


class DraysonHealthProduct(BaseProduct, StructuredNode):

    accessibility_discussed = BooleanProperty(default=False)
    accessibility_discussed_with = StringProperty()
    accessibility_discussed_date_ = DateProperty()

    opened_date_ = DateProperty(default=datetime.now().date, db_property="opened_date")
    closed_date_ = DateProperty(default=None, db_property="closed_date")
    closed_reason = StringProperty()
    closed_reason_other = StringProperty()

    monitored_by_clinician = BooleanProperty(default=True)
    changes: RelationshipDefinition = RelationshipTo(
        ".drayson_health_product.DraysonHealthProductChange", "HAS_CHANGE"
    )

    @property
    def opened_date(self) -> Optional[str]:

        if self.opened_date_ is None:
            return None

        return parse_date_to_iso8601(self.opened_date_)

    @opened_date.setter
    def opened_date(self, value: str) -> None:

        if value is None:
            return

        self.opened_date_ = parse_iso8601_to_date(value)

    @property
    def closed_date(self) -> Optional[str]:

        if self.closed_date_ is None:
            return None

        return parse_date_to_iso8601(self.closed_date_)

    @closed_date.setter
    def closed_date(self, value: Optional[str]) -> None:

        if value is None:
            return

        self.closed_date_ = parse_iso8601_to_date(value)

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

    @property
    def accessibility_discussed_date(self) -> Optional[str]:

        if self.accessibility_discussed_date_ is None:
            return None

        return parse_date_to_iso8601(self.accessibility_discussed_date_)

    @accessibility_discussed_date.setter
    def accessibility_discussed_date(self, value: Optional[str]) -> None:

        if value is None:
            return

        self.accessibility_discussed_date_ = parse_iso8601_to_date(value)

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "DraysonHealthProduct":
        schema.post(json_in=kwargs, **cls.schema())
        return cls(*args, **kwargs)

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, type]]:
        return {
            "optional": {
                "closed_date": str,
                "closed_reason": str,
                "closed_reason_other": str,
                "accessibility_discussed": bool,
                "accessibility_discussed_with": str,
                "accessibility_discussed_date": str,
                "monitored_by_clinician": bool,
            },
            "required": {"product_name": str, "opened_date": str},
            "updatable": {
                "product_name": str,
                "opened_date": str,
                "closed_date": str,
                "closed_reason": str,
                "closed_reason_other": str,
                "monitored_by_clinician": bool,
            },
        }

    def _new_event(self, event: DraysonHealthProductChangeEvent) -> None:
        change_node = DraysonHealthProductChange.new(event=event.value)
        change_node.save()
        self.changes.connect(change_node)

    def on_patch(self, _json: Dict = None, *args: Any, **kwargs: Any) -> None:

        if _json is None:
            return

        if "product_name" in _json:
            query = """match(p:Patient)-[:ACTIVE_ON_PRODUCT]-(d:DraysonHealthProduct)
                where d.uuid = {uuid} return p"""
            results, meta = db.cypher_query(query, {"uuid": self.uuid})

            p = patient_module.PatientSchema.inflate(results[0][0])

            for prod in p.dh_products:
                if (
                    prod.product_name == _json["product_name"]
                    and prod.closed_date is None
                ):
                    abort(400, f"patient is already active on {_json['product_name']}")

        super(DraysonHealthProduct, self).on_patch()
        self.save()

    def close(
        self,
        closed_date: str,
        closed_reason: Optional[str] = None,
        closed_reason_other: Optional[str] = None,
    ) -> None:
        self.closed_date = closed_date
        self.closed_reason = closed_reason
        self.closed_reason_other = closed_reason_other

        if self.monitored_by_clinician:
            self.stop_monitoring()

        self._new_event(event=DraysonHealthProductChangeEvent.ARCHIVE)

        self.save()

    def stop_monitoring(self) -> None:
        self.monitored_by_clinician = False
        self.save()
        self._new_event(event=DraysonHealthProductChangeEvent.STOP_MONITORING)

    def start_monitoring(self) -> None:
        self.monitored_by_clinician = True
        self.save()
        self._new_event(event=DraysonHealthProductChangeEvent.START_MONITORING)

    def to_dict_no_relations(self, clinician: Dict = None) -> Dict:
        resp = {
            "product_name": self.product_name,
            "opened_date": self.opened_date,
            "closed_date": self.closed_date,
            "closed_reason": self.closed_reason,
            "closed_reason_other": self.closed_reason_other,
            "monitored_by_clinician": self.monitored_by_clinician,
            **self.pack_base_product(),
        }

        if self.accessibility_discussed:
            resp["accessibility_discussed"] = self.accessibility_discussed
            resp["accessibility_discussed_with"] = self.accessibility_discussed_with
            resp["accessibility_discussed_date"] = self.accessibility_discussed_date

        return resp

    def to_dict(self) -> Dict[str, Optional[str]]:
        resp = {
            "product_name": self.product_name,
            "opened_date": self.opened_date,
            "closed_date": self.closed_date,
            "closed_reason": self.closed_reason,
            "closed_reason_other": self.closed_reason_other,
            "monitored_by_clinician": self.monitored_by_clinician,
            "changes": list(
                sorted(
                    (change.to_dict() for change in self.changes),
                    key=lambda x: x["created"],
                )
            ),
            **self.pack_base_product(),
        }

        if self.accessibility_discussed:
            resp["accessibility_discussed"] = self.accessibility_discussed
            resp["accessibility_discussed_with"] = self.accessibility_discussed_with
            resp["accessibility_discussed_date"] = self.accessibility_discussed_date

        return resp

    def to_compact_dict(self) -> Dict[str, Optional[str]]:
        return {
            "product_name": self.product_name,
            "opened_date": self.opened_date,
            "closed_date": self.closed_date,
            "closed_reason": self.closed_reason,
            "closed_reason_other": self.closed_reason_other,
            "monitored_by_clinician": self.monitored_by_clinician,
            **self.compack_identifier(),
        }

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        return response_to_dict(
            cls,
            response,
            primary="drayson_health_product",
            single={"clinician": clinician_module.Clinician},
            multiple={"changes": DraysonHealthProductChange},
            method=method,
        )


class ClinicianProduct(BaseProduct, StructuredNode):
    @classmethod
    def schema(cls) -> Dict[str, Dict[str, type]]:
        return {
            "optional": {"closed_date": str},
            "required": {"product_name": str, "opened_date": str},
            "updatable": {"product_name": str, "opened_date": str, "closed_date": str},
        }

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {**self.pack_base_product()}

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "ClinicianProduct":
        schema.post(json_in=kwargs, **cls.schema())
        return cls(*args, **kwargs)

    def on_patch(self, _json: Dict = None, *args: Any, **kwargs: Any) -> None:

        if _json is None:
            return

        if "product_name" in _json:
            query = """match(c:Clinician)-[:ACTIVE_ON_PRODUCT]-(d:ClinicianProduct)
                where d.uuid = {uuid} return p"""
            results, meta = db.cypher_query(query, {"uuid": self.uuid})

            p = patient_module.PatientSchema.inflate(results[0][0])

            for prod in p.dh_products:
                if (
                    prod.product_name == _json["product_name"]
                    and prod.closed_date is None
                ):
                    abort(
                        400, f"clinician is already active on {_json['product_name']}"
                    )

        super(ClinicianProduct, self).on_patch()
        self.save()


class LocationProduct(BaseProduct, StructuredNode):
    @classmethod
    def schema(cls) -> Dict[str, Dict[str, type]]:
        return {
            "optional": {"closed_date": str},
            "required": {"product_name": str, "opened_date": str},
            "updatable": {"product_name": str, "opened_date": str, "closed_date": str},
        }

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "product_name": self.product_name,
            "opened_date": self.opened_date,
            "closed_date": self.closed_date,
            **self.compack_identifier(),
        }

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "LocationProduct":
        schema.post(json_in=kwargs, **cls.schema())
        return cls(*args, **kwargs)

    def on_patch(self, _json: Dict = None, *args: Any, **kwargs: Any) -> None:

        if _json is None:
            return

        if "product_name" in _json:
            query = """match(l:Location)-[:ACTIVE_ON_PRODUCT]-(d:LocationProduct)
                where d.uuid = {uuid} return l"""
            results, meta = db.cypher_query(query, {"uuid": self.uuid})

            loc = LocationProduct.inflate(results[0][0])

            for prod in loc.dh_products:
                if (
                    prod.product_name == _json["product_name"]
                    and prod.closed_date is None
                ):
                    abort(400, f"Location is already active on {_json['product_name']}")

        super(LocationProduct, self).on_patch()
        self.save()


class DraysonHealthProductChange(NeomodelIdentifier, StructuredNode):
    event = StringProperty()

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "DraysonHealthProductChange":
        schema.post(json_in=kwargs, **cls.schema())
        return cls(*args, **kwargs)

    @classmethod
    def schema(cls) -> Dict:
        return {
            "optional": {},
            "required": {"event": str},
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event": self.event,
            **self.pack_identifier(),
        }

    to_dict_no_relations = to_dict

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        """Inflate from a response that may include include dicts for related nodes
        then convert to a dict. Any related nodes must be included in the dict or
        they are ignored.
        """
        return response_to_dict(
            cls, response, primary="drayson_health_product_change", method=method
        )
