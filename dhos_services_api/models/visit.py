from datetime import datetime
from typing import Dict, List, Optional

from flask_batteries_included.helpers import schema
from flask_batteries_included.helpers.timestamp import join_timestamp, split_timestamp
from neomodel import (
    DateTimeProperty,
    IntegerProperty,
    RelationshipTo,
    StringProperty,
    StructuredNode,
    ZeroOrOne,
)

import dhos_services_api.models.patient
from dhos_services_api.helpers.neo_utils import get_node_or_404
from dhos_services_api.helpers.responses import (
    QueryResponse,
    response_to_dict,
    validate_single_uuid,
    validate_uuid_list,
)
from dhos_services_api.models.diagnosis import Diagnosis
from dhos_services_api.neodb import NeomodelIdentifier, db


class Visit(NeomodelIdentifier, StructuredNode):

    visit_date_ = DateTimeProperty(db_property="visit_date")
    visit_date_timezone = IntegerProperty(unique=False, nullable=False)

    summary = StringProperty()

    clinician_uuid = StringProperty()
    location: str = StringProperty()

    diagnoses = RelationshipTo(".record.Diagnosis", "RELATES_TO_DIAGNOSIS")

    @property
    def visit_date(self) -> datetime:
        return join_timestamp(self.visit_date_, self.visit_date_timezone)

    @visit_date.setter
    def visit_date(self, value: str) -> None:
        self.visit_date_, self.visit_date_timezone = split_timestamp(value)

    @property
    def patient(self) -> Optional["dhos_services_api.models.patient.Patient"]:
        query = """
        match(p:Patient)-[:HAS_RECORD]-(r:Record)
        where r.uuid = {uuid}
        return p  
        """
        record = self.record
        if record is None:
            return None

        results, meta = db.cypher_query(query, {"uuid": record.single().uuid})
        return (
            dhos_services_api.models.patient.Patient.inflate(results[0][0])
            if len(results[0]) > 0
            else None
        )

    @property
    def record(self) -> Optional["dhos_services_api.models.record.Record"]:
        query = """
        match(r:Record)-[:HAD_VISIT]-(v:Visit)
        where v.uuid = {uuid}
        return r
        """

        results, meta = db.cypher_query(query, {"uuid": self.uuid})
        return (
            dhos_services_api.models.record.Record.inflate(results[0][0])
            if len(results[0]) > 0
            else None
        )

    @classmethod
    def new(cls, *args: List, **kwargs: Dict) -> "Visit":

        schema.post(json_in=kwargs, **cls.schema())

        diagnoses_uuids: List = kwargs.pop("diagnoses", [])  # type: ignore

        obj = cls(*args, **kwargs)
        obj.save()

        for diagnoses_uuid in diagnoses_uuids:
            diagnosis = get_node_or_404(Diagnosis, uuid=diagnoses_uuid)
            obj.diagnoses.connect(diagnosis)

        return obj

    @classmethod
    def schema(cls) -> Dict:
        return {
            "optional": {"summary": str, "diagnoses": [dict]},
            "required": {"visit_date": str, "clinician_uuid": str, "location": str},
            "updatable": {
                "visit_date": str,
                "clinician_uuid": str,
                "summary": str,
                "location": str,
                "diagnoses": [dict],
            },
        }

    def to_dict_no_relations(
        self,
        diagnoses: List[str] = None,
    ) -> Dict:
        return {
            "visit_date": self.visit_date,
            "summary": self.summary,
            "location": self.location,
            "diagnoses": diagnoses,
            "clinician_uuid": self.clinician_uuid,
            **self.pack_identifier(),
        }

    def to_dict(self) -> Dict:
        return {
            "visit_date": self.visit_date,
            "summary": self.summary,
            "location": self.location,
            "diagnoses": [d.uuid for d in self.diagnoses],
            "clinician_uuid": self.clinician_uuid,
            **self.pack_identifier(),
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
            primary="visit",
            custom={"diagnoses": validate_uuid_list},
            method=method,
        )
