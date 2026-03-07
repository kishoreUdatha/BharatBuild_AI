#!/usr/bin/env python3
"""
Anthropic-Style Training Pipeline for BharatBuild AI

What Anthropic does:
1. Single strong model (not per-stack adapters)
2. Instruction + Preference tuning (SFT + DPO)
3. Agent loop (read repo, edit, test, retry)
4. Smart prompting/routing (different system prompts per task)

This is simpler and more effective than per-stack LoRA adapters.
"""

import json
import re
import torch
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

SCRIPT_DIR = Path(__file__).parent

# ============================================================================
# TASK TYPES & SMART PROMPTING (Instead of per-stack adapters)
# ============================================================================

class TaskType(Enum):
    """Task types for smart routing."""
    API_IMPLEMENTATION = "api"
    BUG_FIX = "bug"
    ADD_TESTS = "test"
    REFACTOR = "refactor"
    SECURITY = "security"
    AI_ML = "aiml"
    FRONTEND = "frontend"
    DATABASE = "database"
    DEVOPS = "devops"
    GENERAL = "general"


# Task detection keywords
TASK_KEYWORDS = {
    TaskType.API_IMPLEMENTATION: ["api", "endpoint", "rest", "crud", "route", "controller"],
    TaskType.BUG_FIX: ["fix", "bug", "error", "issue", "broken", "crash", "fail"],
    TaskType.ADD_TESTS: ["test", "pytest", "unittest", "coverage", "spec"],
    TaskType.REFACTOR: ["refactor", "clean", "improve", "restructure", "solid"],
    TaskType.SECURITY: ["security", "auth", "jwt", "oauth", "password", "encrypt", "xss", "sql injection"],
    TaskType.AI_ML: ["pytorch", "tensorflow", "model", "train", "neural", "ml", "ai", "sklearn", "pandas"],
    TaskType.FRONTEND: ["react", "vue", "angular", "frontend", "component", "ui", "css"],
    TaskType.DATABASE: ["database", "sql", "query", "migration", "orm", "postgresql", "mongodb"],
    TaskType.DEVOPS: ["docker", "kubernetes", "deploy", "ci/cd", "pipeline", "nginx"],
}


def detect_task_type(prompt: str) -> TaskType:
    """Detect task type from prompt for smart routing."""
    prompt_lower = prompt.lower()

    scores = {task: 0 for task in TaskType}

    for task_type, keywords in TASK_KEYWORDS.items():
        for keyword in keywords:
            if keyword in prompt_lower:
                scores[task_type] += 1

    best_task = max(scores, key=scores.get)
    return best_task if scores[best_task] > 0 else TaskType.GENERAL


# ============================================================================
# SYSTEM PROMPTS (Smart routing instead of adapters)
# ============================================================================

BASE_SYSTEM_PROMPT = """You are an expert software engineer. Respond with this exact structure:

PLAN:
1) First step
2) Second step
...

FILES:
- path/to/file.py
...

PATCH:
*** Begin Patch
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -line,count +line,count @@
 context
-removed
+added
*** End Patch

COMMANDS:
- command to run
...

NOTES:
- Important notes
...

Use unified diff format. Be precise and production-ready."""


