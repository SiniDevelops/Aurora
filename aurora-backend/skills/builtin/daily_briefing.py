import logging
from typing import Any
from datetime import datetime, timedelta
from ..base_skill import BaseSkill
from data.models import SkillMetadata, SkillInput, SkillOutput

class DailyBriefingSkill(BaseSkill):
    """Skill to provide a daily summary of the vault."""
    
    metadata = SkillMetadata(
        id='daily_briefing',
        name='Daily Briefing',
        description='Generate a daily vault summary and task list.',
        triggers=['daily', 'briefing', 'today', 'what happened'],
        examples=['/daily', 'Give me my daily briefing'],
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
        
        notes = self.vault_manager.notes_cache.values()
        
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        
        recent_notes = []
        incomplete_tasks = []
        new_notes_today = 0
        total_notes = len(notes)
        
        for note in notes:
            # Check recently modified
            if note.modified_at >= yesterday:
                recent_notes.append(note)
            
            # Check new today
            if note.created_at.date() == now.date():
                new_notes_today += 1
                
            # Extract incomplete tasks
            for line in note.content.split('\n'):
                if '- [ ]' in line:
                    incomplete_tasks.append(f"- {line.strip()} (in {note.title})")
                    
        context = f"Vault Stats:\n- Total Notes: {total_notes}\n- New Notes Today: {new_notes_today}\n"
        context += f"- Recently Modified Notes: {len(recent_notes)}\n\n"
        
        if recent_notes:
            context += "Recently Modified:\n"
            for rn in recent_notes[:10]:
                context += f"- {rn.title}\n"
        
        if incomplete_tasks:
            context += "\nPending Tasks:\n"
            context += "\n".join(incomplete_tasks[:20]) # Limit to 20 to avoid huge prompts
            
        prompt_messages = [
            {"role": "system", "content": "You are a friendly personal assistant. Generate a brief, encouraging daily briefing based on the vault statistics, recent notes, and pending tasks provided. Use markdown formatting."},
            {"role": "user", "content": context},
        ]
        
        try:
            briefing = await self.llm_client.complete(prompt_messages)
        except Exception:
            briefing = f"Here is your raw daily briefing (LLM failed):\n\n{context}"
            
        output = SkillOutput(
            response_text=briefing,
            metadata={
                "total_notes": total_notes,
                "new_today": new_notes_today,
                "tasks_count": len(incomplete_tasks)
            }
        )
        return await self.post_execute(output)
