from typing import Dict

from behave import given, step
from behave.runner import Context
from clients import locations_api_client, services_api_client
from helpers import sample_data


@step("a new location is created")
def create_location(context: Context) -> None:
    request_body: Dict = {
        "location_type": "264362003",
        "display_name": "Big Hospital",
        "ods_code": "RTH",
        "address_line_1": "Headley Way",
        "address_line_2": "Headington",
        "address_line_3": "An address fragment",
        "address_line_4": "A fourth address fragment",
        "locality": "Oxford",
        "region": "Oxfordshire",
        "postcode": "OX3 9DU",
        "country": "UK",
        "dh_products": [{"product_name": "GDM", "opened_date": "2019-01-01"}],
    }
    context.location_request_body = request_body
    location_body: Dict = locations_api_client.post_location(
        context=context, location=request_body
    )
    assert "uuid" in location_body
    context.location_uuid = location_body["uuid"]
    context.location_body = location_body


@given("an alternate location exists")
def alternate_location_exists(context: Context) -> None:
    location_data = {
        "address_line_1": "Address",
        "postcode": "",
        "country": "",
        "location_type": "",
        "ods_code": "L21",
        "display_name": "Alternate Hospital",
        "dh_products": [{"product_name": "GDM", "opened_date": "2010-01-01"}],
    }
    context.alternate_location_uuid = locations_api_client.post_location(
        context, location_data
    )["uuid"]


@step("the location is retrieved")
def retrieve_location(context: Context) -> None:
    context.location_body = locations_api_client.get_location(
        context=context, location_uuid=context.location_uuid
    )


@step("the location is updated")
def update_location(context: Context) -> None:
    location: Dict = sample_data.location_data()
    del location["dh_products"]
    location["score_system_default"] = "meows"
    context.location_request_body = location
    context.location_body = locations_api_client.patch_location(
        context=context, location_uuid=context.location_uuid, location=location
    )


@step("the (?:retrieved|returned) location matches that of the location request")
def assert_created_location(context: Context) -> None:
    actual: Dict = context.location_body.copy()

    # these fields will be system-generated
    for dh_product in actual["dh_products"]:
        del dh_product["uuid"]
        del dh_product["closed_date"]
        del dh_product["created"]

    # and this one will not be returned if it was None in request
    if context.location_request_body.get("parent_ods_code", {}) is None:
        actual["parent_ods_code"] = None

    for key in context.location_request_body:
        assert context.location_request_body[key] == actual[key]


@step("all locations are retrieved and the product is (?P<product_name>\w+)")
def get_all_locations_for_product(context: Context, product_name: str) -> None:
    context.location_list = locations_api_client.get_all_locations(
        context=context, product_name=product_name
    )


@step(
    "the (?P<original_or_alternate>original|alternate) location exists in the retrieved location list"
)
def assert_location_in_list(context: Context, original_or_alternate: str) -> None:
    location_uuids: list = [loc_uuid for loc_uuid in context.location_list]
    if original_or_alternate == "original":
        assert context.location_uuid in location_uuids
    else:
        assert context.alternate_location_uuid in location_uuids


@step(
    "a list of patients is retrieved for the location and the product is (?P<product_name>\w+)"
)
def get_patient_list_for_location(context: Context, product_name: str) -> None:
    context.patient_list = services_api_client.get_list_of_patients_for_location(
        context=context, location_uuid=context.location_uuid, product_name=product_name
    )


@step(
    "a list of (?P<current>active|inactive)?\s*GDM patients (?P<created_in_error>including created in error)?\s*is retrieved for the location"
)
def get_gdm_patient_list_for_location(
    context: Context, current: str, created_in_error: str
) -> None:
    params = {}
    if current:
        params["current"] = current == "active"
    if created_in_error:
        params["include_all"] = True

    context.patient_list = services_api_client.get_gdm_patients_for_location(
        context=context, location_uuid=context.location_uuid, **params
    )