TASK_SPECIFIC_ADDITIONS = {
    TaskType.API_IMPLEMENTATION: """
Focus on:
- RESTful conventions
- Input validation with Pydantic
- Proper error handling (HTTPException)
- Pagination for list endpoints
- OpenAPI documentation""",

    TaskType.BUG_FIX: """
Focus on:
- Root cause analysis first
- Minimal change to fix the issue
- Add test to prevent regression
- Check for similar issues elsewhere""",

    TaskType.ADD_TESTS: """
Focus on:
- Arrange-Act-Assert pattern
- Test edge cases and error paths
- Use fixtures for setup
- Mock external dependencies
- Aim for high coverage of critical paths""",

    TaskType.REFACTOR: """
Focus on:
- SOLID principles
- Don't change external behavior
- Small, incremental changes
- Keep tests passing
- Improve readability""",

    TaskType.SECURITY: """
Focus on:
- OWASP Top 10 prevention
- Input validation and sanitization
- Secure password handling (bcrypt)
- JWT best practices
- No hardcoded secrets
- Parameterized queries (no SQL injection)""",

    TaskType.AI_ML: """
Focus on:
- Reproducibility (set seeds)
- Proper train/val/test splits
- Avoid data leakage
- Use appropriate metrics
- Save model checkpoints
- Log experiments properly""",

    TaskType.FRONTEND: """
Focus on:
- Component reusability
- Proper state management
- Accessibility (a11y)
- Responsive design
- Error boundaries""",

    TaskType.DATABASE: """
Focus on:
- Proper indexing
- N+1 query prevention
- Transaction handling
- Migration safety
- Connection pooling""",

    TaskType.DEVOPS: """
Focus on:
- Infrastructure as code
- Health checks
- Proper logging
- Secret management
- Graceful shutdown""",

    TaskType.GENERAL: ""
}


def get_system_prompt(task_type: TaskType) -> str:
    """Get task-specific system prompt."""
    addition = TASK_SPECIFIC_ADDITIONS.get(task_type, "")
    if addition:
        return BASE_SYSTEM_PROMPT + "\n" + addition
    return BASE_SYSTEM_PROMPT


# ============================================================================
# AGENT LOOP (The real power - not adapters)
# ============================================================================

@dataclass
class AgentResult:
    success: bool
    response: str
    attempts: int
    files_modified: List[str]
    tests_passed: bool
    errors: List[str]


