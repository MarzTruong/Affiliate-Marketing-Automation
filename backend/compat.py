"""Database type compatibility for SQLite and PostgreSQL."""

import json
import uuid

from sqlalchemy import String, Text, TypeDecorator
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeEngine

from backend.config import settings

IS_SQLITE = settings.database_url.startswith("sqlite")


class GUID(TypeDecorator):
    """Platform-independent UUID type. Uses String(36) on SQLite, native UUID on PostgreSQL."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine:
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID

            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value: uuid.UUID | str | None, dialect: Dialect) -> str | uuid.UUID | None:
        if value is not None:
            if dialect.name == "postgresql":
                return value
            return str(value)
        return value

    def process_result_value(self, value: str | uuid.UUID | None, dialect: Dialect) -> uuid.UUID | None:
        if value is not None:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
        return value


class JSONType(TypeDecorator):
    """Platform-independent JSON type. Uses Text with JSON serialization on SQLite, JSONB on PostgreSQL."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine:
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB

            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: dict | list | None, dialect: Dialect) -> str | dict | list | None:
        if value is not None and dialect.name != "postgresql":
            return json.dumps(value)
        return value

    def process_result_value(self, value: str | dict | list | None, dialect: Dialect) -> dict | list | None:
        if value is not None and isinstance(value, str):
            return json.loads(value)
        return value


class StringArrayType(TypeDecorator):
    """Platform-independent array type. Uses JSON on SQLite, ARRAY on PostgreSQL."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine:
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import ARRAY

            return dialect.type_descriptor(ARRAY(String))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: list | None, dialect: Dialect) -> str | list | None:
        if value is not None and dialect.name != "postgresql":
            return json.dumps(value)
        return value

    def process_result_value(self, value: str | list | None, dialect: Dialect) -> list | None:
        if value is not None and isinstance(value, str):
            return json.loads(value)
        return value
