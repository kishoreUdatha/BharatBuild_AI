"""
Quick test for Docker Sandbox - Layer 1
"""
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.services.docker_sandbox import docker_sandbox, ProjectType, detect_project_type

async def test_sandbox():
    print("=" * 60)
    print("TESTING DOCKER SANDBOX (Layer 1)")
    print("=" * 60)

    # Test 1: Check Docker connection
    print("\n1. Testing Docker connection...")
    try:
        client = docker_sandbox._get_client()
        print(f"   [OK] Docker connected: {client.version()['Version']}")
    except Exception as e:
        print(f"   [FAIL] Docker error: {e}")
        return

    # Test 2: Create a sandbox
    print("\n2. Creating sandbox...")
    try:
        sandbox = await docker_sandbox.create_sandbox(
            project_id="test-sandbox-001",
            user_id="test-user",
            project_type=ProjectType.NODEJS
        )
        print(f"   [OK] Sandbox created!")
        print(f"      ID: {sandbox.sandbox_id}")
        print(f"      Container: {sandbox.container_id[:12]}")
        print(f"      Status: {sandbox.status.value}")
        print(f"      Preview URL: {sandbox.preview_url}")
        print(f"      Port: {sandbox.external_port}")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return

    # Test 3: Write a file
    print("\n3. Writing file to sandbox...")
    try:
        success = await docker_sandbox.write_file(
            sandbox.sandbox_id,
            "/app/index.js",
            'console.log("Hello from BharatBuild Sandbox!");'
        )
        print(f"   [OK] File written: {success}")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")

    # Test 4: Execute command
    print("\n4. Executing command...")
    try:
        result = await docker_sandbox.execute_command(
            sandbox.sandbox_id,
            ["node", "-e", "console.log('Node.js works!')"]
        )
        print(f"   [OK] Command executed!")
        print(f"      Exit code: {result.get('exit_code')}")
        print(f"      Output: {result.get('stdout', '').strip()}")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")

    # Test 5: Get logs
    print("\n5. Getting container logs...")
    try:
        logs = await docker_sandbox.get_logs(sandbox.sandbox_id, tail=5)
        print(f"   [OK] Logs retrieved: {len(logs)} lines")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")

    # Test 6: Get stats
    print("\n6. Getting sandbox stats...")
    try:
        stats = await docker_sandbox.get_stats()
        print(f"   [OK] Stats:")
        print(f"      Running: {stats['running']}")
        print(f"      Max concurrent: {stats['max_concurrent']}")
        print(f"      Available ports: {stats['available_ports']}")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")

    # Test 7: Stop sandbox
    print("\n7. Stopping sandbox...")
    try:
        success = await docker_sandbox.stop_sandbox(sandbox.sandbox_id)
        print(f"   [OK] Sandbox stopped: {success}")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")

    # Test 8: Auto-detect project type
    print("\n8. Testing auto-detection...")
    files = ["package.json", "next.config.js", "src/App.tsx"]
    detected = detect_project_type(files)
    print(f"   Files: {files}")
    print(f"   [OK] Detected: {detected.value}")

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_sandbox())
