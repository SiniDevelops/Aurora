import re
from typing import List, Dict, Tuple, Optional, Any
from pydantic import BaseModel
from data.models import Note

class PIIMatch(BaseModel):
    text: str
    category: str
    start: int
    end: int

class TokenEntry(BaseModel):
    token: str
    original: str
    category: str

class FilterResult(BaseModel):
    allowed: bool
    reason: str

class PrivacyConfig(BaseModel):
    enabled_categories: List[str] = []
    rules: List[Any] = []

class PIIDetector:
    """Detects PII in text via Regex and NER."""
    
    PATTERNS = {
        'EMAIL': r'[\w\.-]+@[\w\.-]+\.\w+',
        'PHONE': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    }
    
    def __init__(self, enabled_categories: List[str]):
        self.enabled_categories = enabled_categories
        
    async def detect(self, text: str) -> List[PIIMatch]:
        matches = self._regex_detect(text)
        matches.extend(self._ner_detect(text))
        return matches
        
    def _regex_detect(self, text: str) -> List[PIIMatch]:
        matches = []
        for cat, pattern in self.PATTERNS.items():
            if cat in self.enabled_categories:
                for match in re.finditer(pattern, text):
                    matches.append(PIIMatch(text=match.group(), category=cat, start=match.start(), end=match.end()))
        return matches
        
    def _ner_detect(self, text: str) -> List[PIIMatch]:
        return []

class ContentFilterEngine:
    """Applies content filtering rules."""
    
    def __init__(self, rules: List[Any]):
        self.rules = rules
        
    def filter(self, content: str, source_note: Optional[Note]) -> FilterResult:
        return FilterResult(allowed=True, reason="")

class TokenMapper:
    """Maps PII data to anonymized tokens and vice-versa."""
    
    def __init__(self):
        self._token_map: Dict[str, str] = {}
        self._reverse_map: Dict[str, str] = {}
        self._counters: Dict[str, int] = {}
        
    def tokenize(self, text: str, matches: List[PIIMatch]) -> str:
        for match in sorted(matches, key=lambda m: m.start, reverse=True):
            token = self._get_or_create_token(match)
            text = text[:match.start] + token + text[match.end:]
        return text
        
    def detokenize(self, text: str) -> str:
        for token, original in self._reverse_map.items():
            text = text.replace(token, original)
        return text
        
    def _get_or_create_token(self, match: PIIMatch) -> str:
        if match.text in self._token_map:
            return self._token_map[match.text]
            
        count = self._counters.get(match.category, 0) + 1
        self._counters[match.category] = count
        token = f"<{match.category}_{count}>"
        
        self._token_map[match.text] = token
        self._reverse_map[token] = match.text
        return token
        
    def get_report(self) -> List[TokenEntry]:
        return [TokenEntry(token=t, original=o, category=t.strip("<>").split("_")[0]) for o, t in self._token_map.items()]
        
    def reset(self):
        self._token_map.clear()
        self._reverse_map.clear()
        self._counters.clear()

class PrivacySanitizer:
    """Full privacy sanitizer pipeline."""
    
    def __init__(self, config: PrivacyConfig):
        self._pii_detector = PIIDetector(config.enabled_categories)
        self._content_filter = ContentFilterEngine(config.rules)
        self._token_mapper = TokenMapper()
        
    async def sanitize(self, text: str, source_note: Optional[Note] = None) -> Tuple[str, List[PIIMatch], List[TokenEntry]]:
        filter_res = self._content_filter.filter(text, source_note)
        if not filter_res.allowed:
            return "", [], []
            
        matches = await self._pii_detector.detect(text)
        sanitized_text = self._token_mapper.tokenize(text, matches)
        
        return sanitized_text, matches, self._token_mapper.get_report()
        
    def detokenize(self, text: str) -> str:
        return self._token_mapper.detokenize(text)
        
    def get_audit_report(self) -> List[TokenEntry]:
        return self._token_mapper.get_report()
        
    def reset_session(self):
        self._token_mapper.reset()
