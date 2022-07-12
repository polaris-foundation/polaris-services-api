from io import StringIO
from pathlib import Path

import connexion
import kombu_batteries_included
from connexion import FlaskApp
from flask import Flask
from flask_batteries_included import augment_app as fbi_augment_app
from flask_batteries_included import sqldb
from flask_batteries_included.config import is_not_production_environment
from neomodel import install_all_labels

from dhos_services_api.blueprint_development import development_blueprint
from dhos_services_api.blueprint_patients import patients_blueprint
from dhos_services_api.config import init_config
from dhos_services_api.error_handler import init_neo4j_error_handler
from dhos_services_api.helpers.cli import add_cli_command
from dhos_services_api.migrations import migrate_cli
from dhos_services_api.neodb import init_db


def create_app(testing: bool = False) -> Flask:
    openapi_dir: Path = Path(__file__).parent / "openapi"
    connexion_app: FlaskApp = connexion.App(
        __name__,
        specification_dir=openapi_dir,
        options={"swagger_ui": is_not_production_environment()},
    )
    connexion_app.add_api("openapi.yaml")
    app: Flask = fbi_augment_app(
        app=connexion_app.app,
        use_auth0=True,
        use_pgsql=True,
        testing=testing,
    )

    # Apply config
    init_config(app)

    # Register custom error handlers
    init_neo4j_error_handler(app)

    # Configure the Neo4J database connection.
    if app.config["NEO4J_ENABLED"]:
        app.logger.info("Neo4J enabled, initializing")
        init_db(app=app)
        # Set up neomodel constraints.
        output: StringIO = StringIO()
        install_all_labels(stdout=output)
        app.logger.info("Created neomodel constraints")
    else:
        app.logger.info("Neo4J disabled, skipping initialization")

    # Initialise k-b-i library to allow publishing to RabbitMQ.
    kombu_batteries_included.init()

    # Configure the sqlalchemy connection.
    sqldb.init_db(app=app, testing=testing)

    # API blueprint registration
    app.register_blueprint(patients_blueprint)
    app.logger.info("Registered patients API blueprint")

    # Development blueprint registration if in a lower environment
    if is_not_production_environment():
        app.register_blueprint(development_blueprint)
        app.logger.info("Registered development blueprint")

    add_cli_command(app)
    app.cli.add_command(migrate_cli)

    app.logger.info("App ready to serve requests")

    return app
