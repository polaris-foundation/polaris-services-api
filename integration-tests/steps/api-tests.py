import inspect
import json
from pprint import pprint
from typing import Any, Callable, Dict, Optional, Sequence, Set

import jsonpatch
import requests
from behave import given, step, then
from behave.runner import Context
from clients import services_api_client, users_api_client
from clients.rabbitmq_client import get_rabbitmq_message
from helpers import security
from helpers.json import load_json_test, load_patched_json
from helpers.sample_data import create_patient_context_variables
from jsonpatch import JsonPatch, JsonPatchTestFailed
from steps.patient import RABBITMQ_MESSAGES

TOKEN_GENERATORS: Dict[str, Callable[[Context], str]] = {
    "system": security.generate_system_token,
    "login": security.generate_login_token,
    "clinician": security.generate_clinician_token,
    "superclinician": security.generate_superclinician_token,
    "patient": security.generate_patient_token,
}


@step(
    "we (?P<method>\w+) to (?P<url_path>\S+) with data from (?P<data_filename>\S+)(?: with status ("
    "?P<status_code>\d+))?"
)
def call_api_endpoint_with_data(
    context: Context,
    method: str,
    url_path: str,
    data_filename: str,
    status_code: Optional[str],
) -> None:
    create_patient_context_variables(
        context, accessibility_discussed_with=context.clinician_uuid
    )
    data = load_patched_json(context, data_filename)

    if "{" in url_path:
        url_path = url_path.format(context=context)

    response: requests.Response = requests.request(
        method,
        f"{services_api_client.base_url}/{url_path}",
        headers={"Authorization": f"Bearer {context.current_jwt}"},
        json=data,
        timeout=15,
    )
    expected_status_code = int(status_code) if status_code is not None else 200
    assert response.status_code == expected_status_code, (
        f"{method} status returned {response.status_code} (expected "
        f"{expected_status_code})"
    )
    context.output = response.json()


@step("we (?P<method>\w+) to (?P<url_path>\S+) with no data")
def call_api_endpoint_no_data(context: Context, method: str, url_path: str) -> None:
    create_patient_context_variables(
        context, accessibility_discussed_with=context.clinician_uuid
    )

    if "{" in url_path:
        url_path = url_path.format(context=context)

    response = requests.request(
        method,
        f"{services_api_client.base_url}/{url_path}",
        headers={"Authorization": f"Bearer {context.system_jwt}"},
        json=None,
        timeout=15,
    )
    assert response.status_code == 200
    context.output = response.json()


@step("acting as a (?P<user_type>system|login|superclinician|clinician|patient) user")
def set_current_jwt(context: Context, user_type: str) -> None:
    if user_type in TOKEN_GENERATORS:
        TOKEN_GENERATORS[user_type](context)
    else:
        raise RuntimeError("Unknown user type")


@step("we GET from (?P<url_path>\S+)(?: with status (?P<status_code>\d+))?")
def get_api_endpoint(
    context: Context, url_path: str, status_code: Optional[str]
) -> None:
    if "{" in url_path:
        url_path = url_path.format(context=context)

    headers = {"Authorization": f"Bearer {context.current_jwt}"}
    if context.text is not None:
        for extra_header in context.text.split("\n"):
            name, value = extra_header.strip().split(":", 1)
            if name.strip():
                headers[name.strip()] = value.strip()

    response = requests.get(
        f"{services_api_client.base_url}/{url_path}", headers=headers, timeout=15
    )
    expected_status_code = int(status_code) if status_code is not None else 200
    assert response.status_code == expected_status_code, (
        f"GET status returned {response.status_code} (expected "
        f"{expected_status_code})"
    )
    context.output = response.json()


def recursively_remove(obj: Any, keys: Set[str]) -> Any:
    if isinstance(obj, list):
        return [recursively_remove(item, keys) for item in obj]
    if isinstance(obj, dict):
        return {k: recursively_remove(obj[k], keys) for k in obj if k not in keys}
    return obj


