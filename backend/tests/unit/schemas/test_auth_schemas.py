"""
Unit Tests for Auth Schemas
Tests for: validation, serialization, input/output schemas
"""
import pytest
from pydantic import ValidationError
from datetime import datetime
from uuid import uuid4

from app.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    LoginResponse,
    Token,
    TokenData,
    GoogleAuthRequest,
    OAuthCodeRequest,
    OAuthCallbackRequest,
    OAuthUrlResponse,
    OAuthTokenResponse
)


class TestUserRegister:
    """Test UserRegister schema"""

    def test_valid_student_registration(self):
        """Test creating valid student registration"""
        data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test User",
            "role": "student",
            "roll_number": "CS2024001",
            "college_name": "Test Engineering College",
            "department": "Computer Science",
            "course": "B.Tech",
            "guide_name": "Dr. Test Guide"
        }
        user = UserRegister(**data)

        assert user.email == "test@example.com"
        assert user.roll_number == "CS2024001"
        assert user.college_name == "Test Engineering College"

    def test_student_missing_required_fields_fails(self):
        """Test student registration without required fields fails"""
        data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test User",
            "role": "student"
            # Missing: roll_number, college_name, department, course, guide_name
        }

        with pytest.raises(ValidationError) as exc_info:
            UserRegister(**data)

        error_str = str(exc_info.value)
        assert "Required fields for students" in error_str

    def test_registration_invalid_email(self):
        """Test registration with invalid email"""
        data = {
            "email": "invalid-email",
            "password": "SecurePassword123!",
            "full_name": "Test User",
            "role": "developer"
        }

        with pytest.raises(ValidationError) as exc_info:
            UserRegister(**data)

        assert "email" in str(exc_info.value).lower()

    def test_registration_short_password_fails(self):
        """Test registration with short password fails"""
        data = {
            "email": "test@example.com",
            "password": "short",  # Less than 8 chars
            "full_name": "Test User",
            "role": "developer"
        }

        with pytest.raises(ValidationError):
            UserRegister(**data)

    def test_non_student_role_no_academic_required(self):
        """Test non-student roles don't require academic fields"""
        data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test Developer",
            "role": "developer"
        }
        user = UserRegister(**data)

        assert user.email == "test@example.com"
        assert user.role == "developer"

    def test_registration_with_phone(self):
        """Test registration with valid Indian phone number"""
        data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test User",
            "phone": "9876543210",
            "role": "developer"
        }
        user = UserRegister(**data)

        assert user.phone == "9876543210"

    def test_registration_invalid_phone_fails(self):
        """Test registration with invalid phone format fails"""
        data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test User",
            "phone": "1234567890",  # Doesn't start with 6-9
            "role": "developer"
        }

        with pytest.raises(ValidationError):
            UserRegister(**data)


class TestUserLogin:
    """Test UserLogin schema"""

    def test_valid_login(self):
        """Test valid login data"""
        data = {
            "email": "test@example.com",
            "password": "password123"
        }
        login = UserLogin(**data)

        assert login.email == "test@example.com"
        assert login.password == "password123"

    def test_login_invalid_email(self):
        """Test login with invalid email"""
        data = {
            "email": "not-an-email",
            "password": "password123"
        }

        with pytest.raises(ValidationError):
            UserLogin(**data)

    def test_login_missing_password(self):
        """Test login missing password"""
        data = {
            "email": "test@example.com"
        }

        with pytest.raises(ValidationError):
            UserLogin(**data)


class TestUserResponse:
    """Test UserResponse schema"""

    def test_valid_user_response(self):
        """Test valid user response"""
        data = {
            "id": uuid4(),
            "email": "test@example.com",
            "full_name": "Test User",
            "role": "student",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.utcnow()
        }
        response = UserResponse(**data)

        assert response.email == "test@example.com"
        assert response.is_active is True

    def test_user_response_with_academic_details(self):
        """Test user response with academic details"""
        data = {
            "id": uuid4(),
            "email": "test@example.com",
            "full_name": "Test User",
            "role": "student",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.utcnow(),
            "roll_number": "CS001",
            "college_name": "Test College",
            "department": "CS"
        }
        response = UserResponse(**data)

        assert response.roll_number == "CS001"
        assert response.college_name == "Test College"

    def test_user_response_id_serialization(self):
        """Test UUID is serialized to string"""
        uid = uuid4()
        data = {
            "id": uid,
            "email": "test@example.com",
            "role": "student",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.utcnow()
        }
        response = UserResponse(**data)
        json_data = response.model_dump()

        assert json_data["id"] == str(uid)


