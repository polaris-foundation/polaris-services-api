import copy
from typing import Callable, Optional

import pytest
from flask_batteries_included.helpers import generate_uuid

from dhos_services_api.models.dose import Dose


@pytest.mark.usefixtures("app")
class TestDose:
    def test_on_patch(self, node_factory: Callable) -> None:
        dose_details = {"medication_id": generate_uuid(), "dose_amount": 1.5}
        dose_uuid: str = node_factory("Dose", **dose_details)
        original_dose: Optional[Dose] = Dose.nodes.get_or_none(uuid=dose_uuid)
        assert original_dose is not None
        dose_update = {
            "medication_id": generate_uuid(),
            "dose_amount": 2.5,
        }
        original_dose.on_patch(copy.copy(dose_update))
        updated_dose: Optional[Dose] = Dose.nodes.get_or_none(uuid=dose_uuid)
        assert updated_dose is not None
        assert updated_dose.medication_id == dose_update["medication_id"]
        assert updated_dose.dose_amount == dose_update["dose_amount"]
