"""
Unit Tests for Feature Flags Module
Tests for: feature access checking, plan-based features, global flags
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from faker import Faker

from app.modules.auth.feature_flags import (
    FREE_TIER_FEATURES,
    get_global_feature_flag,
    has_token_purchase,
    get_user_plan,
    check_feature_access,
    require_feature_access,
    require_feature
)
from app.models.user import User, UserRole
from app.models.billing import Plan, Subscription, SubscriptionStatus, PlanType

fake = Faker()


class TestFreeTierFeatures:
    """Test free tier feature definitions"""

    def test_free_tier_has_code_execution(self):
        """Test free tier has code execution enabled"""
        assert FREE_TIER_FEATURES["code_execution"] is True

    def test_free_tier_has_code_preview(self):
        """Test free tier has code preview enabled"""
        assert FREE_TIER_FEATURES["code_preview"] is True

    def test_free_tier_no_document_generation(self):
        """Test free tier has document generation disabled"""
        assert FREE_TIER_FEATURES["document_generation"] is False

    def test_free_tier_no_project_generation(self):
        """Test free tier has project generation disabled"""
        assert FREE_TIER_FEATURES["project_generation"] is False

    def test_free_tier_no_bug_fixing(self):
        """Test free tier has bug fixing disabled"""
        assert FREE_TIER_FEATURES["bug_fixing"] is False

    def test_free_tier_no_download(self):
        """Test free tier has download disabled"""
        assert FREE_TIER_FEATURES["download_files"] is False


class TestGlobalFeatureFlag:
    """Test global feature flag retrieval"""

    @pytest.mark.asyncio
    async def test_get_flag_not_set_returns_true(self, db_session):
        """Test that unset flag defaults to True"""
        result = await get_global_feature_flag(db_session, "nonexistent_feature")

        assert result is True

    @pytest.mark.asyncio
    async def test_get_flag_set_to_true(self, db_session):
        """Test getting flag that's set to True"""
        from app.models.system_setting import SystemSetting

        setting = SystemSetting(key="features.test_feature", value=True)
        db_session.add(setting)
        await db_session.commit()

        result = await get_global_feature_flag(db_session, "test_feature")

        assert result is True

    @pytest.mark.asyncio
    async def test_get_flag_set_to_false(self, db_session):
        """Test getting flag that's set to False"""
        from app.models.system_setting import SystemSetting

        setting = SystemSetting(key="features.disabled_feature", value=False)
        db_session.add(setting)
        await db_session.commit()

        result = await get_global_feature_flag(db_session, "disabled_feature")

        assert result is False


class TestHasTokenPurchase:
    """Test token purchase checking"""

    @pytest.mark.asyncio
    async def test_no_token_purchase(self, db_session, test_user):
        """Test user without token purchase"""
        result = await has_token_purchase(db_session, str(test_user.id))

        assert result is False

    @pytest.mark.asyncio
    async def test_with_successful_token_purchase(self, db_session, test_user):
        """Test user with successful token purchase"""
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

        result = await has_token_purchase(db_session, str(test_user.id))

        assert result is True

    @pytest.mark.asyncio
    async def test_with_expired_token_purchase(self, db_session, test_user):
        """Test user with expired token purchase"""
        from app.models.token_balance import TokenPurchase

        purchase = TokenPurchase(
            user_id=str(test_user.id),
            amount=100,
            tokens=10000,
            payment_status="success",
            is_expired=True
        )
        db_session.add(purchase)
        await db_session.commit()

        result = await has_token_purchase(db_session, str(test_user.id))

        assert result is False

    @pytest.mark.asyncio
    async def test_with_premium_balance(self, db_session, test_user):
        """Test user with premium tokens in balance"""
        from app.models.token_balance import TokenBalance

        balance = TokenBalance(
            user_id=str(test_user.id),
            premium_tokens=5000,
            free_tokens=0
        )
        db_session.add(balance)
        await db_session.commit()

        result = await has_token_purchase(db_session, str(test_user.id))

        assert result is True


