from typing import Any, Optional, Type, TypeVar

from flask_batteries_included.helpers.error_handler import EntityNotFoundException
from neomodel import StructuredNode

T = TypeVar("T", bound=StructuredNode)


def get_node(model: Type[T], **filter_by: Any) -> Optional[T]:
    """
    :param model: node class
    :param filter_by: comma separated key value pairs to filter results (key=value)
    :return: patient object if found, otherwise None
    """
    nodes: Any = model.nodes  # type:ignore
    return nodes.get_or_none(**filter_by)


def get_node_or_404(model: Type[T], **filter_by: Any) -> T:
    """
    :param model: node class
    :param filter_by: comma separated key value pairs to filter results (key=value)
    :return: patient object if found, otherwise raises 404
    """
    node = get_node(model, **filter_by)
    if not node:
        raise EntityNotFoundException(f"{model.__name__} {filter_by} not found")
    return node
