"""
Dataset schemas for CSV upload and configuration
"""
from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum
from uuid import UUID


class DatasetStatus(str, Enum):
    """Dataset processing status"""
    PENDING = "pending"
    VALIDATED = "validated"
    READY = "ready"
    FAILED = "failed"


class DatasetType(str, Enum):
    """Dataset file type"""
    CSV = "csv"
    IMAGE = "image"  # ZIP archive with image folders


# ==================== Column Info Schemas ====================

class ColumnInfo(BaseModel):
    """Column metadata from CSV analysis"""
    name: str = Field(..., description="Column name")
    dtype: str = Field(..., description="Detected data type (int, float, string, bool)")
    sample_values: List[Any] = Field(default_factory=list, description="Sample values from column")
    null_count: int = Field(default=0, description="Number of null/missing values")
    unique_count: int = Field(default=0, description="Number of unique values")
    is_numeric: bool = Field(default=False, description="Whether column is numeric")
    is_categorical: bool = Field(default=False, description="Whether column is categorical")
    suggested_encoding: Optional[str] = Field(None, description="Suggested encoding method")


class ColumnSummary(BaseModel):
    """Simplified column info for UI display"""
    name: str
    dtype: str
    is_numeric: bool
    is_categorical: bool


# ==================== Request Schemas ====================

class DatasetUploadResponse(BaseModel):
    """Response after successful CSV upload"""
    id: str = Field(..., description="Dataset ID")
    name: str
    original_filename: str
    size_bytes: int
    row_count: int
    column_count: int
    columns: List[ColumnInfo] = Field(default_factory=list)
    preview_rows: List[Dict[str, Any]] = Field(default_factory=list, description="First few rows for preview")
    status: DatasetStatus
    message: str = "Dataset uploaded successfully"

    model_config = ConfigDict(from_attributes=True)


class DatasetConfigureRequest(BaseModel):
    """Request to configure dataset for ML training"""
    dataset_id: str = Field(..., description="Dataset ID to configure")
    target_column: str = Field(..., description="Column to predict (target/label)")
    feature_columns: Optional[List[str]] = Field(None, description="Columns to use as features (defaults to all except target)")
    project_id: Optional[str] = Field(None, description="Associate with existing project")


class DatasetConfigureResponse(BaseModel):
    """Response after configuring dataset"""
    id: str
    name: str
    target_column: str
    feature_columns: List[str]
    status: DatasetStatus
    message: str = "Dataset configured successfully"

    model_config = ConfigDict(from_attributes=True)


# ==================== Response Schemas ====================

