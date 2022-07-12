"""
Migration of user data from neo4j to dhos-users-api.

Usage:
    flask
"""
from __future__ import annotations

import itertools
from typing import Generator, Iterable, Sequence

import click
import requests
from flask import current_app
from neomodel import db

from dhos_services_api.migrations.jwt import get_system_jwt
from dhos_services_api.models.clinician import Clinician
from dhos_services_api.models.terms_agreement import TermsAgreement

MIGRATION_PERMISSIONS = [
    "read:gdm_clinician_all",
    "read:send_clinician_all",
    "write:clinician_migration",  # Special permission just for this migration.
]


def fetch_existing_uuids_from_users() -> set[str]:
    jwt = get_system_jwt(permissions=MIGRATION_PERMISSIONS)
    response = requests.get(
        f"{current_app.config['DHOS_USERS_API_HOST']}/dhos/v1/clinicians",
        params={"expanded": False, "compact": True},
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=30,
    )
    response.raise_for_status()

    user_uuids: set[str] = {u["uuid"] for u in response.json()}
    click.echo(f"Found {len(user_uuids)} existing clinicians")
    return user_uuids


def fetch_all_clinicians_from_neo4j() -> list[dict]:
    """
    Returns all clinicians and associated products
    """
    click.echo(f"Fetching clinicians from database")
    query = """MATCH (c:Clinician)
    OPTIONAL MATCH(c)-[:HAS_ACCEPTED]->(ta:TermsAgreement)
    RETURN c, collect(ta) as ta
    """
    results: Sequence[tuple[dict, list[dict]]]
    results, meta = db.cypher_query(
        query,
    )

    clinicians: list[dict] = []
    for clinician_node, terms_nodes in results:
        clinician_model: Clinician = Clinician.inflate(clinician_node)
        clinician_details = clinician_model.to_dict()
        # Users API needs all terms agreements
        del clinician_details["terms_agreement"]
        clinician_details["terms_agreements"] = [
            TermsAgreement.inflate(tn).to_dict() for tn in terms_nodes
        ]
        # Add extra fields that aren't in to_dict()
        clinician_details["booking_reference"] = clinician_model.booking_reference
        clinician_details["password_salt"] = clinician_model.password_salt
        clinician_details["password_hash"] = clinician_model.password_hash
        clinicians.append(clinician_details)
    click.echo(f"Retrieved {len(clinicians)} clinicians from NEO4J")
    return clinicians


def bulk_create_clinicians(clinicians: list[dict]) -> None:
    if not clinicians:
        click.echo("Nothing to migrate")
        return

    def chunks(
        iterable: Iterable[dict], size: int = 100
    ) -> Generator[list[dict], None, None]:
        """Split an iterable into smaller lists"""
        it = iter(iterable)
        while chunk := list(itertools.islice(it, size)):
            yield chunk

    click.echo(f"Bulk uploading {len(clinicians)} clinicians")
    jwt = get_system_jwt(permissions=MIGRATION_PERMISSIONS)
    created: int = 0
    for clinicians_chunk in chunks(clinicians):
        click.echo(f"Bulk uploading chunk of {len(clinicians_chunk)} clinicians")
        response = requests.post(
            f"{current_app.config['DHOS_USERS_API_HOST']}/dhos/v1/clinician/bulk",
            json=clinicians_chunk,
            headers={"Authorization": f"Bearer {jwt}"},
            timeout=30,
        )
        response.raise_for_status()
        created += response.json()["created"]
    click.echo(f"Created {created} clinicians")
    click.echo("Migration completed")


def migrate_clinicians() -> None:
    """
    Fetch existing uuids from users API
    Fetch all clinicians from NEO4J, filter out any that already exist in users API
    Post bulk create to users API
    """
    click.echo("Migrating clinician data to users API.")
    existing_users: set[str] = fetch_existing_uuids_from_users()
    new_clinicians: list[dict] = [
        u for u in fetch_all_clinicians_from_neo4j() if u["uuid"] not in existing_users
    ]
    bulk_create_clinicians(new_clinicians)
