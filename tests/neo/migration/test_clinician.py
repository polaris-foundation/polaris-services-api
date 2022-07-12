from __future__ import annotations

from typing import Callable

import pytest
from flask import Flask
from flask.testing import FlaskCliRunner
from requests_mock import Mocker
from requests_mock.adapter import _Matcher


class TestClinicianMigration:
    @pytest.fixture
    def runner(self, app: Flask) -> FlaskCliRunner:
        return app.test_cli_runner()

    @pytest.fixture
    def mock_get_clinicians(self, requests_mock: Mocker) -> _Matcher:
        return requests_mock.get(
            "http://dhos-users/dhos/v1/clinicians", json=[{"uuid": "1"}]
        )

    @pytest.fixture
    def mock_post_bulk_clinicians(self, requests_mock: Mocker) -> _Matcher:
        return requests_mock.post(
            "http://dhos-users/dhos/v1/clinician/bulk",
            json={"created": 42},
        )

    def test_nothing_to_migrate(
        self, runner: FlaskCliRunner, mock_get_clinicians: _Matcher
    ) -> None:
        result = runner.invoke(args=["migrate", "clinicians"])

        assert mock_get_clinicians.called_once
        assert "Nothing to migrate" in result.output

    def test_migration(
        self,
        runner: FlaskCliRunner,
        mock_get_clinicians: _Matcher,
        mock_post_bulk_clinicians: _Matcher,
        clinician_factory: Callable,
    ) -> None:
        # Arrange
        clinician_uuids: set[str] = {
            clinician_factory(
                first_name=f"first-name-{i}",
                last_name=f"last-name-{i}",
                nhs_smartcard_number="123",
                product_name="SEND",
                expiry=None,
                login_active=True,
            )
            for i in range(42)
        }
        result = runner.invoke(args=["migrate", "clinicians"])

        assert mock_get_clinicians.called_once
        assert mock_post_bulk_clinicians.called_once
        assert {
            c["uuid"] for c in mock_post_bulk_clinicians.last_request.json()
        } == clinician_uuids
        assert "Bulk uploading 42 clinicians" in result.output
        assert "Created 42 clinicians" in result.output
        assert "Migration completed" in result.output
