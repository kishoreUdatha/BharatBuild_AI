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
        "value": True,
        "description": "Enable email notifications for new users",
        "category": "notifications"
    },
    "notifications.admin_email": {
        "value": "",
        "description": "Admin email to receive new user alerts",
        "category": "notifications"
    },
    "notifications.whatsapp_enabled": {
        "value": False,
        "description": "Enable WhatsApp notifications",
        "category": "notifications"
    },
    "notifications.admin_whatsapp": {
        "value": "",
        "description": "Admin WhatsApp number (with country code, e.g., +919876543210)",
        "category": "notifications"
    },
    "notifications.whatsapp_provider": {
        "value": "exotel",
        "description": "WhatsApp provider: exotel, twilio, or meta",
        "category": "notifications"
    },
    "notifications.exotel_sid": {
        "value": "",
        "description": "Exotel Account SID",
        "category": "notifications"
    },
    "notifications.exotel_token": {
        "value": "",
        "description": "Exotel Auth Token",
        "category": "notifications"
    },
    "notifications.exotel_whatsapp_number": {
        "value": "",
        "description": "Exotel WhatsApp Business Number",
        "category": "notifications"
    },
    "notifications.twilio_sid": {
        "value": "",
        "description": "Twilio Account SID",
        "category": "notifications"
    },
    "notifications.twilio_token": {
        "value": "",
        "description": "Twilio Auth Token",
        "category": "notifications"
    },
    "notifications.twilio_whatsapp_number": {
        "value": "",
        "description": "Twilio WhatsApp Number",
        "category": "notifications"
    },
    "notifications.slack_webhook": {
        "value": "",
        "description": "Slack webhook URL for alerts",
        "category": "notifications"
    },
    "notifications.discord_webhook": {
        "value": "",
        "description": "Discord webhook URL for alerts",
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


# ============== NOTIFICATION SETTINGS ==============
# NOTE: These routes MUST be defined before /{key} routes to prevent conflict

@router.get("/notifications/config")
async def get_notification_settings(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all notification settings in a structured format"""
    await ensure_default_settings(db)

    result = await db.execute(
        select(SystemSetting).where(SystemSetting.category == "notifications")
    )
    settings_list = result.scalars().all()

    # Build structured response
    config = {
        "email": {"enabled": False, "admin_email": ""},
        "whatsapp": {
            "enabled": False,
            "admin_number": "",
            "provider": "exotel",
            "exotel": {"sid": "", "token": "", "whatsapp_number": ""},
            "twilio": {"sid": "", "token": "", "whatsapp_number": ""}
        },
        "webhooks": {"slack": "", "discord": ""}
    }

    for setting in settings_list:
        key = setting.key.replace("notifications.", "")
        value = setting.value

        if key == "email_enabled":
            config["email"]["enabled"] = bool(value)
        elif key == "admin_email":
            config["email"]["admin_email"] = value or ""
        elif key == "whatsapp_enabled":
            config["whatsapp"]["enabled"] = bool(value)
        elif key == "admin_whatsapp":
            config["whatsapp"]["admin_number"] = value or ""
        elif key == "whatsapp_provider":
            config["whatsapp"]["provider"] = value or "exotel"
        elif key == "exotel_sid":
            config["whatsapp"]["exotel"]["sid"] = value or ""
        elif key == "exotel_token":
            config["whatsapp"]["exotel"]["token"] = "********" if value else ""
        elif key == "exotel_whatsapp_number":
            config["whatsapp"]["exotel"]["whatsapp_number"] = value or ""
        elif key == "twilio_sid":
            config["whatsapp"]["twilio"]["sid"] = value or ""
        elif key == "twilio_token":
            config["whatsapp"]["twilio"]["token"] = "********" if value else ""
        elif key == "twilio_whatsapp_number":
            config["whatsapp"]["twilio"]["whatsapp_number"] = value or ""
        elif key == "slack_webhook":
            config["webhooks"]["slack"] = value or ""
        elif key == "discord_webhook":
            config["webhooks"]["discord"] = value or ""

    return {"notifications": config}


@router.patch("/notifications/config")
async def update_notification_settings(
    config: Dict[str, Any],
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Update notification settings"""
    await ensure_default_settings(db)
    changes = {}

    mapping = {
        "email.enabled": "notifications.email_enabled",
        "email.admin_email": "notifications.admin_email",
        "whatsapp.enabled": "notifications.whatsapp_enabled",
        "whatsapp.admin_number": "notifications.admin_whatsapp",
        "whatsapp.provider": "notifications.whatsapp_provider",
        "whatsapp.exotel.sid": "notifications.exotel_sid",
        "whatsapp.exotel.token": "notifications.exotel_token",
        "whatsapp.exotel.whatsapp_number": "notifications.exotel_whatsapp_number",
        "whatsapp.twilio.sid": "notifications.twilio_sid",
        "whatsapp.twilio.token": "notifications.twilio_token",
        "whatsapp.twilio.whatsapp_number": "notifications.twilio_whatsapp_number",
        "webhooks.slack": "notifications.slack_webhook",
        "webhooks.discord": "notifications.discord_webhook",
    }

    def get_nested(d: dict, path: str):
        keys = path.split(".")
        for key in keys:
            if isinstance(d, dict) and key in d:
                d = d[key]
            else:
                return None
        return d

    for path, db_key in mapping.items():
        new_value = get_nested(config, path)
        if new_value is None or new_value == "********":
            continue
        setting = await db.scalar(select(SystemSetting).where(SystemSetting.key == db_key))
        if setting:
            if setting.value != new_value:
                changes[db_key] = {"old": setting.value, "new": new_value}
                setting.value = new_value
                setting.updated_by = current_admin.id
                setting.updated_at = datetime.utcnow()
        else:
            # Create new setting if it doesn't exist
            new_setting = SystemSetting(
                key=db_key,
                value=new_value,
                description=DEFAULT_SETTINGS.get(db_key, {}).get("description", f"Setting: {db_key}"),
                category="notifications",
                updated_by=current_admin.id
            )
            db.add(new_setting)
            changes[db_key] = {"old": None, "new": new_value}

    await db.commit()

    if changes:
        safe_changes = {k: ({"old": "***", "new": "***"} if "token" in k.lower() else v) for k, v in changes.items()}
        log = AuditLog(
            admin_id=str(current_admin.id),
            action="notification_settings_updated",
            target_type="settings",
            details={"changes": safe_changes},
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )
        db.add(log)
        await db.commit()

    return {"message": "Notification settings updated", "changes_count": len(changes)}


@router.post("/notifications/test")
async def test_notification(
    channel: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Send a test notification"""
    from app.services.email_service import email_service
    from app.services import email_templates
    await ensure_default_settings(db)

    settings_dict = {}
    result = await db.execute(select(SystemSetting).where(SystemSetting.category == "notifications"))
    for s in result.scalars().all():
        settings_dict[s.key.replace("notifications.", "")] = s.value

    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    test_message = f"Test notification from BharatBuild AI\nRequested by: {current_admin.email}\nTime: {timestamp}"

    try:
        if channel == "email":
            admin_email = settings_dict.get("admin_email")
            if not admin_email:
                raise HTTPException(status_code=400, detail="Admin email not configured")
            html_content = email_templates.test_notification_email(admin_email, timestamp)
            await email_service.send_email(admin_email, "✅ BharatBuild AI - Test Notification", html_content, test_message)
            return {"success": True, "message": f"Test email sent to {admin_email}"}

        elif channel == "whatsapp":
            admin_whatsapp = settings_dict.get("admin_whatsapp")
            if not admin_whatsapp:
                raise HTTPException(status_code=400, detail="Admin WhatsApp not configured")
            success = await email_service.send_whatsapp_notification_with_settings(admin_whatsapp, test_message, settings_dict)
            if success:
                return {"success": True, "message": f"Test WhatsApp sent to {admin_whatsapp}"}
            raise HTTPException(status_code=500, detail="WhatsApp failed - check credentials")

        elif channel == "slack":
            webhook = settings_dict.get("slack_webhook")
            if not webhook:
                raise HTTPException(status_code=400, detail="Slack webhook not configured")
            import httpx
            async with httpx.AsyncClient() as client:
                r = await client.post(webhook, json={"text": test_message})
                if r.status_code == 200:
                    return {"success": True, "message": "Slack notification sent"}
                raise HTTPException(status_code=500, detail=f"Slack failed: {r.text}")

        elif channel == "discord":
            webhook = settings_dict.get("discord_webhook")
            if not webhook:
                raise HTTPException(status_code=400, detail="Discord webhook not configured")
            import httpx
            async with httpx.AsyncClient() as client:
                r = await client.post(webhook, json={"content": test_message})
                if r.status_code in [200, 204]:
                    return {"success": True, "message": "Discord notification sent"}
                raise HTTPException(status_code=500, detail=f"Discord failed: {r.text}")

        else:
            raise HTTPException(status_code=400, detail=f"Unknown channel: {channel}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


# ============== SETTING CRUD (keep /{key} routes last) ==============

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
