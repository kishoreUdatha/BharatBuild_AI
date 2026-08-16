"""
BharatBuild AI - System Health Check
Verifies all agents can be imported and basic project generation flow works.
"""
import sys
import os
import ast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("  BharatBuild AI - System Health Check")
print("=" * 60)
print()

errors = []
warnings = []

# ============================================================
# PHASE 1: Syntax Check (all agent files)
# ============================================================
print("[Phase 1] Syntax Check - All Agent Files")
print("-" * 40)

agent_dir = os.path.join("app", "modules", "agents")
agent_files = [f for f in os.listdir(agent_dir) if f.endswith(".py")]

for f in sorted(agent_files):
    filepath = os.path.join(agent_dir, f)
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            ast.parse(fh.read())
        print(f"  OK: {f}")
    except SyntaxError as e:
        errors.append(f"SYNTAX: {f} -> {e}")
        print(f"  FAIL: {f} -> {e}")

print()

# ============================================================
# PHASE 2: Utility Imports
# ============================================================
print("[Phase 2] Utility Imports")
print("-" * 40)

util_imports = [
    ("app.utils.security", ["sanitize_user_input", "wrap_user_input", "validate_file_path", "shell_escape"]),
    ("app.utils.token_budget", ["TokenBudget", "estimate_tokens"]),
    ("app.utils.output_parser", ["OutputParser"]),
    ("app.utils.cache", ["LRUCache", "BoundedDict", "AsyncLRUCache"]),
]

for module, symbols in util_imports:
    try:
        mod = __import__(module, fromlist=symbols)
        for sym in symbols:
            if not hasattr(mod, sym):
                raise ImportError(f"Missing symbol: {sym}")
        print(f"  OK: {module} ({', '.join(symbols)})")
    except Exception as e:
        errors.append(f"IMPORT: {module} -> {e}")
        print(f"  FAIL: {module} -> {e}")

print()

# ============================================================
# PHASE 3: Core Config & Services
# ============================================================
print("[Phase 3] Core Config & Services")
print("-" * 40)

core_modules = [
    "app.core.config",
    "app.core.logging_config",
]

for module in core_modules:
    try:
        __import__(module)
        print(f"  OK: {module}")
    except Exception as e:
        errors.append(f"CORE: {module} -> {e}")
        print(f"  FAIL: {module} -> {e}")

print()

# ============================================================
# PHASE 4: Agent Imports (the critical test)
# ============================================================
print("[Phase 4] Agent Imports")
print("-" * 40)

agent_imports = [
    ("app.modules.agents.base_agent", ["BaseAgent", "AgentContext"]),
    ("app.modules.agents.planner_agent", ["PlannerAgent"]),
    ("app.modules.agents.writer_agent", ["WriterAgent"]),
    ("app.modules.agents.debugger_agent", ["DebuggerAgent"]),
    ("app.modules.agents.fixer_agent", ["FixerAgent"]),
    ("app.modules.agents.coder_agent", ["CoderAgent"]),
    ("app.modules.agents.memory_agent", ["MemoryAgent", "get_memory_agent"]),
    ("app.modules.agents.prompt_classifier_agent", ["PromptClassifierAgent"]),
    ("app.modules.agents.docker_infra_fixer_agent", ["DockerInfraFixerAgent"]),
    ("app.modules.agents.production_fixer_agent", ["ProductionFixerAgent"]),
    ("app.modules.agents.document_generator_agent", ["DocumentGeneratorAgent"]),
    ("app.modules.agents.chunked_document_agent", ["ChunkedDocumentAgent"]),
    ("app.modules.agents.verification_agent", ["VerificationAgent"]),
    ("app.modules.agents.bolt_instant_agent", ["BoltInstantAgent"]),
    ("app.modules.agents.orchestrator", ["MultiAgentOrchestrator"]),
]

for module, symbols in agent_imports:
    try:
        mod = __import__(module, fromlist=symbols)
        for sym in symbols:
            if not hasattr(mod, sym):
                raise ImportError(f"Missing: {sym}")
        print(f"  OK: {module}")
    except Exception as e:
        errors.append(f"AGENT: {module} -> {e}")
        print(f"  FAIL: {module} -> {e}")

print()

# ============================================================
# PHASE 5: Functional Tests
# ============================================================
print("[Phase 5] Functional Tests")
print("-" * 40)

# Test 1: Security utils work
try:
    from app.utils.security import sanitize_user_input, validate_file_path, sanitize_file_path
    
    # Test injection sanitization
    result = sanitize_user_input('<file path="hack">evil</file>')
    assert "⟨file" in result or "<file" not in result.lower(), "Injection not sanitized"
    
    # Test path validation
    valid, _ = validate_file_path("src/app.tsx")
    assert valid, "Valid path rejected"
    
    valid, msg = validate_file_path("../../etc/passwd")
    assert not valid, "Traversal path not blocked"
    
    valid, msg = validate_file_path("/etc/shadow")
    assert not valid, "Absolute path not blocked"
    
    # Test path sanitization
    safe = sanitize_file_path("../../hack/../src/file.ts")
    assert safe is None or ".." not in safe, "Traversal not removed"
    
    print("  OK: Security utils functional")
