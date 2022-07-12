"""
Order of migration of records:

Record
    Visit
    Patient
        DraysonHealthProduct
            DraysonHealthProductChange
        PersonalAddress
        TermsAgreement
    Pregnancy
        Delivery
            Patient[Baby] (done above)
    Note
    History
    Diagnosis
        ObservableEntity
        ReadingsPlan
            ReadingsPlanChange
        ManagementPlan
            NonMedicationAction
            Dose
                DoseChange
                DoseHistory
"""
import itertools
import json
from datetime import datetime, timedelta, timezone
from typing import Generator, Iterable, Sequence, Type, TypeVar

import click
from flask_batteries_included.sqldb import db as sql_db
from neomodel import db as neo_db
from sqlalchemy import bindparam, func, select, text

from dhos_services_api import sqlmodels
from dhos_services_api.sqlmodels.mixins import ModelIdentifier

BATCH_SIZE = 1000

COMMON_FIELDS = "uuid: n.uuid, created: n.created, created_by_: n.created_by_, modified: n.modified, modified_by_: n.modified_by_"

T = TypeVar("T")


def chunks(iterable: Iterable[T], size: int = 100) -> Generator[list[T], None, None]:
    """Split an iterable into smaller lists"""
    it = iter(iterable)
    while chunk := list(itertools.islice(it, size)):
        yield chunk


start_time = datetime.now()
last_stamp = start_time


def stamp() -> str:
    global last_stamp
    previous = last_stamp
    last_stamp = datetime.now()
    start_delta = last_stamp - start_time
    last_delta = last_stamp - previous
    return f"{start_delta.total_seconds():.3f} {last_delta.total_seconds():.3f}"


class MigrationBase:
    node: str
    nodes_human: str
    query: str
    sql_model: Type[ModelIdentifier]
    children: "Sequence[Type[MigrationBase]]"

    def fix_node(self, n: dict) -> dict:
        return n | {
            "created": datetime.utcfromtimestamp(n["created"]).replace(
                tzinfo=timezone.utc
            ),
            "modified": datetime.utcfromtimestamp(n["modified"]).replace(
                tzinfo=timezone.utc
            ),
        }

    def existing_uuids(self) -> set[str]:
        """Given uuids from neo4j return a set of uuids that already exist in SQL"""

        results, _ = neo_db.cypher_query(f"""MATCH (n:{self.node}) RETURN n.uuid""")
        neo_uuids = (uuid for uuid, in results)

        uuid_rows = func.unnest(func.string_to_array(bindparam("uuids"), text("'|'")))
        uuid_view = select(uuid_rows.column_valued("value").label("uuid")).alias(
            "uuid_view"
        )
        query = select(self.sql_model.uuid).join(
            uuid_view, self.sql_model.uuid == uuid_view.c.uuid
        )
        existing_uuids: set[str] = set()
        for uuid_chunk in chunks(neo_uuids, size=2000):
            existing_uuids = existing_uuids.union(
                sql_db.session.scalars(query.params(uuids="|".join(uuid_chunk)))
            )
        return existing_uuids

    def neo_node_count(self) -> int:
        results, meta = neo_db.cypher_query(
            f"""MATCH (n:{self.node}) RETURN count(n)"""
        )
        return results[0][0]

    def migrate(self) -> int:
        neo_node_count = self.neo_node_count()
        if neo_node_count == 0:
            click.echo(f"{stamp()} No {self.nodes_human} to upload")
            return 0

        click.echo(f"{stamp()} Bulk uploading {neo_node_count} {self.nodes_human}")

        existing_uuids = self.existing_uuids()
        if existing_uuids:
            click.echo(
                f"{stamp()} Already in SQL {len(existing_uuids)} {self.nodes_human}"
            )
            if len(existing_uuids) == neo_node_count:
                return self.migrate_children(0)

        results, meta = neo_db.cypher_query(self.query)
        click.echo(f"{stamp()} Fetched from neo")
        index = 0
        for index, (node,) in enumerate(results, start=1):
            if node["uuid"] in existing_uuids:
                continue
            self.sql_model.new(**self.fix_node(node))
            if index % BATCH_SIZE == 0:
                sql_db.session.commit()
        sql_db.session.commit()
        click.echo(f"{stamp()} Created {index} new {self.nodes_human}")

        return self.migrate_children(index)

    def migrate_children(self, index: int) -> int:
        child_count = 0
        for child in self.children:
            child_count += child().migrate()
        return index + child_count


