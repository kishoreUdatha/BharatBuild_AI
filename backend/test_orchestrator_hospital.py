"""
Test Dynamic Orchestrator - Hospital Management System
This tests the ACTUAL production pipeline.
"""
import asyncio
import os
from pathlib import Path

# Load API key
api_key = os.environ.get("ANTHROPIC_API_KEY")
for env_file in [".env.test", ".env"]:
    if api_key:
        break
    env_path = Path(__file__).parent / env_file
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").split("\n"):
            if line.startswith("ANTHROPIC_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                os.environ["ANTHROPIC_API_KEY"] = api_key
                break

if not api_key:
    print("[ERROR] ANTHROPIC_API_KEY not found")
    exit(1)

# Now import after setting up env
import sys
sys.path.insert(0, str(Path(__file__).parent))

async def test_orchestrator():
    """Test the actual Dynamic Orchestrator pipeline."""
    print("=" * 70)
    print("DYNAMIC ORCHESTRATOR TEST - Hospital Management")
    print("=" * 70)

    try:
        from app.modules.orchestrator.dynamic_orchestrator import DynamicOrchestrator
        print("[OK] Imported DynamicOrchestrator")
    except ImportError as e:
        print(f"[ERROR] Cannot import orchestrator: {e}")
        print("\nThis test requires all dependencies. Run:")
        print("  pip install -r requirements.txt")
        return

    # Create orchestrator
    orchestrator = DynamicOrchestrator()

    user_request = """Create a Hospital Management System with Spring Boot backend:
- Patient entity: name, email, phone, dateOfBirth, gender (MALE/FEMALE/OTHER), bloodGroup, address
- Doctor entity: name, email, specialization, qualification, experienceYears, consultationFee
- Appointment entity: patient (relationship), doctor (relationship), appointmentDate, status (SCHEDULED/COMPLETED/CANCELLED), notes
- Department entity: name, description

NO authentication/security required. Use PostgreSQL."""

    project_id = "test-hospital-001"
    metadata = {"user_role": "student", "user_id": "test-user"}

    print(f"\n[Request] Hospital Management System (4 entities)")
    print(f"[...] Running orchestrator pipeline...")

    entity_specs_found = False
    files_generated = 0
    plan_files_count = 0
    errors_count = 0

    # Run the orchestrator
    try:
        async for event in orchestrator.execute_workflow(
            user_request=user_request,
            project_id=project_id,
            workflow_name="bolt_standard",
            metadata=metadata
        ):
            event_type = getattr(event, 'type', str(type(event)))

            # Track different event types
            if event_type == 'workflow_started':
                print(f"[OK] Workflow started")

            elif event_type == 'step_started':
                step_name = getattr(event, 'step_name', 'unknown')
                print(f"[...] Step: {step_name}")

            elif event_type == 'plan_complete' or 'plan' in str(event_type).lower():
                # Check if entity_specs was extracted
                if hasattr(orchestrator, '_context') and orchestrator._context:
                    ctx = orchestrator._context
                    if hasattr(ctx, 'plan') and ctx.plan:
                        plan_files_count = len(ctx.plan.get('files', []))
                        if ctx.plan.get('entity_specs'):
                            entity_specs_found = True
                            print(f"[OK] entity_specs extracted: {len(ctx.plan['entity_specs'])} chars")
                        else:
                            print(f"[WARN] entity_specs NOT found in plan!")
                        print(f"[OK] Plan complete - {plan_files_count} files planned")

            elif event_type == 'file_generated' or event_type == 'file_complete':
                files_generated += 1
                file_path = getattr(event, 'file_path', getattr(event, 'path', 'unknown'))
                print(f"  [{files_generated}] {file_path.split('/')[-1] if '/' in str(file_path) else file_path}")

            elif event_type == 'compilation_error' or 'error' in str(event_type).lower():
                errors_count += 1
                error_msg = getattr(event, 'message', str(event))
                if errors_count <= 5:
                    print(f"  [ERROR] {error_msg[:100]}")

            elif event_type == 'workflow_complete':
                print(f"\n[OK] Workflow complete")

    except Exception as e:
        print(f"[ERROR] Orchestrator failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"  entity_specs extracted: {'YES' if entity_specs_found else 'NO'}")
    print(f"  Files planned: {plan_files_count}")
    print(f"  Files generated: {files_generated}")
    print(f"  Compilation errors: {errors_count}")

    if entity_specs_found and errors_count == 0:
        print("\n[SUCCESS] Orchestrator test PASSED!")
    elif entity_specs_found and errors_count > 0:
        print(f"\n[PARTIAL] entity_specs works but {errors_count} compilation errors")
    else:
        print("\n[FAIL] entity_specs NOT extracted - fix not working!")

if __name__ == "__main__":
    asyncio.run(test_orchestrator())
