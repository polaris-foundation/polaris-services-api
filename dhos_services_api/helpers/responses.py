"""
Helper functions converting cypher query responses to a json-compatible dict.

Query results may be:
    A list of neo4j Node objects
    A list of dict
    A list of uuid strings
"""
from typing import Any, Callable, Dict, List, Type, Union

from neo4j import Node
from neomodel import StructuredNode

QueryResponse = Union[Node, Dict]


def validate_uuid_list(values: List[str]) -> List[str]:
    if not all(isinstance(v, str) for v in values):
        raise TypeError("Expected list of uuids")
    return values


def validate_single_uuid(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Expecting single uuid")
    return value


def validate_identity(value: Any) -> Any:
    """Identity validator: just passes the value straight through"""
    return value


def response_to_dict(
    cls: Type[StructuredNode],
    response: QueryResponse,
    primary: str,
    method: str,
    single: Dict[str, Type[StructuredNode]] = None,
    multiple: Dict[str, Type[StructuredNode]] = None,
    custom: Dict[str, Callable[[Any], Any]] = None,
) -> Dict:
    kwargs = {}
    if isinstance(response, Node):
        obj = cls.inflate(response)
    else:
        obj = cls.inflate(response[primary])

        if single:
            for name, klass in single.items():
                if name in response:
                    value = response[name]
                    kwargs[name] = (
                        klass.convert_response_to_dict(value[0], method=method)
                        if value
                        else None
                    )

        if multiple:
            for name, klass in multiple.items():
                if name in response:
                    values = response[name]
                    kwargs[name] = [
                        klass.convert_response_to_dict(value, method=method)
                        for value in values
                    ]

        if custom:
            for name, validator in custom.items():
                if name in response:
                    kwargs[name] = validator(response[name])

    to_dict = getattr(obj, method, obj.to_dict_no_relations)
    return to_dict(**kwargs)
