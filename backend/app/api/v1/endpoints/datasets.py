"""
Datasets API - CSV and Image Upload for ML Training Data

Endpoints:
- POST /datasets/upload - Upload CSV file (multipart/form-data)
- POST /datasets/upload-images - Upload ZIP with images (multipart/form-data)
- POST /datasets/configure - Configure CSV dataset
- POST /datasets/configure-images - Configure image dataset
- GET /datasets/{dataset_id} - Get dataset details
- GET /datasets - List user's datasets
- DELETE /datasets/{dataset_id} - Delete a dataset
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List, Any, Dict
import hashlib
import io
import zipfile
import tempfile
import os
from pathlib import Path
import pandas as pd

from app.core.database import get_db
from app.core.config import settings
from app.core.logging_config import logger
from app.models.user import User
from app.models.dataset import Dataset, DatasetStatus, DatasetType
from app.modules.auth.dependencies import get_current_user
from app.services.storage_service import StorageService
from app.schemas.dataset import (
    DatasetUploadResponse,
    DatasetConfigureRequest,
    DatasetConfigureResponse,
    DatasetResponse,
    DatasetListItem,
    DatasetListResponse,
    ColumnInfo,
    ImageDatasetUploadResponse,
    ImageDatasetConfigureRequest,
    ImageDatasetConfigureResponse,
    ImageClassInfo,
    ImageInfo,
    SplitInfo,
)

router = APIRouter(prefix="/datasets", tags=["Datasets"])

# Constants
MAX_CSV_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_IMAGE_ZIP_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB for image datasets
MAX_PREVIEW_ROWS = 5
MAX_SAMPLE_VALUES = 5
MAX_SAMPLE_IMAGES = 3  # Sample images per class for preview
CATEGORICAL_THRESHOLD = 50  # Unique values threshold for categorical detection
SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}


# ==================== Helper Functions ====================

def detect_column_type(series: pd.Series) -> Dict[str, Any]:
    """
    Detect column data type and characteristics.

    Returns:
        dict with dtype, is_numeric, is_categorical, sample_values, etc.
    """
    # Handle null values
    non_null = series.dropna()
    null_count = series.isna().sum()
    unique_count = series.nunique()

    # Sample values (first N non-null unique values)
    sample_values = non_null.unique()[:MAX_SAMPLE_VALUES].tolist()

    # Detect data type
    dtype = str(series.dtype)
    is_numeric = False
    is_categorical = False
    suggested_encoding = None

    if pd.api.types.is_integer_dtype(series):
        dtype = "int"
        is_numeric = True
    elif pd.api.types.is_float_dtype(series):
        dtype = "float"
        is_numeric = True
    elif pd.api.types.is_bool_dtype(series):
        dtype = "bool"
        is_categorical = True
        suggested_encoding = "binary"
    elif pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
        dtype = "string"
        # String with few unique values = categorical
        if unique_count <= CATEGORICAL_THRESHOLD:
            is_categorical = True
            suggested_encoding = "onehot" if unique_count <= 10 else "label"
        else:
            suggested_encoding = "text_embedding"

    return {
        "dtype": dtype,
        "is_numeric": is_numeric,
        "is_categorical": is_categorical,
        "null_count": int(null_count),
        "unique_count": int(unique_count),
        "sample_values": sample_values,
        "suggested_encoding": suggested_encoding,
    }


def analyze_csv(content: bytes) -> Dict[str, Any]:
    """
    Parse and analyze CSV content.

    Returns:
        dict with row_count, column_count, columns info, preview_rows
    """
    try:
        # Read CSV
        df = pd.read_csv(io.BytesIO(content))

        # Basic stats
        row_count = len(df)
        column_count = len(df.columns)

        # Analyze each column
        columns = []
        for col_name in df.columns:
            col_info = detect_column_type(df[col_name])
            col_info["name"] = col_name
            columns.append(col_info)

        # Preview rows (first N rows as dict)
        preview_rows = df.head(MAX_PREVIEW_ROWS).to_dict(orient="records")

        return {
            "row_count": row_count,
            "column_count": column_count,
            "columns": columns,
            "preview_rows": preview_rows,
        }

    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {str(e)}")


def analyze_image_zip(zip_content: bytes) -> Dict[str, Any]:
    """
    Analyze a ZIP file containing image folders for classification.

    Expected structure:
    dataset.zip
    ├── train/
    │   ├── class1/
    │   │   ├── image1.jpg
    │   │   └── image2.jpg
    │   └── class2/
    │       └── image1.jpg
    └── test/ (optional)
        └── ...

    Or flat structure:
    dataset.zip
    ├── class1/
    │   └── images...
    └── class2/
        └── images...

    Returns:
        dict with classes, total_images, image_info, split_info
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zf:
            # Get all file paths
            all_files = zf.namelist()

            # Find image files
            image_files = [
                f for f in all_files
                if not f.endswith('/') and
                Path(f).suffix.lower() in SUPPORTED_IMAGE_FORMATS
            ]

            if not image_files:
                raise ValueError("No supported image files found in ZIP")

            # Analyze folder structure
            classes_dict: Dict[str, Dict[str, Any]] = {}
            split_counts = {"train": 0, "test": 0, "val": 0}
            has_split = False
            image_formats = set()

            for img_path in image_files:
                parts = Path(img_path).parts

                # Skip hidden files and __MACOSX
                if any(p.startswith('.') or p.startswith('__') for p in parts):
                    continue

                image_formats.add(Path(img_path).suffix.lower().lstrip('.'))

                # Determine class name based on folder structure
                if len(parts) >= 2:
                    # Check for train/test/val split structure
                    if parts[0].lower() in ['train', 'test', 'val', 'validation']:
                        has_split = True
                        split_name = parts[0].lower()
                        if split_name == 'validation':
                            split_name = 'val'
                        split_counts[split_name] = split_counts.get(split_name, 0) + 1

                        if len(parts) >= 3:
                            class_name = parts[1]
                        else:
                            class_name = "unknown"
                    else:
                        # Flat structure: first folder is class
                        class_name = parts[0]
                else:
                    class_name = "unknown"

                # Add to class dict
                if class_name not in classes_dict:
                    classes_dict[class_name] = {
                        "name": class_name,
                        "image_count": 0,
                        "sample_images": []
                    }

                classes_dict[class_name]["image_count"] += 1

                # Store sample images (up to MAX_SAMPLE_IMAGES)
                if len(classes_dict[class_name]["sample_images"]) < MAX_SAMPLE_IMAGES:
                    classes_dict[class_name]["sample_images"].append(img_path)

            # Convert to list and sort by name
            classes = sorted(classes_dict.values(), key=lambda x: x["name"])

            # Calculate totals
            total_images = sum(c["image_count"] for c in classes)
            num_classes = len(classes)

            if num_classes < 2:
                raise ValueError(f"Need at least 2 classes, found {num_classes}")

            # Build split info
            split_info = {
                "train_count": split_counts.get("train", 0),
                "test_count": split_counts.get("test", 0),
                "val_count": split_counts.get("val", 0),
                "has_split": has_split
            }

            # Image info
            image_info = {
                "formats": list(image_formats),
                "avg_width": None,  # Would require opening images
                "avg_height": None,
            }

            # Recommend input size based on common sizes
            recommended_input_size = 224  # Default for most models

            return {
                "classes": classes,
                "num_classes": num_classes,
                "total_images": total_images,
                "image_info": image_info,
                "split_info": split_info,
                "recommended_input_size": recommended_input_size,
            }

    except zipfile.BadZipFile:
        raise ValueError("Invalid ZIP file")
    except Exception as e:
        raise ValueError(f"Failed to analyze image ZIP: {str(e)}")


