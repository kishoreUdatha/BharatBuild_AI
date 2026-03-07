#!/usr/bin/env python3
"""
STEP 6: Agent Loop Integration

Even Model v3 will sometimes fail.
This adds:
1. Patch application
2. Test execution
3. Error feedback
4. Retry logic (2-3 times)

Result: Claude Code-like experience
"""

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import torch

SCRIPT_DIR = Path(__file__).parent
MODEL_DIR = SCRIPT_DIR / "models" / "dpo_v3"

# ============================================================================
# OUTPUT PARSING
# ============================================================================

@dataclass
class ClaudeStyleOutput:
    """Parsed Claude-style output."""
    plan: List[str]
    files: List[str]
    patch: str
    commands: List[str]
    notes: List[str]
    raw: str

    @classmethod
    def from_string(cls, text: str) -> "ClaudeStyleOutput":
        """Parse Claude-style output string."""

        def extract_section(name: str) -> List[str]:
            pattern = rf"{name}:\s*\n(.*?)(?=\n(?:PLAN|FILES|PATCH|COMMANDS|NOTES):|$)"
            match = re.search(pattern, text, re.DOTALL)
            if not match:
                return []
            content = match.group(1).strip()
            lines = [line.strip().lstrip("- ").lstrip("0123456789.)") for line in content.split("\n") if line.strip()]
            return lines

        # Extract patch separately
        patch = ""
        patch_match = re.search(
            r"\*\*\* Begin Patch\n(.*?)\*\*\* End Patch",
            text,
            re.DOTALL
        )
        if patch_match:
            patch = patch_match.group(1)

        return cls(
            plan=extract_section("PLAN"),
            files=extract_section("FILES"),
            patch=patch,
            commands=extract_section("COMMANDS"),
            notes=extract_section("NOTES"),
            raw=text
        )


# ============================================================================
# PATCH APPLICATION
# ============================================================================

def apply_patch(patch: str, base_dir: Path) -> Tuple[bool, str]:
    """
    Apply a unified diff patch to the file system.
    Returns (success, error_message)
    """
    if not patch.strip():
        return True, ""

    # Parse patch to find files and changes
    current_file = None
    hunks = []

    for line in patch.split('\n'):
        if line.startswith('--- '):
            pass  # Old file marker
        elif line.startswith('+++ '):
            # Extract new file path
            path = line[4:].strip()
            if path.startswith('b/'):
                path = path[2:]
            current_file = base_dir / path
        elif line.startswith('@@'):
            # New hunk
            hunks.append({
                "file": current_file,
                "changes": []
            })
        elif hunks and current_file:
            hunks[-1]["changes"].append(line)

    # Apply changes (simplified - for new files)
    try:
        for hunk in hunks:
            file_path = hunk["file"]
            if not file_path:
                continue

            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Extract added lines
            content_lines = []
            for line in hunk["changes"]:
                if line.startswith('+') and not line.startswith('+++'):
                    content_lines.append(line[1:])
                elif line.startswith(' '):
                    content_lines.append(line[1:])

            # Write file
            with open(file_path, 'w') as f:
                f.write('\n'.join(content_lines))

        return True, ""
    except Exception as e:
        return False, str(e)


# ============================================================================
# TEST EXECUTION
# ============================================================================

def run_tests(commands: List[str], work_dir: Path, timeout: int = 60) -> Tuple[bool, str]:
    """
    Run test commands.
    Returns (success, output)
    """
    test_commands = [cmd for cmd in commands if "test" in cmd.lower() or "pytest" in cmd.lower()]

    if not test_commands:
        return True, "No tests to run"

    outputs = []
    all_passed = True

    for cmd in test_commands:
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            outputs.append(f"$ {cmd}\n{result.stdout}\n{result.stderr}")

            if result.returncode != 0:
                all_passed = False

        except subprocess.TimeoutExpired:
            outputs.append(f"$ {cmd}\nTIMEOUT after {timeout}s")
            all_passed = False
        except Exception as e:
            outputs.append(f"$ {cmd}\nERROR: {e}")
            all_passed = False

    return all_passed, "\n\n".join(outputs)


# ============================================================================
# AGENT LOOP
# ============================================================================

