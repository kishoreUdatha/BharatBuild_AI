"""
Dataset model for ML training data uploads
"""
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class DatasetStatus(str, enum.Enum):
    """Dataset processing status"""
    PENDING = "pending"        # Uploaded but not yet validated
    VALIDATED = "validated"    # Parsed and validated successfully
    READY = "ready"            # Configured with target/features, ready for ML
    FAILED = "failed"          # Validation or processing failed


class DatasetType(str, enum.Enum):
    """Dataset file type"""
    CSV = "csv"
    IMAGE = "image"  # ZIP archive with image folders


class Dataset(Base):
    """
    Dataset model for storing ML training data metadata.

    Stores information about uploaded CSV files for ML model training,
    including column analysis, target/feature selection, and S3 storage info.
    """
    __tablename__ = "datasets"

    # Database indexes for performance
    __table_args__ = (
        Index('ix_datasets_user_id', 'user_id'),
        Index('ix_datasets_project_id', 'project_id'),
        Index('ix_datasets_status', 'status'),
        Index('ix_datasets_created_at', 'created_at'),
        Index('ix_datasets_user_status', 'user_id', 'status'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Basic info
    name = Column(String(255), nullable=False)
    original_filename = Column(String(500), nullable=False)

    # S3 storage
    s3_key = Column(String(1000), nullable=False)
    content_hash = Column(String(64), nullable=True)  # SHA-256 hash for deduplication

    # File metadata
    size_bytes = Column(Integer, nullable=False)
    dataset_type = Column(SQLEnum(DatasetType), default=DatasetType.CSV, nullable=False)

    # Data statistics
    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)

    # Column analysis - JSON array of column info:
    # [{name, dtype, sample_values, null_count, unique_count, is_numeric, is_categorical}]
    columns = Column(JSON, nullable=True)

    # ML configuration (for CSV/tabular)
    target_column = Column(String(255), nullable=True)
    feature_columns = Column(JSON, nullable=True)  # List of selected feature column names

    # Image dataset fields
    # Classes detected from folder structure: [{name, image_count, sample_images}]
    classes = Column(JSON, nullable=True)
    num_classes = Column(Integer, nullable=True)
    total_images = Column(Integer, nullable=True)
    # Image format info: {formats: ["jpg", "png"], avg_width, avg_height}
    image_info = Column(JSON, nullable=True)
    # Train/test split info: {train_count, test_count, val_count}
    split_info = Column(JSON, nullable=True)
    # Recommended input size based on image analysis
    recommended_input_size = Column(Integer, nullable=True)

    # Processing status
    status = Column(SQLEnum(DatasetStatus), default=DatasetStatus.PENDING, nullable=False)
    validation_errors = Column(JSON, nullable=True)  # List of validation error messages

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="datasets")
    project = relationship("Project", back_populates="datasets")

    def __repr__(self):
        return f"<Dataset {self.name} ({self.status.value})>"

    @property
    def is_ready(self) -> bool:
        """Check if dataset is ready for ML training"""
        if self.dataset_type == DatasetType.CSV:
            return self.status == DatasetStatus.READY and self.target_column is not None
        elif self.dataset_type == DatasetType.IMAGE:
            return self.status == DatasetStatus.READY and self.num_classes is not None and self.num_classes >= 2
        return False

    @property
    def is_image_dataset(self) -> bool:
        """Check if this is an image dataset"""
        return self.dataset_type == DatasetType.IMAGE

    @property
    def class_names(self) -> list:
        """Get class names for image datasets"""
        if self.classes:
            return [cls.get('name') for cls in self.classes]
        return []

    @property
    def preview_columns(self) -> list:
        """Get column names for preview"""
        if self.columns:
            return [col.get('name') for col in self.columns]
        return []

    @property
    def numeric_columns(self) -> list:
        """Get numeric column names"""
        if self.columns:
            return [col.get('name') for col in self.columns if col.get('is_numeric')]
        return []

    @property
    def categorical_columns(self) -> list:
        """Get categorical column names"""
        if self.columns:
            return [col.get('name') for col in self.columns if col.get('is_categorical')]
        return []
