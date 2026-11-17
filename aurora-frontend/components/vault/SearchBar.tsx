'use client';
import { useState, useEffect } from 'react';

interface SearchBarProps {
  onSearch: (query: string, filters: { tag?: string; folder?: string; sort?: string }) => void;
  tags: Record<string, number>;
  folders: string[];
}

export default function SearchBar({ onSearch, tags, folders }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [tag, setTag] = useState('');
  const [folder, setFolder] = useState('');
  const [sort, setSort] = useState('title');

  useEffect(() => {
    const handler = setTimeout(() => {
      onSearch(query, { tag, folder, sort });
    }, 300);
    return () => clearTimeout(handler);
  }, [query, tag, folder, sort, onSearch]);

  return (
    <div className="search-bar-container">
      <input
        type="text"
        className="search-input"
        placeholder="Search vault..."
        value={query}
        onChange={e => setQuery(e.target.value)}
      />
      <div className="search-filters">
        <select value={tag} onChange={e => setTag(e.target.value)}>
          <option value="">All Tags</option>
          {Object.keys(tags).map(t => (
            <option key={t} value={t}>{t} ({tags[t]})</option>
          ))}
        </select>
        <select value={folder} onChange={e => setFolder(e.target.value)}>
          <option value="">All Folders</option>
          {folders.map(f => (
            <option key={f} value={f}>{f}</option>
          ))}
        </select>
        <select value={sort} onChange={e => setSort(e.target.value)}>
          <option value="title">Sort by Title</option>
          <option value="word_count">Sort by Word Count</option>
        </select>
      </div>
    </div>
  );
}
