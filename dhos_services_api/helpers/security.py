from typing import Any, Dict

from flask import request
from she_logging import logger


def current_user_is_specified_patient_or_any_gdm_clinician(
    jwt_claims: Dict, claims_map: Dict, **kwargs: Any
) -> bool:
    if jwt_claims.get("clinician_id") and request.args.get("product_name") == "GDM":
        return True

    if not request.view_args:
        logger.error("No view_args available")
        return False

    patient_id = request.view_args.get("patient_id")

    if patient_id == jwt_claims.get("patient_id") and patient_id is not None:
        return True

    return False
