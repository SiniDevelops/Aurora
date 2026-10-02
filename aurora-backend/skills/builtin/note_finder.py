import logging
from typing import Any
from ..base_skill import BaseSkill
from data.models import SkillMetadata, SkillInput, SkillOutput

class NoteFinderSkill(BaseSkill):
    """Skill to search for notes."""
    
    metadata = SkillMetadata(
        id='note_finder',
        name='Note Finder',
        description='Search and retrieve notes.',
        triggers=['find', 'search', 'look for', 'where is', 'show me', 'get'],
        examples=['Find notes about AI'],
        category='NOTE_RETRIEVAL',
        permissions=['VAULT_READ', 'LLM_ACCESS'],
        parameters={
            'max_results': 5,
            'search_type': 'hybrid',
            'include_preview': True
        }
    )
    
    def can_handle(self, user_input: str) -> float:
        input_lower = user_input.lower()
        if any(trigger in input_lower for trigger in self.metadata.triggers):
            return 0.9
        return 0.1
        
    async def execute(self, input: SkillInput) -> SkillOutput:
        await self.pre_execute(input)
        
        query = input.user_message
        limit = self.metadata.parameters.get('max_results', 5)
        results = await self.vault_manager.search_notes(query, limit=limit)
        
        formatted = [{"title": getattr(r, "title", "Untitled"), "path": getattr(r, "path", ""), "preview": getattr(r, "content", "")[:100]} for r in results]
        
        if formatted:
            summary = "\n".join([f"- **{r['title']}** ({r['path']}): {r['preview']}..." for r in formatted])
            response = f"Found {len(formatted)} note(s) matching '{query}':\n\n{summary}"
        else:
            response = f"No notes found matching '{query}'. Try a different search term."
            
        output = SkillOutput(
            response_text=response,
            metadata={"results": formatted, "query": query}
        )
        return await self.post_execute(output)
