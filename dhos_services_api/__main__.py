import os

from waitress import serve

from dhos_services_api.app import create_app

SERVER_PORT = os.getenv("SERVER_PORT", 5000)


if __name__ == "__main__":
    app = create_app()
    serve(app, host="0.0.0.0", port=SERVER_PORT)  # NOSONAR
    # even if you take this from an env var and default to 0.0.0.0,
    # sonar still complains that it is not configurable :(
