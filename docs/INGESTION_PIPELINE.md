# Aurora — External Data Ingestion Pipeline

> **Owner**: _Unassigned_
> **Status**: Not Started
> **Priority**: High
> **Last Updated**: 2026-09-22

---

## 1. What This Pipeline Does

Aurora's brain is the **Obsidian vault** — a folder of `.md` files. The `VaultManager` already handles reading, indexing, searching, and watching for changes inside this folder. It supports `.md` and `.canvas` files, parses YAML frontmatter, extracts tags/links, and caches everything in memory. A file watcher picks up new/modified/deleted files in real-time.

**Your job is to build the pipeline that sits _before_ the vault** — an external service that:

1. Connects to various external data sources (email, web, PDFs, YouTube, etc.)
2. Extracts the content from each source
3. Converts it into a clean `.md` file with proper YAML frontmatter metadata
4. Saves the `.md` file into the correct folder inside the vault

**Once the `.md` file lands in the vault, your job is done.** The `VaultManager` and file watcher handle everything downstream (indexing, embedding, search, AI context).

```
┌─────────────────────────────────────────────────────────────┐
│                   EXTERNAL DATA SOURCES                     │
│                                                             │
│  Email · Web Pages · PDFs · YouTube · RSS · Notion · etc.   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                    YOUR PIPELINE BUILDS THIS
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    .md FILES WITH FRONTMATTER                │
│                                                             │
│  Dropped into:  ${AURORA_VAULT_PATH}/<appropriate-folder>/  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ALREADY HANDLED — DON'T TOUCH
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  VaultManager → FileWatcher → Indexing → ChromaDB → AI     │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Output Rules — The Markdown Standard

Every file your pipeline creates **must** follow these rules so `VaultManager` can parse them correctly.

### 2.1 YAML Frontmatter (Required)

Every `.md` file must start with a YAML frontmatter block between `---` delimiters. The `VaultManager` parses these fields directly:

```yaml
---
title: "The actual title of the content"
date: 2026-09-22
source: "email"                          # which source this came from
source_url: "https://..."                # original URL / reference (if applicable)
tags:
  - ingested
  - email
  - work
aliases:
  - "Alternative name for this note"     # optional — helps Obsidian link resolution
author: "John Doe"                       # who wrote the original content
ingested_at: 2026-09-22T16:45:00+05:30   # when your pipeline processed this
status: "unread"                         # unread | read | archived
---
```

**Required fields** (must always be present):

| Field | Type | Description |
|-------|------|-------------|
| `title` | `string` | Clear, descriptive title. The `VaultManager` uses this as the note's display title. If missing, it falls back to the filename. |
| `date` | `date` or `datetime` | Date the original content was created/published. Use ISO 8601 format. |
| `source` | `string` | Identifier for the source type. Use one of: `email`, `web`, `pdf`, `youtube`, `rss`, `notion`, `google-keep`, `twitter`, `reddit`, `slack`, `discord`, `telegram`, `voice-memo`, `screenshot`, `github`, `readwise`, `pocket`, `manual` |
| `tags` | `list[string]` | Always include `ingested` as the first tag. Add source-specific and content-specific tags. The `VaultManager` extracts these and makes them searchable. |
| `ingested_at` | `datetime` | ISO 8601 timestamp of when the pipeline processed this item. |

**Recommended fields** (include when available from the source):

| Field | Type | Description |
|-------|------|-------------|
| `source_url` | `string` | Original URL, message ID, or reference link |
| `author` | `string` | Original author / sender |
| `aliases` | `list[string]` | Alternative names (helps Obsidian's `[[link]]` resolution) |
| `status` | `string` | `unread` / `read` / `archived` — for user workflow |
| `summary` | `string` | One-line summary (useful for search and briefings) |
| `language` | `string` | Content language code, e.g. `en`, `ta`, `hi` |
| `word_count` | `int` | Word count of the body content |
| `attachments` | `list[string]` | Relative paths to any attachment files saved alongside |

**Source-specific fields** (add these based on the source type):

| Source | Extra Fields |
|--------|-------------|
| `email` | `from`, `to`, `cc`, `subject`, `thread_id`, `has_attachments` |
| `web` | `site_name`, `description`, `favicon_url` |
| `pdf` | `page_count`, `file_size_kb`, `original_filename` |
| `youtube` | `channel`, `duration`, `video_id`, `thumbnail_url` |
| `rss` | `feed_name`, `feed_url`, `published_at` |
| `twitter` | `tweet_id`, `handle`, `retweet_count`, `like_count` |
| `reddit` | `subreddit`, `post_id`, `score`, `comment_count` |
| `slack` / `discord` | `channel`, `workspace`, `thread_id` |
| `voice-memo` | `duration_seconds`, `transcription_model` |
| `screenshot` | `ocr_model`, `ocr_confidence` |
| `github` | `repo`, `issue_number`, `pr_number`, `gist_id` |

### 2.2 Markdown Body

After the frontmatter, write the body as **clean Obsidian-compatible markdown**:

```markdown
---
title: "How Transformers Work"
date: 2026-09-20
source: "youtube"
source_url: "https://youtube.com/watch?v=..."
tags:
  - ingested
  - youtube
  - machine-learning
  - transformers