class AnthropicStyleAgent:
    """
    Agent that mimics Claude Code's approach:
    1. Single model (no adapter switching)
    2. Smart prompting based on task
    3. Read repo context
    4. Generate → Apply → Test → Retry loop
    """

    def __init__(self, model_path: str = None, max_retries: int = 3):
        self.model_path = model_path
        self.max_retries = max_retries
        self.model = None
        self.tokenizer = None

    def load_model(self):
        """Load single fine-tuned model."""
        if self.model is not None:
            return

        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel

        base = "Qwen/Qwen2.5-Coder-7B-Instruct"

        self.model = AutoModelForCausalLM.from_pretrained(
            base,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
        )

        if self.model_path and Path(self.model_path).exists():
            self.model = PeftModel.from_pretrained(self.model, self.model_path)

        self.tokenizer = AutoTokenizer.from_pretrained(base, trust_remote_code=True)

    def read_repo_context(self, repo_path: str, relevant_files: List[str] = None) -> str:
        """Read repository context (like Claude Code does)."""
        context_parts = []
        repo = Path(repo_path)

        if not repo.exists():
            return ""

        # Read relevant files or auto-detect
        if relevant_files:
            files_to_read = [repo / f for f in relevant_files]
        else:
            # Auto-detect important files
            patterns = ["*.py", "*.ts", "*.js", "requirements.txt", "package.json"]
            files_to_read = []
            for pattern in patterns:
                files_to_read.extend(list(repo.rglob(pattern))[:10])

        for file_path in files_to_read[:10]:  # Limit context
            if file_path.exists() and file_path.stat().st_size < 50000:
                try:
                    content = file_path.read_text()
                    rel_path = file_path.relative_to(repo)
                    context_parts.append(f"=== {rel_path} ===\n{content[:2000]}")
                except:
                    pass

        return "\n\n".join(context_parts)

    def generate(
        self,
        task: str,
        repo_context: str = "",
        error_feedback: str = "",
        task_type: TaskType = None
    ) -> str:
        """Generate response with smart prompting."""
        self.load_model()

        # Detect task type if not provided
        if task_type is None:
            task_type = detect_task_type(task)

        # Get task-specific system prompt (smart routing)
        system_prompt = get_system_prompt(task_type)

        # Build user message
        user_content = task
        if repo_context:
            user_content = f"Repository context:\n{repo_context[:3000]}\n\nTask:\n{task}"
        if error_feedback:
            user_content += f"\n\nPrevious attempt failed:\n{error_feedback}\n\nPlease fix the issues."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=2048,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        response = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:],
            skip_special_tokens=True
        )
        return response

    def apply_patch(self, response: str, repo_path: str) -> Tuple[bool, str]:
        """Apply patch from response."""
        patch_match = re.search(
            r"\*\*\* Begin Patch\n(.*?)\*\*\* End Patch",
            response, re.DOTALL
        )

        if not patch_match:
            return False, "No patch found in response"

        patch = patch_match.group(1)
        repo = Path(repo_path)

        # Parse and apply patch
        current_file = None
        added_lines = []

        try:
            for line in patch.split('\n'):
                if line.startswith('+++ '):
                    # Save previous file
                    if current_file and added_lines:
                        file_path = repo / current_file
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        file_path.write_text('\n'.join(added_lines))

                    # Start new file
                    path = line[4:].strip()
                    if path.startswith('b/'):
                        path = path[2:]
                    current_file = path
                    added_lines = []

                elif line.startswith('+') and not line.startswith('+++'):
                    added_lines.append(line[1:])
                elif line.startswith(' '):
                    added_lines.append(line[1:])

            # Save last file
            if current_file and added_lines:
                file_path = repo / current_file
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text('\n'.join(added_lines))

            return True, ""
        except Exception as e:
            return False, str(e)

    def run_tests(self, repo_path: str, commands: List[str]) -> Tuple[bool, str]:
        """Run test commands."""
        import subprocess

        test_commands = [c for c in commands if 'test' in c.lower() or 'pytest' in c.lower()]

        if not test_commands:
            return True, "No tests to run"

        outputs = []
        all_passed = True

        for cmd in test_commands:
            try:
                result = subprocess.run(
                    cmd, shell=True, cwd=repo_path,
                    capture_output=True, text=True, timeout=60
                )
                outputs.append(f"$ {cmd}\n{result.stdout}\n{result.stderr}")
                if result.returncode != 0:
                    all_passed = False
            except Exception as e:
                outputs.append(f"$ {cmd}\nERROR: {e}")
                all_passed = False

        return all_passed, "\n".join(outputs)

    def extract_commands(self, response: str) -> List[str]:
        """Extract commands from response."""
        commands_match = re.search(r"COMMANDS:\n(.*?)(?=\nNOTES:|$)", response, re.DOTALL)
        if not commands_match:
            return []

        commands = []
        for line in commands_match.group(1).split('\n'):
            line = line.strip().lstrip('- ')
            if line:
                commands.append(line)
        return commands

    def extract_files(self, response: str) -> List[str]:
        """Extract files from response."""
        files_match = re.search(r"FILES:\n(.*?)(?=\nPATCH:|$)", response, re.DOTALL)
        if not files_match:
            return []

        files = []
        for line in files_match.group(1).split('\n'):
            line = line.strip().lstrip('- ')
            if line:
                files.append(line)
        return files

    def execute(
        self,
        task: str,
        repo_path: str = None,
        relevant_files: List[str] = None
    ) -> AgentResult:
        """
        Full agent loop (like Claude Code):
        1. Read repo context
        2. Generate with smart prompting
        3. Apply patch
        4. Run tests
        5. Retry on failure
        """
        import tempfile

        if repo_path is None:
            repo_path = tempfile.mkdtemp()

        # Read repository context
        repo_context = self.read_repo_context(repo_path, relevant_files)

        errors = []
        error_feedback = ""
        response = ""
        files_modified = []

        for attempt in range(1, self.max_retries + 1):
            print(f"\n[Attempt {attempt}/{self.max_retries}]")

            # Generate with smart prompting
            response = self.generate(task, repo_context, error_feedback)
            files_modified = self.extract_files(response)
            commands = self.extract_commands(response)

            print(f"  Files: {files_modified}")
            print(f"  Commands: {commands}")

            # Apply patch
            patch_ok, patch_error = self.apply_patch(response, repo_path)
            if not patch_ok:
                error_feedback = f"Patch failed: {patch_error}"
                errors.append(error_feedback)
                print(f"  Patch: FAILED - {patch_error}")
                continue
            print("  Patch: OK")

            # Run tests
            tests_ok, test_output = self.run_tests(repo_path, commands)
            if tests_ok:
                print("  Tests: PASSED")
                return AgentResult(
                    success=True,
                    response=response,
                    attempts=attempt,
                    files_modified=files_modified,
                    tests_passed=True,
                    errors=errors
                )

            error_feedback = f"Tests failed:\n{test_output[:500]}"
            errors.append(error_feedback)
            print(f"  Tests: FAILED")

        # All retries exhausted
        return AgentResult(
            success=False,
            response=response,
            attempts=self.max_retries,
            files_modified=files_modified,
            tests_passed=False,
            errors=errors
        )


