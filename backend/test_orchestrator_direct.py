"""
Direct test of Dynamic Orchestrator without FastAPI/Database dependencies
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


async def test_orchestrator_workflow():
    """Test the orchestrator workflow execution"""
    print("=" * 60)
    print("🧪 TESTING DYNAMIC ORCHESTRATOR")
    print("=" * 60)
    print()

    # Initialize orchestrator
    print("1️⃣  Initializing Dynamic Orchestrator...")
    try:
        orchestrator = DynamicOrchestrator()
        print("✅ Orchestrator initialized successfully")
        print(f"   - Agents loaded: {len(orchestrator.agent_registry.list_agents())}")
        print(f"   - Workflows loaded: {len(orchestrator.workflow_engine.list_workflows())}")
    except Exception as e:
        print(f"❌ Failed to initialize orchestrator: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    print("2️⃣  Testing workflow execution...")
    print()

    # Test request
    user_request = "Build a simple todo app with React and TypeScript"
    project_id = "test-project-001"

    event_count = 0
    events_by_type = {}

    try:
        async for event in orchestrator.execute_workflow(
            user_request=user_request,
            project_id=project_id,
            workflow_name="bolt_standard"
        ):
            event_count += 1
            event_type = event.type

            # Track events by type
            if event_type not in events_by_type:
                events_by_type[event_type] = 0
            events_by_type[event_type] += 1

            # Print event
            print(f"📡 Event {event_count}: {event_type}")
            if event.message:
                print(f"   Message: {event.message}")
            if event.data:
                print(f"   Data: {str(event.data)[:100]}...")
            if event.agent:
                print(f"   Agent: {event.agent}")
            print()

            # Stop after a reasonable number of events for testing
            if event_count >= 50:
                print("⚠️  Stopping after 50 events (test limit)")
                break

    except Exception as e:
        print(f"❌ Workflow execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    print("=" * 60)
    print("✅ TEST RESULTS")
    print("=" * 60)
    print(f"Total events received: {event_count}")
    print()
    print("Events by type:")
    for event_type, count in sorted(events_by_type.items()):
        print(f"  - {event_type}: {count}")
    print()

    # Check for key event types
    required_events = [EventType.STATUS, EventType.AGENT_START]
    missing_events = [e for e in required_events if e not in events_by_type]

    if missing_events:
        print(f"⚠️  Missing expected events: {missing_events}")
        return False
    else:
        print("✅ All core event types present")
        return True


async def test_agent_registry():
    """Test agent registry"""
    print()
    print("=" * 60)
    print("🧪 TESTING AGENT REGISTRY")
    print("=" * 60)
    print()

    try:
        orchestrator = DynamicOrchestrator()
        agents = orchestrator.agent_registry.list_agents()

        print(f"Loaded {len(agents)} agents:")
        for agent_type, config in agents.items():
            print(f"  ✅ {agent_type.value}")
            print(f"     Name: {config.name}")
            print(f"     Model: {config.model}")
            print(f"     Enabled: {config.enabled}")
            print(f"     Capabilities: {config.capabilities}")
            print()

        return True
    except Exception as e:
        print(f"❌ Agent registry test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_workflow_list():
    """Test workflow listing"""
    print()
    print("=" * 60)
    print("🧪 TESTING WORKFLOW ENGINE")
    print("=" * 60)
    print()

    try:
        orchestrator = DynamicOrchestrator()
        workflows = orchestrator.workflow_engine.list_workflows()

        print(f"Loaded {len(workflows)} workflows:")
        for workflow_name, steps in workflows.items():
            print(f"  ✅ {workflow_name}")
            print(f"     Steps: {len(steps)}")
            for i, step in enumerate(steps, 1):
                condition_text = " (conditional)" if step.condition else ""
                print(f"       {i}. {step.name} [{step.agent_type.value}]{condition_text}")
            print()

        return True
    except Exception as e:
        print(f"❌ Workflow engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" * 2)
    print("🚀 DYNAMIC ORCHESTRATOR END-TO-END TEST")
    print("=" * 60)
    print()

    results = []

    # Test 1: Agent Registry
    results.append(("Agent Registry", await test_agent_registry()))

    # Test 2: Workflow Engine
    results.append(("Workflow Engine", await test_workflow_list()))

    # Test 3: Workflow Execution (THIS IS THE MAIN TEST)
    print("\n⚠️  WARNING: Workflow execution test requires valid ANTHROPIC_API_KEY")
    print("    Set it in backend/.env file before running this test")
    print()

    response = input("Do you want to run the workflow execution test? (y/n): ").strip().lower()

    if response == 'y':
        results.append(("Workflow Execution", await test_orchestrator_workflow()))
    else:
        print("⏭️  Skipping workflow execution test")
        results.append(("Workflow Execution", None))

    # Print final summary
    print()
    print("=" * 60)
    print("📊 FINAL TEST SUMMARY")
    print("=" * 60)
    print()

    for test_name, result in results:
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⏭️  SKIPPED"

        print(f"{status}  {test_name}")

    print()
    print("=" * 60)

    # Overall result
    failed_tests = [name for name, result in results if result is False]
    if failed_tests:
        print(f"❌ {len(failed_tests)} test(s) failed: {', '.join(failed_tests)}")
        return False
    else:
        passed_count = sum(1 for _, result in results if result is True)
        print(f"✅ All tests passed ({passed_count}/{len(results)})")
        return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
