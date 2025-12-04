"""
Prompt Classifier Agent

An AI-powered agent that uses Claude to intelligently classify user prompts.
This is the first layer in the request pipeline - it determines the user's intent
before routing to the appropriate handler.

Similar to how Bolt.new, Cursor, and Replit Agent classify prompts.
"""

import json
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.utils.claude_client import claude_client
from app.core.logging_config import logger


# In-memory cache for classifications (with TTL)
_classification_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


# Clean, focused system prompt for classification
CLASSIFIER_SYSTEM_PROMPT = """You are the PromptClassifier Agent for an AI Project Generator.

Your job is ONLY to classify the user's message.
You MUST NOT provide explanations, code, plans, or suggestions.

Read the user's latest message and classify it into ONE of the following labels:

1. "project_request"
   - User clearly asks to create, build, generate, scaffold, or develop a software project
   - Mentions: application, website, API, backend, frontend, UI, system, full-stack, microservice, ML project, etc.

2. "small_task"
   - User wants a short code snippet, bug fix, explanation, conversion, test case, or small feature
   - Not a full project

3. "general_question"
   - User is asking conceptual or informational questions
   - Not requesting project generation

4. "greeting"
   - User says hi/hello/thanks or sends emojis, fillers, or acknowledgements

5. "unclear"
   - Message is too short, vague, meaningless, or incomplete
   - Cannot determine intent

Rules:
- Respond ONLY in this JSON format:
  {"type": "<label>"}
- No additional text.
- No comments.
- No reasoning.
- No Markdown."""


# Mapping from simple labels to internal intent format
LABEL_TO_INTENT = {
    "project_request": "GENERATE",
    "small_task": "MODIFY",
    "general_question": "EXPLAIN",
    "greeting": "CHAT",
    "unclear": "CHAT"
}

LABEL_TO_WORKFLOW = {
    "project_request": "bolt_standard",
    "small_task": "bolt_instant",
    "general_question": "chat_only",
    "greeting": "chat_only",
    "unclear": "chat_only"
}

# Chat responses for different scenarios
CHAT_RESPONSES = {
    "greeting": "Hello! I'm BharatBuild AI. What would you like to build today?",
    "unclear": "I'm not sure what you'd like me to do. Could you describe the project or feature you want to build?",
    "general_question": None,  # Will be handled by explain flow
}


