"""
Unit Tests for Usage Limits Module
Tests for: plan limits, token limits, project limits, rate limits
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from faker import Faker

from app.modules.auth.usage_limits import (
    UserLimits,
    UsageLimitCheck,
    FREE_LIMITS,
    get_user_limits,
    check_token_limit,
    check_project_limit,
    check_api_rate_limit,
    check_document_generation_limit,
    check_document_type,
    check_bug_fixing_limit,
    check_model_access,
    check_all_limits,
    require_feature,
    deduct_tokens,
    log_api_usage,
    get_current_token_usage,
    check_project_generation_allowed
)
from app.models.user import User, UserRole
from app.models.billing import Plan, Subscription, SubscriptionStatus, PlanType
from app.models.project import Project, ProjectStatus, ProjectMode

fake = Faker()


class TestUserLimits:
    """Test UserLimits dataclass"""

    def test_is_unlimited_with_none_token_limit(self):
        """Test is_unlimited returns True when token_limit is None"""
        limits = UserLimits(
            plan_name="Pro",
            plan_type=PlanType.PRO,
            token_limit=None
        )

        assert limits.is_unlimited is True

    def test_is_unlimited_with_token_limit(self):
        """Test is_unlimited returns False when token_limit is set"""
        limits = UserLimits(
            plan_name="Free",
            plan_type=PlanType.FREE,
            token_limit=10000
        )

        assert limits.is_unlimited is False


class TestFreeLimits:
    """Test FREE_LIMITS default"""

    def test_free_limits_token_limit(self):
        """Test free tier has token limit"""
        assert FREE_LIMITS.token_limit == 10000

    def test_free_limits_project_limit(self):
        """Test free tier has project limit"""
        assert FREE_LIMITS.project_limit == 1

    def test_free_limits_max_files(self):
        """Test free tier has max files limit"""
        assert FREE_LIMITS.max_files_per_project == 3

    def test_free_limits_feature_flags(self):
        """Test free tier feature flags"""
        assert FREE_LIMITS.feature_flags["code_execution"] is True
        assert FREE_LIMITS.feature_flags["download_files"] is False


class TestGetUserLimits:
    """Test getting user limits"""

    @pytest.mark.asyncio
    async def test_get_limits_no_subscription(self, db_session, test_user):
        """Test limits for user without subscription"""
        limits = await get_user_limits(test_user, db_session)

        assert limits.plan_name == "Free"
        assert limits.token_limit == FREE_LIMITS.token_limit

    @pytest.mark.asyncio
    async def test_get_limits_with_token_purchase(self, db_session, test_user):
        """Test limits for user with token purchase"""
        from app.models.token_balance import TokenPurchase

        purchase = TokenPurchase(
            user_id=str(test_user.id),
            amount=100,
            tokens=10000,
            payment_status="success",
            is_expired=False
        )
        db_session.add(purchase)
        await db_session.commit()

        limits = await get_user_limits(test_user, db_session)

        assert "Premium" in limits.plan_name or "Token Purchase" in limits.plan_name
        assert limits.token_limit is None  # Unlimited

    @pytest.mark.asyncio
    async def test_get_limits_with_subscription(self, db_session, test_user):
        """Test limits for user with subscription"""
        plan = Plan(
            name="Student",
            plan_type=PlanType.STUDENT,
            price=499,
            token_limit=50000,
            project_limit=5,
            feature_flags={"project_generation": True}
        )
        db_session.add(plan)
        await db_session.flush()

        subscription = Subscription(
            user_id=str(test_user.id),
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE
        )
        db_session.add(subscription)
        await db_session.commit()

        limits = await get_user_limits(test_user, db_session)

        assert limits.plan_name == "Student"
        assert limits.token_limit == 50000


class TestCheckTokenLimit:
    """Test token limit checking"""

    @pytest.mark.asyncio
    async def test_check_unlimited_tokens(self, db_session, test_user):
        """Test unlimited tokens always allowed"""
        from app.models.token_balance import TokenPurchase

        purchase = TokenPurchase(
            user_id=str(test_user.id),
            amount=100,
            tokens=10000,
            payment_status="success",
            is_expired=False
        )
        db_session.add(purchase)
        await db_session.commit()

        result = await check_token_limit(test_user, db_session, tokens_needed=1000000)

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_check_within_limit(self, db_session, test_user):
        """Test tokens within limit allowed"""
        result = await check_token_limit(test_user, db_session, tokens_needed=100)

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_check_exceeds_limit(self, db_session, test_user):
        """Test tokens exceeding limit denied"""
        from app.models.usage import TokenUsage

        # Add usage that nearly exhausts the limit
        usage = TokenUsage(
            user_id=str(test_user.id),
            date=datetime.utcnow().replace(day=1),
            total_tokens=9500
        )
        db_session.add(usage)
        await db_session.commit()

        result = await check_token_limit(test_user, db_session, tokens_needed=1000)

        assert result.allowed is False
        assert "exceeded" in result.reason.lower()


class TestCheckProjectLimit:
    """Test project limit checking"""

    @pytest.mark.asyncio
    async def test_check_no_projects(self, db_session, test_user):
        """Test project limit when user has no projects"""
        result = await check_project_limit(test_user, db_session)

        assert result.allowed is True
        assert result.current_usage == 0

    @pytest.mark.asyncio
    async def test_check_with_completed_projects(self, db_session, test_user):
        """Test project limit counting only completed projects"""
        # Create a completed project
        project = Project(
            user_id=str(test_user.id),
            title="Completed Project",
            description="Test",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.COMPLETED
        )
        db_session.add(project)
        await db_session.commit()

        result = await check_project_limit(test_user, db_session)

        # Free tier has 1 project limit, so should be at limit
        assert result.current_usage == 1

    @pytest.mark.asyncio
    async def test_partial_completed_not_counted(self, db_session, test_user):
        """Test PARTIAL_COMPLETED projects don't count against limit"""
        project = Project(
            user_id=str(test_user.id),
            title="Partial Project",
            description="Test",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.PARTIAL_COMPLETED
        )
        db_session.add(project)
        await db_session.commit()

        result = await check_project_limit(test_user, db_session)

        assert result.current_usage == 0  # Partial doesn't count


