import logging
from typing import Any
from ..base_skill import BaseSkill
from data.models import SkillMetadata, SkillInput, SkillOutput

class NoteCreatorSkill(BaseSkill):
    """Skill to create new notes in the vault."""
    
    metadata = SkillMetadata(
        id='note_creator',
        name='Note Creator',
        description='Create new notes in the vault.',
        triggers=['create', 'new note', 'write about', 'draft', 'make a note'],
        examples=['Create a note about quantum computing', 'Write a summary of today\'s meeting'],
        category='NOTE_MANAGEMENT',
        permissions=['VAULT_READ', 'VAULT_WRITE', 'LLM_ACCESS'],
        parameters={
            'default_folder': 'Inbox',
            'add_frontmatter': True,
            'auto_tag': True,
            'auto_link': True
        }
    )
    
    def can_handle(self, user_input: str) -> float:
        input_lower = user_input.lower().strip()
        # Only trigger on imperative commands — input must START with a trigger word
        # Prevents false matches like "Where did you create that note?"
        for trigger in self.metadata.triggers:
            if input_lower.startswith(trigger):
                return 0.85
        return 0.0
        
    async def execute(self, input: SkillInput) -> SkillOutput:
        await self.pre_execute(input)
        
        user_query = input.user_message
        original_input = input.parameters.get("original_input", "")
        
        # If the user_message is vague (e.g. "a note about it") but we have
        # the full original input, use that for better context
        vague_phrases = ["about it", "about that", "about this", "note about it", "a note"]
        if any(user_query.lower().strip().endswith(phrase) for phrase in vague_phrases) and original_input:
            # Strip the /create command from original to get full topic
            import re
            topic = re.sub(r'\s*/\w+\s*', ' ', original_input).strip()
            user_query = topic
        
        # Generate note content via LLM
        prompt_messages = [
            {"role": "system", "content": "You are a note-writing assistant. Create well-structured markdown notes with headings, bullet points, and links where appropriate. Output only the note content, no explanations."},
            {"role": "user", "content": f"Create a comprehensive note about: {user_query}"},
        ]
        
        try:
            content = await self.llm_client.complete(prompt_messages)
            llm_succeeded = True
        except Exception:
            content = f"# {user_query}\n\n*(Content generation failed — please edit this note manually)*"
            llm_succeeded = False
            
        # Extract a clean title
        import re as _re
        from datetime import datetime as _dt
        
        # First: clean up filler phrases from the query
        clean_query = user_query.strip()
        for prefix in ["explain why ", "explain ", "write about ", "tell me about ",
                       "a note about ", "a note on ", "note about ", "note on ",
                       "create ", "make "]:
            if clean_query.lower().startswith(prefix):
                clean_query = clean_query[len(prefix):]
        clean_query = clean_query.strip().capitalize()
        
        # If LLM succeeded, try to use its heading; otherwise use cleaned query
        if llm_succeeded:
            heading_match = _re.search(r'^#\s+(.+)$', content, _re.MULTILINE)
            title = heading_match.group(1).strip()[:60] if heading_match else clean_query[:60]
        else:
            title = clean_query[:60]
        
        title = title.replace("/", "-")
        
        frontmatter = {
            "title": title,
            "tags": ["auto-generated"],
            "date": _dt.now().strftime("%Y-%m-%d"),
        }
            
        folder = self.metadata.parameters.get('default_folder', 'Inbox').strip('/')
        safe_title = title.replace(' ', '_').replace('?', '').replace(':', '').replace('"', '').replace("'", '')
        path = f"{folder}/{safe_title}.md"
        
        try:
            await self.vault_manager.write_note(path, content, frontmatter)
            response = f"Created note **{title}** at `{path}`"
        except Exception as e:
            response = f"Failed to create note: {e}"
        
        output = SkillOutput(
            response_text=response,
            metadata={"path": path, "preview": content[:200]}
        )
        return await self.post_execute(output)