class MigrateVisit(MigrationBase):
    def fix_node(self, n: dict) -> dict:
        return n | {
            "created": datetime.utcfromtimestamp(n["created"]).replace(
                tzinfo=timezone.utc
            ),
            "modified": datetime.utcfromtimestamp(n["modified"]).replace(
                tzinfo=timezone.utc
            ),
            "visit_date": datetime.utcfromtimestamp(n["visit_date"]).replace(
                tzinfo=timezone(timedelta(hours=n.pop("visit_date_timezone") or 0))
            ),
        }

    node = "Visit"
    nodes_human = "Visits"
    sql_model = sqlmodels.Visit
    query = (
        f"MATCH (n:Visit)--(r:Record)"
        f"OPTIONAL MATCH (n:Visit)--(d:Diagnosis)"
        f"RETURN {{{COMMON_FIELDS},"
        f"""record_id: r.uuid,
        diagnoses: collect(d.uuid),
        summary: n.summary,
        visit_date: n.visit_date,
        visit_date_timezone: n.visit_date_timezone,
        clinician_uuid: n.clinician_uuid,
        location: n.location }}"""
    )
    children = ()


class MigrateDraysonHealthProductChange(MigrationBase):
    node = "DraysonHealthProductChange"
    nodes_human = "Drayson Health Product Changes"
    sql_model = sqlmodels.DraysonHealthProductChange
    query = (
        f"MATCH (n:DraysonHealthProductChange)<-[:HAS_CHANGE]-(dh:DraysonHealthProduct) RETURN {{{COMMON_FIELDS},"
        f"""event: n.event, drayson_health_product_id: dh.uuid }}"""
    )
    children = ()


class MigrateDraysonHealthProduct(MigrationBase):
    node = "DraysonHealthProduct"
    nodes_human = "Drayson Health Products"
    sql_model = sqlmodels.DraysonHealthProduct
    query = (
        f"MATCH (n:DraysonHealthProduct)-[:ACTIVE_ON_PRODUCT]-(p:Patient) RETURN {{{COMMON_FIELDS},"
        f"""patient_id: p.uuid,
            product_name: n.product_name,
            opened_date: n.opened_date,
            closed_date: n.closed_date,
            closed_reason: n.closed_reason,
            closed_reason_other: n.closed_reason_other,
            accessibility_discussed: n.accessibility_discussed,
            accessibility_discussed_with: n.accessibility_discussed_with,
            accessibility_discussed_date: n.accessibility_discussed_date_,
            monitored_by_clinician: n.monitored_by_clinician }}"""
    )
    children = (MigrateDraysonHealthProductChange,)


class MigratePersonalAddress(MigrationBase):
    node = "PersonalAddress"
    nodes_human = "Personal Addresses"
    sql_model = sqlmodels.PersonalAddress
    query = (
        f"MATCH (n:PersonalAddress)-[:HAS_PERSONAL_ADDRESS]-(p:Patient) RETURN {{{COMMON_FIELDS},"
        f"""patient_id: p.uuid,
            lived_from: n.lived_from,
            lived_until: n.lived_until,
            address_line_1: n.address_line_1,
            address_line_2: n.address_line_2,
            address_line_3: n.address_line_3,
            address_line_4: n.address_line_4,
            locality: n.locality,
            region: n.region,
            postcode: n.postcode,
            country: n.country }}"""
    )
    children = ()


