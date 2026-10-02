import re
import yaml
from typing import Tuple, List, Dict
from datetime import datetime
import hashlib
from aurora_backend.data.models import FrontmatterData, NoteLink, NoteEmbed, Note
import os

def parse_frontmatter(content: str) -> Tuple[FrontmatterData, str]:
    fm_match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
    if not fm_match:
        return FrontmatterData(), content
        
    fm_text = fm_match.group(1)
    body = fm_match.group(2)
    
    try:
        data = yaml.safe_load(fm_text) or {}
    except Exception:
        data = {}
        
    return FrontmatterData(
        raw=data,
        title=data.get('title'),
        date=str(data.get('date')) if data.get('date') else None,
        tags=data.get('tags', []),
        aliases=data.get('aliases', []),
        custom_fields={k: v for k, v in data.items() if k not in ['title', 'date', 'tags', 'aliases']}
    ), body

def extract_wiki_links(content: str) -> List[NoteLink]:
    links = []
    pattern = r'\[\[(.*?)\]\]'
    matches = re.finditer(pattern, content)
    for match in matches:
        inner = match.group(1)
        if inner.startswith('!'):
            continue
            
        parts = inner.split('|', 1)
        target_full = parts[0]
        display = parts[1] if len(parts) > 1 else None
        
        heading, block_ref = None, None
        target = target_full
        if '#' in target_full:
            target, heading = target_full.split('#', 1)
        elif '^' in target_full:
            target, block_ref = target_full.split('^', 1)
            
        links.append(NoteLink(
            target=target,
            display_text=display,
            link_type="wiki",
            heading=heading,
            block_ref=block_ref
        ))
    return links

def extract_embeds(content: str) -> List[NoteEmbed]:
    embeds = []
    pattern = r'!\[\[(.*?)\]\]'
    matches = re.finditer(pattern, content)
    for match in matches:
        inner = match.group(1)
        parts = inner.split('|', 1)
        target_full = parts[0]
        
        heading, block_ref = None, None
        target = target_full
        if '#' in target_full:
            target, heading = target_full.split('#', 1)
        elif '^' in target_full:
            target, block_ref = target_full.split('^', 1)
            
        embed_type = "note"
        lower_target = target.lower()
        if lower_target.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
            embed_type = "image"
        elif lower_target.endswith('.pdf'):
            embed_type = "pdf"
        elif lower_target.endswith(('.mp3', '.wav', '.ogg')):
            embed_type = "audio"
        elif lower_target.endswith(('.mp4', '.webm')):
            embed_type = "video"
            
        embeds.append(NoteEmbed(
            target=target,
            embed_type=embed_type,
            heading=heading,
            block_ref=block_ref
        ))
    return embeds

def extract_tags(content: str, frontmatter_tags: List[str]) -> List[str]:
    inline_tags = re.findall(r'(?<!\S)#([a-zA-Z0-9_\-]+)', content)
    all_tags = [t.lower() for t in frontmatter_tags + inline_tags]
    return list(set(all_tags))

def extract_aliases(frontmatter: FrontmatterData) -> List[str]:
    return frontmatter.aliases if frontmatter.aliases else []

def clean_content(content: str) -> str:
    _, body = parse_frontmatter(content)
    return body.strip()

def parse_note(path: str, content: str) -> Note:
    fm, body = parse_frontmatter(content)
    tags = extract_tags(body, fm.tags)
    links = extract_wiki_links(body)
    embeds = extract_embeds(body)
    
    clean_text = clean_content(content)
    word_count = len(clean_text.split())
    char_count = len(clean_text)
    content_hash = hashlib.md5(content.encode()).hexdigest()
    
    filename = os.path.basename(path)
    folder = os.path.dirname(path)
    
    return Note(
        id=hashlib.sha1(path.encode()).hexdigest(),
        path=path,
        filename=filename,
        folder=folder,
        content=content,
        clean_content=clean_text,
        frontmatter=fm,
        tags=tags,
        aliases=extract_aliases(fm),
        links=links,
        backlinks=[],
        embeds=embeds,
        created_at=datetime.utcnow(),
        modified_at=datetime.utcnow(),
        word_count=word_count,
        character_count=char_count,
        content_hash=content_hash
    )
