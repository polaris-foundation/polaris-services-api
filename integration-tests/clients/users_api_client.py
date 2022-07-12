from typing import Any, Dict, List, Optional

import requests
from behave import use_fixture
from behave.runner import Context
from environs import Env
from helpers.security import get_login_token, get_system_token
from requests import Response

base_url: str = Env().str("DHOS_USERS_BASE_URL", "http://dhos-users-api:5000")


def get_all_clinicians(
    context: Context,
    product_name: Optional[str] = None,
    compact: bool = True,
    expanded: bool = False,
) -> dict:
    use_fixture(get_system_token, context)
    params: Dict[str, Any] = {
        "product_name": product_name,
        "compact": compact,
        "expanded": expanded,
    }

    response: Response = requests.get(
        f"{base_url}/dhos/v1/clinicians",
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        params=params,
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()


def reset_users_api(context: Context) -> None:
    use_fixture(get_system_token, context)
    response: Response = requests.post(
        f"{base_url}/drop_data",
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        timeout=15,
    )
    assert response.status_code == 200


def post_clinician(context: Context, clinician: dict) -> str:
    use_fixture(get_system_token, context)

    response: Response = requests.post(
        f"{base_url}/dhos/v1/clinician",
        params={"send_welcome_email": False},
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        json=clinician,
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()["uuid"]


def retrieve_clinicians_by_uuids(context: Context, uuids: List[str]) -> Dict[str, Dict]:
    use_fixture(get_system_token, context)

    response: Response = requests.post(
        f"{base_url}/dhos/v1/clinician_list",
        params={"compact": False},
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        json=uuids,
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()


def clinician_login(context: Context, basic_auth_value: str) -> Dict[str, Dict]:
    use_fixture(get_login_token, context)

    response: Response = requests.get(
        f"{base_url}/dhos/v1/clinician/login",
        headers={
            "Authorization": f"Bearer {context.login_jwt}",
            "UserAuthorization": f"Bearer {basic_auth_value}",
        },
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()