class TestCheckApiRateLimit:
    """Test API rate limit checking"""

    @pytest.mark.asyncio
    async def test_check_rate_limit_not_exceeded(self, db_session, test_user):
        """Test rate limit not exceeded"""
        result = await check_api_rate_limit(test_user, db_session)

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, db_session, test_user):
        """Test rate limit exceeded"""
        from app.models.usage import UsageLog

        # Add many logs for today
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        for _ in range(150):  # Exceed 100 limit
            log = UsageLog(
                user_id=str(test_user.id),
                endpoint="/api/test",
                method="POST",
                created_at=today + timedelta(hours=1)
            )
            db_session.add(log)
        await db_session.commit()

        result = await check_api_rate_limit(test_user, db_session)

        assert result.allowed is False


class TestCheckDocumentGeneration:
    """Test document generation limit checking"""

    @pytest.mark.asyncio
    async def test_check_no_documents(self, db_session, test_user):
        """Test limit when user has no documents"""
        # Give user Premium access
        from app.models.token_balance import TokenPurchase
        purchase = TokenPurchase(
            user_id=str(test_user.id),
            amount=100,
            tokens=10000,
            payment_status="success",
            is_expired=False
        )
        db_session.add(purchase)
        await db_session.commit()

        result = await check_document_generation_limit(test_user, db_session)

        assert result.allowed is True


class TestCheckDocumentType:
    """Test document type access checking"""

    @pytest.mark.asyncio
    async def test_srs_denied_free_tier(self, db_session, test_user):
        """Test SRS document denied for free tier"""
        result = await check_document_type(test_user, db_session, "srs")

        assert result.allowed is False
        assert "Premium" in result.reason

    @pytest.mark.asyncio
    async def test_srs_allowed_premium(self, db_session, test_user):
        """Test SRS document allowed for premium"""
        from app.models.token_balance import TokenPurchase
        purchase = TokenPurchase(
            user_id=str(test_user.id),
            amount=100,
            tokens=10000,
            payment_status="success",
            is_expired=False
        )
        db_session.add(purchase)
        await db_session.commit()

        result = await check_document_type(test_user, db_session, "srs")

        assert result.allowed is True


class TestCheckBugFixingLimit:
    """Test bug fixing limit checking"""

    @pytest.mark.asyncio
    async def test_bug_fixing_denied_free(self, db_session, test_user):
        """Test bug fixing denied for free tier"""
        result = await check_bug_fixing_limit(test_user, db_session)

        assert result.allowed is False
        assert "Premium" in result.reason

    @pytest.mark.asyncio
    async def test_bug_fixing_allowed_premium(self, db_session, test_user):
        """Test bug fixing allowed for premium"""
        from app.models.token_balance import TokenPurchase
        purchase = TokenPurchase(
            user_id=str(test_user.id),
            amount=100,
            tokens=10000,
            payment_status="success",
            is_expired=False
        )
        db_session.add(purchase)
        await db_session.commit()

        result = await check_bug_fixing_limit(test_user, db_session)

        assert result.allowed is True


