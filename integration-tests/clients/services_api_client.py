from typing import Dict, List, Optional

import requests
from behave import fixture, use_fixture
from behave.runner import Context
from environs import Env
from helpers.security import (
    generate_superclinician_token,
    generate_system_token,
    get_login_token,
    get_system_token,
)
from requests import Response

base_url: str = Env().str("DHOS_SERVICES_BASE_URL", "http://dhos-services-api:5000")


def post_patient(context: Context, patient: dict, product_name: str) -> str:
    generate_system_token(context)

    response: Response = requests.post(
        f"{base_url}/dhos/v1/patient",
        params={"product_name": product_name},
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        json=patient,
        timeout=15,
    )
    context.patient_response = response.json()
    assert response.status_code == 200
    return response.json()["uuid"]


def post_patient_neo4j(context: Context, patient: dict, product_name: str) -> str:
    generate_system_token(context)

    response: Response = requests.post(
        f"{base_url}/dhos/v1/neo4j_patient",
        params={"product_name": product_name},
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        json=patient,
        timeout=15,
    )
    context.patient_response = response.json()
    assert response.status_code == 200
    return response.json()["uuid"]


def patch_patient(
    context: Context, patient_uuid: str, data: Dict, product_name: str
) -> str:
    generate_system_token(context)

    response: Response = requests.patch(
        f"{base_url}/dhos/v1/patient/{patient_uuid}",
        params={"product_name": product_name},
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        json=data,
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()["uuid"]


def get_patient(context: Context, patient_uuid: str, product_name: str) -> Dict:
    generate_superclinician_token(context)

    response: Response = requests.get(
        f"{base_url}/dhos/v1/patient/{patient_uuid}",
        params={"product_name": product_name},
        headers={"Authorization": f"Bearer {context.superclinician_jwt}"},
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()


@fixture
def drop_data(context: Context) -> Dict:
    use_fixture(get_system_token, context)
    response: Response = requests.post(
        f"{base_url}/drop_data",
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        timeout=15,
    )
    assert response.status_code == 200, str(response)
    return response.json()


def get_patient_uuids(context: Context, product_name: str) -> Dict:
    generate_superclinician_token(context)

    response: Response = requests.get(
        f"{base_url}/dhos/v1/patient_uuids",
        params={"product_name": product_name},
        headers={"Authorization": f"Bearer {context.superclinician_jwt}"},
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()


def get_patient_list(context: Context, product_name: str, locs: List[str]) -> Dict:
    generate_superclinician_token(context)

    response: Response = requests.get(
        f"{base_url}/dhos/v1/patient_list",
        params={"product_name": product_name, "locs": locs},
        headers={"Authorization": f"Bearer {context.superclinician_jwt}"},
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()


def retrieve_patients_by_uuids(
    context: Context, uuids: List[str], product_name: str
) -> List[Dict]:
    generate_superclinician_token(context)

    response: Response = requests.post(
        f"{base_url}/dhos/v1/patient_list",
        params={"product_name": product_name},
        json=uuids,
        headers={"Authorization": f"Bearer {context.superclinician_jwt}"},
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()


def retrieve_patients_by_uuids_neo4j(
    context: Context, uuids: List[str], product_name: str
) -> List[Dict]:
    generate_superclinician_token(context)

    response: Response = requests.post(
        f"{base_url}/dhos/v1/neo4j_patient_list",
        params={"product_name": product_name},
        json=uuids,
        headers={"Authorization": f"Bearer {context.superclinician_jwt}"},
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()


def get_list_of_patients_for_location(
    context: Context, location_uuid: str, product_name: str
) -> Dict:
    use_fixture(get_system_token, context)
    response: Response = requests.get(
        f"{base_url}/dhos/v2/location/{location_uuid}/patient",
        params={"product_name": product_name},
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()


def get_gdm_patients_for_location(
    context: Context,
    location_uuid: str,
    current: Optional[bool] = None,
    include_all: Optional[bool] = None,
) -> Dict:
    use_fixture(get_system_token, context)
    params: dict = {}
    if current is not None:
        params["current"] = current
    if include_all is not None:
        params["include_all"] = include_all

    response: Response = requests.get(
        f"{base_url}/dhos/v1/location/{location_uuid}/gdm_patient",
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        params=params,
        timeout=15,
    )
    assert response.status_code == 200
    return response.json()
