from typing import Any, Dict, List, Sequence, Set, Tuple, Type, Union

from neomodel import RelationshipManager, StructuredNode
from she_logging import logger

import dhos_services_api.models.delivery
import dhos_services_api.models.visit
from dhos_services_api.helpers.neo_utils import get_node, get_node_or_404

# Only relations in this set will be followed when patching.
RELATION_KEYS: Set[str] = {
    "notes",
    "diagnoses",
    "deliveries",
    "pregnancies",
    "actions",
    "doses",
    "visits",
    "locations",
    "bookmarks",
    "observable_entities",
    "dh_products",
    "personal_addresses",
    "terms_of_service",
    "parent_locations",
    "child_of",
    "products",
}


def recursive_delete(model: StructuredNode, data_to_delete: dict) -> None:
    """
    Delete parts of a larger structure, including list items
    :param model: The model to modify
    :param data_to_delete: The dict to delete with
    :return: None
    """
    for key in data_to_delete:
        value = data_to_delete[key]

        # make sure the key exists on the model
        if not hasattr(model, key):
            raise KeyError(f"Entity does not have attribute: {key}")

        # if the item is a dict, call recursive delete on it
        elif isinstance(value, dict):
            recursive_delete(getattr(model, key).single(), value)

        # if the item is a list, get the list attribute from the model
        elif isinstance(value, (list, tuple)):
            _delete_collection(key, model, value)

        model.save()


def _delete_collection(key: str, model: StructuredNode, value: Sequence[Any]) -> None:
    model_item_list = getattr(model, key)
    for item in value:
        if isinstance(item, str):
            _delete_str_from_collection(key, item, model_item_list)

        # if a list of objects, identify using uuid and remove from model list
        elif isinstance(item, dict):
            _delete_from_related_node(item, model_item_list)

        # u wot m8?
        else:
            raise ValueError("Can only delete from a list of objects or strings")


def _delete_from_related_node(
    item: Dict[str, Any], model_item_list: RelationshipManager
) -> None:
    # no uuid to identify model
    if "uuid" not in item:
        raise ValueError("Can not identify item without a uuid")

    # if the uuid is the only key on the model, this model is to be deleted
    elif len(item) == 1:
        model_item = next((x for x in model_item_list if x.uuid == item["uuid"]), None)

        if model_item is not None:
            on_delete_hook = getattr(model_item, "on_delete", None)
            if on_delete_hook is None or on_delete_hook():
                model_item_list.disconnect(model_item)
                model_item.delete()

        else:
            raise ValueError("No object found with that uuid")

    # if more keys were supplied,
    # the uuid is for identity purposes and the other keys need to be inspected
    else:
        model_item = next((x for x in model_item_list if x.uuid == item["uuid"]), None)
        recursive_delete(model_item, item)


def _delete_str_from_collection(key: str, item: Any, model_item_list: List) -> None:
    # list of uuids
    if isinstance(model_item_list, RelationshipManager):
        if key not in RELATION_KEYS:
            raise KeyError(f"{key} does not map to a permitted model")

        m_type = model_item_list.definition["node_class"]
        related_model = get_node(m_type, uuid=item)
        if related_model is not None:
            model_item_list.disconnect(related_model)

    # list of strings (probably snomed codes)
    else:
        if item in model_item_list:
            model_item_list.remove(item)


def recursive_patch(model: StructuredNode, data_to_update: Dict) -> None:
    """
    Patches an entire structure with another structure, including list items
    :param model: The model to patch
    :param data_to_update: The dict to patch with
    :return: None
    """

    # Perform any custom patching first.
    model.on_patch(data_to_update)

    for key, new_value in data_to_update.items():

        logger.debug("Patching '%s' on type '%s'", key, type(model))

        if (type(model), key) in skip_patch:
            continue

        if key in no_patch:
            # attribute can not be patched
            logger.warning(
                "Field '%s' cannot be patched on type '%s'", key, type(model)
            )
            raise KeyError(f"Cannot patch {key}")

        if not hasattr(model, key):
            # model does not have attribute
            raise KeyError(f"Entity does not have attribute: {key}")

        if isinstance(new_value, dict):
            # call again on dict object
            if isinstance(getattr(model, key), dict):
                _patch_attribute(key, model, new_value)
            else:
                recursive_patch(getattr(model, key).single(), new_value)

        elif isinstance(new_value, (list, tuple)):
            _patch_collection(key, model, new_value)
        else:
            _patch_attribute(key, model, new_value)

    model.save()


