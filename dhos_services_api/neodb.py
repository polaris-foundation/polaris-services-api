import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Union
from uuid import uuid4

import neomodel
from flask import Flask
from flask_batteries_included.blueprint_monitoring import healthcheck
from flask_batteries_included.helpers.security.jwt import current_jwt_user
from flask_batteries_included.helpers.timestamp import (
    parse_datetime_to_iso8601,
    parse_iso8601_to_datetime,
)
from neobolt.exceptions import TransientError
from neomodel import Database, DateTimeProperty, StringProperty, db
from she_logging import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logging.getLogger("neo4j.bolt").setLevel(logging.WARNING)


def enable_retry(database: Database = db) -> None:
    # https://sensynehealth.atlassian.net/browse/PLAT-841

    if hasattr(database.cypher_query, "retry"):
        raise ValueError("Retry has already been enabled.")

    logger.info("Enabling retry on TransientError.")
    database.cypher_query = retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(),
        retry=retry_if_exception_type(TransientError),
        reraise=True,
    )(database.cypher_query)


def init_db(app: Flask, testing: bool = False) -> None:
    """Set up the Neo4J connection and add a healthcheck"""
    # TODO: set up this connection in a less fragmented way.
    db.set_connection(app.config["NEO4J_DATABASE_URI"])
    neomodel.config.DATABASE_URL = app.config["NEO4J_DATABASE_URI"]

    if not testing:
        # Only add db healthchecks if not testing
        healthcheck.add_check(database_connectivity_test)
        enable_retry()


def database_connectivity_test() -> Tuple[bool, str]:
    """Healthcheck for database connectivity"""
    try:
        db.cypher_query("MATCH () RETURN 1 LIMIT 1;")
    except Exception as e:
        return False, "Database not available. Reason: " + str(e)

    return True, "Database ok"


class NeomodelIdentifier:
    """
    This class is designed to be used by classes extending `neomodel.StructuredNode`. It provides
    common identifier fields for models and includes a pre_save() hook that automatically updates
    the `modified` and `modified_by` fields.
    """

    uuid: str = StringProperty(unique_index=True, default=uuid4)
    uri: str = StringProperty(
        default="http://snomed.codes"
    )  # TODO: fix this, obviously

    created_: Optional[datetime] = DateTimeProperty(
        default_now=True, db_property="created"
    )
    created_by_: str = StringProperty(default=current_jwt_user)

    modified_: Optional[datetime] = DateTimeProperty(
        default_now=True, db_property="modified"
    )
    modified_by_: str = StringProperty(default=current_jwt_user)

    def pre_save(self) -> None:
        """
        Executed automatically when calling save() on the object directly or when
        creating a new relationship via connect(). Updates the `modified` and
        `modified_by` fields.
        """
        self.modified = datetime.utcnow()
        self.modified_by = current_jwt_user()

    def on_patch(self, *args: Any, **kwargs: Any) -> None:
        """
        Kept only to avoid breaking changes - the pre_save() hook above, which is
        called automatically, has deprecated this function.
        """
        self.modified = datetime.utcnow()
        self.modified_by = current_jwt_user()

    @property
    def created(self) -> Optional[str]:
        dt = self.created_.replace(tzinfo=timezone.utc) if self.created_ else None
        return parse_datetime_to_iso8601(dt)

    @created.setter
    def created(self, value: Union[str, datetime]) -> None:
        if isinstance(value, datetime):
            self.created_ = value
        else:
            self.created_ = parse_iso8601_to_datetime(value)

    @property
    def modified(
        self,
    ) -> Any:  # Returns Any as otherwise mypy thinks assigning to it should be a str
        dt = self.modified_.replace(tzinfo=timezone.utc) if self.modified_ else None
        return parse_datetime_to_iso8601(dt)

    @modified.setter
    def modified(self, value: Union[str, datetime]) -> None:
        if isinstance(value, datetime):
            self.modified_ = value
        else:
            self.modified_ = parse_iso8601_to_datetime(value)

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

    def pack_identifier(self) -> Dict:
        return {
            "uuid": self.uuid,
            "created": self.created,
            "created_by": self.created_by,
            "modified": self.modified,
            "modified_by": self.modified_by,
        }

    def compack_identifier(self) -> Dict:
        return {"created": self.created, "uuid": self.uuid}
