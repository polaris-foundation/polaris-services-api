from typing import Dict

import pytest
from flask import Flask
from flask.ctx import AppContext
from flask.testing import FlaskClient
from pytest_mock import MockFixture


@pytest.mark.usefixtures("mock_retrieve_jwt_claims", "mock_bearer_validation")
class TestDevRoutes:
    @pytest.fixture
    def mock_reset_database(self, mocker: MockFixture) -> None:
        from dhos_services_api import blueprint_development

        mocker.patch.object(blueprint_development, "reset_database")

    def test_drop_data_prod(
        self,
        mock_reset_database: MockFixture,
        app: Flask,
        client: FlaskClient,
        app_context: AppContext,
        jwt_system: Dict,
    ) -> None:
        app.config["ENVIRONMENT"] = "PRODUCTION"
        response = client.post("/drop_data")
        assert response.status_code == 403

    def test_drop_data_non_prod(
        self,
        mock_reset_database: MockFixture,
        app: Flask,
        client: FlaskClient,
        app_context: AppContext,
        jwt_system: Dict,
    ) -> None:
        app.config["ALLOW_DROP_DATA"] = True
        app.config["ENVIRONMENT"] = "TRAINING"
        response = client.post("/drop_data")
        assert response.status_code == 200
