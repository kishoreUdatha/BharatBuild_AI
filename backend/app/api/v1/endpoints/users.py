"""
Users Management API

Provides endpoints for listing, searching, and managing users with:
- Pagination (page, page_size)
- Search (by name, email, organization)
- Sorting (by any field, asc/desc)
- Filtering (by role, status)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, asc, desc
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal
from datetime import datetime, timedelta
from uuid import UUID

from app.core.database import get_db
from app.models.user import User, UserRole
from app.modules.auth.dependencies import get_current_user, require_admin

router = APIRouter()


# ==================== Schemas ====================

class UserListItem(BaseModel):
    """User item in list response"""
    id: str
    email: str
    full_name: Optional[str] = None
    username: Optional[str] = None
    role: str
    organization: Optional[str] = None
    is_active: bool
    is_verified: bool
    avatar_url: Optional[str] = None
    oauth_provider: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedUsersResponse(BaseModel):
    """Paginated users response"""
    items: List[UserListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class UserUpdateRequest(BaseModel):
    """Request to update a user"""
    full_name: Optional[str] = None
    role: Optional[str] = None
    organization: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserStatsResponse(BaseModel):
    """User statistics response"""
    total_users: int
    active_users: int
    verified_users: int
    users_by_role: dict
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int


# ==================== Endpoints ====================

@router.get("/", response_model=PaginatedUsersResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name, email, or organization"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users with pagination, search, and sorting.

    Supports:
    - Pagination: page, page_size
    - Search: searches in full_name, email, organization
    - Filtering: by role, is_active, is_verified
    - Sorting: by any field (created_at, email, full_name, role, etc.)
    """
    # Build base query
    query = select(User)
    count_query = select(func.count(User.id))

    # Apply search filter
    if search:
        search_filter = or_(
            User.full_name.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
            User.organization.ilike(f"%{search}%"),
            User.username.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Apply role filter
    if role:
        try:
            role_enum = UserRole(role)
            query = query.where(User.role == role_enum)
            count_query = count_query.where(User.role == role_enum)
        except ValueError:
            pass  # Ignore invalid role

    # Apply active filter
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)

    # Apply verified filter
    if is_verified is not None:
        query = query.where(User.is_verified == is_verified)
        count_query = count_query.where(User.is_verified == is_verified)

    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply sorting
    sort_column = getattr(User, sort_by, User.created_at)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    users = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedUsersResponse(
        items=[
            UserListItem(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                username=user.username,
                role=user.role.value if user.role else "student",
                organization=user.organization,
                is_active=user.is_active,
                is_verified=user.is_verified,
                avatar_url=user.avatar_url,
                oauth_provider=user.oauth_provider,
                created_at=user.created_at,
                last_login=user.last_login
            )
            for user in users
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user statistics."""
    from datetime import timedelta

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    # Total users
    total_result = await db.execute(select(func.count(User.id)))
    total_users = total_result.scalar() or 0

    # Active users
    active_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = active_result.scalar() or 0

    # Verified users
    verified_result = await db.execute(
        select(func.count(User.id)).where(User.is_verified == True)
    )
    verified_users = verified_result.scalar() or 0

    # Users by role
    role_counts = {}
    for role in UserRole:
        role_result = await db.execute(
            select(func.count(User.id)).where(User.role == role)
        )
        role_counts[role.value] = role_result.scalar() or 0

    # New users today
    today_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )
    new_users_today = today_result.scalar() or 0

    # New users this week
    week_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= week_start)
    )
    new_users_this_week = week_result.scalar() or 0

    # New users this month
    month_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= month_start)
    )
    new_users_this_month = month_result.scalar() or 0

    return UserStatsResponse(
        total_users=total_users,
        active_users=active_users,
        verified_users=verified_users,
        users_by_role=role_counts,
        new_users_today=new_users_today,
        new_users_this_week=new_users_this_week,
        new_users_this_month=new_users_this_month
    )


@router.get("/{user_id}", response_model=UserListItem)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific user by ID."""
    try:
        result = await db.execute(
            select(User).where(User.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    return UserListItem(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        username=user.username,
        role=user.role.value if user.role else "student",
        organization=user.organization,
        is_active=user.is_active,
        is_verified=user.is_verified,
        avatar_url=user.avatar_url,
        oauth_provider=user.oauth_provider,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.patch("/{user_id}", response_model=UserListItem)
async def update_user(
    user_id: str,
    user_data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a user.
    Regular users can only update their own profile.
    Admins can update any user.
    """
    try:
        result = await db.execute(
            select(User).where(User.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    # Check permission: user can only update themselves unless admin
    if str(current_user.id) != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )

    # Update fields
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.organization is not None:
        user.organization = user_data.organization

    # Only admins can update these fields
    if current_user.role == UserRole.ADMIN:
        if user_data.role is not None:
            try:
                user.role = UserRole(user_data.role)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid role"
                )
        if user_data.is_active is not None:
            user.is_active = user_data.is_active
        if user_data.is_verified is not None:
            user.is_verified = user_data.is_verified

    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    return UserListItem(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        username=user.username,
        role=user.role.value if user.role else "student",
        organization=user.organization,
        is_active=user.is_active,
        is_verified=user.is_verified,
        avatar_url=user.avatar_url,
        oauth_provider=user.oauth_provider,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a user (admin only).
    Soft deletes by setting is_active to False.
    """
    # Only admins can delete users
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        result = await db.execute(
            select(User).where(User.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    # Prevent self-deletion
    if str(current_user.id) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    # Soft delete
    user.is_active = False
    user.updated_at = datetime.utcnow()
    await db.commit()

    return {"success": True, "message": "User deactivated"}


@router.get("/roles/list")
async def list_roles():
    """Get list of available user roles."""
    return {
        "roles": [
            {"value": role.value, "label": role.value.replace("_", " ").title()}
            for role in UserRole
        ]
    }


@router.post("/seed-sample-data")
async def seed_sample_employees(
    count: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate sample employee data for testing pagination.
    Creates specified number of sample users.
    """
    import random
    from app.core.security import get_password_hash

    first_names = [
        "Rahul", "Priya", "Amit", "Sneha", "Vikram", "Ananya", "Rohan", "Kavya",
        "Arjun", "Meera", "Karthik", "Divya", "Suresh", "Anjali", "Vivek", "Swati",
        "Aditya", "Neha", "Rajesh", "Pooja", "Sameer", "Deepika", "Manish", "Sonali",
        "Gaurav", "Priyanka", "Akshay", "Tanvi", "Harsh", "Riya", "Kunal", "Shreya",
        "Varun", "Megha", "Siddharth", "Nisha", "Aakash", "Ishita", "Rohit", "Kavitha"
    ]

    last_names = [
        "Sharma", "Patel", "Kumar", "Reddy", "Singh", "Gupta", "Mehta", "Nair",
        "Verma", "Shah", "Rajan", "Krishnan", "Babu", "Menon", "Jain", "Bose",
        "Das", "Tiwari", "Yadav", "Sinha", "Patil", "Iyer", "Joshi", "Saxena",
        "Malhotra", "Kapoor", "Thakur", "Desai", "Mishra", "Agarwal", "Khanna", "Rao"
    ]

    organizations = [
        "TechCorp India", "Infosys", "Wipro", "TCS", "HCL Tech", "Tech Mahindra",
        "Cognizant", "Accenture", "Capgemini", "L&T Infotech", "Mindtree", "Mphasis",
        "IIT Delhi", "IIT Bombay", "NIT Trichy", "BITS Pilani", "VIT Vellore",
        "InnovateTech", "HealthAI", "EduSmart", "FinFlow", "AgriNext", "RetailPro"
    ]

    roles = list(UserRole)
    created_users = []
    default_password = get_password_hash("Password123!")

    for i in range(count):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        full_name = f"{first_name} {last_name}"
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}@example.com"

        # Check if email exists
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            continue

        user = User(
            email=email,
            full_name=full_name,
            username=f"{first_name.lower()}{random.randint(100, 9999)}",
            hashed_password=default_password,
            role=random.choice(roles),
            organization=random.choice(organizations),
            is_active=random.random() > 0.1,  # 90% active
            is_verified=random.random() > 0.3,  # 70% verified
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 365)),
            last_login=datetime.utcnow() - timedelta(hours=random.randint(1, 720)) if random.random() > 0.3 else None
        )
        db.add(user)
        created_users.append(full_name)

    await db.commit()

    return {
        "success": True,
        "message": f"Created {len(created_users)} sample employees",
        "count": len(created_users)
    }


# ==================== Email Endpoints ====================

class SendEmailRequest(BaseModel):
    """Request model for sending emails"""
    subject: str
    message: str
    user_ids: Optional[List[str]] = None  # Specific user IDs
    role: Optional[str] = None  # Send to all users with this role (e.g., "student")
    include_login_link: bool = True


class SendEmailResponse(BaseModel):
    """Response model for email sending"""
    success: bool
    message: str
    success_count: int
    failed_count: int
    failed_emails: List[str] = []


@router.post("/send-email", response_model=SendEmailResponse)
async def send_email_to_users(
    request: SendEmailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send email to students/users.

    Admin only endpoint. Can send to:
    - Specific users by IDs
    - All users with a specific role (e.g., 'student')

    Requires SENDGRID_API_KEY or SMTP configuration.
    """
    from app.services.email_service import email_service

    # Check admin permission
    if not current_user.is_superuser and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can send bulk emails"
        )

    # Check if email is configured
    if not email_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service not configured. Set SENDGRID_API_KEY or SMTP credentials."
        )

    # Build query based on request
    query = select(User).where(User.is_active == True)

    if request.user_ids:
        # Send to specific users
        query = query.where(User.id.in_(request.user_ids))
    elif request.role:
        # Send to all users with specific role
        try:
            role = UserRole(request.role)
            query = query.where(User.role == role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {request.role}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify either user_ids or role"
        )

    # Get users
    result = await db.execute(query)
    users = result.scalars().all()

    if not users:
        return SendEmailResponse(
            success=True,
            message="No users found matching criteria",
            success_count=0,
            failed_count=0,
            failed_emails=[]
        )

    # Prepare recipient list
    recipients = [
        {"email": user.email, "name": user.full_name or user.username or "Student"}
        for user in users
    ]

    # Send emails
    result = await email_service.send_to_students(
        students=recipients,
        subject=request.subject,
        message=request.message,
        include_login_link=request.include_login_link
    )

    return SendEmailResponse(
        success=result["failed_count"] == 0,
        message=f"Sent {result['success_count']} emails, {result['failed_count']} failed",
        success_count=result["success_count"],
        failed_count=result["failed_count"],
        failed_emails=result["failed_emails"]
    )
