from datetime import date, datetime, timezone

import pytest
from flask import g
from flask_batteries_included.helpers import generate_uuid
from flask_sqlalchemy import SQLAlchemy
from pytest_mock import MockerFixture

from dhos_services_api.sqlmodels.drayson_health_product import DraysonHealthProduct


@pytest.mark.usefixtures("app", "uses_sql_database")
class TestDraysonHealthProduct:
    @pytest.fixture
    def dh_product(self) -> dict:
        return {
            "product_name": "SEND",
            "opened_date": "2018-10-16",
        }

    def test_create_drayson_health_product_minimal(self, dh_product: dict) -> None:
        dhp = DraysonHealthProduct.new(**dh_product)
        assert dhp.opened_date == dh_product["opened_date"]

    def test_pre_save_hook(
        self,
        _db: SQLAlchemy,
        mocker: MockerFixture,
        patient_uuid: str,
        dh_product: dict,
    ) -> None:
        mocker.patch.dict(g.jwt_claims, {"clinician_id": "rob"})
        dhp_uuid = generate_uuid()

        # Neo4j tests used freezer to set times but the sql models ignore the fake times from freezer
        time_before_create = datetime.utcnow().replace(tzinfo=timezone.utc)
        DraysonHealthProduct.new(uuid=dhp_uuid, patient_id=patient_uuid, **dh_product)
        _db.session.commit()
        time_after_commit = datetime.utcnow().replace(tzinfo=timezone.utc)
        dhp: DraysonHealthProduct = _db.session.get(DraysonHealthProduct, dhp_uuid)
        assert dhp is not None
        assert dhp.closed_date is None
        assert time_before_create < dhp.created < time_after_commit
        assert time_before_create < dhp.modified < time_after_commit
        assert dhp.modified_by == "rob"

        mocker.patch.dict(g.jwt_claims, {"clinician_id": "sherlock"})
        dhp.closed_date = "2020-06-01"
        _db.session.add(dhp)
        _db.session.commit()
        time_after_update = datetime.utcnow().replace(tzinfo=timezone.utc)

        dhp = _db.session.get(DraysonHealthProduct, dhp_uuid)
        assert dhp.closed_date == date(2020, 6, 1)
        # creation metadta hasn't changed
        assert time_before_create < dhp.created < time_after_commit
        assert dhp.created_by == "rob"
        # modification metadata has changed
        assert time_after_commit < dhp.modified < time_after_update
        assert dhp.modified_by == "sherlock"
