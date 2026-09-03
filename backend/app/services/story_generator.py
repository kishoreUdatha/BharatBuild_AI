"""
Drafting user stories from a batch's approved project details.

Two rules shape everything here:

* The model drafts; it never decides. Whatever comes back lands as
  NEEDS_REVIEW, so a regeneration can never approve its own output.
* A trainer's recorded decision is not the model's to overwrite. The default
  scope replaces only stories nobody has ruled on yet; discarding decided work
  takes an explicit, counted confirmation.
"""

import json
import re
from typing import List, Optional

from app.core.config import settings
from app.core.logging_config import logger
from app.llm import unified_llm_client
from app.models.faculty import ProjectBatch

# Bounds the model is held to. A draft outside these is rejected rather than
# quietly clipped, because a silently truncated backlog is worse than none.
# Guardrails against absurd output, not a contract on the exact count: a
# partial regeneration legitimately asks for as few as one story, so a
# full-backlog minimum applied here would refuse the common case.
MIN_EPICS, MAX_EPICS = 1, 8
MIN_STORIES, MAX_STORIES = 1, 24
MIN_ACCEPTANCE, MAX_ACCEPTANCE = 3, 8
MIN_DONE, MAX_DONE = 3, 8
VALID_POINTS = {1, 2, 3, 5, 8, 13}
VALID_PRIORITIES = {"high", "medium", "low"}

SYSTEM_PROMPT = """You are a technical planning assistant for final-year engineering projects.

You draft epics and user stories from a project's approved registration details.
You do not approve, schedule or assign anything - a human trainer reviews every
story you produce.

Rules:
- Ground every story in the project details you are given. Do not invent
  requirements the project has not stated.
- Each story must be independently deliverable and testable.
- Acceptance criteria must be verifiable statements, not restatements of the title.
- Set ai_confidence honestly: lower it when the project details are thin on that
  area. Do not inflate it.
- Reply with JSON only. No prose, no markdown fences."""

SCHEMA = """{
  "epics": [
    {"key": "EP-01", "title": "short epic name", "description": "one sentence"}
  ],
  "stories": [
    {
      "epic_key": "EP-01",
      "title": "imperative short title",
      "narrative": "As a <role>, I want <goal> so that <benefit>.",
      "acceptance_criteria": ["verifiable statement", "..."],
      "definition_of_done": ["verifiable statement", "..."],
      "story_points": 3,
      "priority": "high",
      "ai_confidence": 88,
      "dependencies": "short text or null"
    }
  ]
}"""


class GenerationError(Exception):
    """A refusal the caller can show the trainer as-is."""