class MigrateTermsAgreement(MigrationBase):
    def fix_node(self, n: dict) -> dict:
        return n | {
            "created": datetime.utcfromtimestamp(n["created"]).replace(
                tzinfo=timezone.utc
            ),
            "modified": datetime.utcfromtimestamp(n["modified"]).replace(
                tzinfo=timezone.utc
            ),
            "accepted_timestamp": datetime.utcfromtimestamp(
                n["accepted_timestamp"]
            ).replace(tzinfo=timezone.utc)
            if n.get("accepted_timestamp")
            else None,
            "tou_accepted_timestamp": datetime.utcfromtimestamp(
                n["tou_accepted_timestamp"]
            ).replace(tzinfo=timezone.utc)
            if n.get("tou_accepted_timestamp")
            else None,
            "patient_notice_accepted_timestamp": datetime.utcfromtimestamp(
                n["patient_notice_accepted_timestamp"]
            ).replace(tzinfo=timezone.utc)
            if n.get("patient_notice_accepted_timestamp")
            else None,
        }

    node = "TermsAgreement"
    nodes_human = "Terms Agreements"
    sql_model = sqlmodels.TermsAgreement
    query = (
        f"MATCH (n:TermsAgreement)-[:HAS_ACCEPTED]-(p:Patient) RETURN {{{COMMON_FIELDS},"
        f"""patient_id: p.uuid,
            product_name: n.product_name,
            version: n.version,
            accepted_timestamp: n.accepted_timestamp,
            tou_version: n.tou_version,
            tou_accepted_timestamp: n.tou_accepted_timestamp,
            patient_notice_version: n.patient_notice_version,
            patient_notice_accepted_timestamp: n.patient_notice_accepted_timestamp }}"""
    )
    children = ()


class MigratePatient(MigrationBase):
    node = "Patient"
    nodes_human = "Patients"
    sql_model = sqlmodels.Patient
    query = f"""MATCH (n:Patient)
        OPTIONAL MATCH (n)-[:HAS_RECORD]->(r:Record)
        OPTIONAL MATCH (n)-[:CHILD_OF]->(parent:Patient) RETURN {{{COMMON_FIELDS},
        record_id: r.uuid,
        patient_type: CASE
                        WHEN 'Baby' IN LABELS(n) THEN 'baby'
                        WHEN 'SendPatient' IN LABELS(n) THEN 'send'
                        ELSE 'patient' END,
        first_name: n.first_name,
        last_name: n.last_name,
        phone_number: n.phone_number,
        dob: n.dob,
        dod: n.dod,
        nhs_number: n.nhs_number,
        hospital_number: n.hospital_number,
        allowed_to_text: n.allowed_to_text,
        allowed_to_email: n.allowed_to_email,
        email_address: n.email_address,
        ethnicity: n.ethnicity,
        ethnicity_other: n.ethnicity_other,
        sex: n.sex,
        height_in_mm: n.height_in_mm,
        weight_in_g: n.weight_in_g,
        highest_education_level: n.highest_education_level,
        highest_education_level_other: n.highest_education_level_other,
        accessibility_considerations: n.accessibility_considerations,
        accessibility_considerations_other: n.accessibility_considerations_other,
        other_notes: n.other_notes,
        locations: n.locations,
        bookmarked_at_locations: n.bookmarked_at_locations,
        has_been_bookmarked: n.has_been_bookmarked,
        parent_patient_id: parent.uuid,
        fhir_resource_id: n.fhir_resource_id }}"""
    children = (
        MigrateDraysonHealthProduct,
        MigratePersonalAddress,
        MigrateTermsAgreement,
    )


class MigrateDelivery(MigrationBase):
    node = "Delivery"
    nodes_human = "Deliveries"
    sql_model = sqlmodels.Delivery
    query = f"""MATCH (n:Delivery)-[:HAS_DELIVERY]-(p:Pregnancy)
            OPTIONAL MATCH (n)--(b:Patient) RETURN {{{COMMON_FIELDS}, 
            pregnancy_id: p.uuid,
            patient_id: b.uuid,
            patient: NULL,
            birth_outcome: n.birth_outcome,
            outcome_for_baby: n.outcome_for_baby,
            neonatal_complications: n.neonatal_complications,
            neonatal_complications_other: n.neonatal_complications_other,
            admitted_to_special_baby_care_unit: n.admitted_to_special_baby_care_unit,
            birth_weight_in_grams: n.birth_weight_in_grams,
            length_of_postnatal_stay_for_baby: n.length_of_postnatal_stay_for_baby,
            apgar_1_minute: n.apgar_1_minute,
            apgar_5_minute: n.apgar_5_minute,
            feeding_method: n.feeding_method,
            date_of_termination: n.date_of_termination_ }}"""
    children = ()