# ============================================================================
# TRAINING CONFIG (Single model, not per-stack)
# ============================================================================

TRAINING_CONFIG = {
    "approach": "anthropic_style",
    "description": "Single strong model + smart prompting + agent loop",

    # Single model training
    "base_model": "Qwen/Qwen2.5-Coder-7B-Instruct",
    "single_lora": True,  # NOT per-stack adapters

    # SFT config
    "sft": {
        "data": "gold_samples.jsonl",  # All 515 samples together
        "epochs": 2,
        "batch_size": 4,
        "learning_rate": 2e-4,
        "lora_r": 64,
        "lora_alpha": 128,
    },

    # DPO config (preference tuning)
    "dpo": {
        "data": "dpo_pairs.jsonl",
        "epochs": 1,
        "beta": 0.1,
        "learning_rate": 5e-5,
    },

    # Agent loop config
    "agent": {
        "max_retries": 3,
        "read_repo_context": True,
        "smart_prompting": True,  # Different prompts per task type
    },

    # NOT using per-stack adapters
    "per_stack_adapters": False,
}


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("ANTHROPIC-STYLE PIPELINE")
    print("=" * 70)
    print("""
What this does (like Anthropic/Claude):
1. Single strong model (NOT per-stack adapters)
2. SFT + DPO for preference tuning
3. Smart prompting based on task type
4. Agent loop: Generate → Apply → Test → Retry

Why this is better:
- Simpler architecture
- Shared learning across all stacks
- Agent loop handles errors automatically
- Smart prompting provides specialization without adapter overhead
""")

    print("\nTask Detection Demo:")
    test_prompts = [
        "Create a REST API for user management",
        "Fix the memory leak in the connection pool",
        "Add unit tests for the payment service",
        "Train a CNN for image classification",
        "Add JWT authentication to the API",
    ]

    for prompt in test_prompts:
        task_type = detect_task_type(prompt)
        print(f"  '{prompt[:40]}...' → {task_type.value}")

    print("\n" + "=" * 70)
    print("TRAINING STEPS")
    print("=" * 70)
    print("""
Step 1: SFT on ALL 515 gold samples (single LoRA)
        python step1_train_sft_v1.py

Step 2: Evaluate on unseen prompts
        python step2_evaluate_v1.py

Step 3: Generate silver data (if passed)
        python step3_generate_silver.py

Step 4: SFT v2 on gold + silver
        python step4_train_sft_v2.py

Step 5: DPO preference tuning
        python step5_train_dpo.py

Step 6: Deploy with agent loop
        Use AnthropicStyleAgent class
""")

    print("\n" + "=" * 70)
    print("AGENT LOOP DEMO")
    print("=" * 70)

    # Demo without actual model
    print("""
agent = AnthropicStyleAgent(model_path="./models/dpo_v3")

result = agent.execute(
    task="Create a REST API for products with CRUD operations",
    repo_path="./my_project",
    relevant_files=["app/models.py", "app/main.py"]
)

# Agent automatically:
# 1. Reads repo context
# 2. Detects task type → API_IMPLEMENTATION
# 3. Uses API-specific system prompt
# 4. Generates code
# 5. Applies patch
# 6. Runs tests
# 7. Retries up to 3 times if tests fail
""")

    print("=" * 70)


if __name__ == "__main__":
    main()
