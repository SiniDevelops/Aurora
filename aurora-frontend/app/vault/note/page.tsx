'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import NoteEditor from '@/components/vault/NoteEditor';
import '@/styles/note.css';

interface NoteData {
  path: string;
  title: string;
  content: string;
  tags: string[];
  links: { target: string; display_text: string | null; link_type: string }[];
  frontmatter: Record<string, unknown>;
}

interface Backlink {
  source: string;
  context: string;
  link_text: string;
}

interface VaultNote {
  path: string;
  title: string;
  tags: string[];
  word_count: number;
}

function NotePageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const path = searchParams.get('path');
  const isEditModeParam = searchParams.get('edit') === '1';

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [note, setNote] = useState<NoteData | null>(null);
  const [backlinks, setBacklinks] = useState<Backlink[]>([]);
  const [allNotes, setAllNotes] = useState<VaultNote[]>([]);
  
  const [isEditMode, setIsEditMode] = useState(isEditModeParam);
  const [showProperties, setShowProperties] = useState(false);

  const fetchNoteData = async (notePath: string) => {
    setLoading(true);
    try {
      const [noteRes, backRes, notesRes] = await Promise.all([
        fetch(`http://localhost:8000/api/vault/note/${encodeURIComponent(notePath)}`),
        fetch(`http://localhost:8000/api/vault/backlinks/${encodeURIComponent(notePath)}`),
        fetch(`http://localhost:8000/api/vault/notes`)
      ]);

      if (!noteRes.ok) {
        if (noteRes.status === 404) throw new Error('Note not found (404)');
        throw new Error('Failed to load note');
      }

      const noteData = await noteRes.json();
      setNote(noteData);

      if (backRes.ok) {
        const backData = await backRes.json();
        setBacklinks(backData.backlinks || []);
      }

      if (notesRes.ok) {
        const notesData = await notesRes.json();
        setAllNotes(notesData);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (path) {
      fetchNoteData(path);
    } else {
      setError('No note path provided');
      setLoading(false);
    }
  }, [path]);

  if (loading) return <div className="note-page"><div className="note-main-content">Loading note...</div></div>;
  if (error) return <div className="note-page"><div className="note-main-content" style={{color: 'red'}}>{error}</div></div>;
  if (!note || !path) return <div className="note-page"><div className="note-main-content">Note not found.</div></div>;

  const folder = note.path.split('/').slice(0, -1).join('/') || '/';

  // Split raw file into the original frontmatter block (kept byte-for-byte)
  // and the body. CRLF-safe: notes written on Windows use \r\n.
  const fmMatch = note.content.match(/^---\r?\n[\s\S]*?\r?\n---[ \t]*(?:\r?\n|$)/);
  const frontmatterBlock = fmMatch ? fmMatch[0] : '';
  const bodyContent = fmMatch ? note.content.slice(fmMatch[0].length) : note.content;

  const handleSave = async (content: string) => {
    // Re-attach the untouched frontmatter block and send frontmatter: null so
    // the backend writes the file verbatim (no lossy YAML re-serialization).
    const res = await fetch(`http://localhost:8000/api/vault/note/${encodeURIComponent(path)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: frontmatterBlock + content, frontmatter: null })
    });
    if (!res.ok) throw new Error('Failed to save');
    await fetchNoteData(path);
    setIsEditMode(false);
  };

  // Obsidian link resolver
  const resolveLink = (target: string) => {
    const targetClean = target.split('#')[0];
    const match = allNotes.find(
      n => n.title.toLowerCase() === targetClean.toLowerCase() || 
           n.path.toLowerCase().endsWith(`/${targetClean.toLowerCase()}.md`)
    );
    return match ? match.path : null;
  };

  const processMarkdown = (text: string) => {
    // Convert Obsidian [[Target|Alias]] / [[Target#Heading]] to markdown links.
    // Unresolved targets get a special "#broken-link" href so the renderer
    // can style them (react-markdown does not render raw HTML strings).
    let processed = text.replace(/\[\[([^\]]+?)\]\]/g, (_m, inner: string) => {
      const parts = inner.split('|');
      const target = parts[0].trim();
      const display = (parts.length > 1 ? parts[1] : target.split('#')[0] || target).trim();
      const resolvedPath = resolveLink(target);
      if (resolvedPath) {
        return `[${display}](/vault/note?path=${encodeURIComponent(resolvedPath)})`;
      }
      return `[${display}](#broken-link)`;
    });

    // Inline #tags → links to the vault filtered by tag
    processed = processed.replace(/(^|\s)#([A-Za-z][\w/-]*)/g, (_m, p1: string, p2: string) => {
      return `${p1}[#${p2}](/vault?tag=${encodeURIComponent(p2)})`;
    });

    return processed;
  };

  const displayContent = processMarkdown(bodyContent);

  return (
    <div className="note-page">
      <div className="note-header">
        <div className="note-breadcrumb">
          <span><a href="/vault" onClick={e => { e.preventDefault(); router.push('/vault'); }}>Vault</a> / {folder}</span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <a href={`obsidian://open?vault=Ai-assitant&file=${encodeURIComponent(path.replace(/\.md$/, ''))}`} className="btn-secondary" style={{textDecoration: 'none'}}>Open in Obsidian</a>
            {!isEditMode && <button className="btn-primary" onClick={() => setIsEditMode(true)}>Edit</button>}
          </div>
        </div>
        <h1 className="note-title">{note.title}</h1>
        <div className="note-meta">
          <div className="note-tags-chips">
            {note.tags.map(t => <span key={t} className="note-chip">#{t}</span>)}
          </div>
          <span>{bodyContent.split(/\s+/).filter(Boolean).length} words</span>
        </div>
      </div>

      <div className="note-body-layout">
        {isEditMode ? (
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <NoteEditor
              initialContent={bodyContent}
              initialFrontmatter={note.frontmatter || {}}
              onSave={handleSave}
              onCancel={() => setIsEditMode(false)}
            />
          </div>
        ) : (
          <div className="note-main-content">
            {Object.keys(note.frontmatter || {}).length > 0 && (
              <div className="properties-panel">
                <details open={showProperties} onToggle={e => setShowProperties((e.target as HTMLDetailsElement).open)}>
                  <summary className="properties-summary">Properties</summary>
                  <div className="properties-content">
                    <pre>{JSON.stringify(note.frontmatter, null, 2)}</pre>
                  </div>
                </details>
              </div>
            )}
            <div className="note-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                // eslint-disable-next-line @typescript-eslint/no-unused-vars
                a: ({ node, href, children, ...props }) => {
                  if (href === '#broken-link') {
                    return <span className="broken-link" title="This note doesn't exist yet">{children}</span>;
                  }
                  if (href && href.startsWith('/vault?tag=')) {
                    return <a href={href} className="note-chip tag-chip" onClick={e => { e.preventDefault(); router.push(href); }}>{children}</a>;
                  }
                  if (href && href.startsWith('/vault/note')) {
                    return <a {...props} href={href} className="wiki-link" onClick={e => {
                      e.preventDefault();
                      router.push(href);
                    }}>{children}</a>;
                  }
                  return <a {...props} href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
                }
              }}>
                {displayContent}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {!isEditMode && (
          <div className="note-sidebar">
            <div className="backlinks-section">
              <h3>Backlinks</h3>
              {backlinks.length > 0 ? (
                backlinks.map((bl, i) => (
                  <div key={i} className="backlink-item" onClick={() => router.push(`/vault/note?path=${encodeURIComponent(bl.source)}`)}>
                    <div className="backlink-title">{bl.source.replace('.md', '').split('/').pop()}</div>
                    <div className="backlink-context">
                      {(() => {
                        const idx = bl.link_text ? bl.context.indexOf(bl.link_text) : -1;
                        if (idx < 0) return bl.context;
                        return (
                          <>
                            {bl.context.slice(0, idx)}
                            <span className="highlight-link">{bl.link_text}</span>
                            {bl.context.slice(idx + bl.link_text.length)}
                          </>
                        );
                      })()}
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty-state" style={{fontSize: '0.9rem'}}>No backlinks found.</div>
              )}
            </div>

            <div className="backlinks-section" style={{ marginTop: '2rem' }}>
              <h3>Outgoing Links</h3>
              {note.links.length > 0 ? (
                note.links.map((lk, i) => {
                  const resolvedPath = resolveLink(lk.target);
                  return (
                    <div key={i} className="backlink-item" onClick={() => resolvedPath && router.push(`/vault/note?path=${encodeURIComponent(resolvedPath)}`)}>
                      <div className="backlink-title" style={!resolvedPath ? {color: '#e74c3c'} : {}}>
                        {lk.display_text || lk.target} {!resolvedPath && '(Broken)'}
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="empty-state" style={{fontSize: '0.9rem'}}>No outgoing links.</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function NotePage() {
  return (
    <Suspense fallback={<div className="note-page" style={{padding: '2rem'}}>Loading...</div>}>
      <NotePageContent />
    </Suspense>
  );
}