class MigratePregnancy(MigrationBase):
    node = "Pregnancy"
    nodes_human = "Pregnancies"
    sql_model = sqlmodels.Pregnancy
    query = (
        f"MATCH (n:Pregnancy)-[:HAS_PREGNANCY]-(r:Record) RETURN {{{COMMON_FIELDS},"
        f"""record_id: r.uuid,
            estimated_delivery_date: n.estimated_delivery_date,
            planned_delivery_place: n.planned_delivery_place,
            length_of_postnatal_stay_in_days: n.length_of_postnatal_stay_in_days,
            colostrum_harvesting: n.colostrum_harvesting,
            expected_number_of_babies: n.expected_number_of_babies,
            pregnancy_complications: n.pregnancy_complications,
            induced: n.induced,
            height_at_booking_in_mm: n.height_at_booking_in_mm,
            weight_at_booking_in_g: n.weight_at_booking_in_g,
            weight_at_diagnosis_in_g: n.weight_at_diagnosis_in_g,
            weight_at_36_weeks_in_g: n.weight_at_36_weeks_in_g,
            delivery_place: n.delivery_place,
            delivery_place_other: n.delivery_place_other,
            first_medication_taken: n.first_medication_taken,
            first_medication_taken_recorded: n.first_medication_taken_recorded }}"""
    )
    children = (MigrateDelivery,)


class MigrateNote(MigrationBase):
    node = "Note"
    nodes_human = "Notes"
    sql_model = sqlmodels.Note
    query = (
        f"MATCH (n:Note)--(r:Record) RETURN {{{COMMON_FIELDS},"
        f"""record_id: r.uuid,
            content: n.content,
            clinician_uuid: n.clinician_uuid }}"""
    )
    children = ()


class MigrateHistory(MigrationBase):
    node = "History"
    nodes_human = "Histories"
    sql_model = sqlmodels.History
    query = (
        f"MATCH (n:History)<-[:HAS_HISTORY]-(r:Record) RETURN {{{COMMON_FIELDS},"
        f"""record_id: r.uuid,
            parity: n.parity,
            gravidity: n.gravidity }}"""
    )
    children = ()


class MigrateObservableEntities(MigrationBase):
    node = "ObservableEntity"
    nodes_human = "Observable Entities"
    sql_model = sqlmodels.ObservableEntity
    query = (
        f"MATCH (n:ObservableEntity)-[:RELATED_OBSERVATION]-(d:Diagnosis) RETURN {{{COMMON_FIELDS},"
        f"""diagnosis_id: d.uuid,
        sct_code: n.sct_code,
        date_observed: n.date_observed,
        value_as_string: n.value_as_string,
        metadata_: n.metadata }}"""
    )
    children = ()

    def fix_node(self, n: dict) -> dict:
        return n | {
            "created": datetime.utcfromtimestamp(n["created"]).replace(
                tzinfo=timezone.utc
            ),
            "modified": datetime.utcfromtimestamp(n["modified"]).replace(
                tzinfo=timezone.utc
            ),
            "metadata_": json.loads(n["metadata_"]),
        }


class MigrateReadingsPlanChange(MigrationBase):
    node = "ReadingsPlanChange"
    nodes_human = "Readings Plan Changes"
    sql_model = sqlmodels.ReadingsPlanChange
    query = (
        f"MATCH (n:ReadingsPlanChange)<-[:HAS_CHANGE]-(rp:ReadingsPlan) RETURN {{{COMMON_FIELDS},"
        f"""readings_plan_id: rp.uuid,
        days_per_week_to_take_readings: n.days_per_week_to_take_readings,
        readings_per_day: n.readings_per_day }}"""
    )
    children = ()


class MigrateReadingsPlan(MigrationBase):
    node = "ReadingsPlan"
    nodes_human = "Readings Plans"
    sql_model = sqlmodels.ReadingsPlan
    query = (
        f"MATCH (n:ReadingsPlan)-[:HAS_READINGS_PLAN]-(d:Diagnosis) RETURN {{{COMMON_FIELDS},"
        f"""diagnosis_id: d.uuid,
        days_per_week_to_take_readings: n.days_per_week_to_take_readings,
        readings_per_day: n.readings_per_day,
        start_date: n.start_date,
        end_date: n.end_date,
        sct_code: n.sct_code,
        changes: NULL }}"""
    )
    children = (MigrateReadingsPlanChange,)


