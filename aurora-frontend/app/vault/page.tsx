'use client';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import SearchBar, { SearchFilters } from '@/components/vault/SearchBar';
import '@/styles/vault.css';

const API = 'http://localhost:8000/api/vault';

interface VaultNote {
  path: string;
  title: string;
  tags: string[];
  word_count: number;
  folder?: string;
  created_at?: string;
  modified_at?: string;
}

interface TreeNode {
  [key: string]: TreeNode | 'file';
}

interface SectionHit {
  heading: string;
  snippet: string;
  score: number;
}

interface SearchResult extends VaultNote {
  preview: string;
  sections?: SectionHit[];
}

function collectFolders(node: TreeNode, prefix = ''): string[] {
  const out: string[] = [];
  for (const [key, value] of Object.entries(node)) {
    if (value === 'file') continue;
    const path = prefix ? `${prefix}/${key}` : key;
    out.push(path, ...collectFolders(value as TreeNode, path));
  }
  return out;
}

function formatDate(iso?: string) {
  if (!iso) return '';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? '' : d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

function highlight(text: string, query: string) {
  const terms = query.trim().split(/\s+/).filter(t => t.length > 1)
    .map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  if (!terms.length) return text;
  const re = new RegExp(`(${terms.join('|')})`, 'gi');
  return text.split(re).map((part, i) =>
    i % 2 === 1 ? <mark key={i} className="search-highlight">{part}</mark> : part
  );
}

export default function VaultPage() {
  const router = useRouter();
  const [notes, setNotes] = useState<VaultNote[]>([]);
  const [tree, setTree] = useState<TreeNode>({});
  const [allTags, setAllTags] = useState<Record<string, number>>({});

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<SearchFilters>({ sort: 'relevance' });
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searchTotal, setSearchTotal] = useState(0);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/notes`).then(r => r.ok ? r.json() : Promise.reject('Failed to load notes')),
      fetch(`${API}/tree`).then(r => r.ok ? r.json() : Promise.reject('Failed to load tree')),
      fetch(`${API}/tags`).then(r => r.ok ? r.json() : Promise.reject('Failed to load tags')),
    ])
      .then(([notesData, treeData, tagsData]) => {
        setNotes(notesData);
        setTree(treeData.tree || {});
        setAllTags(tagsData || {});
        setLoading(false);
      })
      .catch(err => { setError(String(err)); setLoading(false); });
  }, []);

  const hasServerFilters = Boolean(query.trim() || filters.tag || filters.folder || filters.dateFrom || filters.dateTo);

  useEffect(() => {
    if (loading || error) return;
    if (!hasServerFilters) {
      setSearchResults(null);
      return;
    }
    const controller = new AbortController();
    setSearching(true);
    fetch(`${API}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        query,
        limit: 200,
        tags: filters.tag ? [filters.tag] : null,
        folder: filters.folder || null,
        date_from: filters.dateFrom || null,
        date_to: filters.dateTo || null,
        date_field: filters.dateField || 'modified',
        include_sections: true,
      }),
    })
      .then(r => r.ok ? r.json() : r.json().then(d => Promise.reject(d.detail || 'Search failed')))
      .then(data => {
        setSearchResults(data.results || []);
        setSearchTotal(data.total ?? (data.results || []).length);
        setSearching(false);
      })
      .catch(err => {
        if (err?.name === 'AbortError') return;
        console.error(err);
        setSearching(false);
      });
    return () => controller.abort();
  }, [query, filters.tag, filters.folder, filters.dateFrom, filters.dateTo, filters.dateField, hasServerFilters, loading, error]);

  // Stable callback so SearchBar's debounce effect doesn't re-fire on every render
  const handleSearch = useCallback((newQuery: string, newFilters: SearchFilters) => {
    setQuery(newQuery);
    setFilters(prev => JSON.stringify(prev) === JSON.stringify(newFilters) ? prev : newFilters);
  }, []);

  const allFolders = useMemo(() => collectFolders(tree).sort(), [tree]);

  const handleNewNote = async () => {
    const title = prompt('Enter new note title:');
    if (!title) return;
    try {
      const today = new Date().toISOString().split('T')[0];
      const res = await fetch(`${API}/note`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: `Inbox/${title}.md`,
          content: `# ${title}\n\n`,
          frontmatter: { title, tags: [], date: today }
        })
      });
      if (!res.ok) throw new Error('Failed to create note');
      const data = await res.json();
      router.push(`/vault/note?path=${encodeURIComponent(data.path)}&edit=1`);
    } catch (e) {
      alert(String(e));
    }
  };

  const renderTree = (node: TreeNode, currentPath = '', depth = 0) => {
    return Object.entries(node).map(([key, value]) => {
      if (value === 'file') {
        const fullPath = notes.find(n => n.path === currentPath + key)?.path
          || notes.find(n => n.path.endsWith(key))?.path || currentPath + key;
        return (
          <div
            key={currentPath + key}
            className="file"
            style={{ paddingLeft: `${(depth + 1) * 16}px` }}
            onClick={() => router.push(`/vault/note?path=${encodeURIComponent(fullPath)}`)}
          >
            📄 {key.replace('.md', '')}
          </div>
        );
      }
      return (
        <div key={currentPath + key} className="folder">
          <span className="folder-name" style={{ paddingLeft: `${depth * 16}px` }}>
            📁 {key}
          </span>
          <div className="folder-content">
            {renderTree(value as TreeNode, currentPath + key + '/', depth + 1)}
          </div>
        </div>
      );
    });
  };

  if (loading) return <div className="vault-container"><p style={{ padding: '2rem' }}>Loading vault...</p></div>;
  if (error) return <div className="vault-container"><p style={{ padding: '2rem', color: '#e74c3c' }}>Error: {error}</p></div>;

  const displayedNotes: SearchResult[] = searchResults
    ? [...searchResults]
    : notes.map(n => ({ ...n, preview: '' }));

  const byDate = (field: 'created_at' | 'modified_at') => (a: SearchResult, b: SearchResult) =>
    (b[field] || '').localeCompare(a[field] || '');

  switch (filters.sort) {
    case 'word_count': displayedNotes.sort((a, b) => b.word_count - a.word_count); break;
    case 'modified': displayedNotes.sort(byDate('modified_at')); break;
    case 'created': displayedNotes.sort(byDate('created_at')); break;
    case 'title': displayedNotes.sort((a, b) => a.title.localeCompare(b.title)); break;
    default:
      // relevance: keep server order for searches; alphabetical when browsing
      if (!searchResults) displayedNotes.sort((a, b) => a.title.localeCompare(b.title));
  }

  return (
    <div className="vault-container">
      <div className="vault-sidebar">
        <div className="vault-actions">
          <button className="btn-primary" style={{ width: '100%' }} onClick={handleNewNote}>
            + New note
          </button>
        </div>
        <div className="vault-stats">
          <span>{notes.length} notes</span>
        </div>
        <div className="file-tree">
          {renderTree(tree)}
        </div>
      </div>
      <div className="results-area">
        <SearchBar onSearch={handleSearch} tags={allTags} folders={allFolders} />
        <div className="search-summary">
          {searching ? 'Searching…'
            : searchResults ? `${searchTotal} matching note${searchTotal === 1 ? '' : 's'}`
            : `${notes.length} notes`}
        </div>
        <div>
          {displayedNotes.length > 0 ? (
            displayedNotes.map(n => (
              <div key={n.path} className="search-result-card" onClick={() => router.push(`/vault/note?path=${encodeURIComponent(n.path)}`)}>
                <div className="search-result-header">
                  <span className="search-result-title">{highlight(n.title, query)}</span>
                  <span className="search-result-folder">{n.path.split('/').slice(0, -1).join('/')}</span>
                </div>
                {n.preview && !(n.sections && n.sections.length) && (
                  <div className="search-result-preview">{highlight(n.preview, query)}</div>
                )}
                {n.sections && n.sections.length > 0 && (
                  <div className="search-result-sections">
                    {n.sections.map((s, i) => (
                      <div key={i} className="search-section-hit">
                        <div className="search-section-heading">§ {s.heading}</div>
                        <div className="search-section-snippet">{highlight(s.snippet, query)}</div>
                      </div>
                    ))}
                  </div>
                )}
                <div className="search-result-meta">
                  {n.tags && n.tags.length > 0 && (
                    <div className="file-tags">
                      {n.tags.map(t => <span key={t} className="tag-badge">#{t}</span>)}
                    </div>
                  )}
                  <span className="search-result-date">
                    {n.word_count ? `${n.word_count} words` : ''}
                    {n.modified_at ? ` · modified ${formatDate(n.modified_at)}` : ''}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <div className="empty-state">{searching ? '' : 'No matching notes found.'}</div>
          )}
        </div>
      </div>
    </div>
  );
}