channel: "3Blue1Brown"
duration: "26:14"
ingested_at: 2026-09-22T16:45:00+05:30
status: "unread"
---

# How Transformers Work

> **Source**: [3Blue1Brown — YouTube](https://youtube.com/watch?v=...)
> **Duration**: 26:14 · **Channel**: 3Blue1Brown

## Key Concepts

- Attention mechanism allows the model to focus on relevant parts of the input
- Self-attention computes relationships between all positions in a sequence
- Multi-head attention runs several attention operations in parallel

## Detailed Notes

### The Attention Mechanism

The core idea behind transformers is the **attention mechanism**...

### Positional Encoding

Since transformers process all tokens in parallel, they need a way to understand order...

## Timestamps

- `00:00` — Introduction
- `03:24` — What is attention?
- `12:15` — Multi-head attention
- `20:00` — Why transformers replaced RNNs

## Related

- [[Attention Is All You Need]]
- [[Neural Network Basics]]
```

**Body formatting rules:**

1. **Start with an H1 heading** (`# Title`) matching the frontmatter `title`
2. **Include a source attribution block** at the top (as a blockquote) with the original link
3. **Use proper heading hierarchy** — `##` for sections, `###` for subsections
4. **Use Obsidian wiki-links** (`[[Other Note Name]]`) where you can link to existing vault content
5. **Preserve meaningful structure** — bullet points, numbered lists, tables, code blocks
6. **Keep images/attachments as relative Obsidian embeds** — `![[image.png]]` (save the file alongside, see §2.3)
7. **No HTML** — use pure markdown. Obsidian renders markdown, not HTML.
8. **Encoding**: UTF-8, always

### 2.3 File Naming & Placement

**File naming convention:**
```
<YYYY-MM-DD>_<source>_<sanitized-title>.md
```

Examples:
```
2026-09-22_email_Weekly_Team_Standup_Notes.md
2026-09-20_youtube_How_Transformers_Work.md
2026-09-18_web_Understanding_Vector_Databases.md
2026-09-15_pdf_Q3_Financial_Report.md
```

Rules:
- Replace spaces with `_`
- Remove or replace special characters: `? : * " < > | / \` → strip them
- Truncate title portion to **80 characters max**
- Ensure filename is unique — if a file with the same name exists, append `_2`, `_3`, etc.

**Folder placement inside the vault:**

Place files into folders based on their source type. The vault path is configured in `aurora.yaml` as `vault.path` (environment variable `${AURORA_VAULT_PATH}`).

```
${AURORA_VAULT_PATH}/
├── Inbox/                    ← Default landing zone for uncategorized ingested content
├── Ingested/
│   ├── Email/                ← Emails
│   ├── Web/                  ← Web clippings / articles
│   ├── PDF/                  ← Extracted PDF content
│   ├── YouTube/              ← YouTube transcripts / notes
│   ├── RSS/                  ← RSS feed articles
│   ├── Social/               ← Twitter, Reddit, etc.
│   ├── Chat/                 ← Slack, Discord, Telegram
│   ├── Voice/                ← Transcribed voice memos
│   ├── Screenshots/          ← OCR'd screenshots
│   ├── Code/                 ← GitHub issues, gists, snippets
│   └── Notes/                ← Notion, Google Keep, etc.
└── Attachments/
    └── Ingested/             ← Images, PDFs, audio files referenced by notes
```

> **Important**: Do NOT write files into folders starting with `.` (`.obsidian`, `.trash`, `.git`) — these are in the `VaultManager`'s `excluded_folders` list and will be ignored.

### 2.4 Attachments

If the source content includes images, PDFs, or other media:

1. Save the attachment to `${AURORA_VAULT_PATH}/Attachments/Ingested/<filename>`
2. Reference it in the `.md` body using Obsidian embed syntax: `![[filename.png]]`
3. List the relative paths in the frontmatter `attachments` field
4. Supported attachment extensions (from `aurora.yaml`): `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`, `.pdf`

---

## 3. Data Sources to Implement

Implement connectors for these sources, ordered by priority:

### Tier 1 — Core (Build First)

#### 3.1 📧 Email (Gmail / Outlook)

| | |
|---|---|
| **What to ingest** | Starred/labeled emails, or all emails from a configured label/folder |
| **API** | Gmail API (`google-api-python-client`) or Microsoft Graph API |
| **Auth** | OAuth 2.0 |
| **What becomes a note** | Each email thread → 1 `.md` file |
| **Body content** | Sender, recipients, date, subject as metadata. Email body converted from HTML to markdown. Thread replies in chronological order under `## Replies` |
| **Attachments** | Save to `Attachments/Ingested/`, embed in note |
| **Dedup strategy** | Track `message_id` or `thread_id` — skip already-ingested threads |
| **Folder** | `Ingested/Email/` |

#### 3.2 🌐 Web Pages / Articles

| | |
|---|---|
| **What to ingest** | URLs provided by the user, or from a bookmarks/read-later integration |
| **Libraries** | `trafilatura` or `readability-lxml` for article extraction, `markdownify` for HTML→MD |
| **What becomes a note** | Each URL → 1 `.md` file |
| **Body content** | Article title, author, publish date as metadata. Main body text extracted (strip nav, ads, footer). Preserve headings, lists, images, code blocks. |
| **Images** | Download referenced images, save to `Attachments/Ingested/`, replace URLs with `![[image.png]]` |
| **Dedup strategy** | Track by URL — skip already-ingested URLs |
| **Folder** | `Ingested/Web/` |

#### 3.3 📄 PDF Documents

| | |
|---|---|
| **What to ingest** | PDF files from a configured watch folder, or uploaded via API |
| **Libraries** | `pymupdf` (fitz) for text extraction, `pdfplumber` for tables |
| **What becomes a note** | Each PDF → 1 `.md` file (or 1 per chapter for large documents) |
| **Body content** | Extracted text with heading structure preserved where possible. Tables converted to markdown tables. Include page numbers as references (`[p.12]`). |
| **Attachments** | Keep original PDF in `Attachments/Ingested/`, link from note: `Original: ![[filename.pdf]]` |
| **Dedup strategy** | Track by file hash (SHA256) — skip already-ingested PDFs |
| **Folder** | `Ingested/PDF/` |
| **Splitting** | If a PDF exceeds 5,000 words, consider splitting by chapter/section into multiple notes linked together with `[[Part 1]]`, `[[Part 2]]` etc. |

#### 3.4 🎥 YouTube Videos

| | |
|---|---|
| **What to ingest** | YouTube URLs provided by user, or from a playlist / watch-later list |
| **Libraries** | `youtube-transcript-api` for transcripts, `yt-dlp` for metadata |
| **What becomes a note** | Each video → 1 `.md` file |
| **Body content** | Video title, channel, duration, description as metadata. Full transcript with timestamps. Key sections identified by natural topic breaks. |
| **Attachments** | Download thumbnail, save as attachment |
| **Dedup strategy** | Track by `video_id` — skip already-ingested videos |
| **Folder** | `Ingested/YouTube/` |

### Tier 2 — Important (Build Second)

#### 3.5 📰 RSS Feeds

| | |
|---|---|
| **What to ingest** | Articles from configured RSS/Atom feed URLs |
| **Libraries** | `feedparser` for feed parsing, `trafilatura` for full article extraction |
| **What becomes a note** | Each article → 1 `.md` file |
| **Body content** | If feed provides full content, use it. Otherwise fetch the article URL and extract with `trafilatura`. |
| **Dedup strategy** | Track by article `guid` or URL — skip already-ingested articles |
| **Polling** | Check feeds on a configurable interval (default: every 30 minutes) |
| **Folder** | `Ingested/RSS/` |

#### 3.6 📝 Notion Export

| | |
|---|---|
| **What to ingest** | Pages from a connected Notion workspace |
| **API** | Notion API (`notion-client`) |
| **Auth** | Integration token |
| **What becomes a note** | Each Notion page → 1 `.md` file. Databases → 1 `.md` per row. |
| **Body content** | Convert Notion blocks to markdown. Preserve toggles as `<details>` or collapsible sections. Tables, callouts, embeds, etc. |
| **Dedup strategy** | Track by Notion `page_id` + `last_edited_time` — re-ingest if modified |
| **Folder** | `Ingested/Notes/` |

#### 3.7 📌 Google Keep

| | |
|---|---|
| **What to ingest** | Notes and checklists from Google Keep |
| **API** | Google Keep has no official API — use Google Takeout export (JSON) or `gkeepapi` (unofficial) |
| **What becomes a note** | Each Keep note → 1 `.md` file |
| **Body content** | Note content as-is. Checklists → markdown checkbox format (`- [x]`, `- [ ]`). Labels → tags. Colors → tag (e.g., `#keep-blue`). |
| **Folder** | `Ingested/Notes/` |

#### 3.8 📖 Readwise / Pocket / Instapaper

| | |
|---|---|
| **What to ingest** | Highlights and saved articles |
| **API** | Readwise API, Pocket API, Instapaper API |
| **What becomes a note** | Each article/book → 1 `.md` file with highlights as blockquotes |
| **Body content** | Article metadata as frontmatter. Highlights as `> blockquotes` with location/page references. Personal notes inline. |
| **Folder** | `Ingested/Web/` |

### Tier 3 — Nice to Have (Build Later)

#### 3.9 🐦 Twitter / X Bookmarks

| | |
|---|---|
| **What to ingest** | Bookmarked tweets and threads |
| **API** | X API v2 (requires API access) |
| **What becomes a note** | Each bookmarked tweet or thread → 1 `.md` file |
| **Body content** | Tweet text, author, metrics. Threads → sequential messages. Images downloaded as attachments. |
| **Folder** | `Ingested/Social/` |

#### 3.10 💬 Reddit Saved Posts

| | |
|---|---|
| **What to ingest** | Saved posts and comments |
| **API** | Reddit API via `praw` |
| **What becomes a note** | Each saved post → 1 `.md` file (include top comments if it's a discussion) |
| **Folder** | `Ingested/Social/` |

#### 3.11 💼 Slack / Discord / Telegram

| | |
|---|---|
| **What to ingest** | Bookmarked/saved/starred messages, or messages from specific channels |
| **API** | Slack API (`slack-sdk`), Discord API (`discord.py`), Telegram Bot API (`python-telegram-bot`) |
| **What becomes a note** | Each thread or starred message → 1 `.md` file |
| **Body content** | Messages in chronological order. Sender names, timestamps. Code snippets preserved. |
| **Folder** | `Ingested/Chat/` |

#### 3.12 🎤 Voice Memos / Audio

| | |
|---|---|
| **What to ingest** | Audio files from a watch folder or uploaded via API |
| **Libraries** | `openai` Whisper API or `faster-whisper` for local transcription |
| **What becomes a note** | Each audio file → 1 `.md` file with transcript |
| **Body content** | Full transcript with timestamps. Speaker diarization if possible. |
| **Attachments** | Keep original audio in `Attachments/Ingested/` |
| **Folder** | `Ingested/Voice/` |

#### 3.13 📸 Screenshots / Images (OCR)

| | |
|---|---|
| **What to ingest** | Images from a watch folder |
| **Libraries** | `pytesseract` or `easyocr`, or an LLM vision API for better results |
| **What becomes a note** | Each image → 1 `.md` file with extracted text |
| **Body content** | OCR'd text as the body. Original image embedded: `![[screenshot.png]]` |
| **Folder** | `Ingested/Screenshots/` |

#### 3.14 💻 GitHub Issues / Gists

| | |
|---|---|
| **What to ingest** | Starred gists, issues from watched repos, or specific repos |
| **API** | GitHub REST API (`PyGithub`) or GraphQL |
| **What becomes a note** | Each issue → 1 `.md` file. Each gist → 1 `.md` file with code blocks. |
| **Folder** | `Ingested/Code/` |

---

## 4. Deduplication & State Tracking

The pipeline must **never create duplicate notes** for the same source item. Maintain a tracking store (a simple SQLite database or JSON file, separate from Aurora's main DB) with:

```
source_type  |  source_id               |  vault_path                                     |  ingested_at              |  content_hash
─────────────┼──────────────────────────┼─────────────────────────────────────────────────┼───────────────────────────┼─────────────
email        |  msg_id_abc123           |  Ingested/Email/2026-09-22_email_Standup.md      |  2026-09-22T16:45:00      |  sha256...
youtube      |  dQw4w9WgXcQ            |  Ingested/YouTube/2026-09-20_youtube_How_...md   |  2026-09-22T16:46:00      |  sha256...
web          |  https://example.com/... |  Ingested/Web/2026-09-18_web_Vector_DB.md        |  2026-09-22T16:47:00      |  sha256...
```

**On each run:**
1. Fetch items from the source
2. Check `source_id` against the tracking store
3. **New item** → convert to `.md`, save to vault, add tracking row
4. **Existing + content changed** (compare `content_hash`) → overwrite the `.md` file in-place (same path), update tracking row. The file watcher will detect the modification.
5. **Existing + unchanged** → skip entirely
6. **Source item deleted** (optional) → optionally delete or archive the `.md` file, remove tracking row

---

## 5. Pipeline Architecture Recommendation

Build this as a standalone Python service/script that runs alongside the Aurora backend. It should NOT be coupled into the FastAPI backend — it's a separate process.

```
aurora-ingestion/
├── main.py                   # Entry point — scheduler + CLI
├── config.py                 # Reads vault path + source configs from aurora.yaml or its own config
├── tracker.py                # Dedup tracking (SQLite)
├── converter.py              # Shared: content → .md file writer (frontmatter + body)
├── sources/
│   ├── base.py               # Abstract base class for all source connectors
│   ├── email_source.py       # Gmail / Outlook connector
│   ├── web_source.py         # Web clipper
│   ├── pdf_source.py         # PDF extractor
│   ├── youtube_source.py     # YouTube transcript puller
│   ├── rss_source.py         # RSS feed reader
│   ├── notion_source.py      # Notion API connector
│   ├── keep_source.py        # Google Keep connector
│   ├── readwise_source.py    # Readwise / Pocket connector
│   ├── twitter_source.py     # Twitter bookmarks
│   ├── reddit_source.py      # Reddit saved posts
│   ├── chat_source.py        # Slack / Discord / Telegram
│   ├── voice_source.py       # Audio transcription
│   ├── screenshot_source.py  # OCR
│   └── github_source.py      # GitHub issues / gists
├── requirements.txt
└── README.md
```

**Each source connector** should implement:
```python
class BaseSource(ABC):
    @abstractmethod
    async def fetch_items(self) -> List[SourceItem]:
        """Fetch new/updated items from the external source."""
        ...

    @abstractmethod
    async def convert_to_markdown(self, item: SourceItem) -> MarkdownNote:
        """Convert a source item into frontmatter + markdown body."""
        ...
```

**The shared `converter.py`** handles:
```python
def write_note_to_vault(note: MarkdownNote, vault_path: str, folder: str) -> str:
    """
    Writes a MarkdownNote to the vault as a .md file.
    Returns the path of the created file.

    - Constructs the frontmatter YAML block
    - Writes the body
    - Handles filename sanitization and dedup
    - Creates folders if they don't exist
    """
    ...
```

---

## 6. Scheduling & Triggers

The pipeline should support two modes:

| Mode | How It Works |
|------|-------------|
| **Scheduled polling** | A background scheduler (e.g., `APScheduler` or `cron`) that runs each source connector on a configurable interval. Example: check email every 10 minutes, check RSS every 30 minutes. |
| **On-demand / API trigger** | An HTTP endpoint or CLI command to trigger ingestion manually. Example: `python main.py ingest --source email` or `POST /api/ingest?source=web&url=https://...` |

---

## 7. Things to Be Careful About

| Concern | What to Do |
|---------|-----------|
| **Vault path** | Always read from `aurora.yaml` → `vault.path` (which resolves `${AURORA_VAULT_PATH}` from `.env`). Never hardcode. |
| **Excluded folders** | Never write into `.obsidian`, `.trash`, `.git` — the `VaultManager` ignores these. |
| **File encoding** | Always write UTF-8 with no BOM. |
| **Frontmatter format** | Must be valid YAML between `---` delimiters. The `VaultManager` uses a regex parser — malformed YAML will cause the whole frontmatter to be skipped. |
| **Tags format** | In frontmatter: plain strings without `#`. In body: `#tag-name` with the hash. The vault manager handles both. |
| **Rate limits** | Respect API rate limits for Gmail, YouTube, Notion, etc. Add backoff and retry logic. |
| **Large content** | If a single piece of content (e.g., a long PDF or video transcript) exceeds ~5,000 words, consider splitting into multiple linked notes. |
| **Privacy** | Do NOT ingest into folders that are blocked by Aurora's privacy rules (e.g., `Journal/`, `Personal/Diary/`). The `Ingested/` folder structure avoids this by design. |
| **Existing files** | Before writing, check if the file already exists. If the content is the same (hash match), skip. If different, overwrite. |
| **Concurrent writes** | If running multiple source connectors in parallel, ensure no two connectors write to the same file path simultaneously. |
| **Obsidian links** | Where possible, add `[[wiki-links]]` to connect ingested content with existing vault notes. A simple heuristic: if the note title matches an existing note filename in the vault, link it. |

---

## 8. Example Output — Complete `.md` Files

### Email Example
```markdown
---
title: "Weekly Team Standup Notes"
date: 2026-09-22
source: "email"
source_url: "mailto:msg_id_abc123"
tags:
  - ingested
  - email
  - work
  - standup
from: "alice@company.com"
to: "team@company.com"
subject: "Weekly Team Standup Notes"
thread_id: "thread_xyz789"
has_attachments: true
attachments:
  - "sprint_board.png"
ingested_at: 2026-09-22T16:45:00+05:30
status: "unread"
---

# Weekly Team Standup Notes

> **From**: alice@company.com · **To**: team@company.com
> **Date**: 2026-09-22 · **Subject**: Weekly Team Standup Notes

## Updates

- **Backend**: API endpoints for vault search completed
- **Frontend**: Chat UI streaming is working
- **Infra**: Docker compose setup ready for review

## Action Items

- [ ] Review PR #42 — vault search endpoint
- [ ] Schedule design review for settings page
- [ ] Update sprint board

## Attachments

![[sprint_board.png]]
```

### PDF Example
```markdown
---
title: "Q3 2026 Financial Report"
date: 2026-09-15
source: "pdf"
tags:
  - ingested
  - pdf
  - finance
  - quarterly-report
author: "Finance Department"
page_count: 24
file_size_kb: 1850
original_filename: "Q3_2026_Financial_Report.pdf"
attachments:
  - "Q3_2026_Financial_Report.pdf"
ingested_at: 2026-09-22T17:00:00+05:30
status: "unread"
---

# Q3 2026 Financial Report

> **Source**: [[Q3_2026_Financial_Report.pdf]] · 24 pages
> **Author**: Finance Department

## Executive Summary

Revenue grew 12% quarter-over-quarter driven by strong performance in...

## Revenue Breakdown

| Segment     | Q2 2026 | Q3 2026 | Growth |
|-------------|---------|---------|--------|
| Product A   | $1.2M   | $1.4M   | +16%   |
| Product B   | $800K   | $870K   | +9%    |
| Services    | $450K   | $510K   | +13%   |

## Key Metrics [p.8]

- Customer acquisition cost: $142 (down from $168)
- Monthly active users: 52,000
- Churn rate: 3.2%

*[Full content extracted from pages 1–24]*
```

### Web Clipping Example
```markdown
---
title: "Understanding Vector Databases"
date: 2026-09-18
source: "web"
source_url: "https://blog.example.com/vector-databases-explained"
tags:
  - ingested
  - web
  - databases
  - machine-learning
  - embeddings
author: "Jane Smith"
site_name: "Tech Blog"
ingested_at: 2026-09-22T16:50:00+05:30
status: "unread"
summary: "A comprehensive guide to how vector databases work and when to use them."
---

# Understanding Vector Databases

> **Source**: [Tech Blog](https://blog.example.com/vector-databases-explained)
> **Author**: Jane Smith · **Published**: 2026-09-18

## What Is a Vector Database?

A vector database is a type of database optimized for storing and querying
high-dimensional vector embeddings...

## How Similarity Search Works

Unlike traditional databases that match exact values, vector databases use
**approximate nearest neighbor (ANN)** algorithms...

## Popular Options

- **ChromaDB** — lightweight, Python-native, great for prototyping
- **Pinecone** — fully managed, scales to billions of vectors
- **Weaviate** — open source with built-in vectorization

## Related

- [[Embeddings]]
- [[ChromaDB]]
- [[Semantic Search]]
```

---

## 9. Acceptance Criteria

This pipeline is **done** when:

- [ ] At least the 4 Tier 1 connectors (Email, Web, PDF, YouTube) are functional
- [ ] Every generated `.md` file has valid YAML frontmatter with all required fields
- [ ] Files are placed in the correct `Ingested/<Source>/` subfolder
- [ ] `VaultManager` successfully discovers and parses all generated files (test by restarting Aurora and checking note count)
- [ ] The file watcher detects newly ingested files in real-time
- [ ] Deduplication works — running the pipeline twice doesn't create duplicate notes
- [ ] Updated source content overwrites the existing note (not a new file)
- [ ] Attachments are saved to `Attachments/Ingested/` and correctly embedded
- [ ] No files are written to excluded folders (`.obsidian`, `.trash`, `.git`)
- [ ] The pipeline handles API errors gracefully (retries, logging, skip-and-continue)
- [ ] A simple CLI or scheduler exists to run the pipeline

---

## 10. Questions for the Team

Before starting, clarify these with the team:

1. **Which email provider(s) do we need to support first?** Gmail only, or Outlook too?
2. **Do we want a watch folder for PDFs**, or will they be uploaded through an API endpoint?
3. **YouTube**: Should we ingest from a specific playlist, watch-later, or only on-demand URLs?
4. **RSS**: Do we have a predefined list of feeds, or should there be a UI to manage them?
5. **Should the pipeline run as a separate service** (recommended) or be embedded in the Aurora backend?
6. **Should deleted source items** (e.g., unstarred emails) cause the vault note to be deleted or archived?
