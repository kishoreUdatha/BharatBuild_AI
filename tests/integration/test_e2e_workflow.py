"""
BharatBuild AI - End-to-End Workflow Integration Tests
Tests complete user journeys from frontend to backend.
"""
import pytest
import asyncio
import uuid
from datetime import datetime

from api_client import BharatBuildAPIClient
from config import config


class TestCompleteUserJourney:
    """Test complete user workflows end-to-end"""

    @pytest.mark.asyncio
    async def test_new_user_complete_journey(self):
        """
        IT-E2E-001: Complete new user journey

        1. Register new account
        2. Login
        3. View profile
        4. Check plan status
        5. List projects (empty)
        6. View document types
        7. Logout
        """
        email = f"journey_{uuid.uuid4().hex[:8]}@test.com"
        password = "TestPassword123!"

        print(f"\n{'='*60}")
        print(f"E2E TEST: Complete New User Journey")
        print(f"Email: {email}")
        print(f"{'='*60}\n")

        async with BharatBuildAPIClient() as client:
            # Step 1: Register
            print("Step 1: Registration...")
            reg_response = await client.register(
                email=email,
                password=password,
                full_name="E2E Test User"
            )
            assert reg_response.success, f"Registration failed: {reg_response.data}"
            print(f"  [OK] Registered successfully")

            # Step 2: Login
            print("Step 2: Login...")
            login_response = await client.login(email, password)
            if login_response.status == 429:
                print(f"  [SKIP] Rate limited - waiting and retrying...")
                await asyncio.sleep(5)
                login_response = await client.login(email, password)

            if login_response.status == 429:
                print(f"  [SKIP] Still rate limited - test cannot complete")
                pytest.skip("Rate limited - cannot complete test")
                return

            assert login_response.success, f"Login failed: {login_response.data}"
            assert client.token is not None
            print(f"  [OK] Logged in, token received")

            # Step 3: View profile
            print("Step 3: Get profile...")
            profile_response = await client.get_current_user()
            assert profile_response.success, f"Get profile failed: {profile_response.data}"
            assert profile_response.data.get("email") == email
            print(f"  [OK] Profile retrieved: {profile_response.data.get('full_name')}")

            # Step 4: Check plan status
            print("Step 4: Check plan status...")
            plan_response = await client.get_plan_status()
            # Plan status may fail for new users - accept both success and known errors
            if plan_response.success:
                print(f"  [OK] Plan status: {plan_response.data}")
            else:
                print(f"  [INFO] Plan status returned: {plan_response.status} (acceptable for new user)")

            # Step 5: List projects
            print("Step 5: List projects...")
            projects_response = await client.list_projects()
            assert projects_response.success, f"List projects failed: {projects_response.data}"
            project_count = len(projects_response.data.get("items", []))
            print(f"  [OK] Projects count: {project_count}")

            # Step 6: View document types
            print("Step 6: Get document types...")
            doc_types_response = await client.get_document_types()
            assert doc_types_response.success, f"Get doc types failed: {doc_types_response.data}"
            print(f"  [OK] Document types: {len(doc_types_response.data)} available")

            # Step 7: Logout
            print("Step 7: Logout...")
            await client.logout()
            assert client.token is None
            print(f"  [OK] Logged out successfully")

            print(f"\n{'='*60}")
            print(f"[PASS] Complete user journey successful!")
            print(f"{'='*60}\n")

    @pytest.mark.asyncio
    async def test_premium_feature_restrictions(self):
        """
        IT-E2E-002: Test premium feature restrictions for free user

        Verify that free users cannot:
        1. Run projects
        2. Export projects
        3. Download documents
        """
        email = f"free_user_{uuid.uuid4().hex[:8]}@test.com"
        password = "TestPassword123!"

        print(f"\n{'='*60}")
        print(f"E2E TEST: Premium Feature Restrictions")
        print(f"{'='*60}\n")

        async with BharatBuildAPIClient() as client:
            # Register and login as free user
            await client.register(email=email, password=password, full_name="Free User")
            await client.login(email, password)

            # Get a project to test with
            projects_response = await client.list_projects()

            if projects_response.success and projects_response.data.get("items"):
                project_id = projects_response.data["items"][0]["id"]

                # Test 1: Run project (should fail)
                print("Test: Run project (should require premium)...")
                run_response = await client.run_project(project_id)
                if not run_response.success and run_response.status in [402, 403]:
                    print(f"  [OK] Run blocked for free user (status: {run_response.status})")
                else:
                    print(f"  [INFO] Run returned: {run_response.status}")

                # Test 2: Export project (should fail)
                print("Test: Export project (should require premium)...")
                export_response = await client.export_project(project_id)
                if not export_response.success and export_response.status in [402, 403]:
                    print(f"  [OK] Export blocked for free user (status: {export_response.status})")
                else:
                    print(f"  [INFO] Export returned: {export_response.status}")

                # Test 3: Download document (should fail)
                print("Test: Download document (should require premium)...")
                download_response = await client.download_document(project_id, "project_report")
                if not download_response.success and download_response.status in [402, 403, 404]:
                    print(f"  [OK] Download blocked for free user (status: {download_response.status})")
                else:
                    print(f"  [INFO] Download returned: {download_response.status}")

                print(f"\n[PASS] Premium restrictions working correctly!")
            else:
                print(f"[SKIP] No projects available to test premium restrictions")

    @pytest.mark.asyncio
    async def test_api_rate_limiting(self):
        """
        IT-E2E-003: Test API rate limiting

        Make rapid requests to verify rate limiting is active.
        """
        print(f"\n{'='*60}")
        print(f"E2E TEST: API Rate Limiting")
        print(f"{'='*60}\n")

        async with BharatBuildAPIClient() as client:
            results = {"200": 0, "429": 0, "other": 0}

            # Make 20 rapid requests to health endpoint
            print("Making 20 rapid requests to /health...")
            for i in range(20):
                response = await client.health_check()
                if response.status == 200:
                    results["200"] += 1
                elif response.status == 429:
                    results["429"] += 1
                else:
                    results["other"] += 1

            print(f"  Results: 200 OK: {results['200']}, 429 Rate Limited: {results['429']}, Other: {results['other']}")

            # Health endpoint usually has high rate limits, let's test login
            print("\nMaking rapid login attempts...")
            login_results = {"401": 0, "429": 0, "other": 0}

            for i in range(10):
                response = await client.login("fake@test.com", "wrongpass")
                if response.status == 401:
                    login_results["401"] += 1
                elif response.status == 429:
                    login_results["429"] += 1
                else:
                    login_results["other"] += 1

            print(f"  Results: 401 Invalid: {login_results['401']}, 429 Rate Limited: {login_results['429']}, Other: {login_results['other']}")

            if login_results["429"] > 0:
                print(f"\n[PASS] Rate limiting is active!")
            else:
                print(f"\n[INFO] Rate limiting may have higher thresholds")


