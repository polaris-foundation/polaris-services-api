from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from typing import Any, Sequence, Type, TypeVar, Union

from flask_batteries_included import sqldb
from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.sqldb import db
from she_logging import logger
from sqlalchemy import Table

ValidationSchema = dict[str, dict[str, Union[type, list[type]]]]


class ModelIdentifier(sqldb.ModelIdentifier):
    __table__: Table
    __abstract__ = True
    created = db.Column(
        db.DateTime(timezone=True),
        unique=False,
        nullable=False,
        default=datetime.utcnow,
    )
    modified = db.Column(
        db.DateTime(timezone=True),
        unique=False,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    uuid = db.Column(
        db.String(length=36),
        unique=True,
        nullable=False,
        primary_key=True,
        default=generate_uuid,
    )

    @property
    def created_by(self) -> str:
        """Overridden from base class for simplicity, it's the setter that is differnt."""
        return self.created_by_

    @created_by.setter
    def created_by(self, value: str) -> None:
        self.created_by_ = value

    @property
    def modified_by(self) -> str:
        """Overridden from base class for simplicity, it's the setter that is differnt."""
        return self.modified_by_

    @modified_by.setter
    def modified_by(self, value: str) -> None:
        self.modified_by_ = value

    @classmethod
    @abstractmethod
    def new(cls, **kwargs: Any) -> Any:
        """Abstract definition for Klass.new
        Note that all arguments must be keyword only (use * argument to enforce this).
        If you add more specific arguments you must also give them a default value otherwise mypy will rightly complain.
        e.g.
        def new(cls, *, patient_id: str=None, **kwargs) -> 'Something': ...
        """

    def __init__(self, **kwargs: Any) -> None:
        """Ensure uuid default is set even before we flush the session"""
        if "uuid" not in kwargs:
            kwargs["uuid"] = generate_uuid()

        super().__init__(**kwargs)

    @classmethod
    def schema(cls) -> ValidationSchema:
        raise NotImplementedError()

    def on_patch(self, *args: Any, **kwargs: Any) -> None:
        ...

    def on_delete(self, parent: Any) -> None:
        ...

    def recursive_patch(self, **kwargs: Any) -> None:
        """Simple patching of values on a model. Override if the model has relationships"""
        self.on_patch(kwargs)

        for key, new_value in kwargs.items():
            if key in self._no_patch:
                # attribute can not be patched
                logger.warning(
                    "Field '%s' cannot be patched on type '%s'", key, type(self)
                )
                raise KeyError(f"Cannot patch {key}")

            column = self.__table__.columns.get(key, None)
            if column is None:
                # model does not have attribute or it is a relationship
                raise KeyError(f"{self.__table__.name} does not have attribute: {key}")

            logger.debug("Patching '%s' on type '%s'", key, type(self))

            if isinstance(new_value, (list, tuple)):
                if not all(isinstance(v, str) for v in new_value):
                    raise TypeError("list elements should be strings")

                model_item_list = getattr(self, key)
                setattr(
                    self,
                    key,
                    model_item_list
                    + [item for item in new_value if item not in model_item_list],
                )
            else:
                setattr(self, key, new_value)
        db.session.add(self)

    @classmethod
    def patch_or_add(
        cls, instance: ModelIdentifier | None, patch_data: dict, parent_data: dict
    ) -> None:
        if not patch_data:
            return
        if instance:
            instance.recursive_patch(**patch_data)
        else:
            cls.new(**patch_data, **parent_data)

    @classmethod
    def patch_related_objects(
        cls, related_column: Any, parent_id: str, patch_data: Sequence[dict | str]
    ) -> None:
        if not patch_data:
            return

        new_connections = [v for v in patch_data if isinstance(v, str)]
        new_models = [v for v in patch_data if isinstance(v, dict) and "uuid" not in v]
        updated_models = {
            v["uuid"]: v for v in patch_data if isinstance(v, dict) and "uuid" in v
        }
        if len(patch_data) != len(new_connections) + len(new_models) + len(
            updated_models
        ):
            raise TypeError("list elements should be either dicts or uuid strings")

        if new_connections:
            db.session.query(cls).filter(cls.uuid.in_(patch_data)).update(
                {related_column: parent_id}
            )

        if new_models:
            for new_model in new_models:
                cls.new(**(new_model | {related_column.key: parent_id}))

        if updated_models:
            query = db.session.query(cls).filter(
                related_column == parent_id, cls.uuid.in_(updated_models.keys())
            )
            for obj in query:
                patch = updated_models[obj.uuid]
                obj.recursive_patch(**{k: patch[k] for k in patch.keys() - {"uuid"}})

    def recursive_delete(self, **kwargs: object) -> None:
        """
        Delete items from a model
        :param cls: The model to modify
        :param kwargs: list[str] remove string from list column or remove related items by uuid,
            dict to apply recursive delete to a related item.

        :return: None
        """
        for key, value in kwargs.items():
            if isinstance(value, dict):
                # key must refer to a single model, apply recursive delete
                try:
                    child = getattr(self, key)
                except AttributeError:
                    raise KeyError(
                        f"{self.__table__.name} does not have attribute: {key}"
                    )
                child.recursive_delete(**value)
                continue

            if not isinstance(value, (list, tuple)):
                continue

            delete_str = [v for v in value if isinstance(v, str)] + [
                v["uuid"] for v in value if isinstance(v, dict) and v.keys() == {"uuid"}
            ]
            delete_dicts = {
                v["uuid"]: v
                for v in value
                if isinstance(v, dict) and v.keys() > {"uuid"}
            }

            if not len(delete_str) + len(delete_dicts) == len(value):
                raise TypeError(
                    "Can only delete from a list of strings or objects with a uuid"
                )

            # make sure the key exists on the model
            if not hasattr(self, key):
                raise KeyError(f"{self.__table__.name} does not have attribute: {key}")

            if key in self.__table__.columns.keys():
                old_value = getattr(self, key)
                if isinstance(old_value, (list, tuple)):
                    if delete_dicts:
                        raise ValueError(
                            f"Cannot delete dict from an array column {key}"
                        )

                    # list of strings (e.g. snomed codes, external uuids)
                    setattr(self, key, [v for v in old_value if v not in delete_str])
                    continue

            if delete_str:
                # Must be list of uuids for related items
                old_value = getattr(self, key)
                children_to_notify: list[ModelIdentifier] = [
                    child for child in old_value if child.uuid in delete_str
                ]

                setattr(self, key, [v for v in old_value if v.uuid not in delete_str])
                for child in children_to_notify:
                    child.on_delete(parent=self)

            if delete_dicts:
                for obj in getattr(self, key):
                    if obj.uuid in delete_dicts:
                        patch = delete_dicts[obj.uuid]
                        obj.recursive_delete(
                            **{k: patch[k] for k in patch.keys() - {"uuid"}}
                        )
        db.session.add(self)

    _no_patch = ["uuid", "created", "modified", "bookmarked", "closed_date"]


T = TypeVar("T", bound=ModelIdentifier)


def construct_children(data: Sequence[dict | T] | None, klass: Type[T]) -> list[T]:
    if data is None:
        return []
    return [klass.new(**item) if isinstance(item, dict) else item for item in data]


def construct_single_child(item: dict | T | None, klass: Type[T]) -> T | None:
    if item is None:
        return None
    if isinstance(item, dict):
        return klass.new(**item)
    return item
