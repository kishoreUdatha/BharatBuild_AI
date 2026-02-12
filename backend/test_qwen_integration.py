#!/usr/bin/env python3
"""
Test script for Qwen model integration

Run this after training completes to verify the local model works:
    python test_qwen_integration.py

Prerequisites:
1. Train the model using RunPod (see backend/finetuning/runpod_package/)
2. Download trained model to ./finetuned_models/qwen-coder-7b/final/
3. Set USE_LOCAL_QWEN=True in .env
"""
import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_qwen_client():
    """Test the Qwen client directly"""
    print("\n" + "="*60)
    print("Testing Qwen Client")
    print("="*60)

    try:
        from app.utils.qwen_client import qwen_client

        # Check availability
        print(f"\n1. Checking availability...")
        available = qwen_client.is_available()
        print(f"   Available: {available}")
        print(f"   Device: {qwen_client.device}")
        print(f"   Model loaded: {qwen_client._model_loaded}")

        if not available:
            print("\n   [SKIP] Qwen not available, skipping generation test")
            return False

        # Test generation
        print(f"\n2. Testing generation...")
        result = await qwen_client.generate(
            prompt="Create a simple React button component that says 'Click Me'",
            system_prompt="You are a code generator. Generate clean, working code.",
            max_tokens=500,
            temperature=0.7
        )

        print(f"   Input tokens: {result.get('input_tokens', 'N/A')}")
        print(f"   Output tokens: {result.get('output_tokens', 'N/A')}")
        print(f"   Model: {result.get('model', 'N/A')}")
        print(f"\n   Generated code:")
        print("-"*40)
        content = result.get('content', '')
        print(content[:500] + "..." if len(content) > 500 else content)
        print("-"*40)

        # Test cost calculation
        print(f"\n3. Cost calculation...")
        cost = qwen_client.calculate_cost(100, 200)
        print(f"   Cost for 100 input + 200 output tokens: ${cost:.4f}")
        print(f"   (Local model is FREE!)")

        print("\n[SUCCESS] Qwen client working correctly!")
        return True

    except ImportError as e:
        print(f"\n[ERROR] Import error: {e}")
        print("Install required packages: pip install torch transformers peft bitsandbytes")
        return False
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_hybrid_client():
    """Test the hybrid client routing"""
    print("\n" + "="*60)
    print("Testing Hybrid Client")
    print("="*60)

    try:
        from app.utils.hybrid_client import hybrid_client
        from app.core.config import settings

        print(f"\n1. Configuration:")
        print(f"   USE_LOCAL_QWEN: {settings.USE_LOCAL_QWEN}")
        print(f"   HYBRID_ROUTING_ENABLED: {settings.HYBRID_ROUTING_ENABLED}")

        # Test routing decision
        print(f"\n2. Testing routing decisions:")

        test_prompts = [
            ("Create a simple button component", "Simple task - should route to Qwen"),
            ("Design the microservice architecture for a banking system", "Complex task - should route to Claude"),
            ("Create a login form with email and password inputs", "Simple task - should route to Qwen"),
            ("Analyze and optimize this React app's performance", "Complex task - should route to Claude"),
        ]

        for prompt, description in test_prompts:
            backend = hybrid_client._select_backend(prompt)
            print(f"   - '{prompt[:50]}...'")
            print(f"     {description}")
            print(f"     -> Routes to: {backend}")
            print()

        # Get stats
        print(f"\n3. Current stats:")
        stats = hybrid_client.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")

        print("\n[SUCCESS] Hybrid client working correctly!")
        return True

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_generation_with_hybrid():
    """Test actual generation through hybrid client"""
    print("\n" + "="*60)
    print("Testing Generation with Hybrid Client")
    print("="*60)

    try:
        from app.utils.hybrid_client import hybrid_client
        from app.core.config import settings

        if not settings.USE_LOCAL_QWEN and not settings.ANTHROPIC_API_KEY:
            print("\n[SKIP] No AI backend configured (no Qwen, no Claude API key)")
            return False

        # Simple task (should use Qwen if available)
        print("\n1. Simple task generation:")
        result = await hybrid_client.generate(
            prompt="Create a React card component with a title, description, and image",
            system_prompt="Generate clean React code",
            model="haiku",
            max_tokens=500
        )

        print(f"   Backend used: {result.get('backend', 'unknown')}")
        print(f"   Tokens: {result.get('input_tokens', 0)} in, {result.get('output_tokens', 0)} out")
        print(f"   Cost saved: ${result.get('cost_saved_usd', 0):.4f}")

        # Complex task (should use Claude)
        print("\n2. Complex task generation:")
        result = await hybrid_client.generate(
            prompt="Design a scalable microservice architecture for an e-commerce platform with user authentication, product catalog, cart, and payment processing. Include database design.",
            system_prompt="You are a software architect",
            model="haiku",
            max_tokens=500
        )

        print(f"   Backend used: {result.get('backend', 'unknown')}")
        print(f"   Tokens: {result.get('input_tokens', 0)} in, {result.get('output_tokens', 0)} out")
        print(f"   Cost saved: ${result.get('cost_saved_usd', 0):.4f}")

        # Final stats
        print("\n3. Final stats:")
        stats = hybrid_client.get_stats()
        print(f"   Total requests: {stats['total_requests']}")
        print(f"   Qwen requests: {stats['qwen_requests']} ({stats['qwen_percentage']}%)")
        print(f"   Claude requests: {stats['claude_requests']}")
        print(f"   Total cost saved: ${stats['total_cost_saved_usd']:.4f}")

        print("\n[SUCCESS] Hybrid generation working correctly!")
        return True

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n" + "="*60)
    print("BharatBuild AI - Qwen Integration Test")
    print("="*60)

    # Check environment
    from app.core.config import settings
    print(f"\nEnvironment: {settings.ENVIRONMENT}")
    print(f"USE_LOCAL_QWEN: {settings.USE_LOCAL_QWEN}")
    print(f"HYBRID_ROUTING_ENABLED: {settings.HYBRID_ROUTING_ENABLED}")
    print(f"QWEN_MODEL_PATH: {settings.QWEN_MODEL_PATH}")

    results = []

    # Run tests
    results.append(("Qwen Client", await test_qwen_client()))
    results.append(("Hybrid Client", await test_hybrid_client()))

    # Only test generation if at least one backend is available
    if settings.USE_LOCAL_QWEN or settings.ANTHROPIC_API_KEY:
        results.append(("Hybrid Generation", await test_generation_with_hybrid()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")

    all_passed = all(r[1] for r in results)
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
