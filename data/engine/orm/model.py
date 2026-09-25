"""
Model — Active Record base class for Craft ORM: CRUD, mass-assignment
protection, UUID identity, and relationship declarations.
Category: Core Framework (ORM).
Relations:
  - Subclassed by `app/Models/*`; builds queries through
    `engine/orm/query_builder.py` and relations through
    `engine/orm/relationships.py`.
  - Resolves the `db` binding via `Container.getInstance()`
    (`engine/container/application.py`).
References:
  - Guide: `documentation/orm.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import copy
import logging
from typing import Any, Dict, List, Optional, Type
from datetime import datetime, timezone

from engine.orm.query_builder import QueryBuilder, _MISSING, _assert_identifier
from engine.orm.relationships import (
    BelongsTo,
    BelongsToMany,
    HasMany,
    HasOne,
    Relation,
)


_logger = logging.getLogger("craft.orm")


def _infer_table(model: type) -> str:
    """Return the table for a model without `__table__`, honouring the legacy name."""
    from engine.support.naming import table_for

    canonical = table_for(model.__name__)
    legacy = model.__name__.lower()
    legacy = legacy if legacy.endswith("s") else legacy + "s"
    if legacy == canonical or not _table_exists(legacy) or _table_exists(canonical):
        return canonical
    _logger.warning(
        "model_table_legacy_name model=%s table=%s expected=%s hint=set __table__ = %r on the model",
        model.__name__, legacy, canonical, legacy,
    )
    return legacy


def _table_exists(table: str) -> bool:
    """Return whether `table` exists; False when no database is reachable."""
    from engine.container.application import Container

    try:
        return bool(Container.getInstance().make("schema").has_table(table))
    except (KeyError, RuntimeError, OSError):
        return False


class Model:
    """Active Record Base Model."""

    __table__: Optional[str] = None
    #: Mass-assignable columns. Fail closed by default: an empty/undeclared
    #: `fillable` means **nothing** is mass-assignable through `create()` /
    #: `update_attributes()` — the exact opposite of the old (insecure)
    #: default, where empty meant unrestricted. A model that genuinely wants
    #: every column writable from request input must opt in explicitly with
    #: `guarded = False` (mirrors the "guarded" escape hatch other frameworks
    #: use for the same purpose). Trusted internal writes should keep using
    #: `force_create()` / `update()` instead of reaching for `guarded = False`.
    fillable: List[str] = []
    #: Set `False` to disable mass-assignment filtering entirely for this
    #: model — an explicit opt-out, not the default.
    guarded: bool = True
    hidden: List[str] = []
    #: Column values applied on create when the caller omits them.
    defaults: Dict[str, Any] = {}
    primary_key: str = "id"
    key_type: str = "int"  # "int" (auto-increment) or "uuid" (client generated)

    #: Fill a `uuid` column on create when the table has one. This is on by
    #: default: the integer `id` stays the key for joins, and the UUID is the
    #: identifier you expose publicly, so URLs never leak row counts or invite
    #: enumeration. Tables without the column are unaffected — nothing is
    #: inserted that the schema does not declare.
    uses_uuid: bool = True
    uuid_column: str = "uuid"

    #: Column -> cast name, e.g. `{"meta": "jsonb", "tags": "array:str"}`.
    #: Without one, an attribute holds whatever the driver returned and is
    #: written straight back — which works for text and numbers and fails for
    #: every structured PostgreSQL type. See `engine/orm/casts.py`.
    casts: Dict[str, str] = {}

    def __init__(self, attributes: Optional[Dict[str, Any]] = None):
        self._attributes: Dict[str, Any] = attributes or {}
        #: Eager-loaded relations, keyed by relation method name.
        self._relations: Dict[str, Any] = {}
        if self.casts:
            self._hydrate()
        self.sync_original()

    # -- change tracking -------------------------------------------------------

    def sync_original(self) -> None:
        """Record the current attributes as the persisted state.

        A deep copy: cast values such as `jsonb` dicts are mutated in place, and
        a shared reference would make every such change look clean.
        """
        self._original: Dict[str, Any] = copy.deepcopy(self._attributes)
        self._assigned: set = set()

    def get_dirty(self) -> Dict[str, Any]:
        """Return the attributes changed since the last load or save.

        Returns:
            Column -> new value, excluding the primary key.
        """
        original = self.__dict__.get("_original", {})
        return {
            column: value
            for column, value in self._attributes.items()
            if column != self.primary_key and (column not in original or original[column] != value)
        }

    def is_dirty(self) -> bool:
        """Return whether any attribute changed since the last load or save."""
        return bool(self.get_dirty())

    def _write_predicate(self) -> tuple[str, List[Any]]:
        """Return the WHERE clause and bindings that address this row on write."""
        key = self.primary_key
        return f"{key} = ?", [self._original.get(key, self._attributes.get(key))]

    # -- attribute casting -----------------------------------------------------

    @classmethod
    def _driver(cls) -> str:
        try:
            from engine.container.application import Container

            return Container.getInstance().make("db").driver
        except Exception:
            return "sqlite"

    @classmethod
    def _cast_for(cls, column: str) -> Any:
        from engine.orm.casts import resolve_cast

        spec = cls.casts.get(column)
        return resolve_cast(spec) if spec else None

    def _hydrate(self) -> None:
        """Turn stored values into Python ones, in place."""
        driver = self._driver()
        for column in self.casts:
            if column in self._attributes:
                cast = self._cast_for(column)
                self._attributes[column] = cast.hydrate(self._attributes[column], driver)

    @classmethod
    def _dehydrate(cls, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Turn Python values into ones the driver will accept.

        A copy, not in place: the model keeps the Python value after a write, so
        `account.meta["plan"]` still reads as a dict rather than as the JSON
        wrapper that went to the database.
        """
        if not cls.casts:
            return attributes
        driver = cls._driver()
        out = dict(attributes)
        for column in cls.casts:
            if column in out:
                out[column] = cls._cast_for(column).dehydrate(out[column], driver)
        return out

    # -- eager-loaded relation cache -------------------------------------------

    def relation_loaded(self, name: Optional[str]) -> bool:
        return bool(name) and name in self._relations

    def get_relation(self, name: str) -> Any:
        return self._relations.get(name)

    def set_relation(self, name: Optional[str], value: Any) -> None:
        if name:
            self._relations[name] = value

    def unset_relation(self, name: str) -> None:
        self._relations.pop(name, None)

    @staticmethod
    def _calling_relation_name() -> Optional[str]:
        """Name of the model method that is building a relation.

        For the conventional `def posts(self): return self.has_many(Post)`, this
        returns "posts" — which is what the eager-load cache is keyed by. Reading
        the caller's frame is the established way to recover that name.
        """
        import inspect

        frame = inspect.currentframe()
        try:
            # 0: here, 1: has_many/belongs_to/..., 2: the model's relation method
            caller = frame.f_back.f_back if frame and frame.f_back else None
            return caller.f_code.co_name if caller else None
        finally:
            del frame

    @classmethod
    def get_table_name(cls) -> str:
        """Return `__table__`, or the name the generators use (`BlogPost` -> `blog_posts`).

        Before, a model without `__table__` used the class name lowercased plus
        an "s" (`categorys`, `blogposts`), which disagreed with the migrations
        the generators write. A table that exists only under that old name is
        still found, once per class, with a warning to set `__table__`.
        """
        if cls.__table__:
            return cls.__table__
        resolved = cls.__dict__.get("_resolved_table")
        if resolved is None:
            resolved = _infer_table(cls)
            cls._resolved_table = resolved
        return resolved

    @classmethod
    def _base_query(cls) -> QueryBuilder:
        """The unscoped starting point every mixin's `query()` builds from.

        `TenantScoped` and `SoftDeletes` each add their own predicate here via
        `super()._base_query()`, so both cooperate through this one chain
        regardless of which order they're listed in — a model mixing in both
        keeps every predicate no matter its base order.
        """
        return QueryBuilder(model_class=cls)

    @classmethod
    def query(cls) -> QueryBuilder:
        return cls._base_query()

    # -- UUID identity ---------------------------------------------------------

    @staticmethod
    def new_uuid() -> str:
        """A UUIDv7 — 48-bit millisecond timestamp, then randomness.

        Version 4 is uniformly random, so every insert lands on a different
        B-tree leaf and the index write set is effectively the whole index. A v7
        sorts by creation time, so inserts append to one side of it instead of
        scattering across it — same opacity in a URL, materially cheaper to
        index. PostgreSQL 18 has `uuidv7()` natively; on 16 and 17 it is
        generated here.
        """
        import os
        import time
        import uuid

        stamp = int(time.time() * 1000).to_bytes(6, "big")
        rest = bytearray(os.urandom(10))
        rest[0] = (rest[0] & 0x0F) | 0x70   # version 7
        rest[2] = (rest[2] & 0x3F) | 0x80   # RFC 4122 variant
        return str(uuid.UUID(bytes=bytes(stamp) + bytes(rest)))

    @classmethod
    def has_uuid_column(cls) -> bool:
        """Whether the table declares the public UUID column.

        The answer is cached on the DatabaseManager, not here: a schema belongs
        to a connection, so swapping connections — a replica, a tenant schema, a
        test database — has to invalidate it. Caching per model class meant a
        swap left the wrong answer behind.
        """
        try:
            from engine.container.application import Container

            db = Container.getInstance().make("db")
            return db.table_has_column(cls.get_table_name(), cls.uuid_column)
        except Exception:
            return False

    @classmethod
    def find_by_uuid(cls, value: str) -> Optional['Model']:
        if not value or (isinstance(value, str) and value.isdigit()):
            return None
        return cls.query().where(cls.uuid_column, value).first()

    @classmethod
    def find_by_uuid_or_fail(cls, value: str) -> 'Model':
        from engine.orm.exceptions import ModelNotFoundError

        found = cls.find_by_uuid(value)
        if found is None:
            raise ModelNotFoundError(f"No {cls.__name__} with uuid [{value}].")
        return found

    def route_key(self) -> Any:
        """The identifier to put in a URL — the UUID when there is one."""
        if self.uses_uuid and self._attributes.get(self.uuid_column):
            return self._attributes[self.uuid_column]
        return self._attributes.get(self.primary_key)

    @classmethod
    def find_by_route_key(cls, value: Any) -> Optional['Model']:
        """Resolve whatever `route_key()` produced, UUID or primary key.

        For security, when UUID is enabled on the model and schema, sequential
        integer queries are rejected to prevent ID enumeration.
        """
        if cls.uses_uuid and cls.has_uuid_column():
            if str(value).isdigit():
                return None
            return cls.find_by_uuid(str(value))
        return cls.find(value)

    @classmethod
    def create(cls, attributes: Dict[str, Any]) -> 'Model':
        # Mass-assignment protection, fail closed: only columns listed in
        # `fillable` may arrive from bulk input. An empty/undeclared
        # `fillable` means *nothing* is mass-assignable — not "everything",
        # which was the old, insecure default. Framework-managed columns
        # (primary key, UUID, timestamps) stay allowed regardless.
        # `guarded = False` is the explicit opt-out for a model that wants
        # every column writable; `force_create()` bypasses the guard
        # entirely for trusted internal writes.
        return cls.force_create(cls._mass_assignable(attributes))

    @classmethod
    def _mass_assignable(cls, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Return the part of bulk input `fillable` allows, warning about the rest.

        Dropping a column silently is how a record ends up saved without the
        field its author meant to write, so every discarded key is logged with
        the model and its current `fillable`. Keys starting with `_` (form
        plumbing such as `_token` and `_method`) are dropped without a warning.

        Args:
            attributes: Bulk input, typically a request body.

        Returns:
            The attributes that may be written.
        """
        if cls.guarded is False:
            return dict(attributes)
        allowed = set(cls.fillable) | {cls.primary_key, cls.uuid_column, "created_at", "updated_at"}
        dropped = sorted(k for k in attributes if k not in allowed and not str(k).startswith("_"))
        if dropped:
            _logger.warning(
                "mass_assignment_discarded model=%s discarded=%s fillable=%s "
                "hint=add the columns to `fillable`, assign them one by one, or use force_create() for trusted input",
                cls.__name__, dropped, sorted(cls.fillable),
            )
        return {k: v for k, v in attributes.items() if k in allowed}

    @classmethod
    def force_create(cls, attributes: Dict[str, Any]) -> 'Model':
        """Insert without consulting `fillable` — for trusted, internal input."""
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        clean_attrs = dict(cls.defaults)
        clean_attrs.update(attributes)
        clean_attrs.setdefault("created_at", now)
        clean_attrs.setdefault("updated_at", now)

        inst = cls(clean_attrs)

        from engine.container.application import Container
        db = Container.getInstance().make("db")

        # Tables with a non auto-incrementing primary key need a client-side id.
        if cls.primary_key not in clean_attrs and cls.key_type == "uuid":
            clean_attrs[cls.primary_key] = cls.new_uuid()

        # Fill the public UUID when the table declares one.
        if (
            cls.uses_uuid
            and cls.uuid_column not in clean_attrs
            and cls.has_uuid_column()
        ):
            clean_attrs[cls.uuid_column] = cls.new_uuid()
            inst._attributes[cls.uuid_column] = clean_attrs[cls.uuid_column]

        new_id = db.insert_get_id(
            cls.get_table_name(), cls._dehydrate(clean_attrs), cls.primary_key
        )
        if new_id is not None:
            inst._attributes[cls.primary_key] = new_id
        elif cls.primary_key not in inst._attributes:
            import uuid

            inst._attributes[cls.primary_key] = str(uuid.uuid4())
        inst.sync_original()

        from engine.events.lifecycle import ModelCreated, fire

        fire(ModelCreated(inst))
        return inst

    def save(self) -> 'Model':
        """Insert or update this record.

        An update writes only the columns changed since the row was loaded, so
        two users editing different fields of the same record do not overwrite
        each other. A record with no changes issues no statement at all.

        Returns:
            This model.
        """
        from engine.container.application import Container

        if self._attributes.get(self.primary_key) is None:
            # Attributes assigned one by one are the author's explicit intent
            # and are written as given; whatever came in bulk through the
            # constructor is still filtered by `fillable`.
            assigned = self.__dict__.get("_assigned", set())
            bulk = {k: v for k, v in self._attributes.items() if k not in assigned}
            explicit = {k: v for k, v in self._attributes.items() if k in assigned}
            created = self.__class__.force_create({**self._mass_assignable(bulk), **explicit})
            self._attributes = created._attributes
            self.sync_original()
            return self
        if not self.is_dirty():
            return self

        self._attributes["updated_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        # Dehydrated for the write only — `self._attributes` keeps the Python
        # values, so the model reads the same before and after a save.
        updates = self._dehydrate(self.get_dirty())
        for column in updates:
            _assert_identifier(column)
        assignments = ", ".join(f"{column} = ?" for column in updates)
        predicate, bindings = self._write_predicate()
        Container.getInstance().make("db").statement(
            f"UPDATE {self.get_table_name()} SET {assignments} WHERE {predicate}",
            list(updates.values()) + bindings,
        )
        self.sync_original()

        from engine.events.lifecycle import ModelUpdated, fire

        fire(ModelUpdated(self))
        return self

    def update(self, attributes: Dict[str, Any]) -> 'Model':
        """Update this record with `attributes` as given — trusted/internal
        input only. For request-supplied data use `update_attributes()`,
        which enforces `fillable` the same way `create()` does."""
        self._attributes.update(attributes)
        return self.save()

    def update_attributes(self, attributes: Dict[str, Any]) -> 'Model':
        """Mass-assignment-guarded update: the `update()` counterpart to
        `create()` for input coming from a request body. Fails closed the
        same way `create()` does — an empty/undeclared `fillable` allows
        nothing through unless the model opts out with `guarded = False`."""
        if self.guarded is not False:
            allowed = set(self.fillable)
            attributes = {k: v for k, v in attributes.items() if k in allowed}
        return self.update(attributes)

    def delete(self) -> bool:
        from engine.container.application import Container

        db = Container.getInstance().make("db")
        if self._attributes.get(self.primary_key) is None:
            return False
        predicate, bindings = self._write_predicate()
        db.statement(f"DELETE FROM {self.get_table_name()} WHERE {predicate}", bindings)

        from engine.events.lifecycle import ModelDeleted, fire

        fire(ModelDeleted(self))
        return True

    @classmethod
    def all(cls) -> Any:
        return cls.query().get()

    @classmethod
    def where(cls, column: str, operator_or_value: Any = _MISSING, value: Any = _MISSING) -> QueryBuilder:
        return cls.query().where(column, operator_or_value, value)

    @classmethod
    def where_vector_similar(
        cls,
        column: str,
        vector: Any,
        min_similarity: float = 0.7,
        metric: str = "cosine",
    ) -> QueryBuilder:
        """Filter records by vector similarity (semantic search)."""
        return cls.query().where_vector_similar(column, vector, min_similarity=min_similarity, metric=metric)

    @classmethod
    def order_by_vector_similarity(
        cls,
        column: str,
        vector: Any,
        ascending: bool = False,
    ) -> QueryBuilder:
        """Sort records by vector similarity."""
        return cls.query().order_by_vector_similarity(column, vector, ascending=ascending)

    @classmethod
    def with_(cls, *relations: str) -> QueryBuilder:
        """Start a query that eager loads the given relations."""
        return cls.query().with_(*relations)

    @classmethod
    def find_or_fail(cls, id_val: Any) -> 'Model':
        from engine.orm.exceptions import ModelNotFoundError

        found = cls.find(id_val)
        if found is None:
            raise ModelNotFoundError(f"No {cls.__name__} found with id [{id_val}].")
        return found

    def to_dict(self) -> Dict[str, Any]:
        hidden = set(getattr(self, "hidden", []))
        return {k: v for k, v in self._attributes.items() if k not in hidden}

    def __getattr__(self, name: str) -> Any:
        attributes = self.__dict__.get("_attributes", {})
        if name in attributes:
            return attributes[name]
        from engine.support.diagnostics import closest, describe

        raise AttributeError(describe(
            "MODEL_ATTRIBUTE_MISSING", model=type(self).__name__, name=name,
            closest=closest(name, attributes), columns=", ".join(sorted(attributes)),
        ))

    def __setattr__(self, name: str, value: Any) -> None:
        """Route `model.column = value` to the attributes `save()` writes.

        Without this, the value landed on the instance and `save()` saw no
        change, so the write was silently dropped while every later read
        still showed the new value. Private names, and names the class itself
        defines (configuration such as `fillable`, properties, methods), keep
        normal attribute semantics.
        """
        if name.startswith("_") or "_attributes" not in self.__dict__ or hasattr(type(self), name):
            object.__setattr__(self, name, value)
            return
        self.set_attribute(name, value)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self._attributes!r}>"

    @classmethod
    def find(cls, id_val: Any) -> Optional['Model']:
        if cls.uses_uuid and cls.has_uuid_column() and isinstance(id_val, str) and not id_val.isdigit():
            found = cls.find_by_uuid(id_val)
            if found is not None:
                return found
        return cls.query().where(cls.primary_key, id_val).first()


    def get_attribute(self, key: str) -> Any:
        return self._attributes.get(key)

    def set_attribute(self, key: str, value: Any) -> None:
        """Assign one column value, to be written by the next `save()`.

        Args:
            key: The column name.
            value: The new value.
        """
        self._attributes[key] = value
        self.__dict__.setdefault("_assigned", set()).add(key)

    # -- relationships ---------------------------------------------------------

    def has_many(self, related_class: Type, foreign_key: Optional[str] = None,
                 local_key: str = "id", name: Optional[str] = None) -> HasMany:
        fk = foreign_key or f"{self.__class__.__name__.lower()}_id"
        return HasMany(
            self, related_class, foreign_key=fk, local_key=local_key,
            name=name or self._calling_relation_name(),
        )

    def has_one(self, related_class: Type, foreign_key: Optional[str] = None,
                local_key: str = "id", name: Optional[str] = None) -> HasOne:
        fk = foreign_key or f"{self.__class__.__name__.lower()}_id"
        return HasOne(
            self, related_class, foreign_key=fk, local_key=local_key,
            name=name or self._calling_relation_name(),
        )

    def belongs_to(self, related_class: Type, foreign_key: Optional[str] = None,
                   owner_key: str = "id", name: Optional[str] = None) -> BelongsTo:
        fk = foreign_key or f"{related_class.__name__.lower()}_id"
        return BelongsTo(
            self, related_class, foreign_key=fk, owner_key=owner_key,
            name=name or self._calling_relation_name(),
        )

    def belongs_to_many(
        self,
        related_class: Type,
        pivot_table: Optional[str] = None,
        foreign_pivot_key: Optional[str] = None,
        related_pivot_key: Optional[str] = None,
        name: Optional[str] = None,
    ) -> BelongsToMany:
        this = self.__class__.__name__.lower()
        other = related_class.__name__.lower()
        # Convention: singular names joined alphabetically.
        pivot = pivot_table or "_".join(sorted([this, other]))
        return BelongsToMany(
            self,
            related_class,
            pivot_table=pivot,
            foreign_pivot_key=foreign_pivot_key or f"{this}_id",
            related_pivot_key=related_pivot_key or f"{other}_id",
            name=name or self._calling_relation_name(),
        )

    # RBAC lived here — `roles()`, `permissions()`, `has_role()`,
    # `has_permission()` — on the base every model inherits from, hardwired to
    # `role_user.user_id`. So `Post.find(1).roles()` returned the roles of
    # *user* 1: wrong data, no error. It also made the framework import
    # `app.Models.Role`, pointing the engine at the application.
    #
    # They now live on the models they describe: `roles`/`has_role`/
    # `has_permission` on `app/Models/User.py`, `permissions` on
    # `app/Models/Role.py`.