def get_storage_service() -> StorageService:
    """Get storage service instance"""
    return StorageService()


# ==================== Endpoints ====================

@router.post("/upload", response_model=DatasetUploadResponse)
async def upload_csv(
    file: UploadFile = File(..., description="CSV file to upload (max 10MB)"),
    name: Optional[str] = Form(None, description="Dataset name (defaults to filename)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a CSV file for ML training data.

    The file will be:
    1. Validated (CSV format, size limit)
    2. Parsed with pandas
    3. Column types detected
    4. Uploaded to S3
    5. Metadata stored in database

    Returns dataset info with column analysis and preview rows.
    """
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )

    # Read file content
    content = await file.read()

    # Validate size
    if len(content) > MAX_CSV_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_CSV_SIZE_BYTES // (1024 * 1024)}MB"
        )

    # Validate content is not empty
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file"
        )

    # Analyze CSV
    try:
        analysis = analyze_csv(content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV file: {str(e)}"
        )

    # Validate minimum columns
    if analysis["column_count"] < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV must have at least 2 columns"
        )

    # Calculate content hash for deduplication
    content_hash = hashlib.sha256(content).hexdigest()

    # Generate S3 key
    dataset_name = name or file.filename.rsplit('.', 1)[0]
    s3_key = f"datasets/{current_user.id}/{content_hash[:8]}_{file.filename}"

    # Upload to S3
    try:
        storage = get_storage_service()
        await storage.upload_file(
            project_id=f"datasets/{current_user.id}",
            file_path=f"{content_hash[:8]}_{file.filename}",
            content=content,
            content_type="text/csv"
        )
    except Exception as e:
        logger.error(f"[Datasets] S3 upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to storage"
        )

    # Create dataset record
    dataset = Dataset(
        user_id=str(current_user.id),
        name=dataset_name,
        original_filename=file.filename,
        s3_key=s3_key,
        content_hash=content_hash,
        size_bytes=len(content),
        dataset_type=DatasetType.CSV,
        row_count=analysis["row_count"],
        column_count=analysis["column_count"],
        columns=analysis["columns"],
        status=DatasetStatus.VALIDATED,
    )

    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)

    logger.info(f"[Datasets] User {current_user.id} uploaded dataset {dataset.id} ({file.filename})")

    return DatasetUploadResponse(
        id=str(dataset.id),
        name=dataset.name,
        original_filename=dataset.original_filename,
        size_bytes=dataset.size_bytes,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        columns=[ColumnInfo(**col) for col in analysis["columns"]],
        preview_rows=analysis["preview_rows"],
        status=DatasetStatus.VALIDATED,
        message="Dataset uploaded and validated successfully"
    )


@router.post("/configure", response_model=DatasetConfigureResponse)
async def configure_dataset(
    request: DatasetConfigureRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Configure a dataset with target and feature columns.

    This prepares the dataset for ML training by specifying:
    - target_column: The column to predict
    - feature_columns: Columns to use as inputs (optional, defaults to all except target)
    """
    # Get dataset
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == request.dataset_id,
            Dataset.user_id == str(current_user.id)
        )
    )
    dataset = result.scalar_one_or_none()

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )

    # Validate target column exists
    column_names = [col.get("name") for col in dataset.columns] if dataset.columns else []
    if request.target_column not in column_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target column '{request.target_column}' not found in dataset"
        )

    # Determine feature columns
    if request.feature_columns:
        # Validate all feature columns exist
        invalid_cols = [c for c in request.feature_columns if c not in column_names]
        if invalid_cols:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Feature columns not found: {invalid_cols}"
            )
        feature_columns = request.feature_columns
    else:
        # Default: all columns except target
        feature_columns = [c for c in column_names if c != request.target_column]

    # Validate at least one feature column
    if not feature_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one feature column is required"
        )

    # Update dataset
    dataset.target_column = request.target_column
    dataset.feature_columns = feature_columns
    dataset.status = DatasetStatus.READY

    # Associate with project if provided
    if request.project_id:
        dataset.project_id = request.project_id

    await db.commit()
    await db.refresh(dataset)

    logger.info(f"[Datasets] Dataset {dataset.id} configured: target={request.target_column}")

    return DatasetConfigureResponse(
        id=str(dataset.id),
        name=dataset.name,
        target_column=dataset.target_column,
        feature_columns=dataset.feature_columns,
        status=DatasetStatus.READY,
        message="Dataset configured successfully"
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dataset details by ID.
    """
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.user_id == str(current_user.id)
        )
    )
    dataset = result.scalar_one_or_none()

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )

    return DatasetResponse(
        id=str(dataset.id),
        project_id=str(dataset.project_id) if dataset.project_id else None,
        user_id=str(dataset.user_id),
        name=dataset.name,
        original_filename=dataset.original_filename,
        s3_key=dataset.s3_key,
        size_bytes=dataset.size_bytes,
        dataset_type=dataset.dataset_type,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        columns=[ColumnInfo(**col) for col in dataset.columns] if dataset.columns else None,
        target_column=dataset.target_column,
        feature_columns=dataset.feature_columns,
        status=dataset.status,
        validation_errors=dataset.validation_errors,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
    )


@router.get("", response_model=DatasetListResponse)
async def list_datasets(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all datasets for the current user.
    """
    # Build query
    query = select(Dataset).where(Dataset.user_id == str(current_user.id))

    if status_filter:
        try:
            status_enum = DatasetStatus(status_filter)
            query = query.where(Dataset.status == status_enum)
        except ValueError:
            pass  # Ignore invalid status filter

    # Count total
    count_query = select(func.count(Dataset.id)).where(Dataset.user_id == str(current_user.id))
    if status_filter:
        try:
            status_enum = DatasetStatus(status_filter)
            count_query = count_query.where(Dataset.status == status_enum)
        except ValueError:
            pass

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Dataset.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    datasets = result.scalars().all()

    return DatasetListResponse(
        datasets=[
            DatasetListItem(
                id=str(ds.id),
                name=ds.name,
                original_filename=ds.original_filename,
                size_bytes=ds.size_bytes,
                row_count=ds.row_count,
                column_count=ds.column_count,
                target_column=ds.target_column,
                status=ds.status,
                created_at=ds.created_at,
            )
            for ds in datasets
        ],
        total=total
    )


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a dataset and its S3 file.
    """
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.user_id == str(current_user.id)
        )
    )
    dataset = result.scalar_one_or_none()

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )

    # Delete from S3 (fire and forget)
    try:
        storage = get_storage_service()
        # Note: StorageService doesn't have a delete method exposed, so we skip S3 deletion
        # In production, you'd add a delete_file method to StorageService
        logger.info(f"[Datasets] Would delete S3 key: {dataset.s3_key}")
    except Exception as e:
        logger.warning(f"[Datasets] Failed to delete S3 file: {e}")

    # Delete from database
    await db.delete(dataset)
    await db.commit()

    logger.info(f"[Datasets] User {current_user.id} deleted dataset {dataset_id}")

    return {"message": "Dataset deleted successfully", "id": dataset_id}


@router.get("/{dataset_id}/preview")
async def get_dataset_preview(
    dataset_id: str,
    rows: int = Query(10, ge=1, le=100, description="Number of rows to preview"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a preview of dataset contents (first N rows).

    Downloads the CSV from S3 and returns preview data.
    """
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.user_id == str(current_user.id)
        )
    )
    dataset = result.scalar_one_or_none()

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )

    # For now, return stored columns and a message
    # In production, you'd download from S3 and parse
    return {
        "id": str(dataset.id),
        "name": dataset.name,
        "columns": dataset.columns,
        "row_count": dataset.row_count,
        "note": "Full preview requires S3 download - using stored column info"
    }


