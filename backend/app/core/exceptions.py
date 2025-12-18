"""
Custom Exceptions for BharatBuild AI
====================================

Use these instead of generic Exception to:
1. Make errors more specific and debuggable
2. Enable proper error handling at API layer
3. Provide meaningful error messages to users

Usage:
    from app.core.exceptions import ProjectNotFoundError, DocumentGenerationError

    if not project:
        raise ProjectNotFoundError(project_id)

    try:
        generate_document(...)
    except DocumentGenerationError as e:
        logger.error(f"Document generation failed: {e}")
        raise
"""

from typing import Optional, Any, Dict


class BharatBuildError(Exception):
    """Base exception for all BharatBuild errors"""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details
        }


# ============================================
# Authentication & Authorization Errors
# ============================================

class AuthenticationError(BharatBuildError):
    """User authentication failed"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="AUTH_FAILED")


class AuthorizationError(BharatBuildError):
    """User not authorized for this action"""

    def __init__(self, message: str = "Not authorized"):
        super().__init__(message, code="NOT_AUTHORIZED")


class TokenExpiredError(AuthenticationError):
    """JWT token has expired"""

    def __init__(self):
        super().__init__("Token has expired")
        self.code = "TOKEN_EXPIRED"


class InvalidTokenError(AuthenticationError):
    """JWT token is invalid"""

    def __init__(self):
        super().__init__("Invalid token")
        self.code = "INVALID_TOKEN"


# ============================================
# Resource Errors (404-type)
# ============================================

class ResourceNotFoundError(BharatBuildError):
    """Base class for not found errors"""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            f"{resource_type} with ID '{resource_id}' not found",
            code=f"{resource_type.upper()}_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class ProjectNotFoundError(ResourceNotFoundError):
    """Project not found"""

    def __init__(self, project_id: str):
        super().__init__("Project", project_id)


class UserNotFoundError(ResourceNotFoundError):
    """User not found"""

    def __init__(self, user_id: str):
        super().__init__("User", user_id)


class DocumentNotFoundError(ResourceNotFoundError):
    """Document not found"""

    def __init__(self, document_id: str):
        super().__init__("Document", document_id)


class FileNotFoundError(ResourceNotFoundError):
    """File not found in project"""

    def __init__(self, file_path: str, project_id: str = ""):
        super().__init__("File", file_path)
        self.details["project_id"] = project_id


# ============================================
# Validation Errors (400-type)
# ============================================

class ValidationError(BharatBuildError):
    """Input validation failed"""

    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class InvalidProjectDataError(ValidationError):
    """Project data is invalid or incomplete"""

    def __init__(self, message: str = "Invalid project data"):
        super().__init__(message)
        self.code = "INVALID_PROJECT_DATA"


class InvalidFileTypeError(ValidationError):
    """File type not allowed"""

    def __init__(self, file_type: str, allowed_types: list):
        super().__init__(
            f"File type '{file_type}' not allowed. Allowed: {', '.join(allowed_types)}"
        )
        self.code = "INVALID_FILE_TYPE"
        self.details = {"file_type": file_type, "allowed_types": allowed_types}


# ============================================
# Document Generation Errors
# ============================================

class DocumentGenerationError(BharatBuildError):
    """Document generation failed"""

    def __init__(self, message: str, doc_type: Optional[str] = None):
        super().__init__(message, code="DOCUMENT_GENERATION_FAILED")
        if doc_type:
            self.details["doc_type"] = doc_type


class SRSGenerationError(DocumentGenerationError):
    """SRS document generation failed"""

    def __init__(self, message: str = "SRS generation failed"):
        super().__init__(message, doc_type="srs")
        self.code = "SRS_GENERATION_FAILED"


class PPTGenerationError(DocumentGenerationError):
    """PPT generation failed"""

    def __init__(self, message: str = "PPT generation failed"):
        super().__init__(message, doc_type="ppt")
        self.code = "PPT_GENERATION_FAILED"


class UMLGenerationError(DocumentGenerationError):
    """UML diagram generation failed"""

    def __init__(self, message: str, diagram_type: Optional[str] = None):
        super().__init__(message, doc_type="uml")
        self.code = "UML_GENERATION_FAILED"
        if diagram_type:
            self.details["diagram_type"] = diagram_type


# ============================================
# AI/Claude Errors
# ============================================

class AIServiceError(BharatBuildError):
    """AI service (Claude) error"""

    def __init__(self, message: str):
        super().__init__(message, code="AI_SERVICE_ERROR")


class AIRateLimitError(AIServiceError):
    """AI rate limit exceeded"""

    def __init__(self, retry_after: Optional[int] = None):
        super().__init__("AI rate limit exceeded. Please try again later.")
        self.code = "AI_RATE_LIMITED"
        if retry_after:
            self.details["retry_after_seconds"] = retry_after


class AIResponseParseError(AIServiceError):
    """Failed to parse AI response"""

    def __init__(self, message: str = "Failed to parse AI response"):
        super().__init__(message)
        self.code = "AI_PARSE_ERROR"


class AITokenLimitError(AIServiceError):
    """Token limit exceeded"""

    def __init__(self, tokens_used: int, token_limit: int):
        super().__init__(f"Token limit exceeded: {tokens_used}/{token_limit}")
        self.code = "TOKEN_LIMIT_EXCEEDED"
        self.details = {"tokens_used": tokens_used, "token_limit": token_limit}


# ============================================
# Storage Errors
# ============================================

class StorageError(BharatBuildError):
    """Storage operation failed"""

    def __init__(self, message: str):
        super().__init__(message, code="STORAGE_ERROR")


class S3UploadError(StorageError):
    """S3 upload failed"""

    def __init__(self, key: str, message: str = "Upload failed"):
        super().__init__(f"Failed to upload to S3: {message}")
        self.code = "S3_UPLOAD_FAILED"
        self.details["s3_key"] = key


class S3DownloadError(StorageError):
    """S3 download failed"""

    def __init__(self, key: str, message: str = "Download failed"):
        super().__init__(f"Failed to download from S3: {message}")
        self.code = "S3_DOWNLOAD_FAILED"
        self.details["s3_key"] = key


# ============================================
# Container/Sandbox Errors
# ============================================

class ContainerError(BharatBuildError):
    """Container operation failed"""

    def __init__(self, message: str, container_id: Optional[str] = None):
        super().__init__(message, code="CONTAINER_ERROR")
        if container_id:
            self.details["container_id"] = container_id


class ContainerTimeoutError(ContainerError):
    """Container operation timed out"""

    def __init__(self, timeout_seconds: int):
        super().__init__(f"Container operation timed out after {timeout_seconds}s")
        self.code = "CONTAINER_TIMEOUT"
        self.details["timeout_seconds"] = timeout_seconds


class ContainerNotFoundError(ContainerError):
    """Container not found"""

    def __init__(self, container_id: str):
        super().__init__(f"Container '{container_id}' not found", container_id)
        self.code = "CONTAINER_NOT_FOUND"


# ============================================
# Project Execution Errors
# ============================================

class ExecutionError(BharatBuildError):
    """Project execution failed"""

    def __init__(self, message: str, project_id: Optional[str] = None):
        super().__init__(message, code="EXECUTION_ERROR")
        if project_id:
            self.details["project_id"] = project_id


class BuildError(ExecutionError):
    """Project build failed"""

    def __init__(self, message: str, stderr: Optional[str] = None):
        super().__init__(message)
        self.code = "BUILD_FAILED"
        if stderr:
            self.details["stderr"] = stderr[:1000]  # Truncate long errors


class DependencyInstallError(ExecutionError):
    """Dependency installation failed"""

    def __init__(self, package: str, message: str = ""):
        super().__init__(f"Failed to install '{package}': {message}")
        self.code = "DEPENDENCY_INSTALL_FAILED"
        self.details["package"] = package


# ============================================
# Payment/Token Errors
# ============================================

class PaymentError(BharatBuildError):
    """Payment operation failed"""

    def __init__(self, message: str):
        super().__init__(message, code="PAYMENT_ERROR")


class InsufficientTokensError(PaymentError):
    """User doesn't have enough tokens"""

    def __init__(self, required: int, available: int):
        super().__init__(
            f"Insufficient tokens. Required: {required}, Available: {available}"
        )
        self.code = "INSUFFICIENT_TOKENS"
        self.details = {"required": required, "available": available}


# ============================================
# Helper function for API responses
# ============================================

def error_response(error: BharatBuildError) -> Dict[str, Any]:
    """Convert exception to API error response format"""
    return {
        "success": False,
        "error": error.to_dict()
    }
