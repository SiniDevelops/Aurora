import logging
from typing import Any
from ..base_skill import BaseSkill
from data.models import SkillMetadata, SkillInput, SkillOutput

class SummarizerSkill(BaseSkill):
    """Skill to summarize notes."""
    
    metadata = SkillMetadata(
        id='summarizer',
        name='Summarizer',
        description='Summarize one or multiple notes.',
        triggers=['summarize', 'summary', 'tldr', 'brief', 'overview', 'recap'],
        examples=['Summarize the meeting notes'],
        category='ANALYSIS',
        permissions=['VAULT_READ', 'LLM_ACCESS'],
        parameters={
            'summary_length': 'medium',
            'format': 'bullet'
        }
    )
    
    def can_handle(self, user_input: str) -> float:
        input_lower = user_input.lower()
        if any(trigger in input_lower for trigger in self.metadata.triggers):
            return 0.85
        return 0.1
        
    async def execute(self, input: SkillInput) -> SkillOutput:
        await self.pre_execute(input)
        
        query = input.user_message
        notes = await self.vault_manager.search_notes(query, limit=3)
        content_to_summarize = "\n\n---\n\n".join([f"## {getattr(n, 'title', 'Untitled')}\n{getattr(n, 'content', '')}" for n in notes])
        
        if not content_to_summarize.strip():
            return SkillOutput(response_text=f"No notes found to summarize for '{query}'.")
        
        length = self.metadata.parameters.get('summary_length', 'medium')
        fmt = self.metadata.parameters.get('format', 'bullet')
        
        try:
            summary = await self.llm_client.complete([
                {"role": "system", "content": f"Summarize the following content. Length: {length}. Format: {fmt} points."},
                {"role": "user", "content": content_to_summarize},
            ])
        except Exception:
            summary = "Summary generation failed."
            
        output = SkillOutput(
            response_text=summary,
            metadata={"notes_summarized": len(notes), "query": query}
        )
        return await self.post_execute(output)