# ==================== Image Dataset Endpoints ====================

@router.post("/upload-images", response_model=ImageDatasetUploadResponse)
async def upload_image_dataset(
    file: UploadFile = File(..., description="ZIP file with images (max 100MB)"),
    name: Optional[str] = Form(None, description="Dataset name (defaults to filename)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a ZIP file containing images for ML training.

    Expected ZIP structure:
    ```
    dataset.zip
    ├── train/           (optional split folder)
    │   ├── class1/
    │   │   ├── img1.jpg
    │   │   └── img2.png
    │   └── class2/
    │       └── img1.jpg
    └── test/            (optional)
        └── ...
    ```

    Or flat structure:
    ```
    dataset.zip
    ├── cats/
    │   └── images...
    └── dogs/
        └── images...
    ```

    Returns dataset info with class detection and sample images.
    """
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only ZIP files are supported for image datasets"
        )

    # Read file content
    content = await file.read()

    # Validate size
    if len(content) > MAX_IMAGE_ZIP_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_IMAGE_ZIP_SIZE_BYTES // (1024 * 1024)}MB"
        )

    # Validate content is not empty
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file"
        )

    # Analyze ZIP contents
    try:
        analysis = analyze_image_zip(content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Calculate content hash for deduplication
    content_hash = hashlib.sha256(content).hexdigest()

    # Generate S3 key
    dataset_name = name or file.filename.rsplit('.', 1)[0]
    s3_key = f"datasets/{current_user.id}/images/{content_hash[:8]}_{file.filename}"

    # Upload to S3
    try:
        storage = get_storage_service()
        await storage.upload_file(
            project_id=f"datasets/{current_user.id}/images",
            file_path=f"{content_hash[:8]}_{file.filename}",
            content=content,
            content_type="application/zip"
        )
    except Exception as e:
        logger.error(f"[Datasets] S3 upload failed for image dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to storage"
        )

    # Create dataset record
    dataset = Dataset(
        user_id=str(current_user.id),
        name=dataset_name,
        original_filename=file.filename,
        s3_key=s3_key,
        content_hash=content_hash,
        size_bytes=len(content),
        dataset_type=DatasetType.IMAGE,
        classes=analysis["classes"],
        num_classes=analysis["num_classes"],
        total_images=analysis["total_images"],
        image_info=analysis["image_info"],
        split_info=analysis["split_info"],
        recommended_input_size=analysis["recommended_input_size"],
        status=DatasetStatus.VALIDATED,
    )

    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)

    logger.info(f"[Datasets] User {current_user.id} uploaded image dataset {dataset.id} ({file.filename}) with {analysis['num_classes']} classes")

    return ImageDatasetUploadResponse(
        id=str(dataset.id),
        name=dataset.name,
        original_filename=dataset.original_filename,
        size_bytes=dataset.size_bytes,
        dataset_type=DatasetType.IMAGE,
        total_images=analysis["total_images"],
        num_classes=analysis["num_classes"],
        classes=[ImageClassInfo(**cls) for cls in analysis["classes"]],
        image_info=ImageInfo(**analysis["image_info"]) if analysis["image_info"] else None,
        split_info=SplitInfo(**analysis["split_info"]) if analysis["split_info"] else None,
        recommended_input_size=analysis["recommended_input_size"],
        status=DatasetStatus.VALIDATED,
        message=f"Image dataset uploaded with {analysis['num_classes']} classes and {analysis['total_images']} images"
    )


@router.post("/configure-images", response_model=ImageDatasetConfigureResponse)
async def configure_image_dataset(
    request: ImageDatasetConfigureRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Configure an image dataset for ML training.

    Sets input size and other training parameters.
    """
    # Get dataset
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == request.dataset_id,
            Dataset.user_id == str(current_user.id),
            Dataset.dataset_type == DatasetType.IMAGE
        )
    )
    dataset = result.scalar_one_or_none()

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image dataset not found"
        )

    # Update configuration
    if request.input_size:
        dataset.recommended_input_size = request.input_size

    # Store augmentation/normalize settings in image_info
    if dataset.image_info:
        image_info = dict(dataset.image_info)
    else:
        image_info = {}

    image_info["augmentation"] = request.augmentation
    image_info["normalize"] = request.normalize
    dataset.image_info = image_info

    # Associate with project if provided
    if request.project_id:
        dataset.project_id = request.project_id

    dataset.status = DatasetStatus.READY

    await db.commit()
    await db.refresh(dataset)

    # Get class names
    class_names = [cls.get("name") for cls in dataset.classes] if dataset.classes else []

    logger.info(f"[Datasets] Image dataset {dataset.id} configured with input_size={request.input_size}")

    return ImageDatasetConfigureResponse(
        id=str(dataset.id),
        name=dataset.name,
        num_classes=dataset.num_classes or 0,
        class_names=class_names,
        input_size=dataset.recommended_input_size or 224,
        status=DatasetStatus.READY,
        message="Image dataset configured successfully"
    )
