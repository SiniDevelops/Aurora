import logging
from typing import Any
from ..base_skill import BaseSkill
from data.models import SkillMetadata, SkillInput, SkillOutput

class TagManagerSkill(BaseSkill):
    """Skill to manage and discover tags."""
    
    metadata = SkillMetadata(
        id='tag_manager',
        name='Tag Manager',
        description='Manage tags, find notes by tag, and get tag suggestions.',
        triggers=['tag', 'tags', 'categorize', 'label'],
        examples=['/tag list', '/tag suggest NoteTitle', '/tag find #AI'],
        category='ORGANIZATION',
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
        
        msg = input.user_message.strip()
        parts = msg.split(maxsplit=1)
        subcommand = parts[0].lower() if parts else "list"
        arg = parts[1] if len(parts) > 1 else ""
        
        notes = self.vault_manager.notes_cache.values()
        
        if subcommand == "list":
            tag_counts = {}
            for n in notes:
                for t in n.tags:
                    tag = t.strip('#')
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                    
            sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
            if not sorted_tags:
                response = "No tags found in the vault."
            else:
                lines = [f"- #{tag} ({count})" for tag, count in sorted_tags]
                response = "**Vault Tags**\n\n" + "\n".join(lines)
                
            return await self.post_execute(SkillOutput(response_text=response, metadata={"action": "list"}))
            
        elif subcommand == "suggest":
            if not arg:
                return await self.post_execute(SkillOutput(response_text="Please specify a note to suggest tags for.", metadata={}))
                
            results = await self.vault_manager.search_notes(arg, limit=1)
            if not results:
                return await self.post_execute(SkillOutput(response_text=f"Note '{arg}' not found.", metadata={}))
                
            target_note = results[0]
            
            prompt = [
                {"role": "system", "content": "You are a categorization assistant. Read the note content and suggest 3-5 relevant concise tags. Output only the tags space-separated, prefixed with #."},
                {"role": "user", "content": f"Title: {target_note.title}\n\nContent:\n{target_note.content[:1000]}"}
            ]
            
            try:
                suggestions = await self.llm_client.complete(prompt)
                response = f"Suggested tags for **{target_note.title}**: {suggestions}"
            except Exception:
                response = "Failed to suggest tags."
                
            return await self.post_execute(SkillOutput(response_text=response, metadata={"action": "suggest"}))
            
        elif subcommand == "find":
            if not arg:
                return await self.post_execute(SkillOutput(response_text="Please specify a tag to find.", metadata={}))
                
            target_tag = arg.strip('#').lower()
            matching_notes = []
            for n in notes:
                if any(t.strip('#').lower() == target_tag for t in n.tags):
                    matching_notes.append(n)
                    
            if not matching_notes:
                response = f"No notes found with tag #{target_tag}."
            else:
                lines = [f"- {n.title} (`{n.path}`)" for n in matching_notes]
                response = f"**Notes with #{target_tag}** ({len(matching_notes)})\n\n" + "\n".join(lines)
                
            return await self.post_execute(SkillOutput(response_text=response, metadata={"action": "find"}))
            
        else:
            return await self.post_execute(SkillOutput(
                response_text="Unknown subcommand. Available: list, suggest <note>, find <tag>",
                metadata={}
            ))