class PromptClassifierAgent:
    """
    AI-powered prompt classifier using Claude Haiku for fast, accurate classification.
    Uses a simple, focused prompt for reliable JSON responses.
    """

    def __init__(self):
        self.client = claude_client
        self.cache = _classification_cache

    def _get_cache_key(self, prompt: str, context_hash: str) -> str:
        """Generate a cache key from prompt and context."""
        combined = f"{prompt.lower().strip()}:{context_hash}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get classification from cache if valid."""
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.now() < cached["expires_at"]:
                logger.info(f"[Classifier] Cache hit for key: {cache_key[:8]}...")
                return cached["result"]
            else:
                # Expired, remove from cache
                del self.cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, result: Dict[str, Any]):
        """Store classification in cache."""
        self.cache[cache_key] = {
            "result": result,
            "expires_at": datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)
        }
        # Clean old entries if cache is too large
        if len(self.cache) > 1000:
            self._cleanup_cache()

    def _cleanup_cache(self):
        """Remove expired entries from cache."""
        now = datetime.now()
        expired_keys = [
            key for key, value in self.cache.items()
            if now >= value["expires_at"]
        ]
        for key in expired_keys:
            del self.cache[key]

    async def classify(
        self,
        prompt: str,
        has_existing_project: bool = False,
        current_files: Optional[List[str]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Classify a user prompt using Claude AI.

        Args:
            prompt: The user's input prompt
            has_existing_project: Whether user has files in their project
            current_files: List of file paths in the current project
            conversation_history: Recent messages for context

        Returns:
            Classification result with intent, confidence, entities, etc.
        """
        # Quick check for empty prompts
        if not prompt or not prompt.strip():
            return self._create_response("greeting", prompt)

        # Check cache first
        context_hash = hashlib.md5(
            f"{has_existing_project}:{len(current_files or [])}".encode()
        ).hexdigest()[:8]
        cache_key = self._get_cache_key(prompt, context_hash)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        try:
            # Use Haiku for fast classification (< 500ms typically)
            # Simple prompt - just the user message
            response = await self.client.generate(
                prompt=prompt,
                system_prompt=CLASSIFIER_SYSTEM_PROMPT,
                model="haiku",
                max_tokens=50,  # Only need {"type": "label"}
                temperature=0.0  # Zero temperature for consistent classification
            )

            # Parse the JSON response
            content = response.get("content", "").strip()

            # Handle potential markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            result = json.loads(content)
            label = result.get("type", "unclear")

            # Validate label
            if label not in LABEL_TO_INTENT:
                label = "unclear"

            # Create normalized response
            normalized_result = self._create_response(label, prompt, has_existing_project)

            # Cache the result
            self._set_cache(cache_key, normalized_result)

            logger.info(
                f"[Classifier] '{prompt[:50]}...' -> {label} -> {normalized_result['intent']}"
            )

            return normalized_result

        except json.JSONDecodeError as e:
            logger.warning(f"[Classifier] Failed to parse JSON response: {e}")
            return self._fallback_classification(prompt, has_existing_project)
        except Exception as e:
            logger.error(f"[Classifier] Error during classification: {e}")
            return self._fallback_classification(prompt, has_existing_project)

    def _create_response(
        self,
        label: str,
        prompt: str,
        has_existing_project: bool = False
    ) -> Dict[str, Any]:
        """Create a normalized response from the classification label."""
        intent = LABEL_TO_INTENT.get(label, "CHAT")
        workflow = LABEL_TO_WORKFLOW.get(label, "chat_only")

        # NOTE: Do NOT switch to bolt_instant when user has existing project
        # bolt_standard shows 7 workflow tasks (Plan, Write, Verify, Run, Fix, Verify, Docs)
        # bolt_instant only shows 2-3 tasks (Understanding, Building, Done)
        # Users prefer seeing all 7 workflow steps regardless of existing project

        requires_generation = label in ["project_request", "small_task"]
        chat_response = CHAT_RESPONSES.get(label) if not requires_generation else None

        # For greeting, generate appropriate response
        if label == "greeting":
            chat_response = self._get_greeting_response(prompt)

        return {
            "intent": intent,
            "confidence": 0.95,
            "reasoning": f"Classified as {label}",
            "entities": {},
            "requiresGeneration": requires_generation,
            "suggestedWorkflow": workflow,
            "chatResponse": chat_response,
            "originalPrompt": prompt,
            "label": label  # Include original label for debugging
        }

    def _get_greeting_response(self, prompt: str) -> str:
        """Get appropriate response for greeting messages."""
        prompt_lower = prompt.lower().strip().rstrip("!?.,")

        responses = {
            "hi": "Hello! I'm BharatBuild AI. What would you like to build today?",
            "hello": "Hi there! I can help you create applications, APIs, and more. What's your project idea?",
            "hey": "Hey! Ready to build something amazing? Tell me about your project.",
            "thanks": "You're welcome! Let me know if you need anything else.",
            "thank you": "Happy to help! What else can I build for you?",
            "bye": "Goodbye! Come back anytime you want to build something new.",
            "ok": "Great! What would you like me to create?",
            "yes": "Perfect! Tell me what you'd like to build.",
            "no": "No problem! Let me know when you're ready.",
        }

        for key, response in responses.items():
            if key in prompt_lower:
                return response

        return "Hello! I'm BharatBuild AI. What would you like to build today?"

    def _fallback_classification(
        self,
        prompt: str,
        has_existing_project: bool
    ) -> Dict[str, Any]:
        """
        Fallback classification using simple rules when AI fails.
        Uses the same label system as the AI classifier.
        """
        prompt_lower = prompt.lower().strip().rstrip("!?.,")
        words = prompt_lower.split()

        # Greeting patterns
        greeting_patterns = [
            "hi", "hello", "hey", "thanks", "thank you", "bye", "goodbye",
            "ok", "okay", "yes", "no", "sure", "good morning", "good afternoon"
        ]

        for pattern in greeting_patterns:
            if prompt_lower == pattern or pattern in prompt_lower:
                return self._create_response("greeting", prompt, has_existing_project)

        # Project request keywords
        project_keywords = [
            "create", "build", "make", "develop", "generate", "implement",
            "scaffold", "bootstrap", "new project", "full stack", "application",
            "website", "web app", "api", "backend", "frontend"
        ]

        for keyword in project_keywords:
            if keyword in prompt_lower:
                return self._create_response("project_request", prompt, has_existing_project)

        # Small task keywords
        small_task_keywords = [
            "add", "update", "change", "modify", "edit", "fix", "debug",
            "remove", "delete", "convert", "refactor", "test"
        ]

        for keyword in small_task_keywords:
            if keyword in prompt_lower:
                return self._create_response("small_task", prompt, has_existing_project)

        # Question patterns
        question_patterns = [
            "what is", "what are", "how does", "how do", "why", "explain",
            "describe", "tell me", "can you explain"
        ]

        for pattern in question_patterns:
            if pattern in prompt_lower:
                return self._create_response("general_question", prompt, has_existing_project)

        # Default: if long enough, treat as project_request
        if len(words) >= 5:
            return self._create_response("project_request", prompt, has_existing_project)

        # Short and unclear
        return self._create_response("unclear", prompt, has_existing_project)


# Singleton instance
prompt_classifier_agent = PromptClassifierAgent()
