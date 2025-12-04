"""Custom SQLAlchemy types for cross-database compatibility"""
from sqlalchemy import String
import uuid


def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())


# Simple String-based UUID - works with all databases
# Just use String(36) and store UUIDs as strings
GUID = String(36)
