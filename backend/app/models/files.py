"""
Stored files.

Until now the file-bearing rows described files that existed nowhere: a
`BatchDocument` carried a name, a size and a page count but no pointer to any
bytes, and `BasePaper.file_name` named a PDF nobody could open. Every screen
that offered a download was offering one that could not be produced.

One row per blob, addressed by the SHA-256 of its content. Two consequences
follow from that choice and both are wanted:

* the same PDF uploaded by four teammates is stored once, and
* the stored key is derived from the content rather than the client's
  filename, so nothing a browser sends can influence where a file lands.

Blobs are never deleted when a document that referenced them is: another
version, another batch, or another team may share the same content.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class StoredFile(Base):
    """One blob in the file store, wherever it physically lives."""
    __tablename__ = "stored_files"
    __table_args__ = (
        UniqueConstraint("college_id", "sha256", name="uq_stored_file_per_college"),
    )


    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Content address. Unique: uploading identical bytes twice reuses the row.
    # Which institution this row belongs to. See the add_tenant_isolation migration.
    college_id = Column(GUID, ForeignKey("colleges.id"), nullable=False, index=True)
    
    sha256 = Column(String(64), nullable=False, index=True)

    # Which backend holds it, and the key within that backend. Recorded per
    # row rather than read from config at download time, so files written
    # while the deployment used local disk stay readable after a move to S3.
    backend = Column(String(16), nullable=False, default="local")
    storage_key = Column(String(500), nullable=False)

    # What the uploader called it. Shown to people and used for the download
    # filename; never used to build a path.
    original_name = Column(String(255), nullable=False)
    mime_type = Column(String(120), nullable=False)
    byte_size = Column(Integer, nullable=False)
    page_count = Column(Integer, nullable=True)

    uploaded_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])

    def __repr__(self):
        return f"<StoredFile {self.original_name} {self.byte_size}b>"
