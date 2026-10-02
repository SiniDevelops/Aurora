'use client';
import { useState, useEffect } from 'react';
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

export default function VaultPage() {
  const [notes, setNotes] = useState<VaultNote[]>([]);
  const [tree, setTree] = useState<TreeNode>({});
  const [activeNote, setActiveNote] = useState<{ path: string; title: string; content: string; tags: string[]; frontmatter: Record<string, unknown> } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      fetch('http://localhost:8000/api/vault/notes').then(r => r.ok ? r.json() : Promise.reject('Failed to load notes')),
      fetch('http://localhost:8000/api/vault/tree').then(r => r.ok ? r.json() : Promise.reject('Failed to load tree')),
    ])
      .then(([notesData, treeData]) => {
        setNotes(notesData);
        setTree(treeData.tree || {});
        setLoading(false);
      })
      .catch(err => { setError(String(err)); setLoading(false); });
  }, []);

  const loadNote = (path: string) => {
    fetch(`http://localhost:8000/api/vault/note/${encodeURIComponent(path)}`)
      .then(res => {
        if (!res.ok) throw new Error(`${res.status}`);
        return res.json();
      })
      .then(data => setActiveNote(data))
      .catch(() => setActiveNote({ path, title: path, content: 'Failed to load note.', tags: [], frontmatter: {} }));
  };

  const filteredNotes = searchQuery
    ? notes.filter(n =>
        n.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        n.tags.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : null;

  const renderTree = (node: TreeNode, depth = 0) => {
    return Object.entries(node).map(([key, value]) => {
      if (value === 'file') {
        return (
          <div
            key={key}
            className={`file ${activeNote?.path?.endsWith(key) ? 'active' : ''}`}
            style={{ paddingLeft: `${(depth + 1) * 16}px` }}
            onClick={() => {
              // Find the full path for this file
              const note = notes.find(n => n.path.endsWith(key));
              if (note) loadNote(note.path);
            }}
          >
            📄 {key.replace('.md', '')}
          </div>
        );
      }
      return (
        <div key={key} className="folder">
          <span className="folder-name" style={{ paddingLeft: `${depth * 16}px` }}>
            📁 {key}
          </span>
          <div className="folder-content">
            {renderTree(value as TreeNode, depth + 1)}
          </div>
        </div>
      );
    });
  };

  if (loading) return <div className="vault-container"><p style={{ padding: '2rem' }}>Loading vault...</p></div>;
  if (error) return <div className="vault-container"><p style={{ padding: '2rem', color: '#e74c3c' }}>Error: {error}</p></div>;

  return (
    <div className="vault-container">
      <div className="vault-sidebar">
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search notes..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="vault-stats">
          <span>{notes.length} notes</span>
        </div>
        <div className="file-tree">
          {searchQuery && filteredNotes ? (
            filteredNotes.length > 0 ? (
              filteredNotes.map(n => (
                <div
                  key={n.path}
                  className={`file ${activeNote?.path === n.path ? 'active' : ''}`}
                  onClick={() => loadNote(n.path)}
                >
                  📄 {n.title}
                  {n.tags.length > 0 && (
                    <div className="file-tags">
                      {n.tags.slice(0, 3).map(t => <span key={t} className="tag-badge">#{t}</span>)}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <p style={{ padding: '1rem', opacity: 0.5 }}>No notes match &quot;{searchQuery}&quot;</p>
            )
          ) : (
            renderTree(tree)
          )}
        </div>
      </div>
      <div className="note-preview">
        {activeNote ? (
          <div className="note-content">
            <h1>{activeNote.title}</h1>
            {activeNote.tags && activeNote.tags.length > 0 && (
              <div className="note-tags">
                {activeNote.tags.map(t => <span key={t} className="tag-badge">#{t}</span>)}
              </div>
            )}
            <hr />
            <pre className="note-body">{activeNote.content}</pre>
          </div>
        ) : (
          <div className="empty-state">Select a note to preview</div>
        )}
      </div>
    </div>
  );
}
