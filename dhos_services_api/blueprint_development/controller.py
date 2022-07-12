from flask import current_app
from flask_batteries_included.sqldb import db as sqldb
from she_logging import logger

from dhos_services_api import sqlmodels
from dhos_services_api.clients.common_client import make_json_object_request
from dhos_services_api.neodb import db as neodb

ITERATIVE_DB_DROP_QUERY = "MATCH (n) WITH n LIMIT 1000 DETACH DELETE n RETURN count(n)"


def reset_database() -> None:

    # Reset neo4j
    if current_app.config["NEO4J_ENABLED"]:
        while True:
            results, _ = neodb.cypher_query(ITERATIVE_DB_DROP_QUERY)
            if not results[0][0]:
                break

    # Reset postgres
    try:
        # Order of deletion matters for Delivery and Patient
        sqldb.session.query(sqlmodels.Delivery).delete()
        sqldb.session.query(sqlmodels.Patient).delete()
        sqldb.session.commit()
    except Exception:
        logger.exception("Drop SQL data failed")
        sqldb.session.rollback()

    # Because we're still in the process of migrating, also reset the users API.
    logger.info("Reset users")
    base_url: str = current_app.config["DHOS_USERS_API_HOST"]
    full_url: str = f"{base_url}/drop_data"
    result = make_json_object_request(method="post", url=full_url, json_data={})
    logger.info("Users reset returned %r", result)