@then("the response matches (?P<output_filename>\S+)")
def the_response_matches(context: Context, output_filename: str) -> None:
    """Output filename should be in json patch format and may modify and test the output as
    required."""
    json_test = load_json_test(context, output_filename)

    output = recursively_remove(
        context.output, {"created", "created_by", "modified", "modified_by"}
    )

    patch = JsonPatch(json_test)
    # Json patch throws an assertion error if the patch does not match the JSON to which it is applied.
    # Apply each patch step individually so we can give more context if it fails.
    for operation in patch._ops:
        try:
            output = operation.apply(output)
        except JsonPatchTestFailed as e:
            print("Output:")
            pprint(output)
            print("Operation:")
            pprint(operation.operation)

            f_locals = inspect.trace()[-1][0].f_locals
            if "val" in f_locals and "value" in f_locals:
                actual = inspect.trace()[-1][0].f_locals["val"]
                expected = inspect.trace()[-1][0].f_locals["value"]
                print("Test:")
                pprint(actual)
                print("Difference:")
                print(
                    json.dumps(jsonpatch.make_patch(actual, expected).patch, indent=3)
                )
            raise
        except Exception:
            print("Output:")
            pprint(output)
            print("Operation")
            pprint(operation.operation)
            raise


@step("we save \{(?P<expr>[^}]+)\} as (?P<context_name>\S+)")
def save_variable(context: Context, expr: str, context_name: str) -> None:
    format_str = "{" + expr + "}"
    value = format_str.format(context=context)
    setattr(context, context_name, value)


@given("many clinicians exist")
def many_clinicians_exist(context: Context) -> None:
    clinician_identifier = 444_440

    def new_clinician(
        first_name: str,
        last_name: str,
        email_address: str,
        locations: Sequence[str],
        phone_number: str = "07123456770",
        nhs_smartcard_number: str = "211213",
        job_title: str = "winner",
        groups: Sequence[str] = ("GDM Clinician"),
    ) -> str:
        nonlocal clinician_identifier
        clinician_data = {
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": f"07123{clinician_identifier}",
            "nhs_smartcard_number": f"{clinician_identifier}",
            "email_address": email_address,
            "job_title": job_title,
            "locations": locations,
            "groups": list(groups),
            "products": [{"product_name": "GDM", "opened_date": "2017-01-01"}],
        }

        uuid = users_api_client.post_clinician(context, clinician_data)
        clinician_identifier += 1
        # Eat the rabbit notification of a new clinician
        get_rabbitmq_message(context, RABBITMQ_MESSAGES["CLINICIAN_CREATED_MESSAGE"])
        return uuid

    context.execute_steps("""Given an alternate location exists""")

    # Create many clinicians
    context.john_snow = new_clinician(
        first_name="John",
        last_name="Snow",
        email_address="john.snow@nhs.com",
        locations=[context.location_uuid, context.alternate_location_uuid],
        groups=["GDM Superclinician"],
    )
    context.aubrey_oneill = new_clinician(
        first_name="Aubrey",
        last_name="O'Neill",
        email_address="a.oneill@mail.com",
        locations=[context.alternate_location_uuid],
        groups=["GDM Clinician"],
        job_title="midwife",
    )
    context.kiara_welsh = new_clinician(
        first_name="Kiara",
        last_name="Welsh",
        email_address="k.welsh@mail.com",
        locations=[context.alternate_location_uuid, context.location_uuid],
        groups=["GDM Clinician"],
        job_title="midwife",
    )
    context.hollie_white = new_clinician(
        first_name="Hollie",
        last_name="White",
        email_address="h.white@mail.com",
        locations=[context.alternate_location_uuid, context.location_uuid],
        groups=["GDM Clinician"],
        job_title="midwife",
    )
    context.oj_wolrab = new_clinician(
        first_name="OJ",
        last_name="Wolrab",
        email_address="wolrab@mail.com",
        locations=[context.alternate_location_uuid, context.location_uuid],
        groups=["GDM Clinician"],
        job_title="midwife",
    )
    context.moe_smith = new_clinician(
        first_name="Moe",
        last_name="Smith",
        email_address="Moe@mail.com",
        locations=[context.alternate_location_uuid, context.location_uuid],
        groups=["GDM Clinician"],
        job_title="midwife",
    )


@step("we cleanup the output sorted by (?P<field>\S+)")
def we_cleanup_the_output(context: Context, field: str) -> None:
    """Remove unwanted fields and sort list response"""
    response = getattr(context, "output", {}) or getattr(context, "patient_list")

    for obj in response:
        for unwanted in (
            "uuid",
            "created",
            "created_by",
            "modified",
            "modified_by",
            "products",
        ):
            if unwanted in obj:
                del obj[unwanted]

            if "locations" in obj:
                obj["locations"] = [
                    "L1"
                    if loc == context.location_uuid
                    else "L2"
                    if loc == getattr(context, "alternate_location_uuid", "")
                    else loc
                    for loc in obj["locations"]
                ]
                obj["locations"].sort()

            if "groups" in obj:
                obj["groups"].sort()

    response.sort(key=lambda obj: obj.get(field, None))  # type: ignore