def _patch_collection(
    key: str, model: StructuredNode, new_values: Sequence[Any]
) -> None:

    model_item_list = getattr(model, key)

    if isinstance(model_item_list, RelationshipManager):
        _list_type_check(
            new_values,
            (dict, str),
            "List elements should be either dicts or uuid strings",
        )

        if key in patch_overwrites_existing:
            # Remove any existing related nodes that are not in the new list.
            _remove_unreferenced_from_relation(
                model_item_list, related_uuids=new_values
            )

        for item in new_values:
            if isinstance(item, str):
                # list of uuid strings
                _connect_by_uuid(item, key, model_item_list)

            # list of objects
            elif "uuid" in item:
                _updated_existing_related_node(item, model_item_list)
            else:
                _patch_add_relation(item, key, model_item_list)

    else:
        _list_type_check(new_values, str, "List elements should be strings")

        for item in new_values:
            # list of strings (probably snomed codes)
            if item not in model_item_list:
                model_item_list.append(item)
        model.save()


def _list_type_check(
    elements: Sequence[Any], valid_type: Union[type, Tuple[Any, ...]], message: str
) -> None:
    if not all(isinstance(item, valid_type) for item in elements):
        raise TypeError(message)


def _connect_by_uuid(item: Any, key: str, model_item_list: Type) -> None:
    if key not in RELATION_KEYS:
        raise KeyError(f"{key} does not map to a permitted model")
    m_type = model_item_list.definition["node_class"]
    m = get_node_or_404(m_type, uuid=item)
    if model_item_list.relationship(m) is None:
        model_item_list.connect(m)


def _remove_unreferenced_from_relation(
    model_relationship: RelationshipManager, related_uuids: Sequence[str]
) -> None:
    """Remove from relationship when uuid not in related_uuids"""
    for related in list(model_relationship):
        if related.uuid not in related_uuids:
            model_relationship.disconnect(related)


def _patch_add_relation(
    item: Dict, key: str, model_item_list: RelationshipManager
) -> None:
    # create new list element
    if key not in RELATION_KEYS:
        raise KeyError(f"{key} does not map to a permitted model")

    if not isinstance(model_item_list, RelationshipManager):
        raise KeyError(f"{key} is not a relationship")

    m_type = model_item_list.definition["node_class"]
    m = m_type.new(**item)
    m.save()

    model_item_list.connect(m)
    on_create_hook = getattr(m, "on_create", None)
    if on_create_hook is not None:
        on_create_hook()


def _updated_existing_related_node(
    item: Dict, model_item_list: RelationshipManager
) -> None:
    model_item = next((x for x in model_item_list if x.uuid == item["uuid"]), None)
    if model_item is not None:

        # Remove uuid so patch doesn't try to change it
        del item["uuid"]

        # patch list element by uuid
        recursive_patch(model_item, item)

    else:
        raise KeyError(f"No entity found with that uuid")


def _patch_attribute(key: str, model: StructuredNode, new_value: Any) -> None:
    logger.debug("Patching attribute '%s'", key)
    # uuid string relationship
    model_relationship = getattr(model, key, None)
    if isinstance(model_relationship, RelationshipManager):
        if key not in RELATION_KEYS:
            raise KeyError(f"{key} does not map to a permitted model")

        m_type = model_relationship.definition["node_class"]

        related_uuid = new_value
        if key in patch_overwrites_existing:
            for related in list(model_relationship):
                if related.uuid != related_uuid:
                    model_relationship.disconnect(related)

        m = get_node_or_404(m_type, uuid=related_uuid)
        if model_relationship.relationship(m) is None:
            model_relationship.connect(m)

    # int/float/string/bool etc
    else:
        setattr(model, key, new_value)


patch_overwrites_existing = {"parent_locations"}

no_patch = ["uuid", "created", "modified", "bookmarked", "closed_date"]

skip_patch = [(dhos_services_api.models.visit.Visit, "clinician")]
