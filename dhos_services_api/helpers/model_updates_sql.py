from flask_batteries_included.sqldb import db

# Only relations in this set will be followed when patching.
RELATION_KEYS: set[str] = {
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


def recursive_delete(model: db.Model, data_to_delete: dict) -> None:
    """
    Delete parts of a larger structure, including list items
    :param model: The model to modify
    :param data_to_delete: The dict to delete with
    :return: None
    """
    model.recursive_delete(**data_to_delete)
    db.session.commit()


def recursive_patch(model: db.Model, data_to_update: dict) -> None:
    """
    Patches an entire structure with another structure, including list items
    :param model: The model to patch
    :param data_to_update: The dict to patch with
    :return: None
    """
    model.recursive_patch(**data_to_update)
    db.session.commit()
