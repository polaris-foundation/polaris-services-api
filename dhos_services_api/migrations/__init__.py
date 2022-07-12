from flask.cli import AppGroup

from dhos_services_api.migrations import clinician, patient

migrate_cli = AppGroup("migrate")


@migrate_cli.command("clinicians")
def migrate_clinicians() -> None:
    clinician.migrate_clinicians()


@migrate_cli.command("patients")
def migrate_patients() -> None:
    patient.migrate_patients()