class TestCheckModelAccess:
    """Test model access checking"""

    @pytest.mark.asyncio
    async def test_haiku_allowed_free(self, db_session, test_user):
        """Test Haiku model allowed for free tier"""
        result = await check_model_access(test_user, db_session, "haiku")

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_sonnet_denied_free(self, db_session, test_user):
        """Test Sonnet model denied for free tier"""
        result = await check_model_access(test_user, db_session, "sonnet")

        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_sonnet_allowed_premium(self, db_session, test_user):
        """Test Sonnet model allowed for premium"""
        from app.models.token_balance import TokenPurchase
        purchase = TokenPurchase(
            user_id=str(test_user.id),
            amount=100,
            tokens=10000,
            payment_status="success",
            is_expired=False
        )
        db_session.add(purchase)
        await db_session.commit()

        result = await check_model_access(test_user, db_session, "sonnet")

        assert result.allowed is True


class TestCheckAllLimits:
    """Test combined limit checking"""

    @pytest.mark.asyncio
    async def test_all_limits_pass(self, db_session, test_user):
        """Test all limits pass for normal usage"""
        result = await check_all_limits(test_user, db_session, tokens_needed=100)

        assert result.allowed is True


class TestRequireFeature:
    """Test require_feature function"""

    @pytest.mark.asyncio
    async def test_require_allowed_feature(self, db_session, test_user):
        """Test require doesn't raise for allowed feature"""
        try:
            await require_feature(test_user, db_session, "code_execution")
        except Exception:
            pytest.fail("Should not raise for allowed feature")

    @pytest.mark.asyncio
    async def test_require_denied_feature(self, db_session, test_user):
        """Test require raises for denied feature"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await require_feature(test_user, db_session, "download_files")

        assert exc_info.value.status_code == 403


class TestDeductTokens:
    """Test token deduction"""

    @pytest.mark.asyncio
    async def test_deduct_tokens_new_record(self, db_session, test_user):
        """Test deducting tokens creates new usage record"""
        await deduct_tokens(test_user, db_session, tokens_used=500, model="haiku")

        usage = await get_current_token_usage(test_user, db_session)
        assert usage >= 500

    @pytest.mark.asyncio
    async def test_deduct_tokens_existing_record(self, db_session, test_user):
        """Test deducting tokens updates existing record"""
        await deduct_tokens(test_user, db_session, tokens_used=500, model="haiku")
        await deduct_tokens(test_user, db_session, tokens_used=300, model="haiku")

        usage = await get_current_token_usage(test_user, db_session)
        assert usage >= 800


class TestLogApiUsage:
    """Test API usage logging"""

    @pytest.mark.asyncio
    async def test_log_api_usage(self, db_session, test_user):
        """Test logging API usage"""
        await log_api_usage(
            user=test_user,
            db=db_session,
            endpoint="/api/v1/test",
            method="POST",
            tokens_used=100,
            model="haiku",
            status_code=200
        )

        # Should not raise any exception
        assert True


class TestCheckProjectGenerationAllowed:
    """Test project generation allowed check"""

    @pytest.mark.asyncio
    async def test_generation_allowed_premium(self, db_session, test_user):
        """Test generation allowed for premium user"""
        from app.models.token_balance import TokenPurchase
        purchase = TokenPurchase(
            user_id=str(test_user.id),
            amount=100,
            tokens=10000,
            payment_status="success",
            is_expired=False
        )
        db_session.add(purchase)
        await db_session.commit()

        result = await check_project_generation_allowed(test_user, db_session)

        assert result.allowed is True


class TestUsageLimitCheckDataclass:
    """Test UsageLimitCheck dataclass"""

    def test_create_allowed_check(self):
        """Test creating an allowed check"""
        check = UsageLimitCheck(allowed=True)
        assert check.allowed is True
        assert check.reason is None

    def test_create_denied_check(self):
        """Test creating a denied check"""
        check = UsageLimitCheck(
            allowed=False,
            reason="Limit exceeded",
            current_usage=100,
            limit=50
        )
        assert check.allowed is False
        assert check.reason == "Limit exceeded"
        assert check.current_usage == 100
        assert check.limit == 50
