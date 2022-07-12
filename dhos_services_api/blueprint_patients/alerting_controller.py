from datetime import date, datetime, timedelta, timezone
from typing import Optional

from flask_batteries_included.sqldb import db
from she_logging import logger
from sqlalchemy.orm import Query, subqueryload

from dhos_services_api.blueprint_patients.patient_controller import DIABETES_CODES
from dhos_services_api.sqlmodels import (
    Diagnosis,
    DraysonHealthProduct,
    Patient,
    ReadingsPlan,
    Record,
)
from dhos_services_api.sqlmodels.pydantic_models import (
    ActivityAlertingPatientResponse,
    SimpleReadingsPlan,
)


def _fix_patient(
    patient: ActivityAlertingPatientResponse,
) -> ActivityAlertingPatientResponse:
    # Readings plans may not be sorted, and may include None for some of the values.
    # Sort them oldest first, and replace the missing values from the last value set.
    # If there are missing values at the start then ignore those records as they are
    # invalid history. Also ignore records where nothing changed.
    readings_plans = sorted(patient.readings_plans, key=lambda r: r.created)
    fixed_plans: list[SimpleReadingsPlan] = []
    days_per_week_to_take_readings, readings_per_day = None, None
    last_readings_plan: Optional[SimpleReadingsPlan] = None

    for rp in readings_plans:
        if rp.days_per_week_to_take_readings is not None:
            days_per_week_to_take_readings = rp.days_per_week_to_take_readings
        if rp.readings_per_day is not None:
            readings_per_day = rp.readings_per_day

        if (
            days_per_week_to_take_readings is None
            or readings_per_day is None
            or (
                last_readings_plan is not None
                and last_readings_plan.days_per_week_to_take_readings
                == days_per_week_to_take_readings
                and last_readings_plan.readings_per_day == readings_per_day
            )
        ):
            continue

        last_readings_plan = SimpleReadingsPlan(
            created=rp.created.replace(tzinfo=timezone.utc),
            days_per_week_to_take_readings=days_per_week_to_take_readings,
            readings_per_day=readings_per_day,
        )
        fixed_plans.append(last_readings_plan)

    return ActivityAlertingPatientResponse(
        first_name=patient.first_name,
        locations=patient.locations,
        uuid=patient.uuid,
        readings_plans=fixed_plans,
    )


def _build_query(cutoff_date: date) -> Query:
    query: Query = (
        db.session.query(Patient.uuid, Patient.first_name, Patient.locations, Diagnosis)
        .join(Record, Record.uuid == Patient.record_id)
        .join(Diagnosis, Diagnosis.record_id == Record.uuid)
        .join(DraysonHealthProduct)
    )
    query = query.filter(
        DraysonHealthProduct.opened_date < cutoff_date,
        DraysonHealthProduct.closed_date == None,
        DraysonHealthProduct.product_name == "GDM",
        Diagnosis.sct_code.in_(DIABETES_CODES),
    ).order_by(Patient.uuid, Diagnosis.uuid)

    query = query.options(
        subqueryload(Diagnosis.readings_plan).joinedload(ReadingsPlan.changes),
    )
    return query


def retrieve_open_gdm_patients() -> list[dict]:
    """
    Extract open GDm patients and return them for grey alerts processing
    """
    logger.info("Extracting open GDM patients for activity alerting")

    # Only get records that were opened more than 7 days ago
    seven_days_ago = datetime.now().date() + timedelta(days=-7)
    query = _build_query(seven_days_ago)
    results = query.all()

    patients: dict[str, ActivityAlertingPatientResponse] = {}
    for (uuid, first_name, locations, diagnosis) in results:
        if uuid in patients:
            patients[uuid].readings_plans.append(
                SimpleReadingsPlan.from_orm(diagnosis.readings_plan)
            )
        else:
            patients[uuid] = ActivityAlertingPatientResponse(
                uuid=uuid,
                first_name=first_name,
                locations=locations,
                readings_plans=[diagnosis.readings_plan],
            )

    logger.info("Retrieved %d open GDM patients for activity alerting", len(patients))

    return [_fix_patient(patient).dict() for patient in patients.values()]
