"""
Quick test: Can BharatBuild generate a project?
Tests the full pipeline: Claude API → PlannerAgent → Plan output
"""
import sys, os, asyncio
os.chdir('D:/Smartgrow Projects/BharatBuild_AI/backend')
sys.path.insert(0, '.')

# Force load correct .env file
from dotenv import load_dotenv
load_dotenv('D:/Smartgrow Projects/BharatBuild_AI/backend/.env', override=True)

async def main():
    print("=" * 60)
    print("  BharatBuild AI — Full Generation Test")
    print("=" * 60)
    
    # Step 1: Test Claude API connection
    print("\n[Step 1] Testing Claude API connection...")
    try:
        from app.utils.claude_client import claude_client
        response = await claude_client.generate(
            prompt="Say hello in exactly one word.",
            system_prompt="Reply with exactly one word.",
            model="haiku",
            max_tokens=10
        )
        print(f"  Claude says: {response['content']}")
        print(f"  Tokens used: {response['total_tokens']}")
        print(f"  Model: {response['model']}")
        print("  [PASS] Claude API working!")
    except Exception as e:
        print(f"  [FAIL] Claude API error: {e}")
        print("\n  Make sure ANTHROPIC_API_KEY is set in .env and USE_MOCK_CLAUDE=false")
        return

    # Step 2: Test PlannerAgent
    print("\n[Step 2] Testing PlannerAgent (generating a plan)...")
    try:
        from app.modules.agents.planner_agent import PlannerAgent
        from app.modules.agents.base_agent import AgentContext

        planner = PlannerAgent()
        context = AgentContext(
            user_request="Build a simple counter app with React and Tailwind CSS",
            project_id="test-project-001",
        )

        result = await planner.process(context)
        
        if result.get("success"):
            plan = result.get("plan", {})
            files = plan.get("files", [])
            print(f"  Project name: {plan.get('project_name', 'N/A')}")
            print(f"  Tech stack: {plan.get('tech_stack', 'N/A')}")
            print(f"  Files planned: {len(files)}")
            if files:
                print(f"  First 5 files:")
                for f in files[:5]:
                    path = f.get('path', 'unknown') if isinstance(f, dict) else str(f)
                    print(f"    - {path}")
            print(f"  Token usage: {planner.get_token_usage()}")
            print("  [PASS] PlannerAgent working!")
        else:
            print(f"  [FAIL] Plan failed: {result.get('error', 'Unknown')}")
            # Show raw response for debugging
            raw = result.get("raw_response", "")
            if raw:
                print(f"  Raw response (first 500 chars):\n  {raw[:500]}")
    except Exception as e:
        print(f"  [FAIL] PlannerAgent error: {e}")
        import traceback
        traceback.print_exc()

    # Step 3: Test Prompt Classifier
    print("\n[Step 3] Testing PromptClassifier...")
    try:
        from app.modules.agents.prompt_classifier_agent import prompt_classifier_agent

        result = await prompt_classifier_agent.classify(
            prompt="Build a todo app with React",
            has_existing_project=False
        )
        print(f"  Intent: {result.get('intent')}")
        print(f"  Confidence: {result.get('confidence')}")
        print(f"  Workflow: {result.get('suggestedWorkflow')}")
        print("  [PASS] Classifier working!")
    except Exception as e:
        print(f"  [FAIL] Classifier error: {e}")

    print("\n" + "=" * 60)
    print("  TEST COMPLETE")
    print("=" * 60)

asyncio.run(main())
