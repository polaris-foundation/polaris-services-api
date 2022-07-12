from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, TypedDict

from neomodel import db
from she_logging import logger

from dhos_services_api.blueprint_patients.patient_controller_neo import DIABETES_CODES


class ReadingsPlanSchema(TypedDict):
    created: str
    days_per_week_to_take_readings: int
    readings_per_day: int


class PatientSchema(TypedDict):
    first_name: str
    locations: List[str]
    uuid: str
    readings_plans: List[ReadingsPlanSchema]


class NeoReadingsPlanSchema(TypedDict):
    created: float
    days_per_week_to_take_readings: int
    readings_per_day: int


class NeoPatientSchema(TypedDict):
    first_name: str
    locations: List[str]
    uuid: str
    readings_plans: List[NeoReadingsPlanSchema]


def _fix_patient(neopatient: NeoPatientSchema) -> PatientSchema:
    # Readings plans may not be sorted, and may include None for some of the values.
    # Sort them oldest first, and replace the missing values from the last value set.
    # If there are missing values at the start then ignore those records as they are
    # invalid history. Also ignore records where nothing changed.
    readings_plans = sorted(neopatient["readings_plans"], key=lambda r: r["created"])
    fixed_plans: List[ReadingsPlanSchema] = []
    days_per_week_to_take_readings, readings_per_day = None, None
    last_readings_plan: Optional[ReadingsPlanSchema] = None

    for rp in readings_plans:
        if rp["days_per_week_to_take_readings"] is not None:
            days_per_week_to_take_readings = rp["days_per_week_to_take_readings"]
        if rp["readings_per_day"] is not None:
            readings_per_day = rp["readings_per_day"]

        if (
            days_per_week_to_take_readings is None
            or readings_per_day is None
            or (
                last_readings_plan is not None
                and last_readings_plan["days_per_week_to_take_readings"]
                == days_per_week_to_take_readings
                and last_readings_plan["readings_per_day"] == readings_per_day
            )
        ):
            continue

        last_readings_plan = ReadingsPlanSchema(
            created=datetime.fromtimestamp(rp["created"])
            .replace(tzinfo=timezone.utc)
            .isoformat(timespec="milliseconds"),
            days_per_week_to_take_readings=days_per_week_to_take_readings,
            readings_per_day=readings_per_day,
        )
        fixed_plans.append(last_readings_plan)

    return PatientSchema(
        first_name=neopatient["first_name"],
        locations=neopatient["locations"],
        uuid=neopatient["uuid"],
        readings_plans=fixed_plans,
    )


QUERY = """
    MATCH (d:Diagnosis)<-[:HAS_DIAGNOSIS]-(:Record)<-[:HAS_RECORD]-(patient:Patient)
        -[:ACTIVE_ON_PRODUCT]-(dhp:DraysonHealthProduct)
    WHERE dhp.opened_date < {seven_days_ago}
    AND dhp.closed_date IS NULL
    AND dhp.product_name="GDM"
    AND d.sct_code IN {diagnosis_codes_string}
    WITH patient, HEAD(COLLECT(d)) AS diagnosis
    MATCH (patient)
    WITH patient, diagnosis
    OPTIONAL MATCH (diagnosis)-[:HAS_READINGS_PLAN]->(plan:ReadingsPlan)-[:HAS_CHANGE]->(change:ReadingsPlanChange)
    RETURN patient {.uuid, .first_name, locations: patient.locations,
      readings_plans: COLLECT(plan {.days_per_week_to_take_readings, .readings_per_day, .created}) +
         COLLECT(change {.days_per_week_to_take_readings, .readings_per_day, .created})
      }
"""


def retrieve_open_gdm_patients() -> List[PatientSchema]:
    """
    Extract open GDm patients and return them for grey alerts processing
    """
    logger.info("Extracting open GDM patients for activity alerting")

    # Only get records that were opened more than 7 days ago
    seven_days_ago = str(datetime.now().date() + timedelta(days=-7))
    results: List[Tuple[NeoPatientSchema]]
    meta: Tuple[str]
    results, meta = db.cypher_query(
        QUERY,
        {"seven_days_ago": seven_days_ago, "diagnosis_codes_string": DIABETES_CODES},
    )
    logger.info("Retrieved %d open GDM patients for activity alerting", len(results))
    return [_fix_patient(patient) for (patient,) in results]
