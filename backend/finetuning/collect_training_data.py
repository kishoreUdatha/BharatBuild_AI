#!/usr/bin/env python3
"""
Comprehensive Training Data Collection
Combines database extraction + synthetic generation + public datasets
"""
import os
import sys
import json
import asyncio
import random
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class DataCollectionConfig:
    """Configuration for data collection"""
    output_dir: str = "./data/collected"

    # Database extraction
    extract_from_db: bool = True
    db_limit: Optional[int] = None

    # Synthetic generation
    generate_synthetic: bool = True
    synthetic_count: int = 500

    # Public datasets
    use_public_datasets: bool = True

    # Target tech stack
    tech_stack: List[str] = None

    def __post_init__(self):
        if self.tech_stack is None:
            self.tech_stack = [
                "react", "nextjs", "typescript", "tailwind",
                "fastapi", "python", "sqlalchemy", "pydantic"
            ]


class SyntheticDataGenerator:
    """Generate high-quality synthetic training data"""

    # React component templates
    REACT_COMPONENTS = [
        {
            "type": "button",
            "instruction": "Create a React {variant} button component with {features} using TypeScript and Tailwind CSS",
            "variants": ["primary", "secondary", "outline", "ghost", "destructive"],
            "features_list": [
                "loading state and disabled state",
                "icon support and ripple effect",
                "size variants (sm, md, lg)",
                "onClick handler and accessibility",
            ],
        },
        {
            "type": "form",
            "instruction": "Create a React {form_type} form with {validation} validation using TypeScript and Tailwind CSS",
            "form_types": ["login", "registration", "contact", "checkout", "profile edit", "password reset"],
            "validations": ["Zod", "Yup", "react-hook-form", "custom"],
        },
        {
            "type": "modal",
            "instruction": "Create a React modal/dialog component with {features} using TypeScript and Tailwind CSS",
            "features_list": [
                "backdrop click to close and escape key support",
                "animation transitions and focus trap",
                "custom header, body, and footer slots",
                "confirmation dialog variant",
            ],
        },
        {
            "type": "table",
            "instruction": "Create a React data table component with {features} using TypeScript and Tailwind CSS",
            "features_list": [
                "sorting and pagination",
                "row selection and bulk actions",
                "column filtering and search",
                "responsive design with horizontal scroll",
                "expandable rows and nested data",
            ],
        },
        {
            "type": "card",
            "instruction": "Create a React {card_type} card component using TypeScript and Tailwind CSS",
            "card_types": ["product", "user profile", "pricing", "blog post", "dashboard stat", "notification"],
        },
        {
            "type": "navigation",
            "instruction": "Create a React {nav_type} navigation component using TypeScript and Tailwind CSS",
            "nav_types": ["sidebar", "navbar", "breadcrumb", "tabs", "pagination", "mobile bottom nav"],
        },
        {
            "type": "input",
            "instruction": "Create a React {input_type} input component with validation using TypeScript and Tailwind CSS",
            "input_types": ["text", "email", "password with visibility toggle", "search with autocomplete",
                          "date picker", "file upload with drag-drop", "rich text editor", "OTP input"],
        },
        {
            "type": "list",
            "instruction": "Create a React {list_type} list component using TypeScript and Tailwind CSS",
            "list_types": ["todo list with CRUD", "sortable drag-drop list", "virtualized infinite scroll list",
                         "filterable search list", "grouped/categorized list"],
        },
    ]

    # FastAPI endpoint templates
    FASTAPI_ENDPOINTS = [
        {
            "resource": "users",
            "instruction": "Create FastAPI CRUD endpoints for User management with {features}",
            "features_list": [
                "JWT authentication and role-based access",
                "email verification and password reset",
                "profile update and avatar upload",
                "pagination and filtering",
            ],
        },
        {
            "resource": "products",
            "instruction": "Create FastAPI endpoints for Product catalog with {features}",
            "features_list": [
                "search with filters (price, category, rating)",
                "image upload to S3",
                "inventory management",
                "reviews and ratings",
            ],
        },
        {
            "resource": "orders",
            "instruction": "Create FastAPI endpoints for Order management with {features}",
            "features_list": [
                "cart management and checkout",
                "payment integration (Razorpay/Stripe)",
                "order status tracking",
                "invoice generation",
            ],
        },
        {
            "resource": "auth",
            "instruction": "Create FastAPI authentication endpoints with {features}",
            "features_list": [
                "JWT access and refresh tokens",
                "OAuth2 (Google, GitHub) integration",
                "two-factor authentication",
                "session management",
            ],
        },
        {
            "resource": "files",
            "instruction": "Create FastAPI file management endpoints with {features}",
            "features_list": [
                "multipart upload to S3/MinIO",
                "presigned URLs for secure access",
                "image resize and optimization",
                "chunked upload for large files",
            ],
        },
        {
            "resource": "notifications",
            "instruction": "Create FastAPI notification endpoints with {features}",
            "features_list": [
                "real-time WebSocket notifications",
                "email and SMS integration",
                "push notifications",
                "notification preferences",
            ],
        },
    ]

    # Database model templates
    SQLALCHEMY_MODELS = [
        "User with profile, roles, and OAuth connections",
        "Product with categories, variants, and inventory",
        "Order with items, shipping, and payment status",
        "Blog Post with tags, comments, and likes",
        "Project with files, collaborators, and permissions",
        "Subscription with plans, billing, and usage tracking",
        "Notification with read status and preferences",
        "AuditLog for tracking all entity changes",
    ]

    # Pydantic schema templates
    PYDANTIC_SCHEMAS = [
        "User schemas (Create, Update, Response, List) with validation",
        "Product schemas with nested category and variant schemas",
        "Order schemas with computed totals and status enum",
        "Pagination schema with generic type support",
        "API response wrapper with error handling",
        "File upload schema with size and type validation",
        "Settings schema with environment-specific defaults",
    ]

    # Full-stack features
    FULLSTACK_FEATURES = [
        {
            "feature": "authentication",
            "instruction": "Implement complete authentication system with {specifics}",
            "specifics": [
                "JWT tokens, refresh flow, and secure httpOnly cookies",
                "OAuth2 social login (Google, GitHub)",
                "email verification and password reset flow",
                "role-based access control (RBAC)",
            ],
        },
        {
            "feature": "dashboard",
            "instruction": "Create an admin dashboard with {components}",
            "components": [
                "analytics charts (line, bar, pie) using Recharts",
                "data tables with sorting, filtering, and export",
                "user management with role assignment",
                "system settings and configuration",
            ],
        },
        {
            "feature": "e-commerce",
            "instruction": "Implement e-commerce functionality with {features}",
            "features": [
                "product catalog with search and filters",
                "shopping cart with local storage persistence",
                "checkout flow with address and payment",
                "order history and tracking",
            ],
        },
        {
            "feature": "real-time",
            "instruction": "Add real-time functionality using {technologies}",
            "technologies": [
                "WebSocket for live notifications",
                "Server-Sent Events for activity feed",
                "Socket.io for chat application",
                "Pusher/Ably for scalable real-time",
            ],
        },
    ]

    def __init__(self, config: DataCollectionConfig):
        self.config = config
        self.samples = []

    def generate_react_samples(self) -> List[Dict]:
        """Generate React component training samples"""
        samples = []

        for component in self.REACT_COMPONENTS:
            # Generate variations
            if "variants" in component:
                for variant in component["variants"]:
                    for features in component.get("features_list", [""]):
                        instruction = component["instruction"].format(
                            variant=variant,
                            features=features
                        )
                        samples.append(self._create_sample(instruction, "react_component"))

            elif "form_types" in component:
                for form_type in component["form_types"]:
                    for validation in component["validations"]:
                        instruction = component["instruction"].format(
                            form_type=form_type,
                            validation=validation
                        )
                        samples.append(self._create_sample(instruction, "react_form"))

            elif "card_types" in component:
                for card_type in component["card_types"]:
                    instruction = component["instruction"].format(card_type=card_type)
                    samples.append(self._create_sample(instruction, "react_component"))

            elif "nav_types" in component:
                for nav_type in component["nav_types"]:
                    instruction = component["instruction"].format(nav_type=nav_type)
                    samples.append(self._create_sample(instruction, "react_navigation"))

            elif "input_types" in component:
                for input_type in component["input_types"]:
                    instruction = component["instruction"].format(input_type=input_type)
                    samples.append(self._create_sample(instruction, "react_input"))

            elif "list_types" in component:
                for list_type in component["list_types"]:
                    instruction = component["instruction"].format(list_type=list_type)
                    samples.append(self._create_sample(instruction, "react_list"))

            elif "features_list" in component:
                for features in component["features_list"]:
                    instruction = component["instruction"].format(features=features)
                    samples.append(self._create_sample(instruction, "react_component"))

        return samples

    def generate_fastapi_samples(self) -> List[Dict]:
        """Generate FastAPI endpoint training samples"""
        samples = []

        for endpoint in self.FASTAPI_ENDPOINTS:
            for features in endpoint["features_list"]:
                instruction = endpoint["instruction"].format(features=features)
                samples.append(self._create_sample(instruction, "fastapi_endpoint"))

        return samples

    def generate_model_samples(self) -> List[Dict]:
        """Generate SQLAlchemy model training samples"""
        samples = []

        for model_desc in self.SQLALCHEMY_MODELS:
            instruction = f"Create a SQLAlchemy model for {model_desc}"
            samples.append(self._create_sample(instruction, "sqlalchemy_model"))

        return samples

    def generate_schema_samples(self) -> List[Dict]:
        """Generate Pydantic schema training samples"""
        samples = []

        for schema_desc in self.PYDANTIC_SCHEMAS:
            instruction = f"Create {schema_desc}"
            samples.append(self._create_sample(instruction, "pydantic_schema"))

        return samples

    def generate_fullstack_samples(self) -> List[Dict]:
        """Generate full-stack feature samples"""
        samples = []

        for feature in self.FULLSTACK_FEATURES:
            specifics_key = [k for k in feature.keys() if k not in ["feature", "instruction"]][0]
            for specific in feature[specifics_key]:
                instruction = feature["instruction"].format(**{specifics_key: specific})
                samples.append(self._create_sample(instruction, "fullstack_feature"))

        return samples

    def _create_sample(self, instruction: str, sample_type: str) -> Dict:
        """Create a training sample in ChatML format"""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert full-stack developer specializing in React, Next.js, TypeScript, Tailwind CSS, FastAPI, Python, and SQLAlchemy. Generate clean, production-ready code with proper error handling, TypeScript types, and best practices."
                },
                {
                    "role": "user",
                    "content": instruction
                },
                {
                    "role": "assistant",
                    "content": f"[TO_BE_GENERATED:{sample_type}]"  # Placeholder for actual generation
                }
            ],
            "metadata": {
                "type": sample_type,
                "instruction": instruction,
                "needs_generation": True
            }
        }

    def generate_all(self) -> List[Dict]:
        """Generate all synthetic samples"""
        all_samples = []

        logger.info("Generating React component samples...")
        all_samples.extend(self.generate_react_samples())

        logger.info("Generating FastAPI endpoint samples...")
        all_samples.extend(self.generate_fastapi_samples())

        logger.info("Generating SQLAlchemy model samples...")
        all_samples.extend(self.generate_model_samples())

        logger.info("Generating Pydantic schema samples...")
        all_samples.extend(self.generate_schema_samples())

        logger.info("Generating full-stack feature samples...")
        all_samples.extend(self.generate_fullstack_samples())

        logger.info(f"Generated {len(all_samples)} total instruction templates")

        return all_samples


