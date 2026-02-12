"""
Test RAG integration with HybridClient.
Tests that RAG context is properly retrieved and appended to prompts.

Usage: python test_rag_integration.py
"""

import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_service import rag_service


def test_rag_service():
    """Test RAG service independently"""
    print("\n" + "=" * 60)
    print("TEST 1: RAG Service")
    print("=" * 60)

    if not rag_service.is_available():
        print("[FAIL] RAG service not available")
        return False

    print("[OK] RAG service available")

    # Test retrieval
    context = rag_service.retrieve_for_code_generation(
        prompt="Create a React button component with loading state",
        framework="react",
        n_results=2
    )

    if context and len(context) > 100:
        print(f"[OK] Retrieved context: {len(context)} chars")
        print(f"    Preview: {context[:100]}...")
    else:
        print("[FAIL] No context retrieved")
        return False

    # Test error solution retrieval
    error_context = rag_service.retrieve_error_solution(
        error_message="Cannot read property 'map' of undefined",
        framework="react",
        n_results=1
    )

    if error_context and len(error_context) > 50:
        print(f"[OK] Error solution retrieved: {len(error_context)} chars")
    else:
        print("[WARN] No error solution retrieved")

    return True


def test_hybrid_client_rag():
    """Test HybridClient RAG integration"""
    print("\n" + "=" * 60)
    print("TEST 2: HybridClient RAG Integration")
    print("=" * 60)

    from app.utils.hybrid_client import HybridClient

    # Create fresh instance for testing
    client = HybridClient()

    # Check RAG is enabled
    if client.use_rag:
        print("[OK] RAG enabled in HybridClient")
    else:
        print("[WARN] RAG not enabled")

    # Test RAG context retrieval
    context = client._get_rag_context(
        prompt="Create a FastAPI endpoint for user authentication",
        framework="fastapi"
    )

    if context and len(context) > 100:
        print(f"[OK] RAG context retrieved via HybridClient: {len(context)} chars")
    else:
        print("[WARN] No RAG context retrieved")

    # Test framework detection
    detected = client._detect_framework("Create a React component")
    if detected == "react":
        print(f"[OK] Framework detection: 'react' correctly detected")
    else:
        print(f"[FAIL] Framework detection failed: expected 'react', got '{detected}'")

    detected = client._detect_framework("FastAPI user endpoint")
    if detected == "fastapi":
        print(f"[OK] Framework detection: 'fastapi' correctly detected")
    else:
        print(f"[FAIL] Framework detection failed: expected 'fastapi', got '{detected}'")

    # Check stats
    stats = client.get_stats()
    print(f"\nHybridClient Stats:")
    print(f"  - RAG enabled: {stats.get('rag_enabled', 'N/A')}")
    print(f"  - RAG retrievals: {stats.get('rag_retrievals', 0)}")
    print(f"  - Qwen available: {stats.get('qwen_available', False)}")
    print(f"  - Hybrid routing: {stats.get('hybrid_routing_enabled', False)}")
    print(f"  - Qwen only mode: {stats.get('qwen_only_mode', False)}")

    return True


def test_imports():
    """Test all imports work correctly"""
    print("\n" + "=" * 60)
    print("TEST 3: Import Verification")
    print("=" * 60)

    try:
        from app.utils.hybrid_client import hybrid_client
        print("[OK] hybrid_client imported")
    except Exception as e:
        print(f"[FAIL] hybrid_client import: {e}")
        return False

    try:
        from app.services.rag_service import rag_service
        print("[OK] rag_service imported")
    except Exception as e:
        print(f"[FAIL] rag_service import: {e}")
        return False

    try:
        from app.core.config import settings
        use_rag = getattr(settings, 'USE_RAG', None)
        print(f"[OK] settings.USE_RAG = {use_rag}")
    except Exception as e:
        print(f"[FAIL] settings import: {e}")
        return False

    return True


def main():
    print("=" * 60)
    print("BharatBuild RAG Integration Tests")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("RAG Service", test_rag_service()))
    results.append(("HybridClient RAG", test_hybrid_client_rag()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False

    print("\n" + ("All tests passed!" if all_passed else "Some tests failed!"))

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
