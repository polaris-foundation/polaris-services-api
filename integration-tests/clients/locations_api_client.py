from typing import Any, Dict, List, Optional

import requests
from behave import use_fixture
from behave.runner import Context
from environs import Env
from helpers.security import get_system_token
from requests import Response

base_url: str = Env().str("DHOS_LOCATIONS_BASE_URL", "http://dhos-locations-api:5000")


def get_location(context: Context, location_uuid: str) -> Dict:
    use_fixture(get_system_token, context)
    response: Response = requests.get(
        f"{base_url}/dhos/v1/location/{location_uuid}",
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()


def get_all_locations(
    context: Context,
    product_name: str,
    location_types: str = None,
    compact: bool = False,
    active: Optional[bool] = None,
    children: Optional[bool] = False,
) -> Dict:
    use_fixture(get_system_token, context)
    params: Dict[str, Any] = {
        "product_name": product_name,
        "location_types": location_types,
        "compact": compact,
        "active": active,
        "children": children,
    }

    response: Response = requests.get(
        f"{base_url}/dhos/v1/location/search",
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        params=params,
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()


def reset_locations_api(context: Context) -> None:
    use_fixture(get_system_token, context)
    response: Response = requests.post(
        f"{base_url}/drop_data",
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        timeout=15,
    )
    assert response.status_code == 200


def post_many_locations(context: Context, location_list: List[Dict]) -> Response:
    response = requests.post(
        f"{base_url}/dhos/v1/location/bulk",
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        json=location_list,
        timeout=150,
    )
    return response


def post_location(context: Context, location: Dict) -> Dict:
    use_fixture(get_system_token, context)

    response: Response = requests.post(
        f"{base_url}/dhos/v1/location",
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        json=location,
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()


def patch_location(context: Context, location_uuid: str, location: Dict) -> Dict:
    use_fixture(get_system_token, context)

    response: Response = requests.patch(
        f"{base_url}/dhos/v1/location/{location_uuid}",
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        json=location,
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()