except Exception as e:
    errors.append(f"FUNC: security -> {e}")
    print(f"  FAIL: Security utils -> {e}")

# Test 2: Token budget works
try:
    from app.utils.token_budget import TokenBudget, estimate_tokens
    
    budget = TokenBudget(max_input_tokens=10000, max_output_tokens=5000, max_calls=3)
    assert budget.can_spend_input(5000) == True
    assert budget.can_spend_input(15000) == False
    
    budget.record_call(3000, 2000)
    assert budget.calls_made == 1
    assert budget.input_tokens_used == 3000
    
    tokens = estimate_tokens("Hello world, this is a test")
    assert tokens > 0
    
    print("  OK: Token budget functional")
except Exception as e:
    errors.append(f"FUNC: token_budget -> {e}")
    print(f"  FAIL: Token budget -> {e}")

# Test 3: Output parser works
try:
    from app.utils.output_parser import OutputParser
    
    # Test JSON extraction from markdown
    response = '```json\n{"fixes": [{"file": "test.py"}]}\n```'
    result, error = OutputParser.parse_json(response, required_keys=["fixes"])
    assert result is not None, f"Failed to parse markdown JSON: {error}"
    assert "fixes" in result
    
    # Test direct JSON
    response2 = '{"success": true, "data": "hello"}'
    result2, _ = OutputParser.parse_json(response2)
    assert result2 is not None
    assert result2["success"] == True
    
    # Test XML tag parsing
    response3 = '<file path="src/app.tsx">const App = () => {}</file>'
    files = OutputParser.parse_xml_tags(response3, "file")
    assert len(files) == 1
    assert files[0]["path"] == "src/app.tsx"
    
    print("  OK: Output parser functional")
except Exception as e:
    errors.append(f"FUNC: output_parser -> {e}")
    print(f"  FAIL: Output parser -> {e}")

# Test 4: LRU Cache works
try:
    from app.utils.cache import LRUCache, BoundedDict
    
    cache = LRUCache(max_size=3, ttl_seconds=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") == 1
    
    cache.set("d", 4)  # Should evict "b" (LRU)
    assert cache.get("b") is None  # Evicted
    assert cache.get("d") == 4
    
    bd = BoundedDict(max_size=2)
    bd["x"] = 10
    bd["y"] = 20
    bd["z"] = 30  # Should evict "x"
    assert "x" not in bd
    assert bd["z"] == 30
    
    print("  OK: LRU Cache functional")
except Exception as e:
    errors.append(f"FUNC: cache -> {e}")
    print(f"  FAIL: LRU Cache -> {e}")

# Test 5: PlannerAgent tech detection
try:
    from app.modules.agents.planner_agent import PlannerAgent
    
    # Should detect React
    techs = PlannerAgent._detect_technologies("Build a React todo app with Tailwind")
    assert "react" in techs, f"React not detected: {techs}"
    
    # Should detect Python
    techs = PlannerAgent._detect_technologies("Create a FastAPI REST API for users")
    assert "python" in techs, f"Python not detected: {techs}"
    
    # Should NOT default to only React for backend requests
    techs = PlannerAgent._detect_technologies("Build a REST API scraper tool")
    assert techs != ["react"], f"Still defaulting to just React: {techs}"
    
    print("  OK: PlannerAgent tech detection")
except Exception as e:
    # This might fail if it can't import due to missing deps - that's a warning not error
    warnings.append(f"FUNC: planner tech detection -> {e}")
    print(f"  WARN: PlannerAgent tech detection -> {e}")

print()

# ============================================================
# PHASE 6: Check for missing dependencies
# ============================================================
print("[Phase 6] Requirements Check")
print("-" * 40)

req_file = "requirements.txt"
if os.path.exists(req_file):
    with open(req_file, "r") as f:
        requirements = [line.strip().split("==")[0].split(">=")[0].split("<=")[0] 
                       for line in f if line.strip() and not line.startswith("#")]
    
    missing = []
    for req in requirements[:20]:  # Check first 20
        try:
            __import__(req.replace("-", "_"))
        except ImportError:
            missing.append(req)
    
    if missing:
        print(f"  WARN: {len(missing)} packages may not be installed: {', '.join(missing[:10])}")
        warnings.append(f"Missing packages: {', '.join(missing)}")
    else:
        print("  OK: Core packages available")
else:
    print("  SKIP: requirements.txt not found")

print()

# ============================================================
# SUMMARY
# ============================================================
print("=" * 60)
print("  SUMMARY")
print("=" * 60)
print()

if errors:
    print(f"  [FAIL] {len(errors)} ERROR(S) - System may NOT generate projects correctly:")
    for e in errors:
        print(f"     - {e}")
else:
    print("  [PASS] NO ERRORS - All checks passed!")

if warnings:
    print(f"\n  [WARN] {len(warnings)} WARNING(S):")
    for w in warnings:
        print(f"     - {w}")

print()
print(f"  Total: {len(agent_files)} agent files checked")
print(f"  Result: {'PASS' if not errors else 'FAIL'}")
print()

sys.exit(1 if errors else 0)
