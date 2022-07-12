from collections import Callable
from typing import Any, Dict

import pytest


@pytest.mark.usefixtures("mock_retrieve_jwt_claims", "mock_bearer_validation")
class TestTerms:
    @pytest.fixture
    def terms_agreement_factory(self) -> Callable:
        def make_terms(
            product_name: str = "GDM",
            version: int = 123,
            timestamp: str = "2019-01-01T12:01:01.000+00:00",
        ) -> Dict[str, Any]:
            return {
                "product_name": product_name,
                "version": version,
                "accepted_timestamp": timestamp,
            }

        return make_terms
