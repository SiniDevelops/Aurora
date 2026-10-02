# Custom Skills

Place your custom skills here. Each skill should be in its own directory with:

```
my_skill/
├── skill.yaml    # Skill metadata and configuration
└── skill.py      # Skill implementation (extends BaseSkill)
```

## Quick Start

1. Create a new directory: `my_skill/`
2. Create `skill.yaml`:

```yaml
skill:
  id: "my_custom_skill"
  name: "My Custom Skill"
  description: "What this skill does"
  version: "1.0.0"
  author: "your_name"
  
  triggers:
    - "keyword1"
    - "keyword2"
  
  examples:
    - "Example user message 1"
    - "Example user message 2"
  
  category: "utility"
  
  required_context:
    - "search_results"
  
  required_permissions:
    - "vault_read"
    - "llm_access"
  
  parameters:
    my_param:
      type: "string"
      default: "value"
      description: "What this parameter controls"
  
  privacy_level: "content"
  max_tokens: 2000
```

3. Create `skill.py`:

```python
from skills.base_skill import BaseSkill
from data.models import SkillInput, SkillOutput, SkillMetadata

class MyCustomSkill(BaseSkill):
    async def execute(self, input: SkillInput) -> SkillOutput:
        # Your skill logic here
        response = await self.llm.complete([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": input.user_message},
        ])
        return SkillOutput(response_text=response)
    
    def can_handle(self, user_input: str) -> float:
        # Return confidence 0.0-1.0
        keywords = ["keyword1", "keyword2"]
        if any(kw in user_input.lower() for kw in keywords):
            return 0.8
        return 0.0
```

4. Aurora will auto-discover your skill on startup (if `skills.auto_discover: true` in `aurora.yaml`).