class CodeTemplateLibrary:
    """Library of high-quality code templates for training"""

    REACT_BUTTON = '''```tsx
import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  className,
  disabled,
  ...props
}: ButtonProps) {
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';

  const variants = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-gray-500',
    outline: 'border-2 border-gray-300 text-gray-700 hover:bg-gray-50 focus:ring-gray-500',
    ghost: 'text-gray-700 hover:bg-gray-100 focus:ring-gray-500',
    destructive: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  return (
    <button
      className={cn(baseStyles, variants[variant], sizes[size], className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
      ) : leftIcon ? (
        <span className="mr-2">{leftIcon}</span>
      ) : null}
      {children}
      {rightIcon && <span className="ml-2">{rightIcon}</span>}
    </button>
  );
}
```'''

    REACT_LOGIN_FORM = '''```tsx
import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, Mail, Lock, Eye, EyeOff } from 'lucide-react';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  rememberMe: z.boolean().optional(),
});

type LoginFormData = z.infer<typeof loginSchema>;

interface LoginFormProps {
  onSubmit: (data: LoginFormData) => Promise<void>;
  onForgotPassword?: () => void;
  onSignUp?: () => void;
}

export default function LoginForm({ onSubmit, onForgotPassword, onSignUp }: LoginFormProps) {
  const [showPassword, setShowPassword] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const handleFormSubmit = async (data: LoginFormData) => {
    setIsSubmitting(true);
    try {
      await onSubmit(data);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto p-6 bg-white rounded-xl shadow-lg">
      <h2 className="text-2xl font-bold text-center text-gray-900 mb-6">
        Welcome Back
      </h2>

      <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
            Email
          </label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              {...register('email')}
              type="email"
              id="email"
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="you@example.com"
            />
          </div>
          {errors.email && (
            <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
            Password
          </label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              {...register('password')}
              type={showPassword ? 'text' : 'password'}
              id="password"
              className="w-full pl-10 pr-12 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="••••••••"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
          {errors.password && (
            <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
          )}
        </div>

        <div className="flex items-center justify-between">
          <label className="flex items-center">
            <input
              {...register('rememberMe')}
              type="checkbox"
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span className="ml-2 text-sm text-gray-600">Remember me</span>
          </label>
          {onForgotPassword && (
            <button
              type="button"
              onClick={onForgotPassword}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Forgot password?
            </button>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full py-2 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isSubmitting ? (
            <span className="flex items-center justify-center">
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Signing in...
            </span>
          ) : (
            'Sign In'
          )}
        </button>
      </form>

      {onSignUp && (
        <p className="mt-6 text-center text-sm text-gray-600">
          Don't have an account?{' '}
          <button
            onClick={onSignUp}
            className="text-blue-600 hover:text-blue-800 font-medium"
          >
            Sign up
          </button>
        </p>
      )}
    </div>
  );
}
```'''

    FASTAPI_CRUD = '''```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.product import Product
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=ProductListResponse)
async def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category_id: Optional[UUID] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: str = Query("created_at", regex="^(name|price|created_at)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    """Get paginated list of products with filters"""
    query = db.query(Product).filter(Product.is_active == True)

    # Apply filters
    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%"),
            )
        )
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(Product, sort_by)
    if sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    # Apply pagination
    products = query.offset(skip).limit(limit).all()

    return ProductListResponse(
        items=products,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    db: Session = Depends(get_db),
):
    """Get a single product by ID"""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.is_active == True,
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new product (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    product = Product(**product_data.model_dump(), created_by=current_user.id)
    db.add(product)
    db.commit()
    db.refresh(product)

    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a product (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete a product (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    product.is_active = False
    db.commit()

    return None
```'''

    SQLALCHEMY_MODEL = '''```python
from sqlalchemy import Column, String, Float, Integer, Boolean, Text, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class ProductStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic info
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    short_description = Column(String(500))

    # Pricing
    price = Column(Float, nullable=False)
    compare_at_price = Column(Float)  # Original price for showing discounts
    cost_price = Column(Float)  # For profit calculation

    # Inventory
    sku = Column(String(100), unique=True, index=True)
    barcode = Column(String(100))
    quantity = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=10)
    track_inventory = Column(Boolean, default=True)

    # Status
    status = Column(Enum(ProductStatus), default=ProductStatus.DRAFT)
    is_active = Column(Boolean, default=True, index=True)
    is_featured = Column(Boolean, default=False)

    # SEO
    meta_title = Column(String(255))
    meta_description = Column(String(500))

    # Media
    images = Column(JSONB, default=list)  # [{url, alt, position}]
    thumbnail_url = Column(String(500))

    # Attributes
    attributes = Column(JSONB, default=dict)  # {color, size, material, etc.}

    # Relations
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), index=True)
    category = relationship("Category", back_populates="products")

    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True)
    brand = relationship("Brand", back_populates="products")

    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    reviews = relationship("ProductReview", back_populates="product", cascade="all, delete-orphan")

    # Audit
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_on_sale(self) -> bool:
        return self.compare_at_price is not None and self.compare_at_price > self.price

    @property
    def discount_percentage(self) -> float:
        if not self.is_on_sale:
            return 0
        return round((1 - self.price / self.compare_at_price) * 100, 1)

    @property
    def is_in_stock(self) -> bool:
        if not self.track_inventory:
            return True
        return self.quantity > 0

    @property
    def is_low_stock(self) -> bool:
        if not self.track_inventory:
            return False
        return self.quantity <= self.low_stock_threshold

    @property
    def average_rating(self) -> float:
        if not self.reviews:
            return 0
        return sum(r.rating for r in self.reviews) / len(self.reviews)

    def __repr__(self):
        return f"<Product {self.name}>"
```'''

    PYDANTIC_SCHEMAS = '''```python
from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class ProductStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"


class ProductImage(BaseModel):
    url: str
    alt: Optional[str] = None
    position: int = 0


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    price: float = Field(..., gt=0)
    compare_at_price: Optional[float] = Field(None, gt=0)
    sku: Optional[str] = Field(None, max_length=100)
    quantity: int = Field(default=0, ge=0)
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    status: ProductStatus = ProductStatus.DRAFT
    is_featured: bool = False
    attributes: Dict[str, Any] = Field(default_factory=dict)
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = Field(None, max_length=500)

    @field_validator('compare_at_price')
    @classmethod
    def compare_price_must_be_higher(cls, v, info):
        if v is not None and 'price' in info.data and v <= info.data['price']:
            raise ValueError('compare_at_price must be higher than price')
        return v


class ProductCreate(ProductBase):
    images: List[ProductImage] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, gt=0)
    compare_at_price: Optional[float] = Field(None, gt=0)
    sku: Optional[str] = Field(None, max_length=100)
    quantity: Optional[int] = Field(None, ge=0)
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    status: Optional[ProductStatus] = None
    is_featured: Optional[bool] = None
    attributes: Optional[Dict[str, Any]] = None
    images: Optional[List[ProductImage]] = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str


class BrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    logo_url: Optional[str] = None


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    images: List[ProductImage] = []
    thumbnail_url: Optional[str] = None
    category: Optional[CategoryResponse] = None
    brand: Optional[BrandResponse] = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def is_on_sale(self) -> bool:
        return self.compare_at_price is not None and self.compare_at_price > self.price

    @computed_field
    @property
    def discount_percentage(self) -> float:
        if not self.is_on_sale:
            return 0
        return round((1 - self.price / self.compare_at_price) * 100, 1)

    @computed_field
    @property
    def is_in_stock(self) -> bool:
        return self.quantity > 0


class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    skip: int
    limit: int

    @computed_field
    @property
    def has_more(self) -> bool:
        return self.skip + len(self.items) < self.total
```'''

    @classmethod
    def get_all_templates(cls) -> Dict[str, str]:
        """Get all code templates"""
        return {
            "react_button": cls.REACT_BUTTON,
            "react_login_form": cls.REACT_LOGIN_FORM,
            "fastapi_crud": cls.FASTAPI_CRUD,
            "sqlalchemy_model": cls.SQLALCHEMY_MODEL,
            "pydantic_schemas": cls.PYDANTIC_SCHEMAS,
        }


