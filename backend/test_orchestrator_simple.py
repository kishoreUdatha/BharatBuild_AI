"""
Simple test of Dynamic Orchestrator (no emojis for Windows compatibility)
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.modules.orchestrator.dynamic_orchestrator import (
    DynamicOrchestrator,
    EventType
)


async def test_agent_registry():
    """Test agent registry"""
    print()
    print("=" * 60)
    print("TESTING AGENT REGISTRY")
    print("=" * 60)
    print()

    try:
        orchestrator = DynamicOrchestrator()
        agents = orchestrator.agent_registry.list_agents()

        print(f"Loaded {len(agents)} agents:")
        for agent_type, config in agents.items():
            print(f"  [OK] {agent_type.value}")
            print(f"       Name: {config.name}")
            print(f"       Model: {config.model}")
            print(f"       Enabled: {config.enabled}")
            print()

        return True
    except Exception as e:
        print(f"[FAIL] Agent registry test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_workflow_list():
    """Test workflow listing"""
    print()
    print("=" * 60)
    print("TESTING WORKFLOW ENGINE")
    print("=" * 60)
    print()

    try:
        orchestrator = DynamicOrchestrator()
        workflow_names = orchestrator.workflow_engine.list_workflows()

        print(f"Loaded {len(workflow_names)} workflows:")
        for workflow_name in workflow_names:
            print(f"  [OK] {workflow_name}")
            try:
                workflow_steps = orchestrator.workflow_engine.get_workflow(workflow_name)
                print(f"       Steps: {len(workflow_steps)}")
                for i, step in enumerate(workflow_steps, 1):
                    condition_text = " (conditional)" if step.condition else ""
                    print(f"         {i}. {step.name} [{step.agent_type.value}]{condition_text}")
            except Exception as e:
                print(f"       [WARN] Could not get workflow details: {e}")
            print()

        # Check bolt_standard workflow
        if "bolt_standard" in workflow_names:
            bolt_steps = orchestrator.workflow_engine.get_workflow("bolt_standard")
            print(f"  bolt_standard workflow has {len(bolt_steps)} steps")

            # Verify key steps exist
            step_names = [s.name for s in bolt_steps]
            required_steps = ["Create Plan", "Generate Code"]
            missing = [s for s in required_steps if s not in step_names]

            if missing:
                print(f"  [WARN] Missing required steps: {missing}")
            else:
                print(f"  [OK] All required steps present")

        return True
    except Exception as e:
        print(f"[FAIL] Workflow engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_yaml_config():
    """Test YAML configuration loading"""
    print()
    print("=" * 60)
    print("TESTING YAML CONFIGURATION")
    print("=" * 60)
    print()

    try:
        from app.config.config_loader import get_config_loader

        config_loader = get_config_loader()
        print("[OK] ConfigLoader initialized")

        # Test loading agents
        agents = config_loader.load_agents()
        print(f"[OK] Loaded {len(agents)} agents from YAML")

        # Test loading workflows
        workflows = config_loader.load_workflows()
        print(f"[OK] Loaded {len(workflows)} workflows from YAML")

        return True
    except Exception as e:
        print(f"[FAIL] YAML config test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" * 2)
    print("=" * 60)
    print("DYNAMIC ORCHESTRATOR INTEGRATION TEST")
    print("=" * 60)
    print()

    results = []

    # Test 1: YAML Configuration
    results.append(("YAML Configuration", await test_yaml_config()))

    # Test 2: Agent Registry
    results.append(("Agent Registry", await test_agent_registry()))

    # Test 3: Workflow Engine
    results.append(("Workflow Engine", await test_workflow_list()))

    # Print final summary
    print()
    print("=" * 60)
    print("FINAL TEST SUMMARY")
    print("=" * 60)
    print()

    for test_name, result in results:
        if result is True:
            status = "[PASS]"
        elif result is False:
            status = "[FAIL]"
        else:
            status = "[SKIP]"

        print(f"{status}  {test_name}")

    print()
    print("=" * 60)

    # Overall result
    failed_tests = [name for name, result in results if result is False]
    if failed_tests:
        print(f"[FAIL] {len(failed_tests)} test(s) failed: {', '.join(failed_tests)}")
        return False
    else:
        passed_count = sum(1 for _, result in results if result is True)
        print(f"[PASS] All tests passed ({passed_count}/{len(results)})")
        print()
        print("INTEGRATION STATUS: READY")
        print()
        print("Next steps:")
        print("  1. Ensure PostgreSQL database is running")
        print("  2. Set ANTHROPIC_API_KEY in .env file")
        print("  3. Start backend: uvicorn app.main:app --reload")
        print("  4. Start frontend: npm run dev")
        print("  5. Test at: http://localhost:3000/bolt")
        return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
