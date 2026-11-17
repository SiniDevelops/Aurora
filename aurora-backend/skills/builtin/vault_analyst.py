import logging
from typing import Any
from collections import Counter
from ..base_skill import BaseSkill
from data.models import SkillMetadata, SkillInput, SkillOutput

class VaultAnalystSkill(BaseSkill):
    """Skill to analyze vault health and statistics."""
    
    metadata = SkillMetadata(
        id='vault_analyst',
        name='Vault Analyst',
        description='Generate comprehensive statistics and health analysis for the vault.',
        triggers=['stats', 'statistics', 'health', 'analyze vault', 'vault analysis'],
        examples=['/stats', 'analyze vault'],
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
        
        notes = list(self.vault_manager.notes_cache.values())
        
        total_notes = len(notes)
        total_words = sum(n.word_count for n in notes)
        
        tags = []
        folders = []
        link_counts = Counter()
        orphan_notes = []
        broken_links = 0
        
        for n in notes:
            tags.extend(t.strip('#') for t in n.tags)
            if n.folder:
                folders.append(n.folder)
            else:
                folders.append("Root")
                
            has_link = False
            for link in n.links:
                if getattr(link, 'exists', False) or (isinstance(link, dict) and link.get('exists', False)):
                    target = getattr(link, 'target', link.get('target', ''))
                    link_counts[target] += 1
                    has_link = True
                else:
                    broken_links += 1
            
            # Simplified orphan check (only outbound, as we'd need backlinks to check true orphan)
            if not has_link and not n.backlinks:
                orphan_notes.append(n.title)
                
        tag_dist = Counter(tags).most_common(5)
        folder_dist = Counter(folders).most_common(5)
        most_linked = link_counts.most_common(5)
        
        context = f"""Vault Statistics:
Total Notes: {total_notes}
Total Words: {total_words}
Broken Links: {broken_links}
Orphan Notes (sample): {', '.join(orphan_notes[:5])}

Top Tags: {tag_dist}
Top Folders: {folder_dist}
Most Linked Notes: {most_linked}
"""
        
        prompt = [
            {"role": "system", "content": "You are a vault analyst. Review the provided vault statistics and generate an insightful, brief report about the health and structure of the vault. Highlight any areas for improvement (like broken links or orphans)."},
            {"role": "user", "content": context}
        ]
        
        try:
            report = await self.llm_client.complete(prompt)
        except Exception:
            report = f"Raw Vault Stats:\n\n{context}"
            
        return await self.post_execute(SkillOutput(
            response_text=f"**Vault Analysis Report**\n\n{report}",
            metadata={"total_notes": total_notes, "total_words": total_words}
        ))