class MigrateDoseChange(MigrationBase):
    node = "DoseChange"
    nodes_human = "Dose Changes"
    sql_model = sqlmodels.DoseChange
    query = (
        f"MATCH (n:DoseChange)<-[:HAS_CHANGE]-(d:Dose) RETURN {{{COMMON_FIELDS},"
        f"""dose_id: d.uuid,
        medication_id: n.medication_id,
        dose_amount: n.dose_amount,
        routine_sct_code: n.routine_sct_code }}"""
    )
    children = ()


class MigrateDoseHistory(MigrationBase):
    node = "DoseHistory"
    nodes_human = "Dose Histories"
    sql_model = sqlmodels.DoseHistory
    query = f"""MATCH (n:DoseHistory)
            MATCH (n)-[:RELATES_TO_DOSE]->(d:Dose)
            OPTIONAL MATCH (n)<-[:HAD_DOSE]-(mp:ManagementPlan) RETURN {{{COMMON_FIELDS},
            management_plan_id: mp.uuid, dose_id: d.uuid,
            clinician_uuid: n.clinician_uuid, action: n.action }}"""
    children = ()


class MigrateDose(MigrationBase):
    node = "Dose"
    nodes_human = "Doses"
    sql_model = sqlmodels.Dose
    query = (
        f"""MATCH (n:Dose)
        OPTIONAL MATCH (n)-[:HAS_DOSE]-(mp:ManagementPlan) RETURN {{{COMMON_FIELDS},"""
        f"""management_plan_id: mp.uuid,
        medication_id: n.medication_id,
        dose_amount: n.dose_amount,
        routine_sct_code: n.routine_sct_code,
        changes: NULL,
        plan_add_history: FALSE }}"""
    )
    children = (MigrateDoseChange, MigrateDoseHistory)


class MigrateNonMedicationAction(MigrationBase):
    node = "NonMedicationAction"
    nodes_human = "Non-medication Actions"
    sql_model = sqlmodels.NonMedicationAction
    query = (
        f"MATCH (n:NonMedicationAction)-[:HAS_ACTION]-(mp:ManagementPlan) RETURN {{{COMMON_FIELDS},"
        f"""management_plan_id: mp.uuid,
        action_sct_code: n.action_sct_code }}"""
    )
    children = ()


class MigrateManagementPlan(MigrationBase):
    node = "ManagementPlan"
    nodes_human = "Management Plans"
    sql_model = sqlmodels.ManagementPlan
    query = (
        f"MATCH (n:ManagementPlan)<-[:HAS_MANAGEMENT_PLAN]-(d:Diagnosis) RETURN {{{COMMON_FIELDS},"
        f"""diagnosis_id: d.uuid,
        plan_history: n.plan_history,
        start_date: n.start_date,
        end_date: n.end_date,
        sct_code: n.sct_code }}"""
    )
    children = (MigrateNonMedicationAction, MigrateDose)


class MigrateDiagnosis(MigrationBase):
    node = "Diagnosis"
    nodes_human = "Diagnoses"
    sql_model = sqlmodels.Diagnosis
    query = (
        f"MATCH (n:Diagnosis)<-[:HAS_DIAGNOSIS]-(r:Record) RETURN {{{COMMON_FIELDS},"
        f"""record_id: r.uuid,
            sct_code: n.sct_code,
            diagnosis_other: n.diagnosis_other,
            diagnosed: n.diagnosed_,
            resolved: n.resolved_,
            presented: n.presented_,
            episode: n.episode,
            diagnosis_tool: n.diagnosis_tool,
            diagnosis_tool_other: n.diagnosis_tool_other,
            risk_factors: n.risk_factors }}"""
    )
    children = (MigrateManagementPlan, MigrateReadingsPlan, MigrateObservableEntities)


class MigrateRecord(MigrationBase):
    node = "Record"
    nodes_human = "Records"
    sql_model = sqlmodels.Record
    query = f"""MATCH (n:Record)
     RETURN {{{COMMON_FIELDS}, history: null }}"""
    children = (
        MigrateVisit,
        MigratePatient,
        MigratePregnancy,
        MigrateNote,
        MigrateHistory,
        MigrateDiagnosis,
    )


def migrate_patients() -> None:
    """
    Migrates all the different record types
    """
    click.echo(f"{stamp()} Migrating patient data to Postgresql")

    migrated_count = MigrateRecord().migrate()

    if migrated_count == 0:
        click.echo(f"{stamp()} Nothing to migrate")
    else:
        click.echo(f"{stamp()} Migration completed")