class PublicDatasetDownloader:
    """Download and process public code datasets"""

    DATASETS = {
        "code_alpaca": {
            "source": "sahil2801/CodeAlpaca-20k",
            "description": "20k code instruction-following dataset",
        },
        "code_feedback": {
            "source": "m-a-p/CodeFeedback-Filtered-Instruction",
            "description": "High-quality code feedback data",
        },
        "python_code": {
            "source": "flytech/python-codes-25k",
            "description": "25k Python code examples",
        },
    }

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_dataset(self, dataset_name: str, max_samples: int = 1000) -> List[Dict]:
        """Download a dataset from Hugging Face"""
        try:
            from datasets import load_dataset

            if dataset_name not in self.DATASETS:
                logger.warning(f"Unknown dataset: {dataset_name}")
                return []

            dataset_info = self.DATASETS[dataset_name]
            logger.info(f"Downloading {dataset_name} from {dataset_info['source']}...")

            dataset = load_dataset(dataset_info["source"], split="train")

            samples = []
            for i, item in enumerate(dataset):
                if i >= max_samples:
                    break

                # Convert to our format
                sample = self._convert_sample(item, dataset_name)
                if sample:
                    samples.append(sample)

            logger.info(f"Downloaded {len(samples)} samples from {dataset_name}")
            return samples

        except Exception as e:
            logger.error(f"Failed to download {dataset_name}: {e}")
            return []

    def _convert_sample(self, item: Dict, source: str) -> Optional[Dict]:
        """Convert dataset item to our training format"""
        # Different datasets have different schemas
        instruction = item.get("instruction") or item.get("prompt") or item.get("input")
        output = item.get("output") or item.get("response") or item.get("completion")

        if not instruction or not output:
            return None

        # Filter for relevant content (React, Python, FastAPI, etc.)
        relevant_keywords = ["react", "python", "fastapi", "typescript", "component", "api", "function", "class"]
        text_lower = (instruction + output).lower()

        if not any(kw in text_lower for kw in relevant_keywords):
            return None

        return {
            "messages": [
                {"role": "system", "content": "You are an expert full-stack developer. Generate clean, production-ready code."},
                {"role": "user", "content": instruction},
                {"role": "assistant", "content": output}
            ],
            "metadata": {"source": source}
        }


