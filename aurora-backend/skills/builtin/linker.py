import logging
from typing import Any
from ..base_skill import BaseSkill
from data.models import SkillMetadata, SkillInput, SkillOutput

class LinkerSkill(BaseSkill):
    """Skill to discover connections between notes."""
    
    metadata = SkillMetadata(
        id='linker',
        name='Linker',
        description='Find and explain connections between notes.',
        triggers=['link', 'connect', 'connection', 'related'],
        examples=['/link Artificial Intelligence', 'Find notes related to Quantum Computing'],
        category='ANALYSIS',
        permissions=['VAULT_READ', 'LLM_ACCESS'],
        parameters={}
    )
    
    def can_handle(self, user_input: str) -> float:
        input_lower = user_input.lower().strip()
        for trigger in self.metadata.triggers:
            if input_lower.startswith(trigger):
                return 0.85
        return 0.0
        
    async def execute(self, input: SkillInput) -> SkillOutput:
        await self.pre_execute(input)
        
        target_topic = input.user_message.strip()
        if not target_topic:
            return await self.post_execute(SkillOutput(
                response_text="Please specify a note or topic to find connections for.",
                metadata={}
            ))
            
        results = await self.vault_manager.search_notes(target_topic, limit=1)
        if not results:
            target_note = None
            note_tags = []
        else:
            target_note = results[0]
            note_tags = target_note.tags
            
        related_results = await self.vault_manager.search_notes(target_topic, limit=5)
        related_notes = [n for n in related_results if not target_note or n.path != target_note.path]
        
        if not related_notes:
            return await self.post_execute(SkillOutput(
                response_text=f"Could not find any notes related to '{target_topic}'.",
                metadata={}
            ))
            
        context = f"Target Topic/Note: {target_topic}\n"
        if target_note:
            context += f"Target Note Tags: {', '.join(note_tags)}\n"
        
        context += "\nRelated Notes Found:\n"
        for i, rn in enumerate(related_notes):
            context += f"{i+1}. Title: {rn.title}\nPath: {rn.path}\nPreview: {rn.content[:200]}...\nTags: {', '.join(rn.tags)}\n\n"
            
        prompt_messages = [
            {"role": "system", "content": "You are a vault analysis assistant. Explain how the related notes connect to the target topic. Focus on shared themes, keywords, and tag overlap. Provide a concise, insightful explanation."},
            {"role": "user", "content": context},
        ]
        
        try:
            explanation = await self.llm_client.complete(prompt_messages)
        except Exception:
            explanation = "*(Failed to generate connection explanation via LLM)*"
            
        response_text = f"**Connections for '{target_topic}'**\n\n{explanation}"
        
        output = SkillOutput(
            response_text=response_text,
            metadata={
                "target": target_topic,
                "related_paths": [rn.path for rn in related_notes]
            }
        )
        return await self.post_execute(output)