class TestLoginResponse:
    """Test LoginResponse schema"""

    def test_valid_login_response(self):
        """Test valid login response"""
        data = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "user": {
                "id": uuid4(),
                "email": "test@example.com",
                "full_name": "Test User",
                "role": "student",
                "is_active": True,
                "is_verified": True,
                "created_at": datetime.utcnow()
            }
        }
        response = LoginResponse(**data)

        assert response.access_token.startswith("eyJ")
        assert response.token_type == "bearer"

    def test_login_response_default_type(self):
        """Test login response default type is bearer"""
        data = {
            "access_token": "token123",
            "refresh_token": "refresh123",
            "user": {
                "id": uuid4(),
                "email": "test@example.com",
                "role": "student",
                "is_active": True,
                "is_verified": True,
                "created_at": datetime.utcnow()
            }
        }
        response = LoginResponse(**data)

        assert response.token_type == "bearer"


class TestToken:
    """Test Token schema"""

    def test_valid_token(self):
        """Test valid token"""
        data = {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_123"
        }
        token = Token(**data)

        assert token.access_token == "access_token_123"
        assert token.token_type == "bearer"

    def test_token_default_type(self):
        """Test token default type"""
        data = {
            "access_token": "token",
            "refresh_token": "refresh"
        }
        token = Token(**data)

        assert token.token_type == "bearer"


class TestTokenData:
    """Test TokenData schema"""

    def test_valid_token_data(self):
        """Test valid token data"""
        data = {
            "user_id": str(uuid4()),
            "email": "test@example.com",
            "role": "student"
        }
        token_data = TokenData(**data)

        assert token_data.email == "test@example.com"
        assert token_data.role == "student"


class TestOAuthSchemas:
    """Test OAuth-related schemas"""

    def test_google_auth_request(self):
        """Test GoogleAuthRequest schema"""
        data = {"credential": "google_id_token_123"}
        request = GoogleAuthRequest(**data)

        assert request.credential == "google_id_token_123"

    def test_oauth_code_request(self):
        """Test OAuthCodeRequest schema"""
        data = {
            "code": "auth_code_123",
            "state": "random_state"
        }
        request = OAuthCodeRequest(**data)

        assert request.code == "auth_code_123"
        assert request.state == "random_state"

    def test_oauth_callback_request(self):
        """Test OAuthCallbackRequest schema"""
        data = {
            "code": "callback_code",
            "role": "developer"
        }
        request = OAuthCallbackRequest(**data)

        assert request.code == "callback_code"
        assert request.role == "developer"

    def test_oauth_callback_default_role(self):
        """Test OAuthCallbackRequest default role"""
        data = {"code": "callback_code"}
        request = OAuthCallbackRequest(**data)

        assert request.role == "student"

    def test_oauth_url_response(self):
        """Test OAuthUrlResponse schema"""
        data = {
            "authorization_url": "https://oauth.example.com/auth",
            "state": "random_state_123"
        }
        response = OAuthUrlResponse(**data)

        assert response.authorization_url == "https://oauth.example.com/auth"

    def test_oauth_token_response(self):
        """Test OAuthTokenResponse schema"""
        data = {
            "access_token": "token123",
            "refresh_token": "refresh123",
            "token_type": "bearer",
            "user": {
                "id": uuid4(),
                "email": "test@example.com",
                "role": "student",
                "is_active": True,
                "is_verified": True,
                "created_at": datetime.utcnow()
            },
            "is_new_user": True
        }
        response = OAuthTokenResponse(**data)

        assert response.is_new_user is True


class TestSchemaValidationMessages:
    """Test schema validation error messages"""

    def test_email_validation_message(self):
        """Test email validation provides clear message"""
        try:
            UserLogin(email="invalid", password="test")
            pytest.fail("Should raise ValidationError")
        except ValidationError as e:
            error_str = str(e)
            assert "email" in error_str.lower() or "value" in error_str.lower()

    def test_password_length_message(self):
        """Test password length validation message"""
        try:
            UserRegister(email="test@example.com", password="short", role="developer")
            pytest.fail("Should raise ValidationError")
        except ValidationError as e:
            error_str = str(e)
            assert "8" in error_str or "min_length" in error_str.lower()
