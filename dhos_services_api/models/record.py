from typing import Any, Dict, Iterable, List

from flask_batteries_included.helpers import schema
from neomodel import One, RelationshipFrom, RelationshipTo, StructuredNode

from dhos_services_api.helpers.responses import QueryResponse, response_to_dict
from dhos_services_api.models.diagnosis import Diagnosis
from dhos_services_api.models.history import History
from dhos_services_api.models.note import Note
from dhos_services_api.models.pregnancy import Pregnancy
from dhos_services_api.models.visit import Visit
from dhos_services_api.neodb import NeomodelIdentifier

_MARKER: Any = object()


class Record(NeomodelIdentifier, StructuredNode):
    notes = RelationshipTo(".note.Note", "HAS_NOTE")
    diagnoses = RelationshipTo(".diagnosis.Diagnosis", "HAS_DIAGNOSIS")
    pregnancies = RelationshipTo(".pregnancy.Pregnancy", "HAS_PREGNANCY")
    visits = RelationshipTo(".visit.Visit", "HAD_VISIT")
    history = RelationshipTo(".history.History", "HAS_HISTORY", cardinality=One)
    patient = RelationshipFrom(".patient.Patient", "HAS_RECORD", cardinality=One)

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> "Record":

        schema.post(json_in=kwargs, **cls.schema())

        notes = [Note.new(**note) for note in kwargs.pop("notes", [])]

        diagnoses = [Diagnosis.new(**diag) for diag in kwargs.pop("diagnoses", [])]

        pregnancies = [Pregnancy.new(**preg) for preg in kwargs.pop("pregnancies", [])]

        visits = [Visit.new(**visit) for visit in kwargs.pop("visits", [])]

        history = History.new(**kwargs.pop("history", dict()))

        obj = cls(*args, **kwargs)
        obj.save()

        history.save()
        obj.history.connect(history)

        for note in notes:
            note.save()
            obj.notes.connect(note)

        for visit in visits:
            visit.save()
            obj.visits.connect(visit)

        for diagnosis in diagnoses:
            diagnosis.save()
            obj.diagnoses.connect(diagnosis)

        for preg in pregnancies:
            preg.save()
            obj.pregnancies.connect(preg)

        return obj

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "optional": {
                "pregnancies": [dict],
                "history": dict,
                "notes": [dict],
                "diagnoses": [dict],
                "visits": [dict],
            },
            "required": {},
            "updatable": {
                "pregnancies": [dict],
                "notes": [dict],
                "diagnoses": [dict],
                "visits": [dict],
                "history": dict,
            },
        }

    def to_dict_no_relations(
        self,
        notes: Iterable[Dict] = (),
        diagnoses: Iterable[Dict] = (),
        pregnancies: Iterable[Dict] = (),
        visits: Iterable[Dict] = (),
        history: Dict = None,
    ) -> Dict:
        return {
            "notes": sorted(notes, key=lambda x: x["created"], reverse=True),
            "diagnoses": sorted(diagnoses, key=lambda x: x["created"], reverse=True),
            "pregnancies": sorted(
                pregnancies, key=lambda x: x["created"], reverse=True
            ),
            "visits": sorted(visits, key=lambda x: x["created"], reverse=True),
            "history": history,
            **self.pack_identifier(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.to_dict_no_relations(
            notes=[note.to_dict() for note in self.notes],
            diagnoses=[diagnosis.to_dict() for diagnosis in self.diagnoses],
            pregnancies=[pregnancy.to_dict() for pregnancy in self.pregnancies],
            visits=[visit.to_dict() for visit in self.visits],
            history=self.history.single().to_dict(),
        )

    def to_compact_dict(
        self,
        diagnoses: List[Dict] = _MARKER,
        pregnancies: List[Dict] = _MARKER,
        notes: Iterable[Dict] = None,
        visits: Iterable[Dict] = None,
        history: Dict = None,
    ) -> Dict:
        if diagnoses is _MARKER:
            diagnoses = [diagnosis.to_compact_dict() for diagnosis in self.diagnoses]

        if pregnancies is _MARKER:
            pregnancies = [
                pregnancy.to_compact_dict() for pregnancy in self.pregnancies
            ]

        return {
            "diagnoses": sorted(diagnoses, key=lambda x: x["created"], reverse=True),
            "pregnancies": sorted(
                pregnancies, key=lambda x: x["created"], reverse=True
            ),
            **self.compack_identifier(),
        }

    @classmethod
    def convert_response_to_dict(cls, response: QueryResponse, method: str) -> Dict:
        return response_to_dict(
            cls,
            response,
            primary="record",
            single={"history": History},
            multiple={
                "notes": Note,
                "diagnoses": Diagnosis,
                "pregnancies": Pregnancy,
                "visits": Visit,
            },
            method=method,
        )