def _strip_fences(raw: str) -> str:
    """Models still wrap JSON in fences sometimes, despite being told not to."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text.rstrip())
    # Fall back to the outermost JSON object if there is stray prose around it.
    if not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            text = text[start:end + 1]
    return text.strip()


class StoryGenerator:
    """Builds the prompt, calls the model, and validates what comes back."""

    def __init__(self, model: Optional[str] = None):
        self.model = model or getattr(settings, "CLAUDE_DEFAULT_MODEL", "claude-sonnet-5")

    # ---------------------------------------------------------------- prompt

    @staticmethod
    def project_context(batch: ProjectBatch) -> str:
        """Everything the model is allowed to draft from, and nothing else."""
        objectives = [o.text for o in sorted(batch.objectives, key=lambda o: o.position)]
        methodology = [f"{m.title}: {m.description or ''}".strip(": ")
                       for m in sorted(batch.methodology, key=lambda m: m.position)]
        technologies = [t.name for t in batch.technologies]
        scope_in = [s.text for s in batch.scope_items if s.kind.value == "in_scope"]
        deliverables = [s.text for s in batch.scope_items if s.kind.value == "deliverable"]

        def block(label: str, items: List[str]) -> str:
            return f"{label}:\n" + ("\n".join(f"- {i}" for i in items) if items else "- (none recorded)")

        return "\n\n".join([
            f"Project title: {batch.title or '(untitled)'}",
            f"Domain: {batch.domain or '(unspecified)'}",
            f"Problem statement: {batch.problem_statement or '(not recorded)'}",
            f"Abstract: {batch.abstract or '(not recorded)'}",
            block("Objectives", objectives),
            block("Methodology steps", methodology),
            block("Technology stack", technologies),
            block("In scope", scope_in),
            block("Deliverables", deliverables),
        ])

    def build_prompt(self, batch: ProjectBatch, story_target: int, epic_hint: int) -> str:
        plural = "y" if story_target == 1 else "ies"
        return (
            f"{self.project_context(batch)}\n\n"
            f"Draft about {epic_hint} epic(s) and exactly {story_target} user stor{plural} "
            f"covering this project end to end.\n"
            f"Each story needs {MIN_ACCEPTANCE}-{MAX_ACCEPTANCE} acceptance criteria and "
            f"{MIN_DONE}-{MAX_DONE} definition-of-done items.\n"
            f"story_points must be one of {sorted(VALID_POINTS)}. "
            f"priority must be one of {sorted(VALID_PRIORITIES)}. "
            f"ai_confidence is an integer 0-100.\n\n"
            f"Reply with JSON matching exactly this shape:\n{SCHEMA}"
        )

    # ------------------------------------------------------------- generation

    async def generate(self, batch: ProjectBatch, story_target: int, user_id=None) -> dict:
        if not (MIN_STORIES <= story_target <= MAX_STORIES):
            raise GenerationError(
                f"Ask for between {MIN_STORIES} and {MAX_STORIES} stories."
            )
        # Epics only make sense in proportion to the stories being drafted.
        epic_hint = max(1, min(MAX_EPICS, (story_target + 2) // 3))

        prompt = self.build_prompt(batch, story_target, epic_hint)
        logger.info(f"[Planning] Drafting {story_target} stories for {batch.batch_code} "
                    f"with {self.model}")
        try:
            raw = await unified_llm_client.generate(
                model=self.model,
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                max_tokens=8000,
                temperature=0.4,
                user_id=str(user_id) if user_id else None,
                agent_type="story_planner",
            )
        except Exception as exc:
            logger.error(f"[Planning] LLM call failed: {type(exc).__name__}: {exc}")
            raise GenerationError("The planning model could not be reached. Try again shortly.")

        # The client returns errors as a string rather than raising.
        if not raw or raw.startswith("[ERROR]"):
            logger.error(f"[Planning] LLM returned an error: {raw[:200]}")
            raise GenerationError(
                "The planning model is not available. Check the provider configuration."
            )

        return self.validate(raw)

    # -------------------------------------------------------------- validation

    def validate(self, raw: str) -> dict:
        """
        Parse and check the draft.

        Refuses rather than repairs: a half-understood backlog persisted as if
        it were sound is harder to notice than a failed regeneration.
        """
        try:
            data = json.loads(_strip_fences(raw))
        except json.JSONDecodeError as exc:
            logger.error(f"[Planning] Draft was not valid JSON: {exc}; head={raw[:200]!r}")
            raise GenerationError("The model did not return usable JSON. Try regenerating.")

        if not isinstance(data, dict):
            raise GenerationError("The model did not return a JSON object.")

        epics = data.get("epics")
        stories = data.get("stories")
        if not isinstance(epics, list) or not isinstance(stories, list):
            raise GenerationError("The draft is missing its epics or stories.")
        if not (MIN_EPICS <= len(epics) <= MAX_EPICS):
            raise GenerationError(f"The draft has {len(epics)} epics; expected "
                                  f"{MIN_EPICS}-{MAX_EPICS}.")
        if not (MIN_STORIES <= len(stories) <= MAX_STORIES):
            raise GenerationError(f"The draft has {len(stories)} stories; expected "
                                  f"{MIN_STORIES}-{MAX_STORIES}.")

        clean_epics, seen_keys = [], set()
        for i, e in enumerate(epics):
            key = str(e.get("key") or f"EP-{i + 1:02d}").strip()[:20]
            title = str(e.get("title") or "").strip()[:200]
            if not title:
                raise GenerationError("An epic came back without a title.")
            if key in seen_keys:
                raise GenerationError(f"The draft reuses epic key {key}.")
            seen_keys.add(key)
            clean_epics.append({
                "key": key, "title": title,
                "description": (str(e.get("description") or "").strip() or None),
                "position": i,
            })

        clean_stories, seen_titles = [], set()
        for i, s in enumerate(stories):
            title = str(s.get("title") or "").strip()[:240]
            if not title:
                raise GenerationError("A story came back without a title.")
            lowered = title.lower()
            if lowered in seen_titles:
                raise GenerationError(f'The draft contains two stories titled "{title}".')
            seen_titles.add(lowered)

            epic_key = str(s.get("epic_key") or "").strip()
            if epic_key and epic_key not in seen_keys:
                raise GenerationError(f"Story \"{title}\" references unknown epic {epic_key}.")

            acceptance = [str(a).strip() for a in (s.get("acceptance_criteria") or []) if str(a).strip()]
            done = [str(d).strip() for d in (s.get("definition_of_done") or []) if str(d).strip()]
            if not (MIN_ACCEPTANCE <= len(acceptance) <= MAX_ACCEPTANCE):
                raise GenerationError(
                    f'"{title}" has {len(acceptance)} acceptance '
                    f"criteri{'on' if len(acceptance) == 1 else 'a'}; expected "
                    f"{MIN_ACCEPTANCE}-{MAX_ACCEPTANCE}."
                )
            if not (MIN_DONE <= len(done) <= MAX_DONE):
                raise GenerationError(
                    f'"{title}" has {len(done)} definition-of-done items; expected '
                    f"{MIN_DONE}-{MAX_DONE}."
                )

            try:
                points = int(s.get("story_points") or 0)
            except (TypeError, ValueError):
                points = 0
            if points not in VALID_POINTS:
                raise GenerationError(
                    f'"{title}" has {points} story points; expected one of {sorted(VALID_POINTS)}.'
                )

            priority = str(s.get("priority") or "medium").strip().lower()
            if priority not in VALID_PRIORITIES:
                raise GenerationError(f'"{title}" has priority "{priority}".')

            try:
                confidence = float(s.get("ai_confidence"))
            except (TypeError, ValueError):
                confidence = None
            if confidence is not None:
                confidence = max(0.0, min(100.0, confidence))

            clean_stories.append({
                "epic_key": epic_key or None,
                "title": title,
                "narrative": (str(s.get("narrative") or "").strip() or None),
                "acceptance_criteria": acceptance,
                "definition_of_done": done,
                "story_points": points,
                "priority": priority,
                "ai_confidence": confidence,
                "dependencies": (str(s.get("dependencies") or "").strip() or None) or None,
                "position": i,
            })

        return {"epics": clean_epics, "stories": clean_stories, "model": self.model}
