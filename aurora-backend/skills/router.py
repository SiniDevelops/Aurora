"""
Skill Router — Multi-stage routing to determine which skill handles a request.

Routing stages:
1. Command match (/create, /find, /summarize, etc.) — found ANYWHERE in input
2. Heuristic keyword scoring
3. If score > threshold → use that skill
4. If no skill matches → return None (general LLM chat)
"""

import re
from typing import Optional, Any, Dict
from pydantic import BaseModel
from .registry import SkillRegistry


class RoutingResult(BaseModel):
    """Result of the routing decision."""
    skill_id: Optional[str] = None
    confidence: float = 0.0
    method: str = "none"
    all_scores: Dict[str, float] = {}
    # When a /command is found, this holds the text AFTER the command
    # e.g. "explain emotions and /create a note about it" → "a note about it"
    command_arg: str = ""
    # The full original input (for multi-intent: LLM gets the whole thing)
    original_input: str = ""


class SkillRouter:
    """Multi-stage router to determine which skill should handle a user request."""

    # Explicit slash commands — highest priority, 100% confidence
    COMMANDS = {
        "/create": "note_creator",
        "/new": "note_creator",
        "/find": "note_finder",
        "/search": "note_finder",
        "/summarize": "summarizer",
        "/summary": "summarizer",
        "/link": "linker",
        "/daily": "daily_note",
        "/tag": "tagger",
        "/template": "templater",
        "/stats": "vault_stats",
    }

    # Compiled regex to find /commands anywhere in text
    _COMMAND_RE = re.compile(
        r"(?:^|\s)(/(?:" + "|".join(k.lstrip("/") for k in COMMANDS) + r"))(?:\s|$)",
        re.IGNORECASE,
    )

    CONFIDENCE_THRESHOLD = 0.6

    def __init__(self, registry: SkillRegistry, llm_client: Any, config: dict):
        self.registry = registry
        self.llm_client = llm_client
        self.config = config

    async def route(self, user_input: str) -> RoutingResult:
        """
        Route user input through multi-stage evaluation.
        Returns RoutingResult with skill_id=None if no skill matches.
        """
        # Stage 1: Scan for /command ANYWHERE in input
        match = self._COMMAND_RE.search(user_input)
        if match:
            cmd = match.group(1).lower().strip()
            skill_id = self.COMMANDS.get(cmd)
            if skill_id and self.registry.get_skill(skill_id):
                # Extract the text after the command as the argument
                after_cmd = user_input[match.end():].strip()
                # If command was mid-sentence, also grab context before it
                before_cmd = user_input[:match.start()].strip()
                # The "argument" for the skill is what comes after the command
                # but we pass the full input as original_input for context
                command_arg = after_cmd if after_cmd else before_cmd
                return RoutingResult(
                    skill_id=skill_id,
                    confidence=1.0,
                    method="command",
                    all_scores={skill_id: 1.0},
                    command_arg=command_arg,
                    original_input=user_input,
                )

        # Stage 2: Heuristic keyword scoring
        skills = self.registry.get_enabled_skills()
        scores: Dict[str, float] = {}
        best_skill: Optional[str] = None
        best_score = 0.0

        for skill in skills:
            score = skill.can_handle(user_input)
            scores[skill.metadata.id] = score
            if score > best_score:
                best_score = score
                best_skill = skill.metadata.id

        # Stage 3: Only route to skill if confidence is above threshold
        if best_score >= self.CONFIDENCE_THRESHOLD and best_skill:
            return RoutingResult(
                skill_id=best_skill,
                confidence=best_score,
                method="heuristic",
                all_scores=scores,
                original_input=user_input,
            )

        # No skill matched → general LLM chat
        return RoutingResult(
            skill_id=None,
            confidence=0.0,
            method="none",
            all_scores=scores,
            original_input=user_input,
        )