class CodingAgent:
    """
    Agent that generates code, applies patches, runs tests, and retries on failure.
    """

    def __init__(self, model_dir: Path = MODEL_DIR, max_retries: int = 3):
        self.model_dir = model_dir
        self.max_retries = max_retries
        self.model = None
        self.tokenizer = None

    def load_model(self):
        """Load the fine-tuned model."""
        if self.model is not None:
            return

        print("Loading model...")
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel

        base_model = "Qwen/Qwen2.5-Coder-7B-Instruct"

        self.model = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
        )

        if self.model_dir.exists():
            self.model = PeftModel.from_pretrained(self.model, str(self.model_dir))

        self.tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)

    def generate(self, prompt: str, context: str = "", error_feedback: str = "") -> str:
        """Generate a response."""
        self.load_model()

        system_prompt = """You are an expert software engineer. Respond with this exact structure:

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

Use unified diff format. Be precise."""

        user_content = prompt
        if context:
            user_content = f"Context:\n{context}\n\nTask:\n{prompt}"
        if error_feedback:
            user_content += f"\n\nPrevious attempt failed with:\n{error_feedback}\n\nPlease fix the issues."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
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

    def run(self, prompt: str, work_dir: Optional[Path] = None) -> Dict:
        """
        Full agent loop:
        1. Generate response
        2. Apply patch
        3. Run tests
        4. Retry on failure (up to max_retries)
        """
        if work_dir is None:
            work_dir = Path(tempfile.mkdtemp())

        print(f"Working directory: {work_dir}")
        print(f"Max retries: {self.max_retries}")
        print("-" * 50)

        attempt = 0
        error_feedback = ""
        history = []

        while attempt < self.max_retries:
            attempt += 1
            print(f"\n[Attempt {attempt}/{self.max_retries}]")

            # Generate
            print("Generating response...")
            response = self.generate(prompt, error_feedback=error_feedback)
            output = ClaudeStyleOutput.from_string(response)

            history.append({
                "attempt": attempt,
                "response": response,
                "plan": output.plan,
                "files": output.files
            })

            print(f"Plan: {len(output.plan)} steps")
            print(f"Files: {output.files}")

            # Apply patch
            print("Applying patch...")
            patch_ok, patch_error = apply_patch(output.patch, work_dir)

            if not patch_ok:
                print(f"Patch failed: {patch_error}")
                error_feedback = f"Patch application failed: {patch_error}"
                continue

            print("Patch applied successfully")

            # Run tests
            print("Running tests...")
            tests_ok, test_output = run_tests(output.commands, work_dir)

            if tests_ok:
                print("Tests passed!")
                return {
                    "success": True,
                    "attempts": attempt,
                    "response": response,
                    "output": output,
                    "work_dir": str(work_dir),
                    "history": history
                }
            else:
                print(f"Tests failed")
                error_feedback = f"Tests failed:\n{test_output[:1000]}"

        # All retries exhausted
        print("\nMax retries reached. Returning best effort.")
        return {
            "success": False,
            "attempts": attempt,
            "response": response,
            "output": output,
            "work_dir": str(work_dir),
            "history": history,
            "last_error": error_feedback
        }


# ============================================================================
# INTEGRATION CODE FOR coding_agent.py
# ============================================================================

INTEGRATION_CODE = '''
# Add this to backend/app/agents/coding_agent.py

from dataclasses import dataclass
from typing import List, Optional
import re


@dataclass
class ClaudeStyleOutput:
    """Parsed Claude-style output from fine-tuned Qwen."""
    plan: List[str]
    files: List[str]
    patch: str
    commands: List[str]
    notes: List[str]

    @classmethod
    def from_string(cls, text: str) -> "ClaudeStyleOutput":
        """Parse model output into structured format."""
        def extract_section(name: str) -> List[str]:
            pattern = rf"{name}:\s*\\n(.*?)(?=\\n(?:PLAN|FILES|PATCH|COMMANDS|NOTES):|$)"
            match = re.search(pattern, text, re.DOTALL)
            if not match:
                return []
            content = match.group(1).strip()
            return [l.strip().lstrip("- ").lstrip("0123456789.)")
                    for l in content.split("\\n") if l.strip()]

        patch = ""
        patch_match = re.search(
            r"\\*\\*\\* Begin Patch\\n(.*?)\\*\\*\\* End Patch",
            text, re.DOTALL
        )
        if patch_match:
            patch = patch_match.group(1)

        return cls(
            plan=extract_section("PLAN"),
            files=extract_section("FILES"),
            patch=patch,
            commands=extract_section("COMMANDS"),
            notes=extract_section("NOTES")
        )


class QwenCodingAgent:
    """Coding agent using fine-tuned Qwen with retry logic."""

    def __init__(self, model_path: str, max_retries: int = 3):
        self.model_path = model_path
        self.max_retries = max_retries
        self._model = None

    async def execute(self, task: str, repo_context: str = "") -> dict:
        """Execute coding task with automatic retry on failure."""
        error_feedback = ""

        for attempt in range(self.max_retries):
            # Generate response
            response = await self._generate(task, repo_context, error_feedback)
            output = ClaudeStyleOutput.from_string(response)

            # Apply patch
            patch_ok, patch_error = await self._apply_patch(output.patch)
            if not patch_ok:
                error_feedback = f"Patch failed: {patch_error}"
                continue

            # Run tests
            test_ok, test_output = await self._run_tests(output.commands)
            if test_ok:
                return {"success": True, "output": output, "attempts": attempt + 1}

            error_feedback = f"Tests failed:\\n{test_output[:500]}"

        return {"success": False, "output": output, "error": error_feedback}
'''


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("STEP 6: AGENT LOOP DEMO")
    print("=" * 70)

    # Check model
    if not MODEL_DIR.exists():
        print(f"Model not found at {MODEL_DIR}")
        print("Using base model for demo...")

    agent = CodingAgent(max_retries=3)

    # Demo prompt
    prompt = "Create a simple User model with CRUD API endpoints using FastAPI"

    print(f"\nPrompt: {prompt}")
    print("-" * 50)

    result = agent.run(prompt)

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Success: {result['success']}")
    print(f"Attempts: {result['attempts']}")
    print(f"Files created: {result['output'].files}")
    print(f"Work directory: {result['work_dir']}")

    if not result['success']:
        print(f"Last error: {result.get('last_error', 'Unknown')[:200]}")

    print("\n" + "=" * 70)
    print("INTEGRATION CODE")
    print("=" * 70)
    print("Add the following to backend/app/agents/coding_agent.py:")
    print(INTEGRATION_CODE[:500] + "...")

    print("\n" + "=" * 70)
    print("ROADMAP COMPLETE!")
    print("=" * 70)
    print("""
Your fine-tuned Qwen model is now ready:

Model v1 (SFT on 503 gold samples)
    |
    v
Model v2 (SFT on gold + silver)
    |
    v
Model v3 (DPO for reliability)
    |
    v
Agent Loop (retry on failure)
    |
    v
Claude Code-like experience!

Deployment:
1. Upload model to Hugging Face
2. Update qwen_client.py to use fine-tuned model
3. Integrate QwenCodingAgent into your app
""")


if __name__ == "__main__":
    main()