class DatasetResponse(BaseModel):
    """Full dataset details"""
    id: str
    project_id: Optional[str] = None
    user_id: str
    name: str
    original_filename: str
    s3_key: str
    size_bytes: int
    dataset_type: DatasetType
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    columns: Optional[List[ColumnInfo]] = None
    target_column: Optional[str] = None
    feature_columns: Optional[List[str]] = None
    status: DatasetStatus
    validation_errors: Optional[List[str]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('id', 'project_id', 'user_id')
    def serialize_uuid(self, value):
        return str(value) if value else None


class DatasetListItem(BaseModel):
    """Simplified dataset for list display"""
    id: str
    name: str
    original_filename: str
    size_bytes: int
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    target_column: Optional[str] = None
    status: DatasetStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('id')
    def serialize_uuid(self, value):
        return str(value) if value else None


class DatasetListResponse(BaseModel):
    """List of datasets"""
    datasets: List[DatasetListItem]
    total: int


# ==================== ML Generation with Dataset ====================

class MLGenerateWithDatasetRequest(BaseModel):
    """Request to generate ML project with uploaded dataset"""
    model_type: str = Field(..., description="ML model type (random_forest, xgboost, etc.)")
    project_name: str = Field(..., min_length=1, max_length=100, description="Project name")
    dataset_id: str = Field(..., description="Dataset ID to use")
    target_column: str = Field(..., description="Target column for prediction")
    feature_columns: Optional[List[str]] = Field(None, description="Feature columns (defaults to all except target)")

    # Optional ML configuration
    num_classes: Optional[int] = Field(None, ge=2, description="Number of output classes (for classification)")
    batch_size: Optional[int] = Field(None, ge=1, le=512, description="Training batch size")
    epochs: Optional[int] = Field(None, ge=1, le=1000, description="Number of training epochs")
    learning_rate: Optional[float] = Field(None, gt=0, le=1.0, description="Learning rate")
    test_size: Optional[float] = Field(0.2, gt=0, lt=1.0, description="Test set proportion")

    # Workspace association
    workspace_id: Optional[str] = Field(None, description="Workspace to create project in")


class MLGenerateWithDatasetResponse(BaseModel):
    """Response after generating ML project with dataset"""
    project_id: str
    project_name: str
    model_type: str
    dataset_id: str
    files_created: int
    data_loader_path: str = Field(default="data/data_loader.py", description="Path to generated data loader")
    message: str


# ==================== Tabular Models ====================

TABULAR_ML_MODELS = [
    "random_forest",
    "xgboost",
    "logistic_regression",
    "svm",
    "gradient_boosting",
    "decision_tree",
    "knn",
    "naive_bayes",
]

def is_tabular_model(model_type: str) -> bool:
    """Check if model type supports CSV datasets"""
    return model_type.lower() in TABULAR_ML_MODELS


# ==================== Vision Models ====================

VISION_ML_MODELS = [
    "cnn",
    "resnet",
    "vgg",
    "efficientnet",
    "yolo",
    "unet",
    "mobilenet",
    "inception",
    "densenet",
]

def is_vision_model(model_type: str) -> bool:
    """Check if model type supports image datasets"""
    return model_type.lower() in VISION_ML_MODELS


# ==================== Image Dataset Schemas ====================

class ImageClassInfo(BaseModel):
    """Information about a class in an image dataset"""
    name: str = Field(..., description="Class name (folder name)")
    image_count: int = Field(..., description="Number of images in this class")
    sample_images: List[str] = Field(default_factory=list, description="S3 keys of sample images for preview")


class ImageInfo(BaseModel):
    """Image format information"""
    formats: List[str] = Field(default_factory=list, description="Image formats found (jpg, png, etc.)")
    avg_width: Optional[int] = Field(None, description="Average image width")
    avg_height: Optional[int] = Field(None, description="Average image height")
    min_width: Optional[int] = Field(None, description="Minimum image width")
    min_height: Optional[int] = Field(None, description="Minimum image height")
    max_width: Optional[int] = Field(None, description="Maximum image width")
    max_height: Optional[int] = Field(None, description="Maximum image height")


class SplitInfo(BaseModel):
    """Train/test/val split information"""
    train_count: int = Field(default=0, description="Number of training images")
    test_count: int = Field(default=0, description="Number of test images")
    val_count: int = Field(default=0, description="Number of validation images")
    has_split: bool = Field(default=False, description="Whether dataset has predefined splits")


class ImageDatasetUploadResponse(BaseModel):
    """Response after successful image dataset upload"""
    id: str = Field(..., description="Dataset ID")
    name: str
    original_filename: str
    size_bytes: int
    dataset_type: DatasetType = DatasetType.IMAGE
    total_images: int
    num_classes: int
    classes: List[ImageClassInfo] = Field(default_factory=list)
    image_info: Optional[ImageInfo] = None
    split_info: Optional[SplitInfo] = None
    recommended_input_size: int = Field(default=224, description="Recommended input size for training")
    status: DatasetStatus
    message: str = "Image dataset uploaded successfully"

    model_config = ConfigDict(from_attributes=True)


class ImageDatasetConfigureRequest(BaseModel):
    """Request to configure image dataset for ML training"""
    dataset_id: str = Field(..., description="Dataset ID to configure")
    input_size: Optional[int] = Field(224, ge=32, le=1024, description="Input image size for training")
    augmentation: Optional[bool] = Field(True, description="Enable data augmentation")
    normalize: Optional[bool] = Field(True, description="Normalize images")
    project_id: Optional[str] = Field(None, description="Associate with existing project")


class ImageDatasetConfigureResponse(BaseModel):
    """Response after configuring image dataset"""
    id: str
    name: str
    num_classes: int
    class_names: List[str]
    input_size: int
    status: DatasetStatus
    message: str = "Image dataset configured successfully"

    model_config = ConfigDict(from_attributes=True)


# ==================== ML Generation with Image Dataset ====================

class MLGenerateWithImageDatasetRequest(BaseModel):
    """Request to generate ML project with uploaded image dataset"""
    model_type: str = Field(..., description="ML model type (cnn, resnet, yolo, etc.)")
    project_name: str = Field(..., min_length=1, max_length=100, description="Project name")
    dataset_id: str = Field(..., description="Image dataset ID to use")

    # Image configuration
    input_size: Optional[int] = Field(224, ge=32, le=1024, description="Input image size")
    augmentation: Optional[bool] = Field(True, description="Enable data augmentation")

    # Training configuration
    num_classes: Optional[int] = Field(None, ge=2, description="Number of classes (auto-detected if not provided)")
    batch_size: Optional[int] = Field(32, ge=1, le=256, description="Training batch size")
    epochs: Optional[int] = Field(50, ge=1, le=500, description="Number of training epochs")
    learning_rate: Optional[float] = Field(0.001, gt=0, le=1.0, description="Learning rate")

    # Advanced options
    pretrained: Optional[bool] = Field(True, description="Use pretrained weights (transfer learning)")
    freeze_layers: Optional[bool] = Field(False, description="Freeze early layers during training")

    # Workspace association
    workspace_id: Optional[str] = Field(None, description="Workspace to create project in")


class MLGenerateWithImageDatasetResponse(BaseModel):
    """Response after generating ML project with image dataset"""
    project_id: str
    project_name: str
    model_type: str
    dataset_id: str
    num_classes: int
    input_size: int
    files_created: int
    data_loader_path: str = Field(default="data/image_loader.py", description="Path to generated image loader")
    message: str
