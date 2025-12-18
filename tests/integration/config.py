"""
BharatBuild AI - Integration Test Configuration
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class TestConfig:
    """Test configuration"""
    # URLs
    api_base_url: str = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Test User Credentials
    test_user_email: str = os.getenv("TEST_USER_EMAIL", "integration_test@test.com")
    test_user_password: str = os.getenv("TEST_USER_PASSWORD", "TestPassword123!")
    test_user_name: str = "Integration Test User"

    # Premium Test User
    premium_user_email: str = os.getenv("PREMIUM_USER_EMAIL", "premium_test@test.com")
    premium_user_password: str = os.getenv("PREMIUM_USER_PASSWORD", "PremiumPass123!")

    # Admin User
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@bharatbuild.ai")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "AdminPass123!")

    # Timeouts
    request_timeout: int = 30
    page_load_timeout: int = 60

    # Test Data
    test_project_name: str = "Integration Test Project"
    test_project_prompt: str = "Create a simple todo app with React and Node.js"


# Global config instance
config = TestConfig()
