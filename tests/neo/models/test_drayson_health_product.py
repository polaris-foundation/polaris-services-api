from typing import Dict

import pytest
from freezegun.api import FrozenDateTimeFactory
from pytest_mock import MockerFixture

from dhos_services_api.models.drayson_health_product import DraysonHealthProduct


@pytest.mark.usefixtures("app")
class TestDraysonHealthProduct:
    @pytest.fixture
    def dh_product(self) -> Dict:
        return {
            "product_name": "SEND",
            "opened_date": "2018-10-16",
            "created_by": "rob",
            "modified_by": "rob",
        }

    def test_create_drayson_health_product_minimal(self, dh_product: Dict) -> None:
        dhp = DraysonHealthProduct.new(**dh_product)
        assert dhp.opened_date == dh_product["opened_date"]

    def test_pre_save_hook(
        self, mocker: MockerFixture, freezer: FrozenDateTimeFactory, dh_product: Dict
    ) -> None:
        freezer.move_to("2020-01-01T01:01:01.001Z")
        mocker.patch(
            "dhos_services_api.neodb.current_jwt_user",
            return_value="rob",
        )
        dhp = DraysonHealthProduct.new(**dh_product)
        dhp.save()

        assert dhp.closed_date is None
        assert dhp.modified == "2020-01-01T01:01:01.001Z"
        assert dhp.modified_by == "rob"

        freezer.move_to("2020-02-02T02:02:02.002Z")
        mocker.patch(
            "dhos_services_api.neodb.current_jwt_user",
            return_value="sherlock",
        )
        dhp.closed_date = "2020-06-01"
        dhp.save()

        assert dhp.closed_date == "2020-06-01"
        assert dhp.modified == "2020-02-02T02:02:02.002Z"
        assert dhp.modified_by == "sherlock"
        dhp.delete()