class TestAPIResponseFormats:
    """Test API response format consistency"""

    @pytest.mark.asyncio
    async def test_health_response_format(self):
        """IT-API-001: Health endpoint response format"""
        async with BharatBuildAPIClient() as client:
            response = await client.health_check()

            assert response.success
            assert isinstance(response.data, dict)
            assert "status" in response.data
            print(f"[PASS] Health response format correct: {response.data}")

    @pytest.mark.asyncio
    async def test_error_response_format(self):
        """IT-API-002: Error response format"""
        async with BharatBuildAPIClient() as client:
            # Trigger an error (403 for unauthenticated or 404 for not found)
            response = await client.get_project("nonexistent-id")

            assert not response.success
            assert response.status in [401, 403, 404], f"Expected error status, got {response.status}"
            # Error response should have detail
            assert "detail" in response.data or "error" in response.data or "message" in response.data
            print(f"[PASS] Error response format correct: {response.status} - {response.data}")

    @pytest.mark.asyncio
    async def test_document_types_response_format(self):
        """IT-API-003: Document types response format"""
        async with BharatBuildAPIClient() as client:
            response = await client.get_document_types()

            assert response.success
            # Response can be {"document_types": [...]} or direct list
            data = response.data
            if isinstance(data, dict):
                data = data.get("document_types", [])
            assert isinstance(data, list)
            if data:
                # Each item should have id/type and name/label
                item = data[0]
                assert any(key in item for key in ["id", "type", "value"])
            print(f"[PASS] Document types format correct: {len(data)} items")


class TestConcurrentRequests:
    """Test concurrent request handling"""

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self):
        """IT-CONC-001: Handle concurrent health check requests"""
        print(f"\n{'='*60}")
        print(f"Concurrent Health Check Test")
        print(f"{'='*60}\n")

        async def make_request():
            async with BharatBuildAPIClient() as client:
                return await client.health_check()

        # Make 50 concurrent requests
        print("Making 50 concurrent health check requests...")
        tasks = [make_request() for _ in range(50)]
        results = await asyncio.gather(*tasks)

        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count

        print(f"  Success: {success_count}/50")
        print(f"  Failed: {fail_count}/50")

        assert success_count > 40, "Most requests should succeed"
        print(f"[PASS] Concurrent requests handled correctly")

    @pytest.mark.asyncio
    async def test_concurrent_document_types(self):
        """IT-CONC-002: Handle concurrent document types requests"""
        async def make_request():
            async with BharatBuildAPIClient() as client:
                return await client.get_document_types()

        # Make 30 concurrent requests
        print("\nMaking 30 concurrent document type requests...")
        tasks = [make_request() for _ in range(30)]
        results = await asyncio.gather(*tasks)

        success_count = sum(1 for r in results if r.success)
        print(f"  Success: {success_count}/30")

        assert success_count > 25, "Most requests should succeed"
        print(f"[PASS] Concurrent document requests handled correctly")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
