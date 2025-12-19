"""
Admin System Settings endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Dict, Any

from app.core.database import get_db
from app.models import User, SystemSetting, AuditLog
from app.modules.auth.dependencies import get_current_admin
from app.schemas.admin import (
    SystemSettingResponse, SystemSettingUpdate,
    FeatureFlagsResponse, FeatureFlagsUpdate
)

router = APIRouter()

# Default settings that should exist
DEFAULT_SETTINGS = {
    "general.site_name": {
        "value": "BharatBuild AI",
        "description": "The name of the platform",
        "category": "general"
    },
    "general.maintenance_mode": {
        "value": False,
        "description": "Enable maintenance mode",
        "category": "general"
    },
    "general.signup_enabled": {
        "value": True,
        "description": "Allow new user signups",
        "category": "general"
    },
    "limits.max_projects_per_user": {
        "value": 10,
        "description": "Default maximum projects per user",
        "category": "limits"
    },
    "limits.max_file_size_mb": {
        "value": 10,
        "description": "Maximum file upload size in MB",
        "category": "limits"
    },
    "limits.default_token_limit": {
        "value": 50000,
        "description": "Default token limit for new users",
        "category": "limits"
    },
    "features.agentic_mode": {
        "value": True,
        "description": "Enable agentic mode for projects",
        "category": "features"
    },
    "features.document_generation": {
        "value": True,
        "description": "Enable document generation",
        "category": "features"
    },
    "features.code_execution": {
        "value": True,
        "description": "Enable code execution in sandboxes",
        "category": "features"
    },
    "features.api_access": {
        "value": True,
        "description": "Enable API key creation",
        "category": "features"
    },
    "notifications.email_enabled": {
        "value": False,
        "description": "Enable email notifications",
        "category": "notifications"
    },
    "notifications.slack_webhook": {
        "value": "",
        "description": "Slack webhook URL for alerts",
        "category": "notifications"
    }
}


async def ensure_default_settings(db: AsyncSession):
    """Ensure default settings exist in database"""
    for key, config in DEFAULT_SETTINGS.items():
        existing = await db.scalar(select(SystemSetting).where(SystemSetting.key == key))
        if not existing:
            setting = SystemSetting(
                key=key,
                value=config["value"],
                description=config["description"],
                category=config["category"]
            )
            db.add(setting)
    await db.commit()


@router.get("")
async def list_settings(
    category: str = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List all system settings"""
    await ensure_default_settings(db)

    query = select(SystemSetting)
    if category:
        query = query.where(SystemSetting.category == category)

    query = query.order_by(SystemSetting.category, SystemSetting.key)
    result = await db.execute(query)
    settings = result.scalars().all()

    # Group by category
    grouped = {}
    for setting in settings:
        cat = setting.category or "general"
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append({
            "id": str(setting.id),
            "key": setting.key,
            "value": setting.value,
            "description": setting.description,
            "updated_at": setting.updated_at.isoformat() if setting.updated_at else None
        })

    return {"settings": grouped}


@router.get("/categories")
async def get_categories(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get list of setting categories"""
    result = await db.execute(
        select(SystemSetting.category).distinct().order_by(SystemSetting.category)
    )
    categories = [row[0] for row in result.all() if row[0]]

    return {"categories": categories or ["general", "limits", "features", "notifications"]}


@router.get("/feature-flags", response_model=FeatureFlagsResponse)
async def get_feature_flags(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all feature flags"""
    await ensure_default_settings(db)

    result = await db.execute(
        select(SystemSetting).where(SystemSetting.category == "features")
    )
    settings = result.scalars().all()

    flags = {}
    last_updated = None

    for setting in settings:
        # Extract feature name from key (e.g., "features.agentic_mode" -> "agentic_mode")
        feature_name = setting.key.replace("features.", "")
        flags[feature_name] = bool(setting.value)
        if setting.updated_at and (not last_updated or setting.updated_at > last_updated):
            last_updated = setting.updated_at

    return FeatureFlagsResponse(
        flags=flags,
        updated_at=last_updated or datetime.utcnow()
    )


@router.patch("/feature-flags")
async def update_feature_flags(
    flags_data: FeatureFlagsUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Update feature flags"""
    changes = {}

    for feature, enabled in flags_data.flags.items():
        key = f"features.{feature}"
        setting = await db.scalar(select(SystemSetting).where(SystemSetting.key == key))

        if setting:
            if setting.value != enabled:
                changes[feature] = {"old": setting.value, "new": enabled}
                setting.value = enabled
                setting.updated_by = current_admin.id
                setting.updated_at = datetime.utcnow()
        else:
            # Create new feature flag
            new_setting = SystemSetting(
                key=key,
                value=enabled,
                description=f"Feature flag: {feature}",
                category="features",
                updated_by=current_admin.id
            )
            db.add(new_setting)
            changes[feature] = {"old": None, "new": enabled}

    await db.commit()

    if changes:
        # Log action
        log = AuditLog(
            admin_id=str(current_admin.id),
            action="feature_flags_updated",
            target_type="settings",
            target_id=None,
            details={"changes": changes},
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )
        db.add(log)
        await db.commit()

    return {"message": "Feature flags updated successfully", "changes": changes}


@router.get("/{key}", response_model=SystemSettingResponse)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get a specific setting by key"""
    setting = await db.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    return SystemSettingResponse(
        id=str(setting.id),
        key=setting.key,
        value=setting.value,
        description=setting.description,
        category=setting.category,
        updated_at=setting.updated_at
    )


@router.patch("/{key}")
async def update_setting(
    key: str,
    update_data: SystemSettingUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Update a system setting"""
    setting = await db.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    old_value = setting.value
    setting.value = update_data.value

    if update_data.description is not None:
        setting.description = update_data.description

    setting.updated_by = current_admin.id
    setting.updated_at = datetime.utcnow()

    await db.commit()

    # Log action
    log = AuditLog(
        admin_id=str(current_admin.id),
        action="setting_updated",
        target_type="setting",
        target_id=str(setting.id),
        details={"key": key, "old_value": old_value, "new_value": update_data.value},
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(log)
    await db.commit()

    return {"message": f"Setting '{key}' updated successfully"}


@router.post("")
async def create_setting(
    key: str,
    value: Any,
    description: str = None,
    category: str = "general",
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Create a new system setting"""
    existing = await db.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if existing:
        raise HTTPException(status_code=400, detail="Setting with this key already exists")

    setting = SystemSetting(
        key=key,
        value=value,
        description=description,
        category=category,
        updated_by=current_admin.id
    )
    db.add(setting)
    await db.commit()

    # Log action
    log = AuditLog(
        admin_id=str(current_admin.id),
        action="setting_created",
        target_type="setting",
        target_id=str(setting.id),
        details={"key": key, "value": value},
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(log)
    await db.commit()

    return {"message": f"Setting '{key}' created successfully", "id": str(setting.id)}


@router.delete("/{key}")
async def delete_setting(
    key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Delete a system setting"""
    setting = await db.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    # Don't allow deleting default settings
    if key in DEFAULT_SETTINGS:
        raise HTTPException(status_code=400, detail="Cannot delete default setting")

    await db.delete(setting)
    await db.commit()

    # Log action
    log = AuditLog(
        admin_id=str(current_admin.id),
        action="setting_deleted",
        target_type="setting",
        target_id=str(setting.id),
        details={"key": key},
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(log)
    await db.commit()

    return {"message": f"Setting '{key}' deleted successfully"}
