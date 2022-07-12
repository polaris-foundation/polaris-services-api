from typing import Any, Callable, Dict, List, Mapping, NoReturn, Optional, Union

import requests
from flask import request
from flask_batteries_included.helpers.error_handler import (
    DuplicateResourceException,
    EntityNotFoundException,
    ServiceUnavailableException,
    UnprocessibleEntityException,
)
from requests import Response
from she_logging import logger
from she_logging.request_id import current_request_id

HTTP_ERROR_MAP = {
    400: ValueError,
    403: PermissionError,
    404: EntityNotFoundException,
    409: DuplicateResourceException,
    422: UnprocessibleEntityException,
    500: ServiceUnavailableException,
    503: ServiceUnavailableException,
}


def make_json_object_request(
    method: str,
    url: str,
    params: Optional[Dict] = None,
    json_data: Union[None, List, Mapping[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Dict:
    response: Dict = __make_json_request(
        method=method,
        url=url,
        params=params,
        json_data=json_data,
        headers=headers,
    )
    return response


def make_json_list_request(
    method: str,
    url: str,
    params: Optional[Dict] = None,
    json_data: Union[None, List, Dict] = None,
) -> List:
    response: List[Any] = __make_json_request(
        method=method,
        url=url,
        params=params,
        json_data=json_data,
    )
    return response


def __make_json_request(
    method: str,
    url: str,
    params: Optional[Dict] = None,
    json_data: Union[None, List, Mapping[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Any:
    """
    DO NOT CALL THIS DIRECTLY.

    This method should only be called by:
        - _make_json_list_request
        - _make_json_object_request

    it exists only to save duplicating a few lines of code and make type hinting a little easier.
    """
    response = _make_request(
        method,
        url,
        params,
        json_data,
        headers=headers,
    )

    if response.status_code != 200:
        _propagate_http_error(response)
    return response.json()


def _make_request(
    method: str,
    url: str,
    params: Optional[Dict] = None,
    json_data: Union[None, List, Mapping[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Response:
    actual_method: Callable = getattr(requests, method)
    if headers is None:
        headers = _get_current_request_headers()
    try:
        response: Response = actual_method(
            url=url,
            params=params,
            headers=headers,
            json=json_data,
            timeout=30,
        )
    except requests.ConnectionError as e:
        logger.exception("%s request to %s failed", method.upper(), url)
        raise ServiceUnavailableException(e)
    if "Deprecation" in response.headers:
        successor: Dict[str, str] = response.links.get(
            "successor-version", {"url": "another api"}
        )
        logger.warning(
            "Services API is using a deprecated API %r (use %r)",
            response.request.url,
            successor["url"],
            extra={
                "request_url": response.request.url,
                "successor": successor["url"],
            },
        )
    return response


def _get_current_request_headers() -> Dict:
    headers: Dict[str, Optional[str]] = {"X-Request-ID": current_request_id()}
    header_keys = ["Authorization", "x-authorisation-code", "X-Client", "X-Version"]
    for key in header_keys:
        if key in request.headers:
            headers[key] = request.headers[key]
    return headers


def _propagate_http_error(response: Response) -> NoReturn:
    logger.error(
        "Received unexpected response (%d) during internal HTTP request to %s",
        response.status_code,
        response.request.url,
        extra={
            "request_url": response.request.url,
            "request_body": str(response.request.body),
            "response_status": response.status_code,
            "response_body": response.text,
        },
    )
    if response.json() and response.json().get("message"):
        message = response.json()["message"]
    else:
        message = "Unexpected response forwarding internal request"
    raise HTTP_ERROR_MAP.get(response.status_code, ValueError)(message)