class TestGetUserPlan:
    """Test getting user's subscription plan"""

    @pytest.mark.asyncio
    async def test_no_active_subscription(self, db_session, test_user):
        """Test user without active subscription"""
        result = await get_user_plan(db_session, str(test_user.id))

        assert result is None

    @pytest.mark.asyncio
    async def test_with_active_subscription(self, db_session, test_user):
        """Test user with active subscription"""
        # Create plan
        plan = Plan(
            name="Premium",
            plan_type=PlanType.PRO,
            price=999,
            token_limit=None,
            feature_flags={"project_generation": True}
        )
        db_session.add(plan)
        await db_session.flush()

        # Create subscription
        subscription = Subscription(
            user_id=str(test_user.id),
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE
        )
        db_session.add(subscription)
        await db_session.commit()

        result = await get_user_plan(db_session, str(test_user.id))

        assert result is not None
        assert result.name == "Premium"


class TestCheckFeatureAccess:
    """Test feature access checking"""

    @pytest.mark.asyncio
    async def test_feature_globally_disabled(self, db_session, test_user):
        """Test access denied when feature is globally disabled"""
        from app.models.system_setting import SystemSetting

        setting = SystemSetting(key="features.disabled_globally", value=False)
        db_session.add(setting)
        await db_session.commit()

        result = await check_feature_access(db_session, test_user, "disabled_globally")

        assert result["allowed"] is False
        assert "maintenance" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_feature_allowed_with_token_purchase(self, db_session, test_user):
        """Test access granted with token purchase"""
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

        result = await check_feature_access(db_session, test_user, "project_generation")

        assert result["allowed"] is True
        assert result["current_plan"] == "Premium"

    @pytest.mark.asyncio
    async def test_feature_denied_free_tier(self, db_session, test_user):
        """Test access denied for free tier"""
        result = await check_feature_access(db_session, test_user, "document_generation")

        assert result["allowed"] is False
        assert result["current_plan"] == "Free"
        assert result["upgrade_to"] is not None

    @pytest.mark.asyncio
    async def test_feature_allowed_free_tier(self, db_session, test_user):
        """Test access granted for allowed free tier feature"""
        result = await check_feature_access(db_session, test_user, "code_execution")

        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_feature_allowed_with_plan(self, db_session, test_user):
        """Test access granted with subscription plan"""
        # Create plan with feature
        plan = Plan(
            name="Premium",
            plan_type=PlanType.PRO,
            price=999,
            feature_flags={"test_feature": True}
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

        result = await check_feature_access(db_session, test_user, "test_feature")

        assert result["allowed"] is True
        assert result["current_plan"] == "Premium"


class TestRequireFeatureAccess:
    """Test feature access requirement (raises exception)"""

    @pytest.mark.asyncio
    async def test_require_feature_allowed(self, db_session, test_user):
        """Test no exception when feature is allowed"""
        # code_execution is allowed for free tier
        try:
            await require_feature_access("code_execution", db_session, test_user)
        except Exception:
            pytest.fail("Should not raise exception for allowed feature")

    @pytest.mark.asyncio
    async def test_require_feature_denied(self, db_session, test_user):
        """Test exception raised when feature is denied"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await require_feature_access("document_generation", db_session, test_user)

        assert exc_info.value.status_code == 403
        assert "feature_not_available" in str(exc_info.value.detail)


class TestRequireFeatureFactory:
    """Test require_feature dependency factory"""

    def test_require_feature_returns_callable(self):
        """Test that require_feature returns a callable"""
        checker = require_feature("test_feature")

        assert callable(checker)

    @pytest.mark.asyncio
    async def test_require_feature_checker_works(self, db_session, test_user):
        """Test that the checker function works correctly"""
        from fastapi import HTTPException

        checker = require_feature("document_generation")

        with pytest.raises(HTTPException):
            await checker(current_user=test_user, db=db_session)
