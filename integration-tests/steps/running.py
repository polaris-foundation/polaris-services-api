import requests
from behave import given, then, when
from behave.runner import Context
from clients import services_api_client


@given("dhos-services-api has been started")
def api_has_started(context: Context) -> None:
    pass


@when("we fetch from /running")
def fetch_running(context: Context) -> None:
    response = requests.get(url=f"{services_api_client.base_url}/running")
    context.response = response


@then("the result is 200")
def response_is_ok(context: Context) -> None:
    assert context.response.status_code == 200
