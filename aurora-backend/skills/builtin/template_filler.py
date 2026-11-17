import logging
from typing import Any
import re
from datetime import datetime
from ..base_skill import BaseSkill
from data.models import SkillMetadata, SkillInput, SkillOutput

class TemplateFillerSkill(BaseSkill):
    """Skill to generate notes from templates."""
    
    metadata = SkillMetadata(
        id='template_filler',
        name='Template Filler',
        description='Create a new note from a template and fill it using LLM context.',
        triggers=['template', 'from template'],
        examples=['/template meeting', 'Create note from template'],
        category='GENERATION',
        permissions=['VAULT_READ', 'VAULT_WRITE', 'LLM_ACCESS'],
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
        
        # Find templates in vault, named by filename (frontmatter titles of
        # templates contain raw placeholders like "{{title}}", so don't use them)
        import os as _os
        templates = []
        for n in self.vault_manager.notes_cache.values():
            if 'Templates/' in n.path or (n.folder or '').startswith('Templates'):
                stem = _os.path.splitext(_os.path.basename(n.path))[0]
                name = re.sub(r'\s*template\s*$', '', stem, flags=re.IGNORECASE).strip() or stem
                templates.append((name, n))
                
        if not msg:
            if not templates:
                return await self.post_execute(SkillOutput(response_text="No templates found in 'Templates/' folder.", metadata={}))
            
            lines = [f"- **{name}** — `/template {name.lower()}`" for name, _ in templates]
            response = "**Available Templates**\n\n" + "\n".join(lines) + "\n\nUse `/template <name>` to use one."
            return await self.post_execute(SkillOutput(response_text=response, metadata={}))
            
        # Match template: first word(s) of the message against template names
        msg_lower = msg.lower()
        target_template = None
        template_name = ""
        for name, t in templates:
            if name.lower() in msg_lower or msg_lower.split()[0] in name.lower():
                target_template, template_name = t, name
                break
                
        if not target_template:
            available = ", ".join(name for name, _ in templates) or "none"
            return await self.post_execute(SkillOutput(response_text=f"No template matching '{msg}'. Available: {available}", metadata={}))
            
        # Prepare content
        content = target_template.content
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        title_str = f"{template_name} - {date_str}"
        
        content = (content.replace("{{date}}", date_str)
                          .replace("{{title}}", title_str)
                          .replace("{{time}}", now.strftime("%H:%M")))
        
        # Fill via LLM if there are remaining empty sections or context placeholders
        prompt = [
            {"role": "system", "content": "You are a template filling assistant. You are given a markdown template. If there are sections to fill or prompts in the text (like [fill here]), provide appropriate default content or expand it based on the title and the user's request. Keep the template's structure. Output the completed markdown only, without frontmatter."},
            {"role": "user", "content": f"Title: {title_str}\nUser request: {msg}\n\nTemplate Content:\n{content}"}
        ]
        
        try:
            filled_content = await self.llm_client.complete(prompt)
        except Exception:
            filled_content = content
            
        safe_title = re.sub(r'[<>:"/\\|?*]', '', title_str).replace(' ', '_')
        path = f"Inbox/{safe_title}.md"
        
        try:
            await self.vault_manager.write_note(path, filled_content, {"title": title_str, "date": date_str, "tags": ["from-template"]})
            response = f"Created note **{title_str}** from template at `{path}`"
        except Exception as e:
            response = f"Failed to create note: {e}"
            
        return await self.post_execute(SkillOutput(response_text=response, metadata={"path": path}))
