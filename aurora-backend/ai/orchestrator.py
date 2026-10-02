"""
Aurora AI Orchestrator — LangGraph State Machine

Manages the full AI pipeline: sanitize → context → route → execute → format → respond.
Uses LangGraph for reliable, observable state machine execution.
"""

from typing import TypedDict, Any, AsyncIterator, Optional
from langgraph.graph import StateGraph, START, END


class AuroraState(TypedDict):
    """State for the LangGraph pipeline."""
    messages: list[dict[str, str]]
    user_input: str
    sanitized_input: str
    original_input: str  # Full input before command extraction
    vault_context: Any  # VaultContext or string representation
    active_skill: Optional[str]
    skill_output: str
    response_text: str
    session_id: str
    error: Optional[str]


class AuroraOrchestrator:
    """
    Orchestrates the full Aurora AI pipeline using LangGraph.
    
    Pipeline: sanitize → build_context → route → execute_skill → format → respond
    Each node handles errors gracefully and passes them forward.
    """

    def __init__(
        self,
        sanitizer: Any,
        context_builder: Any,
        skill_registry: Any,
        skill_router: Any,
        llm_client: Any,
    ):
        self.sanitizer = sanitizer
        self.context_builder = context_builder
        self.skill_registry = skill_registry
        self.skill_router = skill_router
        self.llm_client = llm_client
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> Any:
        """Build and compile the LangGraph state machine."""
        workflow = StateGraph(AuroraState)

        # ─── Node: Sanitize Input ────────────────────
        async def sanitize_input(state: AuroraState) -> dict:
            try:
                sanitized_text, _matches, _tokens = await self.sanitizer.sanitize(
                    state["user_input"]
                )
                return {"sanitized_input": sanitized_text or state["user_input"]}
            except Exception as e:
                return {"error": f"Sanitization failed: {e}"}

        # ─── Node: Build Vault Context ───────────────
        async def build_context(state: AuroraState) -> dict:
            if state.get("error"):
                return {}
            try:
                context = await self.context_builder.build_context(
                    query=state["sanitized_input"]
                )
                return {"vault_context": context}
            except Exception as e:
                # Context building failure is non-fatal — proceed without context
                return {"vault_context": None}

        # ─── Node: Route to Skill ────────────────────
        async def route_to_skill(state: AuroraState) -> dict:
            if state.get("error"):
                return {}
            try:
                user_input = state["sanitized_input"]
                result = await self.skill_router.route(user_input)
                
                if result.method == "command" and result.command_arg:
                    # Router found /command — pass extracted arg to skill
                    # e.g. "explain emotions and /create a note about it"
                    #   → skill gets "a note about it" 
                    #   → original_input preserved for multi-intent
                    return {
                        "active_skill": result.skill_id,
                        "sanitized_input": result.command_arg,
                        "original_input": result.original_input,
                    }
                elif result.method == "command":
                    # Bare /command with no argument — use full input
                    parts = user_input.strip().split(maxsplit=1)
                    clean_input = parts[1] if len(parts) > 1 else user_input
                    return {"active_skill": result.skill_id, "sanitized_input": clean_input}
                
                return {"active_skill": result.skill_id}
            except Exception as e:
                return {"error": f"Routing failed: {e}"}

        # ─── Node: Execute Skill ─────────────────────
        async def execute_skill(state: AuroraState) -> dict:
            if state.get("error"):
                return {}
            try:
                skill = self.skill_registry.get_skill(state["active_skill"])
                if skill is None:
                    # No skill matched → use LLM directly for general chat
                    vault_ctx = state.get("vault_context")
                    context_str = ""
                    if vault_ctx and hasattr(vault_ctx, 'notes') and vault_ctx.notes:
                        note_summaries = []
                        for n in vault_ctx.notes[:5]:
                            title = getattr(n, 'title', 'Untitled')
                            preview = getattr(n, 'content', '')[:200]
                            note_summaries.append(f"- {title}: {preview}")
                        context_str = "\n\nRelevant notes from the user's vault:\n" + "\n".join(note_summaries)
                    
                    system_prompt = (
                        "You are Aurora, a helpful AI assistant integrated with the user's Obsidian knowledge vault. "
                        "Be concise, friendly, and helpful. If you have vault context, reference it naturally. "
                        "Format responses in markdown."
                        f"{context_str}"
                    )
                    
                    response = await self.llm_client.complete([
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": state["sanitized_input"]},
                    ])
                    return {"skill_output": response}

                # Build SkillInput — convert context_builder's VaultContext
                # to data.models.VaultContext for the skill
                from data.models import SkillInput
                from data.models import VaultContext as ModelsVaultContext
                
                builder_ctx = state.get("vault_context")
                if builder_ctx is not None:
                    # Map context_builder fields to models fields
                    vault_ctx = ModelsVaultContext(
                        relevant_notes=getattr(builder_ctx, 'notes', []),
                        recent_notes=getattr(builder_ctx, 'recent_notes', []),
                        tag_cloud=getattr(builder_ctx, 'tags', {}),
                        folder_structure=getattr(builder_ctx, 'tree', {}),
                    )
                else:
                    vault_ctx = ModelsVaultContext()

                skill_input = SkillInput(
                    user_message=state["sanitized_input"],
                    chat_history=[],
                    vault_context=vault_ctx,
                    parameters={
                        "original_input": state.get("original_input", ""),
                    },
                )
                output = await skill.execute(skill_input)
                return {"skill_output": output.response_text}
            except Exception as e:
                return {"error": f"Skill execution failed: {e}"}

        # ─── Node: Format Response ───────────────────
        async def format_response(state: AuroraState) -> dict:
            if state.get("error"):
                return {}
            try:
                # De-tokenize the response (restore PII)
                raw_output = state.get("skill_output", "")
                response = self.sanitizer.detokenize(raw_output)
                return {"response_text": response}
            except Exception as e:
                return {"response_text": state.get("skill_output", "An error occurred.")}

        # ─── Node: Handle Error ──────────────────────
        async def handle_error(state: AuroraState) -> dict:
            error_msg = state.get("error", "An unknown error occurred.")
            return {
                "response_text": f"I encountered an issue: {error_msg}. Please try again."
            }

        # ─── Wire up the graph ───────────────────────
        workflow.add_node("sanitize_input", sanitize_input)
        workflow.add_node("build_context", build_context)
        workflow.add_node("route_to_skill", route_to_skill)
        workflow.add_node("execute_skill", execute_skill)
        workflow.add_node("format_response", format_response)
        workflow.add_node("handle_error", handle_error)

        # Edges with error checking
        workflow.add_edge(START, "sanitize_input")

        def check_error(state: AuroraState) -> str:
            return "handle_error" if state.get("error") else "next"

        workflow.add_conditional_edges(
            "sanitize_input", check_error,
            {"handle_error": "handle_error", "next": "build_context"},
        )
        workflow.add_conditional_edges(
            "build_context", check_error,
            {"handle_error": "handle_error", "next": "route_to_skill"},
        )
        workflow.add_conditional_edges(
            "route_to_skill", check_error,
            {"handle_error": "handle_error", "next": "execute_skill"},
        )
        workflow.add_conditional_edges(
            "execute_skill", check_error,
            {"handle_error": "handle_error", "next": "format_response"},
        )
        workflow.add_edge("format_response", END)
        workflow.add_edge("handle_error", END)

        return workflow.compile()

    async def process_message(self, user_input: str, session_id: str) -> str:
        """Process a user message through the full pipeline."""
        initial_state: AuroraState = {
            "messages": [],
            "user_input": user_input,
            "sanitized_input": "",
            "vault_context": None,
            "active_skill": None,
            "skill_output": "",
            "response_text": "",
            "session_id": session_id,
            "error": None,
        }
        result = await self.workflow.ainvoke(initial_state)
        return result.get("response_text", "No response generated.")

    async def stream_message(
        self, user_input: str, session_id: str
    ) -> AsyncIterator[str]:
        """
        Stream a response token-by-token.
        
        Currently processes the full pipeline first, then streams the result.
        Future: integrate streaming directly into the LLM execution step.
        """
        response = await self.process_message(user_input, session_id)
        # Stream word-by-word for now
        words = response.split()
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
