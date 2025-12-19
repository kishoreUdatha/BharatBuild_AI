"""Custom SQLAlchemy types for cross-database compatibility"""
from sqlalchemy import TypeDecorator, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid


def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())


class GUID(TypeDecorator):
    """Platform-independent GUID type that stores UUIDs as VARCHAR(36)"""
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        # Always use String(36) to avoid type mismatch with existing VARCHAR columns
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return str(value)
        return value
