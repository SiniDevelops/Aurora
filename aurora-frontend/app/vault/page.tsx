'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import SearchBar from '@/components/vault/SearchBar';
import '@/styles/vault.css';

interface VaultNote {
  path: string;
  title: string;
  tags: string[];
  word_count: number;
}

interface TreeNode {
  [key: string]: TreeNode | 'file';
}

interface SearchResult {
  path: string;
  title: string;
  preview: string;
  tags: string[];
}

export default function VaultPage() {
  const router = useRouter();
  const [notes, setNotes] = useState<VaultNote[]>([]);
  const [tree, setTree] = useState<TreeNode>({});
  const [allTags, setAllTags] = useState<Record<string, number>>({});
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<{ tag?: string; folder?: string; sort?: string }>({ sort: 'title' });
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);

  useEffect(() => {
    Promise.all([
      fetch('http://localhost:8000/api/vault/notes').then(r => r.ok ? r.json() : Promise.reject('Failed to load notes')),
      fetch('http://localhost:8000/api/vault/tree').then(r => r.ok ? r.json() : Promise.reject('Failed to load tree')),
      fetch('http://localhost:8000/api/vault/tags').then(r => r.ok ? r.json() : Promise.reject('Failed to load tags')),
    ])
      .then(([notesData, treeData, tagsData]) => {
        setNotes(notesData);
        setTree(treeData.tree || {});
        setAllTags(tagsData || {});
        setLoading(false);
      })
      .catch(err => { setError(String(err)); setLoading(false); });
  }, []);

  useEffect(() => {
    if (!loading && !error) {
      if (query.trim()) {
        fetch('http://localhost:8000/api/vault/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, limit: 50 })
        })
          .then(r => r.json())
          .then(data => {
            setSearchResults(data.results);
          })
          .catch(console.error);
      } else {
        setSearchResults(null);
      }
    }
  }, [query, loading, error]);

  const handleSearch = (newQuery: string, newFilters: { tag?: string; folder?: string; sort?: string }) => {
    setQuery(newQuery);
    setFilters(newFilters);
  };

  const getTopLevelFolders = (node: TreeNode) => {
    return Object.keys(node).filter(k => node[k] !== 'file');
  };

  const handleNewNote = async () => {
    const title = prompt('Enter new note title:');
    if (!title) return;
    try {
      const today = new Date().toISOString().split('T')[0];
      const res = await fetch('http://localhost:8000/api/vault/note', {
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
        const fullPath = notes.find(n => n.path.endsWith(key))?.path || key;
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

  let displayedNotes = searchResults ? searchResults.map(r => ({
    ...r,
    word_count: notes.find(n => n.path === r.path)?.word_count || 0
  })) : notes.map(n => ({
    ...n,
    preview: ''
  }));

  if (filters.tag) {
    displayedNotes = displayedNotes.filter(n => n.tags.includes(filters.tag!));
  }
  if (filters.folder) {
    displayedNotes = displayedNotes.filter(n => n.path.startsWith(filters.folder! + '/'));
  }

  if (filters.sort === 'word_count') {
    displayedNotes.sort((a, b) => b.word_count - a.word_count);
  } else {
    displayedNotes.sort((a, b) => a.title.localeCompare(b.title));
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
        <SearchBar
          onSearch={handleSearch}
          tags={allTags}
          folders={getTopLevelFolders(tree)}
        />
        <div style={{ marginTop: '1rem' }}>
          {displayedNotes.length > 0 ? (
            displayedNotes.map(n => (
              <div key={n.path} className="search-result-card" onClick={() => router.push(`/vault/note?path=${encodeURIComponent(n.path)}`)}>
                <div className="search-result-header">
                  <span className="search-result-title">{n.title}</span>
                  <span className="search-result-folder">{n.path.split('/').slice(0, -1).join('/')}</span>
                </div>
                {n.preview && <div className="search-result-preview">{n.preview}...</div>}
                {n.tags && n.tags.length > 0 && (
                  <div className="file-tags">
                    {n.tags.map(t => <span key={t} className="tag-badge">#{t}</span>)}
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="empty-state">No matching notes found.</div>
          )}
        </div>
      </div>
    </div>
  );
}