class TrainingDataCollector:
    """Main class to collect all training data"""

    def __init__(self, config: DataCollectionConfig = None):
        self.config = config or DataCollectionConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def collect_from_database(self) -> List[Dict]:
        """Extract training data from BharatBuild AI database"""
        if not self.config.extract_from_db:
            return []

        logger.info("Extracting data from database...")

        try:
            from data_extractor import TrainingDataExtractor

            extractor = TrainingDataExtractor()
            projects = extractor.get_successful_projects(limit=self.config.db_limit)
            samples = extractor.create_instruction_pairs(projects)

            logger.info(f"Extracted {len(samples)} samples from database")
            return samples

        except Exception as e:
            logger.error(f"Database extraction failed: {e}")
            return []

    def generate_synthetic_data(self) -> List[Dict]:
        """Generate synthetic training data"""
        if not self.config.generate_synthetic:
            return []

        logger.info("Generating synthetic data...")

        generator = SyntheticDataGenerator(self.config)
        templates = generator.generate_all()

        # Fill in templates with actual code from library
        library = CodeTemplateLibrary.get_all_templates()

        filled_samples = []
        for template in templates:
            sample_type = template["metadata"]["type"]

            # Find matching code from library
            code = None
            if "button" in sample_type or "button" in template["metadata"]["instruction"].lower():
                code = library["react_button"]
            elif "form" in sample_type or "login" in template["metadata"]["instruction"].lower():
                code = library["react_login_form"]
            elif "fastapi" in sample_type or "endpoint" in template["metadata"]["instruction"].lower():
                code = library["fastapi_crud"]
            elif "sqlalchemy" in sample_type or "model" in template["metadata"]["instruction"].lower():
                code = library["sqlalchemy_model"]
            elif "pydantic" in sample_type or "schema" in template["metadata"]["instruction"].lower():
                code = library["pydantic_schemas"]

            if code:
                template["messages"][2]["content"] = code
                template["metadata"]["needs_generation"] = False
                filled_samples.append(template)

        logger.info(f"Generated {len(filled_samples)} synthetic samples")
        return filled_samples

    def download_public_datasets(self) -> List[Dict]:
        """Download and process public datasets"""
        if not self.config.use_public_datasets:
            return []

        logger.info("Downloading public datasets...")

        downloader = PublicDatasetDownloader(str(self.output_dir / "public"))

        all_samples = []
        for dataset_name in PublicDatasetDownloader.DATASETS:
            samples = downloader.download_dataset(dataset_name, max_samples=500)
            all_samples.extend(samples)

        logger.info(f"Downloaded {len(all_samples)} samples from public datasets")
        return all_samples

    def collect_all(self) -> List[Dict]:
        """Collect all training data"""
        all_samples = []

        # 1. Database extraction
        db_samples = self.collect_from_database()
        all_samples.extend(db_samples)

        # 2. Synthetic generation
        synthetic_samples = self.generate_synthetic_data()
        all_samples.extend(synthetic_samples)

        # 3. Public datasets
        public_samples = self.download_public_datasets()
        all_samples.extend(public_samples)

        # Shuffle
        random.shuffle(all_samples)

        # Save
        output_file = self.output_dir / "training_data.jsonl"
        with open(output_file, 'w', encoding='utf-8') as f:
            for sample in all_samples:
                # Remove metadata before saving
                clean_sample = {"messages": sample["messages"]}
                f.write(json.dumps(clean_sample, ensure_ascii=False) + '\n')

        logger.info(f"\nTotal samples collected: {len(all_samples)}")
        logger.info(f"  - Database: {len(db_samples)}")
        logger.info(f"  - Synthetic: {len(synthetic_samples)}")
        logger.info(f"  - Public: {len(public_samples)}")
        logger.info(f"Saved to: {output_file}")

        return all_samples


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Collect training data")
    parser.add_argument("--output-dir", type=str, default="./data/collected")
    parser.add_argument("--no-db", action="store_true", help="Skip database extraction")
    parser.add_argument("--no-synthetic", action="store_true", help="Skip synthetic generation")
    parser.add_argument("--no-public", action="store_true", help="Skip public datasets")
    parser.add_argument("--db-limit", type=int, help="Limit database samples")
    parser.add_argument("--synthetic-count", type=int, default=500)
    args = parser.parse_args()

    config = DataCollectionConfig(
        output_dir=args.output_dir,
        extract_from_db=not args.no_db,
        generate_synthetic=not args.no_synthetic,
        use_public_datasets=not args.no_public,
        db_limit=args.db_limit,
        synthetic_count=args.synthetic_count,
    )

    collector = TrainingDataCollector(config)
    collector.collect_all()


if __name__ == "__main__":
    main()
