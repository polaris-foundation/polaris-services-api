import time

from flask import Blueprint, Response, abort, current_app, jsonify
from flask_batteries_included.helpers.security import protected_route
from flask_batteries_included.helpers.security.endpoint_security import (
    and_,
    argument_present,
    key_present,
    or_,
    scopes_present,
)

from dhos_services_api.blueprint_development.controller import reset_database

development_blueprint = Blueprint("gdm/dev", __name__, template_folder="templates")


@development_blueprint.route("/drop_data", methods=["POST"])
@protected_route(key_present("system_id"))
def drop_data_route() -> Response:

    if current_app.config["ALLOW_DROP_DATA"] is not True:
        abort(403, "Cannot drop data in this environment")

    start = time.time()

    reset_database()  # this resets both neo4j and postgres

    total_time = time.time() - start

    return jsonify({"complete": True, "time_taken": str(total_time) + "s"})
